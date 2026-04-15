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
# QUESTION HELPERS
# =============================
def build_fallback_questions(topic: str) -> List[str]:
    return [
        f"1. {topic}의 핵심 원리는 조건이 바뀌어도 항상 동일하게 적용된다. (Yes/No)",
        f"2. {topic}의 첫 단계가 틀려도 최종 결과는 맞을 수 있다. (Yes/No)",
        f"3. {topic}는 새로운 문제 유형에도 같은 방식으로 적용된다. (Yes/No)",
        f"4. {topic}와 유사 개념은 항상 같은 결과를 만든다. (Yes/No)",
        f"5. {topic}에는 반례가 존재하지 않는다. (Yes/No)",
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
# DIAGNOSIS ENGINE
# =============================
def build_smart_diagnosis_from_no(
    weak_points: List[Dict],
    topic: str
) -> Dict:
    missed = []
    explanations = []
    extras = []

    for item in weak_points:
        q = item["question"]

        if "반례" in q:
            concept = f"{topic} 반례 구분 능력"
            explanation = (
                f"{topic}를 일반적인 상황에서는 이해하고 있지만, "
                f"적용되지 않는 반례 상황을 빠르게 구분하는 힘이 약합니다. "
                f"시험에서는 이 부분이 함정 문제로 자주 출제됩니다."
            )
            extra = [
                f"{topic} 반례 문제",
                f"{topic} 오답 패턴",
                f"{topic} 함정 유형"
            ]

        elif "조건" in q or "단계" in q:
            concept = f"{topic} 조건 변화 해석"
            explanation = (
                f"{topic}의 절차나 핵심 단계는 이해하고 있으나 "
                f"조건이 달라졌을 때 어떤 단계가 먼저 영향을 받는지 "
                f"추론하는 부분이 약합니다. "
                f"응용 문제 해결력을 높이려면 조건 변화에 따른 "
                f"결과 흐름을 연결해서 복습해야 합니다."
            )
            extra = [
                f"{topic} 조건 변화",
                f"{topic} 응용 문제",
                f"{topic} 단계별 흐름"
            ]

        else:
            concept = f"{topic} 핵심 원리 연결"
            explanation = (
                f"{topic}의 핵심 개념은 알고 있지만 "
                f"원리 → 구조 → 응용으로 이어지는 연결력이 약합니다. "
                f"왜 이런 결과가 나오는지 설명형 사고를 강화하면 "
                f"정답률이 빠르게 올라갑니다."
            )
            extra = [
                f"{topic} 핵심 원리",
                f"{topic} 구조 복습",
                f"{topic} 실전 응용"
            ]

        missed.append(f"• {concept}")
        explanations.append(f"• {explanation}")
        extras.extend(extra)

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
# READY PAGE
# =============================
if st.session_state.stage == "ready":
    st.markdown("""
    <div style='text-align:center;'>
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
취약 개념을 정확히 잡아내는 OX 퀴즈 5개 생성

규칙:
- 자기평가 질문 금지
- Yes/No 퀴즈형
- 반례 / 예외 / 응용 포함
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
# TEST PAGE
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
# ANALYSIS PAGE (FINAL FIX)
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

    topic = st.session_state.data["topic"]

    if not weak_points:
        st.success("현재 핵심 개념 이해도와 응용력이 매우 안정적입니다.")
    else:
        missed_concepts = []
        explanations = []
        extra_topics = []

        for item in weak_points:
            q = item["question"]

            if "반례" in q:
                missed_concepts.append(
                    f"{topic}의 반례 및 예외 상황 판단"
                )
                explanations.append(
                    f"{topic}를 일반 문제에서는 적용할 수 있지만, "
                    f"예외 조건이 붙었을 때 기존 규칙을 그대로 적용하려는 경향이 있습니다. "
                    f"즉 공식의 적용 범위와 적용 불가능한 상황을 구분하는 힘이 약합니다. "
                    f"시험에서는 이 부분이 함정 선지로 자주 출제됩니다."
                )
                extra_topics += [
                    f"{topic} 반례 문제",
                    f"{topic} 예외 조건",
                    f"{topic} 함정 유형"
                ]

            elif "조건" in q or "단계" in q:
                missed_concepts.append(
                    f"{topic} 단계별 조건 변화 추론"
                )
                explanations.append(
                    f"{topic}의 기본 절차는 이해했지만, "
                    f"중간 단계의 조건이 바뀌었을 때 결과가 어떻게 달라지는지 "
                    f"논리적으로 추적하는 힘이 약합니다. "
                    f"특히 응용 문제에서 단계 순서와 영향 관계를 복습해야 합니다."
                )
                extra_topics += [
                    f"{topic} 단계 추론",
                    f"{topic} 응용 문제",
                    f"{topic} 흐름 연결"
                ]

            else:
                missed_concepts.append(
                    f"{topic} 핵심 원리와 응용 연결"
                )
                explanations.append(
                    f"{topic}의 정의는 기억하고 있지만 "
                    f"왜 그런 결과가 나오는지 원리 수준 설명이 약합니다. "
                    f"현재는 공식 기억형 이해에 가까워 "
                    f"문제 조건이 조금만 바뀌어도 오답률이 높아질 수 있습니다. "
                    f"원리 → 구조 → 응용 순서로 다시 연결 복습이 필요합니다."
                )
                extra_topics += [
                    f"{topic} 핵심 원리",
                    f"{topic} 응용 확장",
                    f"{topic} 오답 패턴"
                ]

        # -------------------------
        # 놓친 개념 카드
        # -------------------------
        with st.container():
            st.markdown("## 놓친 개념")
            for c in sorted(set(missed_concepts)):
                st.info(c)

        # -------------------------
        # 개념 설명 카드
        # -------------------------
        with st.container():
            st.markdown("## 개념 설명")
            for e in sorted(set(explanations)):
                st.write(f"• {e}")

        # -------------------------
        # 추가로 필요한 부분 (링크)
        # -------------------------
        with st.container():
            st.markdown("## 추가로 필요한 부분")
            for extra in sorted(set(extra_topics)):
                link = f"https://chat.openai.com/?q={quote(extra)}"
                st.markdown(f"- [{extra}]({link})")

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
