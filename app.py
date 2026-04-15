import re
import time
import logging
import random
from typing import List, Dict

import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions

# =============================
# 1) CONFIG & STYLE (기본 유지)
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
# 2) ADAPTIVE DIAGNOSTIC LOGIC (기본 유지)
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
# 3) ENGINE (집요함 500% 보강)
# =============================
class VeritasEngine:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """작동 가능한 모델을 탐색합니다."""
        candidates = ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-pro"]
        for name in candidates:
            try:
                m = genai.GenerativeModel(name)
                m.generate_content("ping", generation_config={"max_output_tokens": 1})
                self.model = m
                return
            except: continue

    def call(self, prompt: str) -> str:
        """60초 동안 수단과 방법을 가리지 않고 답변을 쟁취합니다."""
        start_time = time.time()
        attempt = 1
        status_box = st.empty()

        while time.time() - start_time < 60:
            elapsed = int(time.time() - start_time)
            
            # 1. 모델이 없으면 여기서 즉시 다시 초기화 시도 (바로 포기 금지)
            if not self.model:
                status_box.markdown(f"<div class='status-panel'>⚙️ [시스템 복구] AI 엔진을 재구성하고 있습니다... ({elapsed}s)</div>", unsafe_allow_html=True)
                self._initialize_model()
                time.sleep(3)
                continue

            try:
                status_box.markdown(f"<div class='status-panel'>📡 [시도 {attempt}] 지식의 위계 구조를 해체하고 진단 문항을 설계 중... ({elapsed}s)</div>", unsafe_allow_html=True)
                
                # 타임아웃을 넉넉히 주어 끈질기게 응답 대기
                response = self.model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.4, "max_output_tokens": 700},
                    request_options={"timeout": 30}
                )
                
                if response and response.text:
                    status_box.empty()
                    return response.text.strip()

            except exceptions.ResourceExhausted:
                # 429 할당량 초과 시, 뒤로 물러나되 포기하지 않음
                wait = random.uniform(8, 12)
                status_box.markdown(f"<div class='status-panel'>⏳ 서버 과부하 감지. {int(wait)}초간 지능적 대기 후 재진입합니다... ({elapsed}s)</div>", unsafe_allow_html=True)
                time.sleep(wait)
            except Exception as e:
                # 일반 에러 시 잠시 쉬었다가 재시도
                time.sleep(4)
            
            attempt += 1

        status_box.empty()
        return "[LOCAL_FALLBACK]"

def extract_questions(raw: str) -> List[str]:
    lines = raw.split("\n")
    return [l.strip() for l in lines if re.match(r"^\d+[.)]", l.strip())][:5]

# =============================
# 4) MAIN INTERFACE (READY 단계 로직 정밀 수정)
# =============================
if "stage" not in st.session_state: st.session_state.stage = "ready"
if "data" not in st.session_state: st.session_state.data = {}

api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("API KEY", type="password")

if not api_key:
    st.warning("시스템 가동을 위해 API KEY가 필요합니다.")
    st.stop()

engine = VeritasEngine(api_key)

if st.session_state.stage == "ready":
    st.markdown("""
    <div style='text-align: center;'>
        <div class='main-title'>Veritas AI</div>
        <div style='font-size: 0.8rem; color: #8b949e;'>Root-Cause Intelligence by Jun</div>
    </div>
    """, unsafe_allow_html=True)
    
    topic = st.text_input("진단할 학습 주제", placeholder="예: 근의 공식, 재귀함수...")

    if st.button("전문 진단 엔진 가동"):
        if topic:
            # Spinner가 돌기 시작함과 동시에 1분간의 사투 시작
            with st.spinner("지식의 위계를 추적하고 있습니다..."):
                prompt = f"""당신은 교육 공학 전문가입니다. 주제 '{topic}'을 인지적으로 해체하여 
                Yes/No로 답할 수 있는 5단계 진단 질문을 생성하세요. 번호를 붙여 1. 형식으로 출력하세요."""
                
                # [여기가 핵심] call 내부에서 60초를 소모함
                result = engine.call(prompt)
                
                # 60초가 지난 '후'에만 아래 조건문을 탐
                if result == "[LOCAL_FALLBACK]":
                    st.info("💡 장시간 서버 무응답으로 인해 시스템 내장 적응형 질문으로 대체합니다.")
                    questions = build_fallback_questions(topic)
                else:
                    questions = extract_questions(result)
                    # 만약 AI 답변 형식이 잘못되었을 때도 포기하지 않고 백업 질문 사용
                    if not questions: questions = build_fallback_questions(topic)

                st.session_state.data = {"topic": topic, "questions": questions}
                st.session_state.stage = "testing"
                st.rerun()

# --- STAGE: TESTING & ANALYSIS (기존 유지) ---
elif st.session_state.stage == "testing":
    st.subheader(f"🔍 주제: {st.session_state.data['topic']}")
    with st.form("test_form"):
        responses = []
        for i, q in enumerate(st.session_state.data["questions"]):
            st.markdown(f"<div class='diag-card'><b>{q}</b></div>", unsafe_allow_html=True)
            ans = st.radio(f"q{i}", ["Yes", "No"], horizontal=True, label_visibility="collapsed", key=f"radio_{i}")
            reason = ""
            if ans == "No": reason = st.text_input(f"상세 이유", key=f"reason_{i}", placeholder="어느 지점에서 막히나요?")
            responses.append({"question": q, "answer": ans, "reason": reason})

        if st.form_submit_button("최종 진단 보고서 생성"):
            st.session_state.data["responses"] = responses
            st.session_state.stage = "analysis"
            st.rerun()

elif st.session_state.stage == "analysis":
    st.subheader("📋 Veritas 정밀 진단 리포트")
    weak_points = [x for x in st.session_state.data["responses"] if x["answer"] == "No"]

    if not weak_points:
        st.success("🎉 기초 개념이 매우 탄탄합니다. 현재 진도를 유지하셔도 좋습니다.")
    else:
        with st.spinner("인지 구조 모델링 중..."):
            prompt = f"주제: {st.session_state.data['topic']}\n약점 데이터: {weak_points}\n결손 지점과 원인, 복습할 기초 개념을 정리해줘."
            report = engine.call(prompt)
            if report == "[LOCAL_FALLBACK]":
                st.write("### 시스템 기본 분석 결과")
                st.info("하위 연산 단계에서 논리적 단절이 확인되었습니다. 입력하신 주제의 기초 정의를 다시 확인하세요.")
            else:
                st.markdown(f"<div class='diag-card' style='border-left: 8px solid #238636;'>{report}</div>", unsafe_allow_html=True)

    if st.button("새로운 진단 시작"):
        st.session_state.clear()
        st.rerun()
