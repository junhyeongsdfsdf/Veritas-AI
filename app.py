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
# 2) ADAPTIVE DIAGNOSTIC INTELLIGENCE
# =============================
# 범용 학습 진단 차원 (과목/언어/실무 모두 대응)
UNIVERSAL_DIAGNOSTIC_DIMENSIONS = [
    "핵심 개념을 자신의 말로 설명",
    "구성 요소를 구분",
    "동작 원리 또는 문맥 이해",
    "실제 예시에 적용",
    "헷갈리는 예외/유사 개념과 비교",
]

LANGUAGE_KEYWORDS = ["영어", "중국어", "일본어", "한국어", "grammar", "vocabulary", "speaking"]


def infer_domain(topic: str) -> str:
    topic = topic.lower()
    if any(k in topic for k in ["공식", "함수", "방정식", "미분", "적분", "확률"]):
        return "math"
    if any(k in topic for k in ["c", "java", "python", "재귀", "포인터", "sql", "알고리즘"]):
        return "programming"
    if any(k in topic for k in ["물리", "화학", "양자", "생물"]):
        return "science"
    return "general"


def infer_input_type(user_input: str) -> str:
    """어떤 형태의 입력이 와도 먼저 타입을 추론"""
    text = user_input.strip()
    if any(sym in text for sym in ["def ", "for ", "while ", "if ", "{", "}", ";"]):
        return "code"
    if len(text.split()) >= 4 and any(ch in text for ch in ["?", ".", ","]):
        return "sentence"
    if any(k in text.lower() for k in ["error", "bug", "왜", "안돼", "막혀"]):
        return "problem"
    return "concept"


def extract_learning_facets(user_input: str) -> List[str]:
    """입력 문장을 그대로 반복하지 않고 학습의 여러 면을 분해"""
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
    """입력의 단면이 아니라 전체 학습면을 보는 질문 생성"""
    facets = extract_learning_facets(topic)
    return [
        f"{i+1}. 현재 입력에서 '{facet}'를 점검할 수 있나요?"
        for i, facet in enumerate(facets)
    ]

# =============================
# 3) ENGINE
# =============================
class VeritasEngine:
    """환경별 Gemini 호환 + 최종 실패 시 로컬 분석 fallback"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = None
        self.model_name = None
        self._initialize_model()

    def _initialize_model(self):
        candidates = [
            "models/gemini-1.5-flash",
            "gemini-1.5-flash",
            "models/gemini-pro",
            "gemini-pro",
        ]

        # 실제 generate_content 테스트까지 통과한 모델만 채택
        for model_name in candidates:
            try:
                model = genai.GenerativeModel(model_name)
                _ = model.generate_content(
                    "ping",
                    generation_config={"max_output_tokens": 1},
                    request_options={"timeout": 10},
                )
                self.model = model
                self.model_name = model_name
                return
            except Exception:
                continue

        # 동적 탐색
        try:
            for m in genai.list_models():
                methods = getattr(m, "supported_generation_methods", [])
                if "generateContent" not in methods:
                    continue
                try:
                    model = genai.GenerativeModel(m.name)
                    _ = model.generate_content(
                        "ping",
                        generation_config={"max_output_tokens": 1},
                        request_options={"timeout": 10},
                    )
                    self.model = model
                    self.model_name = m.name
                    return
                except Exception:
                    continue
        except Exception:
            pass

    def call(self, prompt: str, retries: int = 2) -> str:
        if not self.model:
            return "[LOCAL_FALLBACK]"

        for attempt in range(retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 700,
                    },
                    request_options={"timeout": 20},
                )
                return response.text.strip()

            except Exception as e:
                logger.warning(f"LLM retry {attempt+1} failed: {e}")
                if attempt == retries - 1:
                    return "[LOCAL_FALLBACK]"
                time.sleep(2)

        return "[LOCAL_FALLBACK]"


def local_root_cause_analysis(topic: str, weak_points: List[Dict]) -> str:
    """AI가 죽어도 반드시 결과를 내는 규칙 기반 분석기"""
    weak_text = " ".join(
        [f"{x['question']} {x.get('reason', '')}" for x in weak_points]
    )

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
            # 주제 적응형 질문 생성
            with st.spinner("주제 구조를 분석하여 맞춤 질문 생성 중..."):
                result = engine.call(f"""
당신은 학습 진단 AI입니다.
사용자 입력: {topic}

중요:
- 입력은 특정 과목이나 개념에 한정되지 않는다.
- 코드, 문장, 외국어 표현, 문제상황, 실수 패턴, 업무 고민, 창작 아이디어 등 광범위할 수 있다.
- 먼저 입력 타입을 추론하라: 개념 / 코드 / 문장 / 오류 / 문제상황 / 응용
- 사용자가 입력한 문장을 그대로 반복하거나 단어만 바꿔 질문하지 말라.
- 입력의 '전체 학습면'을 분해하라: 의미, 구조, 원리, 적용, 비교/재구성.
- 지금 당장 보이는 단면이 아니라 사용자가 다음 단계에서 실패할 가능성이 큰 지점까지 예측하라.
- 질문마다 서로 다른 사고 단계를 겨냥하라.
- Yes/No로 답할 수 있어야 한다.

출력 형식:
1. 질문
2. 질문
3. 질문
4. 질문
5. 질문
""")
                questions = extract_questions(result)

                # AI 실패 시에도 주제 기반 적응형 fallback
                if not questions or result == "[LOCAL_FALLBACK]":
                    questions = build_fallback_questions(topic)

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

        # AI 실패 시에도 무조건 분석 결과 출력
        if report == "[LOCAL_FALLBACK]":
            report = local_root_cause_analysis(
                st.session_state.data['topic'],
                weak_points,
            )

        st.write(report)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
