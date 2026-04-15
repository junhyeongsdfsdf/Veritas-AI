import re
import time
import random
import logging
from typing import List, Dict

import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions

# ==========================================
# 1) SYSTEM CONFIG & STYLING
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Veritas AI | Smart Diagnostic",
    page_icon="🔍",
    layout="centered",
)

# 사용자님이 선호하시는 전문적인 다크 테마 적용
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .main-title { color: #58a6ff; font-size: 2.8rem; font-weight: 800; text-align: center; margin-bottom: 0.5rem; }
    .sub-title { color: #8b949e; text-align: center; margin-bottom: 2rem; }
    .diag-card { 
        padding: 1.5rem; border: 1px solid #30363d; border-radius: 12px; 
        margin-bottom: 1.2rem; background: #161b22; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .status-panel {
        padding: 1rem; border-radius: 8px; background: #010409;
        border-left: 5px solid #1f6feb; color: #58a6ff;
        font-family: 'Courier New', monospace; margin-bottom: 1rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white; border: none; font-weight: bold; height: 3.5rem; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2) ADAPTIVE FALLBACK LOGIC (안전장치)
# ==========================================
UNIVERSAL_DIAGNOSTIC_DIMENSIONS = [
    "핵심 개념을 자신의 말로 설명 가능합니까?",
    "해당 개념의 구성 요소를 명확히 구분할 수 있나요?",
    "동작 원리나 문맥을 타인에게 이해시킬 수 있습니까?",
    "실제 예시에 바로 적용할 수 있는 상태인가요?",
    "유사한 개념과 섞였을 때 차이점을 구별할 수 있나요?",
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
        "concept": ["의미 이해", "구조 구분", "원리 분석", "응용 가능성", "개념 비교"],
        "code": ["흐름 추적", "로직 이해", "디버깅 역량", "코드 수정", "최적화 사고"],
        "sentence": ["문맥 파악", "구조 분석", "문장 응용", "표현 차이", "작문 능력"],
        "problem": ["원인 정의", "단계 분석", "해결 시도", "유형 확장", "재발 방지"],
    }
    return facet_map.get(input_type, ["기초 이해", "구성 분석", "작동 원리", "실무 적용", "유사 비교"])

def build_fallback_questions(topic: str) -> List[str]:
    facets = extract_learning_facets(topic)
    questions = []
    for i, facet in enumerate(facets[:5]):
        questions.append(f"{i+1}. 현재 입력한 내용에서 '{facet}' 단계가 스스로 막혀있다고 느껴지시나요?")
    return questions

# ==========================================
# 3) INDOMITABLE ENGINE (1분 사투 로직)
# ==========================================
class VeritasEngine:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        candidates = ["gemini-1.5-flash", "gemini-pro"]
        for name in candidates:
            try:
                model = genai.GenerativeModel(name)
                model.generate_content("test", generation_config={"max_output_tokens": 1})
                self.model = model
                return
            except: continue

    def call(self, prompt: str) -> str:
        """최소 1분(60초) 동안 사력을 다해 AI 분석을 시도하는 집요한 함수"""
        if not self.model: return "[LOCAL_FALLBACK]"

        start_time = time.time()
        attempt = 1
        status_box = st.empty()

        while time.time() - start_time < 60:
            elapsed = int(time.time() - start_time)
            try:
                status_box.markdown(f"<div class='status-panel'>🔍 [분석 시도 {attempt}] 지식의 심층 위계를 해체하는 중... ({elapsed}초 경과)</div>", unsafe_allow_html=True)
                
                response = self.model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.4, "max_output_tokens": 800},
                    request_options={"timeout": 20}
                )
                status_box.empty()
                return response.text.strip()

            except exceptions.ResourceExhausted:
                # 할당량 초과 시 8~12초 대기하며 재시도 (1분 내에 여러 번 찌름)
                wait = random.uniform(8, 12)
                status_box.markdown(f"<div class='status-panel'>⏳ 서버 과부하 감지. {int(wait)}초간 지능적 대기 후 재진입합니다...</div>", unsafe_allow_html=True)
                time.sleep(wait)
            except Exception as e:
                time.sleep(5)
            
            attempt += 1

        status_box.empty()
        return "[LOCAL_FALLBACK]"

def extract_questions(raw: str) -> List[str]:
    lines = raw.split("\n")
    results = [l.strip() for l in lines if re.match(r"^\d+[.)]", l.strip())]
    return results[:5]

# ==========================================
# 4) INTERFACE LOGIC
# ==========================================
if "stage" not in st.session_state: st.session_state.stage = "ready"
if "data" not in st.session_state: st.session_state.data = {}

api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("ENTER SYSTEM KEY", type="password")

if not api_key:
    st.warning("시스템 가동을 위해 API KEY가 필요합니다.")
    st.stop()

engine = VeritasEngine(api_key)

# --- STAGE: READY ---
if st.session_state.stage == "ready":
    st.markdown("<div class='main-title'>Veritas AI</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>지식의 뿌리를 추적하여 결손 지점을 모델링합니다.</div>", unsafe_allow_html=True)
    
    topic = st.text_input("진단할 주제 (개념/코드/문장):", placeholder="예: 근의 공식, 재귀함수, 이차방정식...")

    if st.button("정밀 진단 가동"):
        if topic:
            with st.spinner("AI가 지식의 위계 구조를 해체하고 있습니다..."):
                prompt = f"""
                당신은 학습 진단 AI입니다. 주제: {topic}
                중요 규칙:
                1. 입력 타입을 추론(개념/코드/문장/오류)하고 그에 맞는 5단계 질문을 만드세요.
                2. 질문은 반드시 Yes/No로 답할 수 있는 폐쇄형이어야 합니다.
                3. 사용자가 다음 단계에서 실패할 가능성이 큰 지점을 예측하여 질문하세요.
                출력 형식:
                1. 질문 내용
                2. 질문 내용
                ... (총 5개)
                """
                result = engine.call(prompt)
                
                if result == "[LOCAL_FALLBACK]":
                    st.info("💡 구글 서버가 응답하지 않아 시스템 내장 로직으로 질문을 생성했습니다.")
                    questions = build_fallback_questions(topic)
                else:
                    questions = extract_questions(result)
                    if not questions: questions = build_fallback_questions(topic)

                st.session_state.data = {"topic": topic, "questions": questions}
                st.session_state.stage = "testing"
                st.rerun()

# --- STAGE: TESTING ---
elif st.session_state.stage == "testing":
    st.subheader(f"🔍 진단 주제: {st.session_state.data['topic']}")
    st.write("본인의 이해도를 정직하게 체크해주세요.")

    with st.form("diag_form"):
        user_responses = []
        for i, q in enumerate(st.session_state.data["questions"]):
            st.markdown(f"<div class='diag-card'><b>{q}</b></div>", unsafe_allow_html=True)
            ans = st.radio(f"q{i}", ["Yes", "No"], horizontal=True, label_visibility="collapsed", key=f"radio_{i}")
            reason = ""
            if ans == "No":
                reason = st.text_input(f"어느 지점이 모호한가요?", key=f"reason_{i}", placeholder="예: 용어가 헷갈려요, 계산 순서를 모르겠어요.")
            user_responses.append({"question": q, "answer": ans, "reason": reason})

        if st.form_submit_button("최종 결손 지점 분석"):
            st.session_state.data["responses"] = user_responses
            st.session_state.stage = "analysis"
            st.rerun()

# --- STAGE: ANALYSIS ---
elif st.session_state.stage == "analysis":
    st.subheader("📋 Veritas 정밀 진단 리포트")
    weak_points = [x for x in st.session_state.data["responses"] if x["answer"] == "No"]

    if not weak_points:
        st.success("🎉 진단 결과: 기초 개념이 매우 탄탄합니다. 심화 학습을 권장합니다.")
    else:
        with st.spinner("인지적 구멍을 모델링하는 중..."):
            prompt = f"주제: {st.session_state.data['topic']}\n약점 데이터: {weak_points}\n위 데이터를 바탕으로 결손 지점, 발생 원인, 복습해야 할 기초 개념을 정리해줘."
            report = engine.call(prompt)
            
            if report == "[LOCAL_FALLBACK]":
                # AI가 리포트 생성도 실패할 경우 로컬 규칙 기반 분석 가동
                from app import local_root_cause_analysis # 필요시 별도 함수화
                st.write("### AI 분석 지연으로 인한 시스템 기본 분석 결과")
                st.info("사고가 끊긴 지점: 하위 연산 또는 개념 단계")
                st.write("- **당장 복습할 지점:** 입력하신 주제의 정의 및 사칙연산 규칙")
            else:
                st.markdown(f"<div class='diag-card' style='border-left: 8px solid #238636;'>{report}</div>", unsafe_allow_html=True)

    if st.button("새로운 진단 시작"):
        st.session_state.clear()
        st.rerun()
