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
    font-size: 2.7rem;
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
    background:#161b22;
}

.result-card {
    padding: 1.4rem;
    border-radius: 14px;
    background: #161b22;
    border: 1px solid #30363d;
    margin-bottom: 1rem;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)

# =============================
# 2) FALLBACK QUESTION ENGINE
# =============================
UNIVERSAL_DIAGNOSTIC_DIMENSIONS = [
    "핵심 의미",
    "구조 이해",
    "원리 적용",
    "유사 개념 비교",
    "재발 방지",
]


def infer_input_type(user_input: str) -> str:
    text = user_input.strip()

    if any(sym in text for sym in ["def ", "for ", "while ", "if ", "{", "}", ";"]):
        return "code"

    if len(text.split()) >= 4 and any(ch in text for ch in [".", ",", "?"]):
        return "sentence"

    if any(k in text.lower() for k in ["error", "bug", "안돼", "왜", "막혀"]):
        return "problem"

    return "concept"


def extract_learning_facets(user_input: str) -> List[str]:
    input_type = infer_input_type(user_input)

    facet_map = {
        "concept": [
            "핵심 개념 정의",
            "구성 요소",
            "작동 원리",
            "응용 방식",
            "헷갈리는 유사 개념",
        ],
        "code": [
            "입출력 흐름",
            "조건/반복",
            "에러 원인",
            "수정 능력",
            "리팩토링",
        ],
        "sentence": [
            "문장 의미",
            "구조/어순",
            "문맥 적용",
            "유사 표현 비교",
            "직접 생성",
        ],
        "problem": [
            "원인 파악",
            "막힌 단계",
            "해결 시도",
            "재적용",
            "재발 방지",
        ],
    }

    return facet_map.get(input_type, UNIVERSAL_DIAGNOSTIC_DIMENSIONS)


def build_fallback_questions(topic: str) -> List[str]:
    facets = extract_learning_facets(topic)

    templates = [
        "{idx}. 이 내용의 '{facet}'를 스스로 설명할 수 있나요?",
        "{idx}. 실제 다른 상황에서도 '{facet}'를 적용할 수 있나요?",
        "{idx}. 비슷한 문제에서도 '{facet}' 기준으로 해결 가능하나요?",
        "{idx}. 헷갈리는 사례와 '{facet}' 차이를 구분할 수 있나요?",
        "{idx}. 다음에 같은 문제에서 '{facet}' 실수를 막을 수 있나요?",
    ]

    return [
        templates[i].format(idx=i + 1, facet=facets[i])
        for i in range(5)
    ]


def extract_questions(raw: str) -> List[str]:
    lines = raw.split("\n")
    questions = []

    for line in lines:
        line = line.strip()
        if re.match(r"^\d+[.)]", line):
            questions.append(line)

    return questions[:5]


# =============================
# 3) OPENAI ENGINE
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-5"

    def generate_questions(self, topic: str, timeout: int = 60) -> List[str]:
        start = time.time()

        while time.time() - start < timeout:
            try:
                response = self.client.responses.create(
                    model=self.model_name,
                    input=f"""
사용자 입력: {topic}

규칙:
- 입력 문장을 반복하지 말 것
- Yes/No 질문 5개
- 서로 다른 사고 단계
- 이해 / 구조 / 적용 / 비교 / 예방
- 반드시 1~5 번호 형식
""",
                )

                text = response.output_text.strip()
                questions = extract_questions(text)

                if len(questions) == 5:
                    return questions

            except Exception as e:
                logger.warning(f"질문 생성 실패: {e}")

            time.sleep(5)

        return build_fallback_questions(topic)

    def generate_report(self, topic: str, weak_points: List[Dict]) -> Dict:
        weak_text = "\n".join(
            [f"{w['question']} / 이유:{w['reason']}" for w in weak_points]
        )

        try:
            response = self.client.responses.create(
                model=self.model_name,
                input=f"""
주제: {topic}
사용자가 어려워한 부분:
{weak_text}

아래 형식으로 짧고 정확하게 답해.

1. 놓친 핵심 개념
2. 왜 놓쳤는지 설명
3. 추가로 필요한 부분 3개
""",
            )

            text = response.output_text.strip()
            lines = [x.strip() for x in text.split("\n") if x.strip()]

            return {
                "core": lines[0] if len(lines) > 0 else "핵심 개념 연결 부족",
                "reason": lines[1] if len(lines) > 1 else "세부 개념 연결이 약합니다.",
                "extra": lines[2:5] if len(lines) >= 5 else [
                    "기초 정의 다시 보기",
                    "대표 문제 반복",
                    "실수 사례 비교",
                ]
            }

        except Exception:
            return {
                "core": "핵심 개념 연결 부족",
                "reason": "세부 원리와 응용 연결이 약합니다.",
                "extra": [
                    "기초 정의 다시 보기",
                    "대표 문제 반복",
                    "실수 사례 비교",
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
        <div style='position: absolute; right: 28%; bottom: -8px; font-size: 0.8rem; color: #8b949e;'>by Jun</div>
    </div>
    """, unsafe_allow_html=True)

    topic = st.text_input("학습 주제", placeholder="예: 근의공식, SQL 오류, 영어 문장")

    if st.button("빠른 진단 시작"):
        if topic:
            progress_text = st.empty()
            progress_bar = st.progress(0)

            progress_text.markdown("### 열심히 탐색중!! 🤗")

            found = False
            questions = []

            start_time = time.time()

            while time.time() - start_time < 60:
                elapsed = time.time() - start_time
                progress = min(int((elapsed / 60) * 100), 100)
                progress_bar.progress(progress)

                questions = engine.generate_questions(topic, timeout=5)

                if len(questions) == 5:
                    found = True
                    break

            progress_bar.progress(100)
            progress_text.markdown("### 탐색 완료! ✨")

            if not found:
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

    if not weak_points:
        st.success("기초 개념이 충분히 잡혀 있습니다.")
    else:
        result = engine.generate_report(
            st.session_state.data["topic"],
            weak_points
        )

        st.markdown(f"""
        <div class='result-card'>
        <b>놓친 핵심 개념</b><br>
        {result["core"]}
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class='result-card'>
        <b>왜 놓쳤는지 설명</b><br>
        {result["reason"]}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='result-card'><b>추가로 필요한 부분</b><br>", unsafe_allow_html=True)

        for item in result["extra"]:
            search_link = f"https://chat.openai.com/?q={item}"
            st.markdown(f"- [{item}]({search_link})")

        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
