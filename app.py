import re
import time
import logging
from typing import List, Dict

import streamlit as st
import google.generativeai as genai

# =============================
# CONFIG
# =============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Veritas AI | Smart Diagnostic",
    page_icon="🔍",
    layout="centered",
)

st.markdown("""
<style>
.stApp {
    background-color: #0d1117;
    color: #c9d1d9;
}
.main-title {
    color: #58a6ff;
    font-size: 2.7rem;
    font-weight: 800;
    text-align: center;
}
.result-title {
    color: #58a6ff;
    font-size: 3rem;
    font-weight: 900;
    text-align: center;
    margin-bottom: 2rem;
}
.category-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}
.category-title {
    color: #58a6ff;
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 0.7rem;
}
.diag-card {
    padding: 1rem;
    border: 1px solid #30363d;
    border-radius: 12px;
    margin-bottom: 1rem;
    background:#161b22;
}
</style>
""", unsafe_allow_html=True)

# =============================
# FALLBACK QUESTION ENGINE
# =============================
def infer_input_type(user_input: str) -> str:
    text = user_input.strip()
    if any(sym in text for sym in ["def ", "for ", "while ", "if ", "{", "}", ";"]):
        return "code"
    if any(k in text.lower() for k in ["error", "bug", "왜", "안돼", "막혀"]):
        return "problem"
    if len(text.split()) >= 4:
        return "sentence"
    return "concept"


def build_fallback_questions(topic: str) -> List[str]:
    return [
        f"1. {topic}를 다른 사람에게 직접 설명할 수 있나요?",
        f"2. {topic}의 핵심 구조를 구분할 수 있나요?",
        f"3. 새로운 문제에서도 {topic}를 적용할 수 있나요?",
        f"4. 비슷한 개념과 {topic}의 차이를 구별할 수 있나요?",
        f"5. 다음에 같은 문제를 혼자 해결할 수 있나요?",
    ]


def extract_questions(raw: str) -> List[str]:
    lines = raw.split("\n")
    results = []
    for line in lines:
        line = line.strip()
        if re.match(r"^\d+[.)]", line):
            results.append(line)
    return results[:5]


# =============================
# GEMINI ENGINE
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def call(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini 실패: {e}")
            return "[LOCAL_FALLBACK]"


# =============================
# 진단 결과 생성 핵심
# =============================
def build_smart_diagnosis_from_no(weak_points: List[Dict], topic: str) -> Dict:
    """
    NO 응답만 기반으로 3카테고리 결과 생성
    절대 KeyError 안 나도록 dict 고정
    """
    missed = []
    explanations = []
    extras = []

    for item in weak_points:
        q = item["question"]
        reason = item.get("reason", "").strip()

        if "설명" in q:
            concept = f"{topic}의 핵심 정의"
            explain = f"{topic}의 정의를 자신의 언어로 설명하지 못했다는 것은 개념의 입력은 되었지만 구조화가 안 된 상태입니다. 즉 단순 암기가 아니라 '왜 그렇게 동작하는지'까지 연결 복습이 필요합니다."
            extra = "정의 → 예시 → 반례 순서로 다시 복습"
        elif "구조" in q:
            concept = f"{topic}의 구성 요소"
            explain = f"{topic}를 이루는 세부 요소의 역할 구분이 약합니다. 어떤 요소가 입력이고 어떤 부분이 처리 단계인지 흐름 중심으로 다시 봐야 합니다."
            extra = "구성 요소별 역할 정리"
        elif "적용" in q:
            concept = f"{topic}의 문제 적용력"
            explain = f"이미 알고 있는 개념을 새로운 문제에 옮겨 쓰는 전이 능력이 부족합니다. 이는 예제 수가 부족하거나 문제 유형 연결이 덜 된 상태입니다."
            extra = "유형별 적용 문제 3개 반복"
        else:
            concept = f"{topic}의 핵심 원리"
            explain = f"{topic}에서 왜 그 방식이 성립하는지 원리 이해가 약합니다. 공식이나 코드의 동작 이유를 단계별로 추적해야 합니다."
            extra = "원리 흐름 다시 추적"

        if reason:
            explain += f" 사용자가 직접 '{reason}' 라고 느낀 부분은 실제 결손 포인트일 가능성이 높습니다."

        missed.append(f"• {concept}")
        explanations.append(f"• {explain}")
        extras.append(f"• {extra}")

    # 중복 제거
    missed = list(dict.fromkeys(missed))
    explanations = list(dict.fromkeys(explanations))
    extras = list(dict.fromkeys(extras))

    return {
        "놓친개념": "<br>".join(missed),
        "개념설명": "<br><br>".join(explanations),
        "추가로 필요한 부분": "<br>".join(extras)
    }


# =============================
# SESSION
# =============================
if "stage" not in st.session_state:
    st.session_state.stage = "ready"
if "data" not in st.session_state:
    st.session_state.data = {}

# =============================
# API KEY
# =============================
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("GEMINI API KEY", type="password")

if not api_key:
    st.warning("GEMINI API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)

# =============================
# READY
# =============================
if st.session_state.stage == "ready":
    st.markdown("""
    <div style='position: relative; display: inline-block; width: 100%; text-align: center;'>
        <div class='main-title'>Veritas AI</div>
        <div style='position: absolute; right: 28%; bottom: -8px; font-size: 0.8rem; color: #8b949e;'>by Jun</div>
    </div>
    """, unsafe_allow_html=True)

    topic = st.text_input("학습 주제", placeholder="예: 근의공식, SQL 오류, 영어 문장")

    if st.button("빠른 진단 시작"):
        if topic:
            with st.spinner("열심히 탐색중!! 🤗"):
                result = engine.call(f"""
사용자 입력: {topic}
서로 다른 사고 단계의 Yes/No 질문 5개 생성
번호 1~5 필수
""")
                questions = extract_questions(result)

                if not questions or result == "[LOCAL_FALLBACK]":
                    questions = build_fallback_questions(topic)

            st.session_state.data["topic"] = topic
            st.session_state.data["questions"] = questions
            st.session_state.stage = "testing"
            st.rerun()

# =============================
# TESTING
# =============================
elif st.session_state.stage == "testing":
    st.subheader(f"주제: {st.session_state.data['topic']}")

    with st.form("test_form"):
        responses = []

        for i, q in enumerate(st.session_state.data["questions"]):
            st.markdown(f"<div class='diag-card'><b>{q}</b></div>", unsafe_allow_html=True)
            ans = st.radio(
                f"q{i}",
                ["Yes", "No"],
                horizontal=True,
                label_visibility="collapsed",
                key=f"radio_{i}",
            )

            reason = ""
            if ans == "No":
                reason = st.text_input(f"막힌 이유 {i+1}", key=f"reason_{i}")

            responses.append({
                "question": q,
                "answer": ans,
                "reason": reason
            })

        if st.form_submit_button("최종 분석"):
            st.session_state.data["responses"] = responses
            st.session_state.stage = "analysis"
            st.rerun()

# =============================
# ANALYSIS
# =============================
elif st.session_state.stage == "analysis":
    st.markdown("<div class='result-title'>진단 결과 😋</div>", unsafe_allow_html=True)

    weak_points = [
        x for x in st.session_state.data["responses"]
        if x["answer"] == "No"
    ]

    if not weak_points:
        st.success("현재는 핵심 개념이 안정적으로 잡혀 있습니다.")
    else:
        result = build_smart_diagnosis_from_no(
            weak_points,
            st.session_state.data["topic"]
        )

        for category in ["놓친개념", "개념설명", "추가로 필요한 부분"]:
            st.markdown(f"""
            <div class='category-card'>
                <div class='category-title'>{category}</div>
                <div>{result[category]}</div>
            </div>
            """, unsafe_allow_html=True)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
