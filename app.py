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
.stApp { background-color: #0d1117; color: #c9d1d9; }
.main-title { color: #58a6ff; font-size: 2.5rem; font-weight: 800; text-align: center; }
.diag-card { padding: 1.2rem; border: 1px solid #30363d; border-radius: 12px; margin-bottom: 1rem; background:#161b22; }
</style>
""", unsafe_allow_html=True)

# =============================
# 2) FALLBACK QUESTION ENGINE
# =============================
UNIVERSAL_DIAGNOSTIC_DIMENSIONS = [
    "핵심 개념을 자신의 말로 설명",
    "구성 요소를 구분",
    "동작 원리 또는 문맥 이해",
    "실제 예시에 적용",
    "헷갈리는 예외/유사 개념과 비교",
]


def infer_input_type(user_input: str) -> str:
    text = user_input.strip()
    if any(sym in text for sym in ["def ", "for ", "while ", "if ", "{", "}", ";"]):
        return "code"
    if len(text.split()) >= 4 and any(ch in text for ch in ["?", ".", ","]):
        return "sentence"
    if any(k in text.lower() for k in ["error", "bug", "왜", "안돼", "막혀"]):
        return "problem"
    return "concept"


def extract_learning_facets(user_input: str) -> List[str]:
    input_type = infer_input_type(user_input)

    facet_map = {
        "concept": [
            "핵심 의미를 이해하는지",
            "구성 요소를 구분하는지",
            "원리가 왜 그렇게 되는지",
            "새로운 예시에 적용 가능한지",
            "비슷한 개념과 비교 가능한지",
        ],
        "code": [
            "입력/출력 흐름을 추적하는지",
            "조건과 반복의 기준을 이해하는지",
            "에러 원인을 재현 가능한지",
            "유사 코드에 수정 적용 가능한지",
            "더 나은 구조로 다시 작성 가능한지",
        ],
        "sentence": [
            "문장의 핵심 의미를 이해하는지",
            "구조나 어순을 구분하는지",
            "다른 문맥에 응용 가능한지",
            "비슷한 표현과 차이를 아는지",
            "직접 새로운 문장을 만들 수 있는지",
        ],
        "problem": [
            "문제의 원인을 정의하는지",
            "어느 단계에서 막히는지 아는지",
            "해결 방법을 시도해봤는지",
            "다른 상황에도 적용 가능한지",
            "같은 문제를 다시 예방 가능한지",
        ],
    }
    return facet_map.get(input_type, UNIVERSAL_DIAGNOSTIC_DIMENSIONS)


def build_fallback_questions(topic: str) -> List[str]:
    facets = extract_learning_facets(topic)
    question_styles = [
        "{idx}. 현재 입력에서 '{facet}'가 막힌 핵심 지점이라고 스스로 판단되나요?",
        "{idx}. 방금 문제를 다시 보면 '{facet}'를 명확히 설명할 수 있나요?",
        "{idx}. 같은 유형이 다시 나오면 '{facet}' 기준으로 바로 해결 가능하나요?",
        "{idx}. 비슷하지만 다른 사례에서도 '{facet}'를 그대로 적용할 수 있나요?",
        "{idx}. 다음에는 혼자서도 '{facet}' 실수를 예방할 수 있나요?",
    ]
    return [question_styles[i].format(idx=i+1, facet=facet) for i, facet in enumerate(facets[:5])]


def extract_questions(raw: str) -> List[str]:
    lines = raw.split("\n")
    results = []
    for line in lines:
        line = line.strip()
        if re.match(r"^\d+[.)]", line):
            results.append(line)
    return results[:5]


# =============================
# 3) OPENAI ENGINE (60s SEARCH)
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-5"

    def call(self, prompt: str, max_wait_seconds: int = 60) -> str:
        """최대 60초 동안 반복 탐색 후 실패 시 fallback"""
        start_time = time.time()
        attempt = 1

        while time.time() - start_time < max_wait_seconds:
            try:
                logger.info(f"LLM 탐색 시도 {attempt}")
                response = self.client.responses.create(
                    model=self.model_name,
                    input=prompt,
                )
                text = response.output_text.strip()
                questions = extract_questions(text)
                if len(questions) >= 5:
                    return text
            except Exception as e:
                logger.warning(f"탐색 실패 {attempt}: {e}")

            time.sleep(5)
            attempt += 1

        return "[LOCAL_FALLBACK]"


# =============================
# 4) ANALYSIS FALLBACK
# =============================
def local_root_cause_analysis(topic: str, weak_points: List[Dict]) -> str:
    weak_text = " ".join([f"{x['question']} {x.get('reason', '')}" for x in weak_points])
    concepts = []

    if "곱셈" in weak_text:
        concepts.append("- 곱셈 순서 및 분배법칙")
    if "음수" in weak_text:
        concepts.append("- 음수 × 양수 / 음수 × 음수 규칙")
    if "제곱근" in weak_text:
        concepts.append("- 제곱근과 루트 계산")
    if "분수" in weak_text:
        concepts.append("- 분수 통분 및 약분")
    if "재귀" in topic:
        concepts.append("- 종료 조건과 호출 스택")

    if not concepts:
        concepts = ["- 개념 정의", "- 연산 순서", "- 유사 문제 반복"]

    return f"""
1. 결손 지점
{topic}의 하위 연산 또는 핵심 개념 단계에서 사고가 끊겼습니다.

2. 왜 어려운지
사용자의 No 응답을 보면 세부 연산 규칙 또는 개념 연결이 불안정합니다.

3. 지금 복습할 기초 개념
{chr(10).join(concepts)}
""".strip()


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
api_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input("OPENAI API KEY", type="password")

if not api_key:
    st.warning("OPENAI API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)


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

    topic = st.text_input("학습 주제", placeholder="예: 근의공식, 영어 문장, SQL 오류")

    if st.button("빠른 진단 시작"):
        if topic:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            progress_text.markdown("### 열심히 탐색중!! 🤗")

            start_time = time.time()
            result = None
            while time.time() - start_time < 60:
                elapsed = time.time() - start_time
                progress = min(int((elapsed / 60) * 100), 100)
                progress_bar.progress(progress)

                # 5초 단위로 내부 탐색 호출
                result = engine.call(f"""
당신은 학습 진단 AI입니다.
사용자 입력: {topic}

규칙:
- 입력 문장을 그대로 반복하지 말 것
- 서로 다른 사고 단계의 Yes/No 질문 5개 생성
- 이해 / 구조 / 적용 / 비교 / 예방을 각각 겨냥
- 반드시 번호 형식 1~5
""", max_wait_seconds=5)

                questions = extract_questions(result)
                if questions and result != "[LOCAL_FALLBACK]":
                    break

            progress_bar.progress(100)
            progress_text.markdown("### 탐색 완료! ✨")
                questions = extract_questions(result if result else "")
                if not questions or result == "[LOCAL_FALLBACK]":
                    questions = build_fallback_questions(topic)

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
# 9) ANALYSIS
# =============================
elif st.session_state.stage == "analysis":
    st.subheader("최종 진단 리포트")

    weak_points = [x for x in st.session_state.data["responses"] if x["answer"] == "No"]

    if not weak_points:
        st.success("기초 개념이 충분히 잡혀 있습니다.")
    else:
        report = local_root_cause_analysis(
            st.session_state.data["topic"],
            weak_points,
        )
        st.write(report)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
