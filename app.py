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

.result-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)


# =============================
# 2) QUESTION FALLBACK ENGINE
# =============================
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

    return facet_map.get(input_type, [
        "핵심 의미",
        "구조 이해",
        "원리 적용",
        "비교 분석",
        "실수 예방",
    ])


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
# 3) LONG SMART DIAGNOSIS ENGINE
# =============================
def build_smart_diagnosis_from_no(
    weak_points: List[Dict],
    topic: str
) -> Dict:
    weak_text = " ".join(
        [f"{x['question']} {x.get('reason', '')}" for x in weak_points]
    ).lower()

    missed_concepts = []
    concept_explanations = []
    additional_parts = []
    practical_tips = []

    if any(k in weak_text for k in ["코드", "python", "java", "c", "반복", "조건", "에러"]):
        missed_concepts.extend([
            "조건문 흐름 추적",
            "반복 종료 조건",
            "에러 재현 사고"
        ])

        concept_explanations.extend([
            "현재 가장 크게 부족한 부분은 코드가 어떤 순서로 실행되는지 머릿속으로 추적하는 힘입니다.",
            "특히 조건문 내부 분기와 반복문의 종료 시점을 정확히 예측하는 부분에서 흔들리고 있습니다.",
            "문법보다 중요한 것은 실행 흐름을 한 줄씩 따라가는 사고력입니다."
        ])

        additional_parts.extend([
            "if-else 분기 추적",
            "for/while 종료 시점",
            "print 디버깅",
            "변수 상태 변화",
            "예외 발생 위치"
        ])

        practical_tips.extend([
            "변수 값이 어떻게 바뀌는지 한 줄씩 적어보세요.",
            "반복문은 종료 조건부터 먼저 확인하는 습관을 가지세요."
        ])

    elif any(k in weak_text for k in ["공식", "함수", "방정식", "수학", "근의"]):
        missed_concepts.extend([
            "공식 구조 이해",
            "항의 역할 분석",
            "대입 순서"
        ])

        concept_explanations.extend([
            "공식은 단순 암기가 아니라 각 항의 역할을 이해해야 응용됩니다.",
            "No 응답 패턴상 어떤 값을 어디에 넣어야 하는지에서 흔들리는 모습이 보입니다.",
            "문제 조건을 식으로 변환하는 과정에서 사고가 자주 끊기는 유형입니다."
        ])

        additional_parts.extend([
            "변수 관계",
            "문제 조건 식 변환",
            "예외값 처리",
            "계산 순서",
            "단위 확인"
        ])

        practical_tips.extend([
            "숫자를 넣기 전에 문자 관계를 먼저 보세요.",
            "문제 조건을 먼저 식으로 정리하면 실수가 크게 줄어듭니다."
        ])

    else:
        missed_concepts.extend([
            "문장 구조 분석",
            "핵심 의미 파악",
            "표현 비교"
        ])

        concept_explanations.extend([
            "단어 뜻보다 문장 구조를 먼저 보는 힘이 부족합니다.",
            "특히 어순과 문맥 역할을 먼저 보지 않으면 응용 문장에서 막힙니다.",
            "해석보다 구조 분석을 먼저 하는 습관이 필요합니다."
        ])

        additional_parts.extend([
            "어순",
            "시제",
            "표현 비교",
            "문맥 의미",
            "주어 동사 관계"
        ])

        practical_tips.extend([
            "문장을 보면 먼저 주어와 동사를 찾으세요.",
            "비슷한 표현을 비교하며 익히면 훨씬 빨라집니다."
        ])

    return {
        "missed": missed_concepts,
        "explanation": concept_explanations,
        "extra": additional_parts,
        "tips": practical_tips
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
- 입력 문장 반복 금지
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

    result = build_smart_diagnosis_from_no(
        weak_points,
        st.session_state.data["topic"]
    )

    st.markdown("## 📌 놓친 개념")
    with st.container():
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        for item in result["missed"]:
            st.write(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## 🧠 개념 설명")
    with st.container():
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        for item in result["explanation"]:
            st.write(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## 🚀 추가로 필요한 부분")
    with st.container():
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        for item in result["extra"]:
            st.markdown(f"- [{item}](?query={item})")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## 🎯 실전 적용 팁")
    with st.container():
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        for item in result["tips"]:
            st.write(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
    
