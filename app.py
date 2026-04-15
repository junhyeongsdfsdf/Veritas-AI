import re
import time
import logging
import urllib.parse
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
.diag-card {
    padding: 1.2rem;
    border: 1px solid #30363d;
    border-radius: 12px;
    margin-bottom: 1rem;
    background:#161b22;
}
</style>
""", unsafe_allow_html=True)

# =============================
# 2) FALLBACK QUESTION ENGINE
# =============================
UNIVERSAL_DIAGNOSTIC_DIMENSIONS = [
    "핵심 의미 이해",
    "구조 분해",
    "원리 설명",
    "응용 적용",
    "예방 가능성",
]

def infer_input_type(user_input: str) -> str:
    text = user_input.strip().lower()

    if any(sym in text for sym in ["def ", "for ", "while ", "{", "}", ";"]):
        return "code"
    if any(k in text for k in ["error", "bug", "안돼", "왜", "막혀"]):
        return "problem"
    if len(text.split()) >= 4:
        return "sentence"
    return "concept"

def extract_learning_facets(user_input: str) -> List[str]:
    input_type = infer_input_type(user_input)

    facet_map = {
        "concept": [
            "핵심 의미를 설명 가능한지",
            "세부 구성요소를 구분 가능한지",
            "왜 그렇게 동작하는지 이해하는지",
            "새로운 사례에 적용 가능한지",
            "비슷한 개념과 비교 가능한지",
        ],
        "code": [
            "입출력 흐름 추적이 가능한지",
            "조건/반복 기준을 설명 가능한지",
            "에러 원인을 재현 가능한지",
            "유사 코드 수정이 가능한지",
            "더 나은 구조로 개선 가능한지",
        ],
        "sentence": [
            "문장의 의미를 정확히 이해하는지",
            "구조와 어순을 분석 가능한지",
            "다른 문맥으로 바꿔 표현 가능한지",
            "유사 표현과 차이를 구분 가능한지",
            "새 문장을 직접 만들 수 있는지",
        ],
        "problem": [
            "문제 원인을 정의 가능한지",
            "막히는 단계를 특정 가능한지",
            "해결 시도를 논리적으로 설명 가능한지",
            "다른 상황에도 적용 가능한지",
            "재발 방지가 가능한지",
        ],
    }

    return facet_map.get(input_type, UNIVERSAL_DIAGNOSTIC_DIMENSIONS)

def build_fallback_questions(topic: str) -> List[str]:
    facets = extract_learning_facets(topic)

    templates = [
        "{idx}. 현재 '{facet}' 부분이 부족하다고 느끼나요?",
        "{idx}. 이 부분을 다른 사례에도 적용할 수 있나요?",
        "{idx}. 비슷한 문제가 다시 나오면 스스로 해결 가능한가요?",
        "{idx}. 유사한 상황에도 그대로 적용 가능한가요?",
        "{idx}. 다음에는 같은 실수를 예방할 수 있나요?",
    ]

    return [
        templates[i].format(idx=i + 1, facet=facet)
        for i, facet in enumerate(facets[:5])
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
# 3) GPT ENGINE
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-5.4"

    def generate_questions(self, topic: str) -> List[str]:
        prompt = f"""
당신은 학습 결손 진단 AI입니다.

입력:
{topic}

규칙:
- 입력 반복 금지
- 서로 다른 사고 단계의 Yes/No 질문 5개
- 이해 / 구조 / 원리 / 응용 / 예방
- 번호 1~5
"""
        response = self.client.responses.create(
            model=self.model_name,
            input=prompt,
        )

        return extract_questions(response.output_text.strip())

    def generate_report(self, topic: str, weak_points: List[Dict]) -> str:
        prompt = f"""
당신은 쪽집개 강사형 AI입니다.

주제:
{topic}

어려워한 부분:
{weak_points}

반드시 아래 3개만 출력:

### 1. 놓친 핵심 개념
- 3개

### 2. 개념 설명
- 각 개념을 1줄 설명

### 3. 추가로 필요한 부분
- 연결 개념 3개
"""
        response = self.client.responses.create(
            model=self.model_name,
            input=prompt,
        )
        return response.output_text.strip()

# =============================
# 4) DETAIL PAGE
# =============================
def render_detail_page(engine):
    detail = st.query_params.get("detail", "")

    if detail:
        st.markdown("""
        <div style="font-size:2.5rem;font-weight:900;color:#58a6ff;">
        📘 개념 상세 설명
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"선택 개념: {detail}")

        response = engine.client.responses.create(
            model=engine.model_name,
            input=f"{detail}를 초보자도 이해할 수 있게 핵심만 설명해줘."
        )

        st.write(response.output_text.strip())

        if st.button("← 리포트로 돌아가기"):
            st.query_params.clear()
            st.rerun()

        st.stop()

# =============================
# 5) SESSION
# =============================
if "stage" not in st.session_state:
    st.session_state.stage = "ready"
if "data" not in st.session_state:
    st.session_state.data = {}

# =============================
# 6) API KEY
# =============================
api_key = (
    st.secrets.get("OPENAI_API_KEY")
    or st.sidebar.text_input("OPENAI API KEY", type="password")
)

if not api_key:
    st.warning("OPENAI API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)
render_detail_page(engine)

# =============================
# 7) READY
# =============================
if st.session_state.stage == "ready":
    st.markdown("""
    <div style='position: relative; display: inline-block; width: 100%; text-align: center;'>
        <div class='main-title'>Veritas AI</div>
        <div style='position: absolute; right: 28%; bottom: -8px; font-size: 0.8rem; color: #8b949e;'>by Jun</div>
    </div>
    """, unsafe_allow_html=True)

    topic = st.text_input("학습 주제")

    if st.button("빠른 진단 시작"):
        if topic:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            progress_text.markdown("### 열심히 탐색중!! 🤗")

            start_time = time.time()
            questions = []

            while time.time() - start_time < 60:
                progress = int(((time.time() - start_time) / 60) * 100)
                progress_bar.progress(progress)

                try:
                    questions = engine.generate_questions(topic)
                    if len(questions) >= 5:
                        break
                except Exception as e:
                    logger.warning(e)

                time.sleep(2)

            if len(questions) < 5:
                questions = build_fallback_questions(topic)

            progress_bar.progress(100)

            st.session_state.data["topic"] = topic
            st.session_state.data["questions"] = questions
            st.session_state.stage = "testing"
            st.rerun()

# =============================
# 8) TESTING
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
# 9) ANALYSIS
# =============================
elif st.session_state.stage == "analysis":
    st.markdown("""
    <div style="
        font-size: 3rem;
        font-weight: 900;
        color: #58a6ff;
        margin-bottom: 1.5rem;
    ">
    진단 결과 😋
    </div>
    """, unsafe_allow_html=True)

    weak_points = [
        x for x in st.session_state.data["responses"]
        if x["answer"] == "No"
    ]

    if not weak_points:
        st.success("현재 핵심 구조는 충분히 이해하고 있습니다.")
    else:
        report = engine.generate_report(
            st.session_state.data["topic"],
            weak_points
        )

        lines = report.split("\n")
        for line in lines:
            stripped = line.strip()

            if stripped.startswith("- "):
                concept = stripped[2:].strip()
                encoded = urllib.parse.quote(concept)
                st.markdown(f"- [{concept}](?detail={encoded})")
            else:
                st.markdown(line)

    if st.button("새 진단"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
