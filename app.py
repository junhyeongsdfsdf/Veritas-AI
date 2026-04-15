import random
from typing import List, Dict
import streamlit as st

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="Veritas AI | Smart Diagnostic",
    page_icon="🔍",
    layout="centered",
)

st.markdown("""
<style>
.stApp { background-color: #0d1117; color: #c9d1d9; }
.main-title {
    color: #58a6ff;
    font-size: 2.7rem;
    font-weight: 800;
    text-align: center;
    margin-bottom: 1rem;
}
.diag-card {
    padding: 1rem;
    border: 1px solid #30363d;
    border-radius: 12px;
    margin-bottom: 1rem;
    background: #161b22;
}
</style>
""", unsafe_allow_html=True)

# =============================
# QUESTION ENGINE
# =============================
QUESTION_LENSES = {
    "understanding": [
        "지금 떠올린 내용을 다른 사람에게 다시 설명할 수 있나요?",
        "핵심 의미와 주변 정보를 구분해서 말할 수 있나요?",
    ],
    "structure": [
        "구성 요소가 어떤 순서로 연결되는지 알고 있나요?",
        "중간 단계가 빠졌을 때 어디가 비는지 찾을 수 있나요?",
    ],
    "application": [
        "처음 보는 상황에도 같은 방식으로 적용할 수 있나요?",
        "실전 문제에 바로 활용할 수 있나요?",
    ],
    "comparison": [
        "비슷한 개념과의 차이를 설명할 수 있나요?",
        "유사한 실수와 현재 문제를 구분할 수 있나요?",
    ],
    "recovery": [
        "막혔을 때 어디부터 다시 점검해야 할지 알고 있나요?",
        "다음에 같은 실수를 예방할 수 있나요?",
    ],
}


def build_brain_like_questions(user_input: str) -> List[str]:
    """
    사용자의 입력을 그대로 반복하지 않고
    항상 다른 사고 단계에서 5가지 Yes/No 질문 생성
    """
    ordered_lenses = [
        "understanding",
        "structure",
        "application",
        "comparison",
        "recovery",
    ]

    questions = []
    for i, lens in enumerate(ordered_lenses, 1):
        q = random.choice(QUESTION_LENSES[lens])
        questions.append(f"{i}. {q}")

    return questions


def generate_weakness_report(user_input: str, responses: List[Dict]) -> str:
    """
    No 응답 기반으로 부족한 학습 파트를 자동 진단
    """
    weak_points = [r for r in responses if r["answer"] == "No"]

    if not weak_points:
        return """
### ✅ 진단 결과
기초 이해와 적용력이 안정적입니다.

### 🚀 다음 추천
- 심화 문제 적용
- 새로운 예시 확장
- 다른 사람에게 설명해보기
""".strip()

    weak_parts = []

    for r in weak_points:
        q = r["question"]

        if "차이" in q or "구분" in q:
            weak_parts.append("유사 개념 비교 능력")
        elif "적용" in q or "실전" in q:
            weak_parts.append("응용 전이 능력")
        elif "순서" in q or "구성" in q:
            weak_parts.append("구조적 연결 능력")
        elif "점검" in q or "예방" in q:
            weak_parts.append("복구 및 예방 전략")
        else:
            weak_parts.append("핵심 개념 이해")

    weak_parts = list(dict.fromkeys(weak_parts))

    return f"""
### 📌 현재 부족한 파트
{chr(10).join([f"- {x}" for x in weak_parts])}

### 🔍 왜 여기서 막히는가
- 이해한 내용을 새로운 상황으로 옮기는 힘이 약합니다.
- 구조를 부분적으로 이해하고 있어 연결 과정에서 흔들립니다.

### 📚 추천 복습 순서
- 핵심 의미 정리
- 단계별 구조 연결
- 새로운 예시 적용
- 유사 개념 비교
- 스스로 설명하기
""".strip()


# =============================
# SESSION STATE
# =============================
if "stage" not in st.session_state:
    st.session_state.stage = "ready"

if "data" not in st.session_state:
    st.session_state.data = {}

# =============================
# READY
# =============================
if st.session_state.stage == "ready":
    st.markdown("<div class='main-title'>Veritas AI</div>", unsafe_allow_html=True)
    st.caption("by Jun")

    topic = st.text_input(
        "학습 중 막힌 부분을 자유롭게 입력하세요",
        placeholder="예: 재귀함수, 영어 문장, 발표 구조, SQL 오류..."
    )

    if st.button("빠른 진단 시작"):
        if topic.strip():
            questions = build_brain_like_questions(topic)

            st.session_state.data["topic"] = topic
            st.session_state.data["questions"] = questions
            st.session_state.stage = "testing"
            st.rerun()

# =============================
# TESTING
# =============================
elif st.session_state.stage == "testing":
    st.subheader(f"📘 진단 주제: {st.session_state.data['topic']}")

    with st.form("diagnosis_form"):
        responses = []

        for i, q in enumerate(st.session_state.data["questions"]):
            st.markdown(f"<div class='diag-card'><b>{q}</b></div>", unsafe_allow_html=True)

            ans = st.radio(
                f"질문 {i+1}",
                ["Yes", "No"],
                horizontal=True,
                key=f"q_{i}"
            )

            responses.append({
                "question": q,
                "answer": ans
            })

        if st.form_submit_button("최종 분석"):
            st.session_state.data["responses"] = responses
            st.session_state.stage = "analysis"
            st.rerun()

# =============================
# ANALYSIS
# =============================
elif st.session_state.stage == "analysis":
    st.subheader("📋 최종 진단 리포트")

    report = generate_weakness_report(
        st.session_state.data["topic"],
        st.session_state.data["responses"]
    )

    st.markdown(report)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
