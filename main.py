import streamlit as st
from app.graph import app_graph

st.set_page_config(page_title="사회 시뮬레이션", layout="wide")

st.title("대규모 사회 시뮬레이션 (Generative Agents)")
st.markdown("자율적인 에이전트들이 고유한 페르소나와 기억을 바탕으로 이동하고, 같은 공간에서 서로 마주치면 실시간으로 대화와 관계를 형성합니다.")
st.divider()

# 초기 세계관 및 에이전트 상태 구성
if "world_state" not in st.session_state:
    st.session_state.world_state = {
        "time": 8,
        "agents": {
            "김개발": {
                "persona": "IT 회사의 3년 차 백엔드 개발자. 커피를 좋아하며 낯을 가리지만 기술 이야기는 좋아한다.",
                "location": "집",
                "action": "기상하여 씻고 출근 준비를 한다.",
                "memory": ["어제 늦게까지 야근해서 매우 피곤하다."]
            },
            "이마케터": {
                "persona": "스타트업의 마케팅 팀장. 활달하고 사람 만나는 것을 즐긴다. 새로운 트렌드에 민감하다.",
                "location": "집",
                "action": "요가를 하며 아침을 시작한다.",
                "memory": ["어제 새로 기획한 캠페인 반응이 좋아서 기분이 좋다."]
            },
            "박바리스타": {
                "persona": "동네 유명 카페의 사장 겸 바리스타. 동네 사람들의 소식을 듣는 것을 좋아한다.",
                "location": "카페",
                "action": "카페 문을 열고 에스프레소 머신을 예열한다.",
                "memory": ["최근 새로 들여온 원두의 향이 아주 마음에 든다."]
            }
        },
        "global_log": ["[8시] 시뮬레이션이 시작되었습니다. 모든 에이전트가 각자의 하루를 준비합니다."]
    }

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader(f"현재 시각: {st.session_state.world_state['time']}시")
    
    if st.button("다음 시간(Tick)으로 진행", use_container_width=True):
        with st.spinner("세계가 진행 중입니다. 에이전트들이 이동하고 상호작용합니다..."):
            
            for output in app_graph.stream(st.session_state.world_state):
                # 방어 로직 (Null Check)
                if not output:
                    continue

                for node_name, state_update in output.items():
                    if not state_update:
                        continue

                    # 상태 업데이트
                    for k, v in state_update.items():
                        st.session_state.world_state[k] = v
        
        st.rerun()
    
    st.divider()
    st.subheader("에이전트 상세 상태")
    for name, data in st.session_state.world_state["agents"].items():
        with st.expander(f"[{name}] 위치: {data['location']}"):
            st.markdown(f"**현재 행동:** {data['action']}")
            st.markdown(f"**기억 목록:**")
            for mem in data['memory']:
                st.markdown(f"- {mem}")

with col2:
    st.subheader("세계 통합 관제 로그")
    
    with st.container(border=True, height=600):
        # 최신 로그가 위로 오도록 역순으로 출력
        logs = st.session_state.world_state.get("global_log", [])
        for log in reversed(logs):
            st.markdown(log)
            st.divider()