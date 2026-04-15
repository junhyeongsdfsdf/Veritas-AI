import re
import time
import logging
from typing import List, Dict
from urllib.parse import quote

import streamlit as st
from openai import OpenAI


# =============================
# CONFIG (원본 유지)
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
.main-title { color: #58a6ff; font-size: 2.8rem; font-weight: 900; text-align: center; }
.result-title { color: #58a6ff; font-size: 3rem; font-weight: 900; text-align: center; margin-bottom: 2rem; }
.diag-card { padding: 1rem; border: 1px solid #30363d; border-radius: 12px; margin-bottom: 1rem; background: #161b22; }
.category-card { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 1.2rem; margin-bottom: 1rem; }
.category-title { color: #58a6ff; font-size: 1.4rem; font-weight: 700; margin-bottom: 0.7rem; }
.wrong-note { border-left: 5px solid #f85149; padding-left: 1rem; background: #1c2128; }
</style>
""", unsafe_allow_html=True)


# =============================
# QUESTION HELPERS (원본 유지)
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
    results = [l.strip() for l in lines if re.match(r"^\d+[.)]", l.strip())]
    return results[:5]


# =============================
# GPT ENGINE (원본 유지)
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
# DIAGNOSIS ENGINE (사족 제거 및 개념 집중)
# =============================
def build_smart_diagnosis_from_no(weak_points: List[Dict], topic: str) -> Dict:
    missed = []
    explanations = []
    extras = []

    for item in weak_points:
        q = item["question"]

        if "반례" in q:
            concept = f"{topic}의 예외 상황(반례) 식별"
            explanation = (
                f"{topic}의 일반적인 규칙이 적용되지 않거나 모순이 발생하는 특수 사례를 의미합니다. "
                f"개념의 완성도를 높이기 위해서는 정의를 만족하지 않는 경계 조건(Boundary Condition)을 구분해야 합니다."
            )
            extra = [f"{topic}의 대표적인 반례 사례", f"{topic} 예외 조건 분석", f"{topic} 정의의 한계"]

        elif "조건" in q or "단계" in q:
            concept = f"{topic}의 연산 절차 및 전제 조건"
            explanation = (
                f"{topic}를 수행하기 위해 선행되어야 하는 수학적/논리적 환경과 그에 따른 단계별 프로세스를 의미합니다. "
                f"특정 조건의 변화가 결과값에 미치는 영향력을 인과관계에 따라 추적하는 과정이 필요합니다."
            )
            extra = [f"{topic} 단계별 계산법", f"{topic} 적용을 위한 필수 조건", f"{topic} 변수 변화 시뮬레이션"]

        else:
            concept = f"{topic}의 근본 원리 및 메커니즘"
            explanation = (
                f"{topic}라는 개념이 성립하게 된 배경과 그 내부의 작동 원리를 뜻합니다. "
                f"단순한 결과 도출이 아닌, 수식이나 이론이 구성되는 논리적 구조를 이해하는 것이 핵심입니다."
            )
            extra = [f"{topic} 원리 상세 정의", f"{topic} 내부 구조 분석", f"{topic} 도출 과정 복습"]

        missed.append(f"• {concept}")
        explanations.append(f"• {explanation}")
        extras.extend(extra)

    return {
        "놓친개념": "<br>".join(sorted(set(missed))),
        "개념설명": "<br><br>".join(sorted(set(explanations))),
        "추가로 필요한 부분": sorted(set(extras)),
    }


# =============================
# SESSION & API (원본 유지)
# =============================
if "stage" not in st.session_state: st.session_state.stage = "ready"
if "data" not in st.session_state: st.session_state.data = {}

api_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input("OPENAI API KEY", type="password")
if not api_key:
    st.warning("OPENAI API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)


# =============================
# READY PAGE (원본 유지)
# =============================
if st.session_state.stage == "ready":
    st.markdown("<div style='text-align:center;'><div class='main-title'>Veritas AI</div><div style='font-size:0.9rem; color:#8b949e;'>by Jun</div></div>", unsafe_allow_html=True)
    topic = st.text_input("학습 주제", placeholder="예: 근의 공식, SQL JOIN 등")
    if st.button("빠른 진단 시작"):
        if topic:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            progress_text.markdown("### 열심히 탐색중!! 🤗")
            result, found, start_time = None, False, time.time()
            while time.time() - start_time < 60:
                elapsed = time.time() - start_time
                progress_bar.progress(min(int((elapsed / 60) * 100), 100))
                result = engine.call(f"주제: {topic}\n내용: 취약 개념 OX 퀴즈 5개 생성 (Yes/No형, 반례/응용 포함, 번호 1~5)")
                questions = extract_questions(result)
                if len(questions) >= 5:
                    found = True
                    break
                time.sleep(3)
            progress_bar.progress(100)
            progress_text.markdown("### 탐색 완료! ✨")
            if not found: questions = build_fallback_questions(topic)
            st.session_state.data = {"topic": topic, "questions": questions}
            st.session_state.stage = "testing"
            st.rerun()


# =============================
# TEST PAGE (원본 유지)
# =============================
elif st.session_state.stage == "testing":
    st.subheader(f"주제: {st.session_state.data['topic']}")
    with st.form("test_form"):
        responses = []
        for i, q in enumerate(st.session_state.data["questions"]):
            st.markdown(f"<div class='diag-card'><b>{q}</b></div>", unsafe_allow_html=True)
            ans = st.radio(f"q{i}", ["Yes", "No"], horizontal=True, key=f"radio_{i}")
            responses.append({"question": q, "answer": ans})
        if st.form_submit_button("최종 분석"):
            st.session_state.data["responses"] = responses
            st.session_state.stage = "analysis"
            st.rerun()


# =============================
# ANALYSIS PAGE (요청 사항 집중 수정)
# =============================
elif st.session_state.stage == "analysis":
    st.markdown("<div class='result-title'>진단 결과 😋</div>", unsafe_allow_html=True)

    weak_points = [x for x in st.session_state.data["responses"] if x["answer"] == "No"]

    if not weak_points:
        st.success("🎉 현재 모든 핵심 개념에 대한 이해도가 완벽합니다!")
    else:
        # 1. 오답 노트 (사용자 입력 기반)
        st.markdown("### 📝 오답 노트")
        for wp in weak_points:
            st.markdown(f"<div class='diag-card wrong-note'><b>❌ 확인 필요:</b> {wp['question']}</div>", unsafe_allow_html=True)
        
        st.divider()

        # 2. 스마트 진단 데이터 생성
        result = build_smart_diagnosis_from_no(weak_points, st.session_state.data["topic"])

        # 놓친 개념
        st.markdown(f"<div class='category-card'><div class='category-title'>놓친 개념</div>{result['놓친개념']}</div>", unsafe_allow_html=True)

        # 개념 설명 (군더더기 없는 오리지널 설명)
        st.markdown(f"<div class='category-card'><div class='category-title'>개념 설명</div>{result['개념설명']}</div>", unsafe_allow_html=True)

        # 추가로 필요한 부분 (챗지피티 링크 삽입)
        extra_html = ""
        for extra in result["추가로 필요한 부분"]:
            # 챗지피티 검색 URL (https://chatgpt.com/?q=내용)
            search_link = f"https://chatgpt.com/?q={quote(extra)}"
            extra_html += f"""
            <div style='margin-top:0.7rem;'>
                <a href="{search_link}" target="_blank" style="color:#c9d1d9; text-decoration:none;">
                   • <span style="text-decoration:underline;">{extra}</span> 🔗
                </a>
            </div>
            """

        st.markdown(f"<div class='category-card'><div class='category-title'>추가로 필요한 부분 (클릭 시 ChatGPT 검색)</div>{extra_html}</div>", unsafe_allow_html=True)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
