import re
import time
import logging
from typing import List, Dict

import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions

# =============================
# 1) CONFIG
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
.stApp { background-color: #0d1117; color: #c9d1d9; }
.main-title { color: #58a6ff; font-size: 2.5rem; font-weight: 800; text-align: center; }
.diag-card { padding: 1.2rem; border: 1px solid #30363d; border-radius: 12px; margin-bottom: 1rem; background:#161b22; }
</style>
""", unsafe_allow_html=True)

# =============================
# 2) KNOWLEDGE TREE
# =============================
KNOWLEDGE_TREE = {
    "근의공식": [
        "1. 이차방정식 ax²+bx+c=0 형태를 이해하나요?",
        "2. b²-4ac에서 곱셈 순서를 이해하나요?",
        "3. 음수와 양수의 곱셈을 계산할 수 있나요?",
        "4. 제곱근 계산 원리를 이해하나요?",
        "5. 최종 분수 계산까지 스스로 할 수 있나요?"
    ],
    "재귀함수": [
        "1. 함수의 기본 구조를 이해하나요?",
        "2. 종료 조건의 필요성을 이해하나요?",
        "3. 함수가 자기 자신을 호출하는 원리를 아나요?",
        "4. 호출 스택 개념을 이해하나요?",
        "5. 작은 문제로 분할하는 사고를 할 수 있나요?"
    ]
}

# =============================
# 3) ENGINE
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def call(self, prompt: str, retries: int = 2) -> str:
        for attempt in range(retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 600,
                    },
                    request_options={"timeout": 20},
                )
                return response.text.strip()

            except exceptions.ResourceExhausted:
                if attempt == retries - 1:
                    return "API 사용량 제한입니다. 잠시 후 다시 시도하세요."
                time.sleep(3)

            except Exception as e:
                logger.exception("LLM Error")
                if attempt == retries - 1:
                    return f"호출 실패: {str(e)}"
                time.sleep(2)

        return "알 수 없는 오류"


def extract_questions(raw: str) -> List[str]:
    lines = raw.split("\n")
    results = []
    for line in lines:
        line = line.strip()
        if re.match(r"^\d+[.)]", line):
            results.append(line)
    return results[:5]


# =============================
# 4) SESSION
# =============================
if "stage" not in st.session_state:
    st.session_state.stage = "ready"
if "data" not in st.session_state:
    st.session_state.data = {}

# =============================
# 5) API KEY
# =============================
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("API KEY", type="password")

if not api_key:
    st.warning("API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)

# =============================
# 6) READY
# =============================
if st.session_state.stage == "ready":
    st.markdown("<div class='main-title'>Veritas AI</div>", unsafe_allow_html=True)
    topic = st.text_input("학습 주제", placeholder="예: 근의공식")

    if st.button("빠른 진단 시작"):
        if topic:
            # 1순위: 고정 지식트리
            if topic in KNOWLEDGE_TREE:
                questions = KNOWLEDGE_TREE[topic]
            else:
                with st.spinner("질문 생성 중..."):
                    result = engine.call(f"""
당신은 교육 전문가입니다.
주제: {topic}

하위 개념을 추적할 수 있는 Yes/No 질문 5개를 반드시 아래 형식으로 작성하세요.
1. 질문
2. 질문
3. 질문
4. 질문
5. 질문
""")
                questions = extract_questions(result)

                # fallback
                if not questions:
                    questions = [
                        "1. 이 개념의 정의를 설명할 수 있나요?",
                        "2. 공식의 각 항의 의미를 이해하나요?",
                        "3. 곱셈/덧셈 연산 과정을 설명할 수 있나요?",
                        "4. 왜 이런 계산이 필요한지 아나요?",
                        "5. 비슷한 문제를 혼자 풀 수 있나요?"
                    ]

            st.session_state.data["topic"] = topic
            st.session_state.data["questions"] = questions
            st.session_state.stage = "testing"
            st.rerun()

# =============================
# 7) TESTING
# =============================
elif st.session_state.stage == "testing":
    st.subheader(f"주제: {st.session_state.data['topic']}")

    with st.form("test_form"):
        responses: List[Dict] = []

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
            responses.append({"question": q, "answer": ans, "reason": reason})

        if st.form_submit_button("최종 분석"):
            st.session_state.data["responses"] = responses
            st.session_state.stage = "analysis"
            st.rerun()

# =============================
# 8) ANALYSIS
# =============================
elif st.session_state.stage == "analysis":
    st.subheader("최종 진단 리포트")

    weak_points = [x for x in st.session_state.data["responses"] if x["answer"] == "No"]

    if not weak_points:
        st.success("기초 개념이 충분히 잡혀 있습니다.")
    else:
        with st.spinner("결손 지점 분석 중..."):
            report = engine.call(f"""
주제: {st.session_state.data['topic']}
약한 개념: {weak_points}

다음 형식으로 분석:
1. 결손 지점
2. 왜 어려운지
3. 지금 복습할 기초 개념
""")
        st.write(report)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
