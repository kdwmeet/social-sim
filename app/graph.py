from typing import TypedDict, List, Dict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

load_dotenv()

# Pydantic 스키마 정의
class AgentAction(BaseModel):
    name: str = Field(description="에이전트 이름")
    location: str = Field(description="이동할 장소 (예: 집, 카페, 회사, 공원 중 택 1)")
    action: str = Field(description="해당 장소에서 수행할 행동 묘사")

class WorldPlan(BaseModel):
    agent_actions: List[AgentAction] = Field(description="모든 에이전트의 이번 시간대 행동 계획")

class Conversation(BaseModel):
    participants: List[str] = Field(description="대화에 참여한 에이전트 이름 목록")
    dialogue_log: str = Field(description="상황에 맞는 자연스러운 대화 기록")

class InteractionResult(BaseModel):
    Conversations: List[Conversation] = Field(description="발생한 모든 대화 목록. 대화가 없다면 빈 리스트 반환")

# 상태 정의
class WorldState(TypedDict):
    time: int                       # 현재 시간
    agents: Dict[str, dict]         # 에이전트 상태 {이름: {persona, location, action, memory}}
    global_log: List[str]           # 월드 전체 이벤트 로그

# 노드 구현
def planning_node(state: WorldState):
    """현재 시간과 에이전트들의 기억을 바탕으로 각자의 다음 위치와 행동을 결정합니다."""
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0.7)
    structured_llm = llm.with_structured_output(WorldPlan)

    current_time = state.get("time", 8)
    agents = state.get("agents", {})

    # 에이전트 상태 문자열 구성
    agent_context = ""
    for name, data in agents.items():
        agent_context += f"이름: {name}\n성격 및 직업:{data.get('persona', '')}\n기억: {data.get('memory')}\n현재 위치:{data.get('location', '')}\n\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 가상 세계의 시뮬레이터입니다. 현재 시간과 각 에이전트의 성격, 과거 기억을 바탕으로 이번 시간에 에이전트들이 어디로 이동하여 무엇을 할지 결정하십시오. 장소는 집, 카페, 회사, 공원 중에서만 선택하십시오."),
        ("user", "현재 시간: {time}시\n\n[에이전트 정보]\n{agent_context}")
    ])

    result: WorldPlan = (prompt | structured_llm).invoke({
        "time": current_time,
        "agent_context": agent_context
    })

    # 상태 업데이트용 딕셔너리 구성
    updated_agents = dict(agents)
    new_logs = state.get("global_log", [])

    for action_plan in result.agent_actions:
        name = action_plan.name
        if name in updated_agents:
            updated_agents[name]["location"] = action_plan.location
            updated_agents[name]["action"] = action_plan.action
            log_entry = f"[{current_time}시 {name}은(는) {action_plan.location}에서 {action_plan.action}을(를) 시작했습니다.]"
            new_logs.append(log_entry)

    return {"agents": updated_agents, "global_log": new_logs}

def interaction_node(state: WorldState):
    """동일한 장소에 있는 에이전트들을 파악하고, 상호작용(대화)을 발생시킵니다."""
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0.8)
    structured_llm = llm.with_structured_output(InteractionResult)

    current_time = state.get("time", 8)
    agents = state.get("agents", {})

    # 장소별 에이전트 그룹화
    location_map = {}
    for name, data in agents.items():
        loc = data.get("location", "")
        if loc not in location_map:
            location_map[loc] = []
        location_map[loc].append({"name": name, "action": data.get("action", ""), "persona": data.get("persona", "")})

    # 2명 이상 모인 장소 파악
    interaction_context = ""
    for loc, people in location_map.items():
        if len(people) >= 2:
            names = [p["name"] for p in people]
            interaction_context += f"장소: {loc}\n모인 사람: {', '.join(names)}\n각자 행동: {[p['action'] for p in people]}\n\n"

    new_logs = state.get("global_log", [])
    updated_agents = dict(agents)

    # 만난 사람이 있다면 대화 생성
    if interaction_context:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "당신은 가상 세계의 스토리텔러입니다. 같은 장소에 모인 에이전트들이 각자의 행동과 성격을 바탕으로 나눌 법한 대화를 창작하십시오. 각자의 과거 기억이 대화에 반영되면 좋습니다."),
            ("user", "현재 시간: {time}시\n\n[상호작용 가능한 그룹]\n{context}")
        ])

        result: InteractionResult = (prompt | structured_llm).invoke({
            "time": current_time,
            "context": interaction_context
        })

        # 대화 결과를 글로벌 로그 및 각 에이전트의 기억에 저장
        for conv in result.Conversations:
            dialogue = f"[{current_time}시 대화 발생] 참여자: {', '.join(conv.participants)}\n{conv.dialogue_log}"
            new_logs.append(dialogue)

            for participant in conv.participants:
                if participant in updated_agents:
                    memory_entry = f"{current_time}시에 나눈 대화: {conv.dialogue_log}"
                    updated_agents[participant]["memory"].append(memory_entry)
            
    # 시간을 1시간 증가시킴
    return {"agents": updated_agents, "global_log": new_logs, "time": current_time + 1}

# 그래프 조립
workflow = StateGraph(WorldState)

workflow.add_node("planning", planning_node)
workflow.add_node("interaction", interaction_node)

# 계획(이동) -> 상호작용(대화) 순서로 1 Tick 완성
workflow.add_edge(START, "planning")
workflow.add_edge("planning", "interaction")
workflow.add_edge("interaction", END)

app_graph = workflow.compile()