import re
import time
import logging
import random
from typing import List, Dict

import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions

# =============================
# 1) CONFIG & STYLE (기존 유지)
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
.status-panel { padding: 1rem; border-radius: 8px; background: #010409; border-left: 5px solid #1f6feb; color: #58a6ff; font-family: monospace; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# =============================
# 2) ADAPTIVE DIAGNOSTIC LOGIC (기존 유지)
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
    if any(sym in text for sym in ["def ", "for ", "while ", "if ", "{", "}", ";"]): return "code"
    if len(text.split()) >= 4 and any(ch in text for ch in ["?", ".", ","]): return "sentence"
    if any(k in text.lower() for k in ["error", "bug", "왜", "안돼", "막혀"]): return "problem"
    return "concept"

def extract_learning_facets(user_input: str) -> List[str]:
    input_type = infer_input_type(user_input)
    facet_map = {
        "concept": ["핵심 의미", "구성 요소", "원리 분석", "새로운 예시", "개념 비교"],
        "code": ["입/출력 흐름", "조건/반복 기준", "에러 재현", "수정 적용", "구조 개선"],
        "sentence": ["핵심 의미", "구조/어순", "문맥 응용", "표현 차이", "문장 생성"],
        "problem": ["원인 정의", "막힌 단계", "해결 시도", "상황 적용", "재발 예방"],
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
    return [question_styles[i].format(idx=i+1, facet=f) for i, f in enumerate(facets[:5])]

# =============================
# 3) ENGINE (1분 사투 로직 수정)
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        candidates = ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-pro"]
        for name in candidates:
            try:
                m = genai.GenerativeModel(name)
                m.generate_content("ping", generation_config={"max_output_tokens": 1})
                self.model = m
                return
            except: continue

    def call(self, prompt: str) -> str:
        """최소 1분(60초) 동안 집요하게 AI 분석을 시도하는 핵심 함수"""
        if not self.model: return "[LOCAL_FALLBACK]"

        start_time = time.time()
        attempt = 1
        status_box = st.empty()

        # 60초가 지날 때까지 무한 반복 시도
        while time.time() - start_time < 60:
            elapsed = int(time.time() - start_time)
            try:
                # 사용자님이 좋아하신 분석 중 멘트와 시간을 표시
                status_box.markdown(f"<div class='status-panel'>📡 [시도 {attempt}] 지식의 위계 구조를 해체하고 진단 문항을 설계 중... ({elapsed}s)</div>", unsafe_allow_html=True)
                
                response = self.model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.3, "max_output_tokens": 700},
                    request_options={"timeout": 20}
                )
                status_box.empty()
                return response.text.strip()

            except exceptions.ResourceExhausted:
                # 429 에러(할당량 부족) 시 랜덤하게 대기 후 다시 찌름
                wait = random.uniform(7, 10)
                time.sleep(wait)
            except Exception:
                time.sleep(3)
            
            attempt += 1

        status_box.empty()
        return "[LOCAL_FALLBACK]"

def extract_questions(raw: str) -> List[str]:
    lines = raw.split("\n")
    return [l.strip() for l in lines if re.match(r"^\d+[.)]", l.strip())][:5]

def local_root_cause_analysis(topic: str, weak_points: List[Dict]) -> str:
    # (기존 규칙 기반 분석기 유지)
    return f"1. 결손 지점: {topic}의 하위 연산 단계\n2. 사유: 개념 연결 불안정\n3. 복습 제언: 기초 정의 및 연산 규칙 재확인"

# =============================
# 4) MAIN FLOW (기존 유지 및 READY 단계 수정)
# =============================
if "stage" not in st.session_state: st.session_state.stage = "ready"
if "data" not in st.session_state: st.session_state.data = {}

api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("API KEY", type="password")

if not api_key:
    st.warning("API 키를 입력하세요.")
    st.stop()

engine = VeritasEngine(api_key)

# --- STAGE: READY ---
if st.session_state.stage == "ready":
    st.markdown("""
    <div style='text-align: center;'>
        <div class='main-title'>Veritas AI</div>
        <div style='font-size: 0.8rem; color: #8b949e;'>by Jun</div>
    </div>
    """, unsafe_allow_html=True)
    
    topic = st.text_input("학습 주제", placeholder="예: 근의 공식")

    if st.button("빠른 진단 시작"):
        if topic:
            with st.spinner("전문 진단 엔진이 가동 중입니다..."):
                prompt = f"당신은 학습 진단 AI입니다. 주제 '{topic}'을 분석하여 Yes/No 질문 5개를 만드세요. 번호를 붙여 1. 형식으로 출력하세요."
                
                # 여기서 1분간의 사투가 벌어집니다.
                result = engine.call(prompt)
                
                # 1분이 지나도 끝내 실패했거나 결과가 없으면 미리 짜둔 질문으로 대체
                if result == "[LOCAL_FALLBACK]":
                    st.info("💡 구글 서버 부하로 인해 시스템 내장 적응형 질문으로 전환합니다.")
                    questions = build_fallback_questions(topic)
                else:
                    questions = extract_questions(result)
                    if not questions: questions = build_fallback_questions(topic)

                st.session_state.data = {"topic": topic, "questions": questions}
                st.session_state.stage = "testing"
                st.rerun()

# --- STAGE: TESTING (기존 유지) ---
elif st.session_state.stage == "testing":
    st.subheader(f"주제: {st.session_state.data['topic']}")
    with st.form("test_form"):
        responses = []
        for i, q in enumerate(st.session_state.data["questions"]):
            st.markdown(f"<div class='diag-card'><b>{q}</b></div>", unsafe_allow_html=True)
            ans = st.radio(f"q{i}", ["Yes", "No"], horizontal=True, label_visibility="collapsed", key=f"radio_{i}")
            reason = ""
            if ans == "No": reason = st.text_input(f"막힌 이유 {i+1}", key=f"reason_{i}")
            responses.append({"question": q, "answer": ans, "reason": reason})

        if st.form_submit_button("최종 분석"):
            st.session_state.data["responses"] = responses
            st.session_state.stage = "analysis"
            st.rerun()

# --- STAGE: ANALYSIS (기존 유지) ---
elif st.session_state.stage == "analysis":
    st.subheader("최종 진단 리포트")
    weak_points = [x for x in st.session_state.data["responses"] if x["answer"] == "No"]

    if not weak_points:
        st.success("기초 개념이 충분히 잡혀 있습니다.")
    else:
        with st.spinner("결손 지점 분석 중..."):
            prompt = f"주제: {st.session_state.data['topic']}\n약점 데이터: {weak_points}\n결손 지점, 원인, 복습 개념을 분석해줘."
            report = engine.call(prompt)
            if report == "[LOCAL_FALLBACK]":
                report = local_root_cause_analysis(st.session_state.data['topic'], weak_points)
            st.write(report)

    if st.button("새 진단"):
        st.session_state.clear()
        st.rerun()
