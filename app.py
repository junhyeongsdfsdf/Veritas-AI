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

.main-title {
    color: #58a6ff;
    font-size: 2.8rem;
    font-weight: 900;
    text-align: center;
}

.diag-card {
    padding: 1.2rem;
    border: 1px solid #30363d;
    border-radius: 14px;
    margin-bottom: 1rem;
    background: #161b22;
}

.result-box {
    padding: 1rem;
    border-radius: 14px;
    background: #161b22;
    border: 1px solid #30363d;
    min-height: 230px;
}
</style>
""", unsafe_allow_html=True)


# =============================
# 2) QUESTION FALLBACK ENGINE
# =============================
UNIVERSAL_DIAGNOSTIC_DIMENSIONS = [
    "핵심 의미",
    "구조 이해",
    "원리 적용",
    "비교 분석",
    "실수 예방",
]


def infer_input_type(user_input: str) -> str:
    text = user_input.strip().lower()

    if any(sym in text for sym in ["def ", "for ", "while ", "if ", "{", "}", ";"]):
        return "code"
    if any(k in text for k in ["error", "bug", "안돼", "막혀"]):
        return "problem"
    if len(text.split()) >= 4:
        return "sentence"
    return "concept"


def extract_learning_facets(user_input: str) -> List[str]:
    input_type = infer_input_type(user_input)

    facet_map = {
        "concept": [
            "핵심 개념 의미",
            "구성 요소 역할",
            "원리 연결",
            "예시 적용",
            "헷갈리는 개념 비교",
        ],
        "code": [
            "실행 흐름 추적",
            "조건 분기 이해",
            "반복 종료 시점",
            "에러 원인 재현",
            "구조 개선",
        ],
        "sentence": [
            "핵심 의미 파악",
            "문장 구조 이해",
            "다른 문맥 응용",
            "표현 비교",
            "직접 문장 생성",
        ],
        "problem": [
            "문제 원인 정의",
            "막힌 단계 식별",
            "해결 시도 경험",
            "다른 상황 적용",
            "재발 방지",
        ],
    }
    return facet_map.get(input_type, UNIVERSAL_DIAGNOSTIC_DIMENSIONS)


def build_fallback_questions(topic: str) -> List[str]:
    facets = extract_learning_facets(topic)

    styles = [
        "{idx}. 현재 '{facet}' 부분이 가장 불안정하다고 느껴지나요?",
        "{idx}. 방금 내용을 다시 봤을 때 '{facet}'를 스스로 설명할 수 있나요?",
        "{idx}. 같은 유형에서 '{facet}'를 바로 적용할 수 있나요?",
        "{idx}. 다른 사례에서도 '{facet}'를 유지할 수 있나요?",
        "{idx}. 다음에는 '{facet}' 실수를 예방할 수 있나요?",
    ]

    return [
        styles[i].format(idx=i + 1, facet=facet)
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
# 3) NO 기반 최종 진단 엔진
# =============================
def build_smart_diagnosis_from_no(weak_points: List[Dict]) -> Dict:
    weak_text = " ".join(
        [f"{x['question']} {x.get('reason', '')}" for x in weak_points]
    ).lower()

    missed = []
    explanation = []
    extra = []

    # 프로그래밍
    if any(k in weak_text for k in ["코드", "조건", "반복", "python", "java", "c", "에러"]):
        missed.append("조건 흐름 추적")
        explanation.append("조건문과 반복문이 실제로 어떤 순서로 실행되는지 추적력이 부족합니다.")
        extra.extend(["if 조건", "반복 종료", "디버깅 순서"])

    # 수학
    if any(k in weak_text for k in ["공식", "함수", "방정식", "수학", "근의"]):
        missed.append("공식 구조 이해")
        explanation.append("공식의 각 요소가 어떤 역할을 하는지 구조적 연결이 약합니다.")
        extra.extend(["변수 관계", "대입 순서", "예외 조건"])

    # 언어
    if any(k in weak_text for k in ["영어", "문장", "문법", "어순"]):
        missed.append("문장 구조 분석")
        explanation.append("문장의 의미보다 구조를 먼저 분석하는 습관이 더 필요합니다.")
        extra.extend(["어순", "시제", "표현 비교"])

    # fallback
    if not missed:
        missed = ["핵심 개념 연결"]
        explanation = ["No 응답을 보면 개념 간 연결과 적용력이 아직 약한 상태입니다."]
        extra = ["기초 정의", "적용 예시", "실수 패턴"]

    return {
        "missed": missed[:3],
        "explanation": explanation[:3],
        "extra": extra[:5]
    }


# =============================
# 4) OPENAI ENGINE
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-5"

    def call(self, prompt: str):
        try:
            response = self.client.responses.create(
                model=self.model_name,
                input=prompt,
            )
            return response.output_text.strip()
        except Exception as e:
            logger.warning(f"LLM 실패: {e}")
            return "[LOCAL_FALLBACK]"


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
api_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input(
    "OPENAI API KEY",
    type="password"
)

if not api_key:
    st.warning("OPENAI API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)


# =============================
# 7) READY
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
        placeholder="예: 근의공식, SQL 오류, 영어 문장"
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
사용자 입력: {topic}

규칙:
- 서로 다른 사고 단계 질문 5개
- Yes/No 질문
- 번호 1~5
- 입력 문장 그대로 반복 금지
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
                key=f"radio_{i}"
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
    <h1 style='text-align:center; color:#58a6ff; font-weight:900; font-size:3rem;'>
    진단 결과 😋
    </h1>
    """, unsafe_allow_html=True)

    weak_points = [
        x for x in st.session_state.data["responses"]
        if x["answer"] == "No"
    ]

    result = build_smart_diagnosis_from_no(weak_points)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("<div class='result-box'><h3>놓친 개념</h3>", unsafe_allow_html=True)
        for item in result["missed"]:
            st.write(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='result-box'><h3>개념 설명</h3>", unsafe_allow_html=True)
        for item in result["explanation"]:
            st.write(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='result-box'><h3>추가로 필요한 부분</h3>", unsafe_allow_html=True)
        for item in result["extra"]:
            st.markdown(f"- [{item}](?query={item})")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
