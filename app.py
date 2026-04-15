import re
import time
import logging
from typing import List, Dict
from urllib.parse import quote

import streamlit as st
from openai import OpenAI


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
    font-size: 2.8rem;
    font-weight: 900;
    text-align: center;
}
.result-title {
    color: #58a6ff;
    font-size: 3rem;
    font-weight: 900;
    text-align: center;
    margin-bottom: 2rem;
}
.diag-card {
    padding: 1rem;
    border: 1px solid #30363d;
    border-radius: 12px;
    margin-bottom: 1rem;
    background: #161b22;
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
</style>
""", unsafe_allow_html=True)


# =============================
# QUIZ FALLBACK ENGINE
# =============================
def build_fallback_questions(topic: str) -> List[str]:
    return [
        f"1. {topic}의 핵심 원리는 반대 상황에서도 동일하게 유지된다. (Yes/No)",
        f"2. {topic}의 첫 단계가 잘못되어도 최종 결과는 정확할 수 있다. (Yes/No)",
        f"3. {topic}는 새로운 문제 유형에서도 같은 방식으로 적용 가능하다. (Yes/No)",
        f"4. {topic}와 유사 개념은 항상 같은 결과를 만든다. (Yes/No)",
        f"5. {topic}의 예외 상황도 기본 원리만으로 해결 가능하다. (Yes/No)",
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
# GPT ENGINE
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-5"

    def call(self, prompt: str):
        try:
            response = self.client.responses.create(
                model=self.model_name,
                input=prompt
            )
            return response.output_text.strip()
        except Exception as e:
            logger.warning(f"GPT 실패: {e}")
            return "[LOCAL_FALLBACK]"


# =============================
# SMART DIAGNOSIS REPORT
# =============================
def build_smart_diagnosis_from_no(
    weak_points: List[Dict],
    topic: str
) -> Dict:
    missed = []
    explanations = []
    extras = []

    for item in weak_points:
        concept = f"{topic}의 핵심 원리와 예외 처리"

        explanation = (
            f"{topic} 관련 퀴즈에서 오답이 발생한 것은 "
            f"핵심 원리 자체보다도 예외 조건, 반례, 응용 조건에서 "
            f"개념 연결이 약하다는 뜻입니다. "
            f"특히 왜 이 원리가 성립하는지와 "
            f"언제 성립하지 않는지를 함께 이해해야 "
            f"실전 문제에서 흔들리지 않습니다."
        )

        extra_topics = [
            f"{topic} 예외 상황",
            f"{topic} 반례 분석",
            f"{topic} 실전 응용 문제"
        ]

        missed.append(f"• {concept}")
        explanations.append(f"• {explanation}")
        extras.extend(extra_topics)

    return {
        "놓친개념": "<br>".join(sorted(set(missed))),
        "개념설명": "<br><br>".join(sorted(set(explanations))),
        "추가로 필요한 부분": sorted(set(extras)),
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
api_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input(
    "OPENAI API KEY",
    type="password"
)

if not api_key:
    st.warning("OPENAI API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)


# =============================
# READY
# =============================
if st.session_state.stage == "ready":
    st.markdown("""
    <div style='position: relative; display: inline-block; width:100%; text-align:center;'>
        <div class='main-title'>Veritas AI</div>
        <div style='font-size:0.9rem; color:#8b949e;'>by Jun</div>
    </div>
    """, unsafe_allow_html=True)

    topic = st.text_input(
        "학습 주제",
        placeholder="예: SQL JOIN, 영어 현재완료, 근의공식"
    )

    if st.button("빠른 진단 시작"):
        if topic:
            progress_text = st.empty()
            progress_bar = st.progress(0)

            progress_text.markdown("### 열심히 탐색중!! 🤗")

            result = None
            found = False
            start_time = time.time()

            while time.time() - start_time < 60:
                elapsed = time.time() - start_time
                progress = min(int((elapsed / 60) * 100), 100)
                progress_bar.progress(progress)

                result = engine.call(f"""
사용자 주제: {topic}

역할:
사용자의 취약 개념을 찾기 위한 OX 퀴즈형 질문 5개 생성

규칙:
- Yes/No로 정답 판별 가능한 퀴즈
- 자기평가 금지
- 서로 다른 사고 단계
- 예외 / 반례 / 응용 포함
- 번호 1~5
""")

                questions = extract_questions(result)

                if len(questions) >= 5:
                    found = True
                    break

                time.sleep(3)

            progress_bar.progress(100)
            progress_text.markdown("### 탐색 완료! ✨")

            if not found:
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
            st.markdown(
                f"<div class='diag-card'><b>{q}</b></div>",
                unsafe_allow_html=True
            )

            ans = st.radio(
                f"q{i}",
                ["Yes", "No"],
                horizontal=True,
                key=f"radio_{i}"
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
    st.markdown(
        "<div class='result-title'>진단 결과 😋</div>",
        unsafe_allow_html=True
    )

    weak_points = [
        x for x in st.session_state.data["responses"]
        if x["answer"] == "No"
    ]

    if not weak_points:
        st.success("현재 핵심 개념과 예외 처리 이해도가 매우 안정적입니다.")
    else:
        result = build_smart_diagnosis_from_no(
            weak_points,
            st.session_state.data["topic"]
        )

        # 놓친개념 + 개념설명
        for category in ["놓친개념", "개념설명"]:
            st.markdown(f"""
            <div class='category-card'>
                <div class='category-title'>{category}</div>
                <div>{result[category]}</div>
            </div>
            """, unsafe_allow_html=True)

        # 추가 학습 링크
        st.markdown("""
        <div class='category-card'>
            <div class='category-title'>추가로 필요한 부분</div>
        </div>
        """, unsafe_allow_html=True)

        for extra in result["추가로 필요한 부분"]:
            link = f"https://chat.openai.com/?q={quote(extra)}"
            st.markdown(f"- [{extra}]({link})")

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
