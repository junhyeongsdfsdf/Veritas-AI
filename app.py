import random
from typing import List, Dict

from veritas_dynamic_question_engine import (
    build_brain_like_questions,
    generate_weakness_report,
)

# ======================================
# 1) OPEN-WORLD DIAGNOSTIC REASONING DB
# ======================================
# 특정 입력 단어를 반복하지 않고, 사용자의 '이해 상태'를 여러 각도에서 검증
QUESTION_LENSES = {
    "understanding": [
        "지금 설명한 내용을 다른 사람에게 예시 없이 다시 설명할 수 있나요?",
        "핵심 의미와 주변 정보를 구분해서 말할 수 있나요?",
        "왜 그렇게 되는지 이유를 스스로 설명할 수 있나요?",
    ],
    "structure": [
        "구성 요소가 어떤 순서로 연결되는지 알고 있나요?",
        "부분들이 서로 어떤 관계를 가지는지 설명할 수 있나요?",
        "중간 단계가 빠졌을 때 어디가 비는지 찾을 수 있나요?",
    ],
    "application": [
        "비슷하지만 처음 보는 상황에도 적용할 수 있나요?",
        "조건이 조금 바뀌어도 같은 원리로 해결할 수 있나요?",
        "실전 문제에서 바로 써먹을 수 있나요?",
    ],
    "comparison": [
        "헷갈리기 쉬운 다른 개념과 차이를 설명할 수 있나요?",
        "비슷한 실수와 현재 문제를 구분할 수 있나요?",
        "같은 유형의 다른 사례와 비교해도 흔들리지 않나요?",
    ],
    "recovery": [
        "막혔을 때 어디부터 다시 점검해야 하는지 알고 있나요?",
        "스스로 복습 순서를 정해서 다시 해결할 수 있나요?",
        "다음에 같은 실수를 예방할 기준이 있나요?",
    ],
}


# ======================================
# 2) INPUT SIGNAL ANALYZER
# ======================================
def infer_signals(user_input: str) -> Dict[str, float]:
    """
    사용자가 무엇을 넣을지 모르므로 주제를 직접 반복하지 않고
    입력의 '인지적 난이도 신호'를 추론한다.
    """
    text = user_input.strip()
    tokens = len(text.split())

    signals = {
        "ambiguity": 0.2,
        "complexity": 0.2,
        "transfer_risk": 0.2,
        "memory_gap": 0.2,
        "execution_gap": 0.2,
    }

    if tokens <= 3:
        signals["ambiguity"] += 0.4
    if any(x in text for x in ["왜", "어떻게", "안됨", "error", "bug"]):
        signals["execution_gap"] += 0.4
    if any(x in text for x in ["비교", "차이", "구분"]):
        signals["transfer_risk"] += 0.4
    if len(text) >= 40:
        signals["complexity"] += 0.3

    return signals


# ======================================
# 3) TRUE DYNAMIC 5 QUESTION GENERATOR
# ======================================
def build_brain_like_questions(user_input: str) -> List[str]:
    """
    입력을 그대로 따라하지 않고, 매번 다른 사고 렌즈를 선택.
    질문 5개가 항상 다른 목적을 가지도록 보장.
    """
    signals = infer_signals(user_input)

    # 신호 기반 우선순위 렌즈 선택
    ordered_lenses = [
        "understanding",
        "structure",
        "application",
        "comparison",
        "recovery",
    ]

    # 입력이 짧고 모호하면 구조/이해 먼저
    if signals["ambiguity"] > 0.5:
        ordered_lenses = [
            "understanding",
            "structure",
            "comparison",
            "application",
            "recovery",
        ]

    # 에러/버그/실전 문제는 recovery 먼저
    if signals["execution_gap"] > 0.5:
        ordered_lenses = [
            "recovery",
            "structure",
            "application",
            "comparison",
            "understanding",
        ]

    questions = []
    for idx, lens in enumerate(ordered_lenses[:5], 1):
        candidate = random.choice(QUESTION_LENSES[lens])
        questions.append(f"{idx}. {candidate}")

    return questions


# ======================================
# 4) WEAK-POINT REPORT ENGINE
# ======================================
def generate_weakness_report(user_input: str, responses: List[Dict]) -> str:
    no_answers = [r for r in responses if r["answer"] == "No"]

    if not no_answers:
        return "기초 이해와 적용력이 안정적입니다. 다음 단계 심화 학습으로 넘어가도 좋습니다."

    categories = []
    for r in no_answers:
        q = r["question"]
        if "이유" in q or "핵심" in q:
            categories.append("핵심 개념 이해")
        elif "순서" in q or "관계" in q:
            categories.append("구조적 연결")
        elif "적용" in q or "실전" in q:
            categories.append("응용 전이")
        elif "차이" in q or "구분" in q:
            categories.append("유사 개념 비교")
        else:
            categories.append("복구 전략")

    unique = list(dict.fromkeys(categories))

    report = [
        "1. 현재 부족한 파트",
        "- " + "\n- ".join(unique),
        "",
        "2. 왜 여기서 막히는가",
        "- 개념을 아는 것과 실제 재구성하는 능력 사이에 간격이 있습니다.",
        "- 입력은 이해했지만 새로운 상황으로 전이되는 과정이 약합니다.",
        "",
        "3. 추천 복습 순서",
        "- 핵심 의미 → 구조 관계 → 새로운 예시 적용 → 유사 개념 비교 → 스스로 설명",
    ]

    return "\n".join(report)
