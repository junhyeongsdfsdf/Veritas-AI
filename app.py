import re
import time
import logging
from typing import List, Dict

import streamlit as st
from openai import OpenAI

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

.big-report-title {
    color: #58a6ff;
    font-size: 3rem;
    font-weight: 900;
    text-align: center;
    margin-bottom: 1.5rem;
}

.diag-card {
    padding: 1.2rem;
    border: 1px solid #30363d;
    border-radius: 12px;
    margin-bottom: 1rem;
    background: #161b22;
}

.result-card {
    padding: 1.4rem;
    border-radius: 14px;
    background: #161b22;
    border: 1px solid #30363d;
    margin-bottom: 1rem;
    line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

# =============================
# 2) QUESTION FALLBACK
# =============================
def infer_input_type(text: str) -> str:
    if any(x in text for x in ["def ", "for ", "while ", "{", "}", ";"]):
        return "code"
    if any(x in text for x in ["왜", "안돼", "error", "bug"]):
        return "problem"
    if len(text.split()) >= 4:
        return "sentence"
    return "concept"


def build_fallback_questions(topic: str) -> List[str]:
    q = [
        f"1. '{topic}'의 핵심 개념을 스스로 설명할 수 있나요?",
        f"2. '{topic}'를 다른 문제에도 적용할 수 있나요?",
        f"3. 비슷한 사례와 차이를 구분할 수 있나요?",
        f"4. 왜 그렇게 동작하는지 원리를 설명할 수 있나요?",
        f"5. 다음에도 같은 실수를 막을 수 있나요?",
    ]
    return q


def extract_questions(raw: str) -> List[str]:
    lines = raw.split("\n")
    result = []

    for line in lines:
        line = line.strip()
        if re.match(r"^\d+[.)]", line):
            result.append(line)

    return result[:5]


# =============================
# 3) OPENAI ENGINE
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-5"

    def generate_questions(self, topic: str, timeout: int = 60):
        start = time.time()

        while time.time() - start < timeout:
            try:
                response = self.client.responses.create(
                    model=self.model_name,
                    input=f"""
사용자 입력: {topic}

규칙:
- Yes/No 질문 5개
- 서로 다른 사고 단계
- 입력 문장 반복 금지
- 이해 / 구조 / 적용 / 비교 / 예방
""",
                )

                text = response.output_text.strip()
                q = extract_questions(text)

                if len(q) == 5:
                    return q

            except Exception:
                pass

            time.sleep(5)

        return build_fallback_questions(topic)

    def generate_report(self, topic: str, weak_points: List[Dict]):
        weak_text = "\n".join(
            [f"{x['question']} / {x['reason']}" for x in weak_points]
        )

        try:
            response = self.client.responses.create(
                model=self.model_name,
                input=f"""
주제: {topic}
약한 부분:
{weak_text}

아래 형식으로 분석:
1. 놓친개념
2. 개념설명
3. 추가로 필요한 부분 3개
짧지만 전문가처럼 정성껏 분석
""",
            )

            text = response.output_text.strip().split("\n")
            lines = [x.strip() for x in text if x.strip()]

            return {
                "missing": lines[0] if len(lines) > 0 else "핵심 구조 이해 부족",
                "explain": lines[1] if len(lines) > 1 else "기초 개념과 응용 연결이 약합니다.",
                "extra": lines[2:5] if len(lines) >= 5 else [
                    "기초 정의",
                    "대표 문제",
                    "실수 비교",
                ]
            }

        except Exception:
            return {
                "missing": "핵심 구조 이해 부족",
                "explain": "기초 개념과 응용 연결이 약합니다.",
                "extra": [
                    "기초 정의",
                    "대표 문제",
                    "실수 비교",
                ]
            }


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
api_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input(
    "OPENAI API KEY",
    type="password"
)

if not api_key:
    st.warning("OPENAI API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)

# =============================
# 6) READY
# =============================
if st.session_state.stage == "ready":
    st.markdown("""
<div style='position: relative; display: inline-block; width: 100%; text-align: center;'>
    <div class='main-title'>Veritas AI</div>
    <div style='position: absolute; right: 28%; bottom: -8px; font-size: 0.8rem; color: #8b949e;'>
        by Jun
    </div>
</div>
""", unsafe_allow_html=True)

    topic = st.text_input("학습 주제")

    if st.button("빠른 진단 시작"):
        if topic:
            progress_text = st.empty()
            progress_bar = st.progress(0)

            progress_text.markdown("### 열심히 탐색중!! 🤗")

            start = time.time()
            questions = []

            while time.time() - start < 60:
                elapsed = time.time() - start
                progress_bar.progress(min(int((elapsed / 60) * 100), 100))

                questions = engine.generate_questions(topic, timeout=5)

                if len(questions) == 5:
                    break

            progress_bar.progress(100)
            progress_text.markdown("### 탐색 완료! ✨")

            st.session_state.data["topic"] = topic
            st.session_state.data["questions"] = questions
            st.session_state.stage = "testing"
            st.rerun()

# =============================
# 7) TESTING
# =============================
elif st.session_state.stage == "testing":
    st.subheader(st.session_state.data["topic"])

    with st.form("diag"):
        responses = []

        for i, q in enumerate(st.session_state.data["questions"]):
            st.markdown(f"<div class='diag-card'><b>{q}</b></div>", unsafe_allow_html=True)

            ans = st.radio(
                f"q{i}",
                ["Yes", "No"],
                horizontal=True,
                key=f"r{i}",
                label_visibility="collapsed"
            )

            reason = ""
            if ans == "No":
                reason = st.text_input(f"막힌 이유 {i+1}", key=f"t{i}")

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
# 8) ANALYSIS
# =============================
elif st.session_state.stage == "analysis":
    st.markdown("<div class='big-report-title'>진단 결과 😋</div>", unsafe_allow_html=True)

    weak_points = [
        x for x in st.session_state.data["responses"]
        if x["answer"] == "No"
    ]

    result = engine.generate_report(
        st.session_state.data["topic"],
        weak_points
    )

    st.markdown(f"""
    <div class='result-card'>
    <b>놓친 개념</b><br><br>
    {result["missing"]}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='result-card'>
    <b>개념 설명</b><br><br>
    {result["explain"]}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='result-card'><b>추가로 필요한 부분</b><br><br>", unsafe_allow_html=True)

    for item in result["extra"]:
        link = f"https://chat.openai.com/?q={item}"
        st.markdown(f"- [{item}]({link})")

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
