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
    font-size: 2.5rem;
    font-weight: 800;
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
            "입력과 출력 흐름을 추적 가능한지",
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
            "새로운 문장을 직접 만들 수 있는지",
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
        "{idx}. 현재 '{facet}' 부분이 핵심적으로 부족하다고 느끼나요?",
        "{idx}. 이 부분을 다른 사례에서도 설명할 수 있나요?",
        "{idx}. 비슷한 문제가 다시 나오면 스스로 해결 가능하나요?",
        "{idx}. 유사하지만 다른 상황에도 그대로 적용 가능하나요?",
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
# 3) GPT-5.4 ENGINE
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-5.4"

    def generate_questions(self, topic: str) -> List[str]:
        prompt = f"""
당신은 학습 결손 진단 AI입니다.

사용자 입력:
{topic}

규칙:
- 입력 문장을 그대로 반복하지 말 것
- 입력 타입 추론: 개념 / 코드 / 언어 / 오류 / 문제상황
- 서로 완전히 다른 사고 단계의 질문 5개 생성
- 이해 / 구조 / 원리 / 응용 / 예방 단계 포함
- 모든 질문은 Yes/No로 답할 수 있어야 함
- 반드시 번호 형식 1~5

출력:
1. ...
2. ...
3. ...
4. ...
5. ...
"""
        response = self.client.responses.create(
            model=self.model_name,
            input=prompt,
        )

        text = response.output_text.strip()
        return extract_questions(text)


# =============================
# 4) ANALYSIS ENGINE
# =============================
def local_root_cause_analysis(topic: str, weak_points: List[Dict]) -> str:
    concepts = []

    weak_text = " ".join(
        [f"{x['question']} {x.get('reason', '')}" for x in weak_points]
    )

    if "반복" in weak_text:
        concepts.append("- 반복 구조와 종료 조건")
    if "조건" in weak_text:
        concepts.append("- 조건 분기 기준")
    if "문장" in weak_text:
        concepts.append("- 문장 구조 및 문맥")
    if "개념" in weak_text:
        concepts.append("- 핵심 개념 정의")

    if not concepts:
        concepts = [
            "- 핵심 정의 복습",
            "- 구조 재분해",
            "- 유사 문제 반복 적용",
        ]

    return f"""
## 1. 결손 지점
'{topic}'에서 특정 사고 단계가 단절되었습니다.

## 2. 왜 어려운지
No 응답 패턴상 구조 이해 또는 응용 전환 단계에서 막혔습니다.

## 3. 지금 복습할 핵심
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
api_key = (
    st.secrets.get("OPENAI_API_KEY")
    or st.sidebar.text_input("OPENAI API KEY", type="password")
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
    <div style='position: relative; display: inline-block; width: 100%; text-align: center;'>
        <div class='main-title'>Veritas AI</div>
        <div style='position: absolute; right: 28%; bottom: -8px; font-size: 0.8rem; color: #8b949e;'>by Jun</div>
    </div>
    """, unsafe_allow_html=True)

    topic = st.text_input(
        "학습 주제",
        placeholder="예: SQL JOIN, 영어 문장, C 포인터, 확률 문제"
    )

    if st.button("빠른 진단 시작"):
        if topic:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            progress_text.markdown("### 열심히 탐색중!! 🤗")

            start_time = time.time()
            questions = []

            while time.time() - start_time < 60:
                elapsed = time.time() - start_time
                progress = int((elapsed / 60) * 100)
                progress_bar.progress(progress)

                try:
                    questions = engine.generate_questions(topic)

                    # ✅ 찾으면 즉시 이동
                    if len(questions) >= 5:
                        break

                except Exception as e:
                    logger.warning(f"탐색 중 오류: {e}")

                time.sleep(2)

            # ✅ 60초 동안 못 찾았을 때만 fallback
            if len(questions) < 5:
                questions = build_fallback_questions(topic)

            progress_bar.progress(100)
            progress_text.markdown("### 탐색 완료! ✨")

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
            st.markdown(
                f"<div class='diag-card'><b>{q}</b></div>",
                unsafe_allow_html=True
            )

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
    st.subheader("진단 결과☺️")

    weak_points = [
        x for x in st.session_state.data["responses"]
        if x["answer"] == "No"
    ]

    if not weak_points:
        st.success("전체 학습 구조가 안정적입니다.")
    else:
        with st.spinner("응답 패턴을 분석하여 결손 지점을 추론 중입니다..."):
            report = None

            try:
                analysis_prompt = f"""
당신은 학습 결손 진단 전문가입니다.

주제:
{st.session_state.data['topic']}

사용자가 어려워한 부분:
{weak_points}

아래 형식으로 깊이 있게 분석하세요.

## 1. 결손 지점
- 사용자가 정확히 어떤 사고 단계에서 막혔는지

## 2. 놓친 핵심 개념
- 지금 반드시 복습해야 할 세부 개념

## 3. 바로 해야 할 학습 액션
- 다음 30분 동안 무엇을 공부하면 되는지
"""

                response = engine.client.responses.create(
                    model=engine.model_name,
                    input=analysis_prompt,
                )

                report = response.output_text.strip()

            except Exception as e:
                logger.warning(f"최종 분석 실패 → fallback 사용: {e}")

            if not report:
                report = local_root_cause_analysis(
                    st.session_state.data["topic"],
                    weak_points
                )

        st.markdown(report)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
