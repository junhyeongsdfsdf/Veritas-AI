import streamlit as st
import google.generativeai as genai
import time
import random
from google.api_core import exceptions

# [1. 시스템 환경 및 UI 최적화]
st.set_page_config(page_title="Veritas AI: Invincible Engine", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e6edf3; }
    .diag-card { padding: 25px; border-radius: 12px; border: 1px solid #30363d; background-color: #161b22; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .stButton>button { background-color: #238636; color: white; border-radius: 8px; height: 3.5rem; font-weight: bold; width: 100%; border: none; }
    .stButton>button:hover { background-color: #2ea043; border: 1px solid #3fb950; }
    .status-box { padding: 10px; border-radius: 5px; background-color: #0d1117; border-left: 5px solid #1f6feb; font-family: monospace; font-size: 0.85rem; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# [2. 지능형 모델 핸들러: 404/429 에러 방어막]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System Key (Google AI Studio)", type="password")

if not api_key:
    st.error("🔑 API Key가 필요합니다. Secrets 설정 혹은 사이드바를 확인하세요.")
    st.stop()

genai.configure(api_key=api_key)

@st.cache_resource
def get_working_model():
    """사용자 키가 허용하는 모델을 실시간으로 스캔하여 '살아있는' 엔진을 확보합니다."""
    try:
        # 1. 내 키가 쓸 수 있는 모델 리스트 직접 조회 (404 원천 차단)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 2. 선호도 순서 (안정적인 모델 위주)
        priority = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for target in priority:
            for actual in available_models:
                if target in actual:
                    try:
                        m = genai.GenerativeModel(actual)
                        # 실제 작동 테스트 (Quota 확인용)
                        m.generate_content("ping", generation_config={"max_output_tokens": 1})
                        return m, actual
                    except: continue
        
        # 3. 우선순위 실패 시 리스트 중 첫 번째 모델 강제 선택
        if available_models:
            return genai.GenerativeModel(available_models[0]), available_models[0]
    except Exception as e:
        st.error(f"API 연결 구성 실패: {e}")
    return None, None

engine, active_model_name = get_working_model()

def safe_generate(prompt, max_retries=5):
    """할당량 초과(429) 시 비굴할 정도로 대기하며 재시도하는 로직"""
    if not engine: return None
    
    for i in range(max_retries):
        try:
            return engine.generate_content(prompt)
        except exceptions.ResourceExhausted:
            wait_time = (i + 1) * 10 + random.uniform(1, 3)
            st.warning(f"⏳ 서버 할당량 초과. {int(wait_time)}초 후 자동으로 다시 시도합니다... ({i+1}/{max_retries})")
            time.sleep(wait_time)
        except Exception as e:
            if i == max_retries - 1:
                st.error(f"❌ 최종 호출 실패: {e}")
                return None
            time.sleep(2)
    return None

if not engine:
    st.error("❌ 현재 API 키로 사용 가능한 모델을 찾지 못했습니다.")
    st.info("Google AI Studio에서 새로운 API 키를 발급받아 교체해보시는 것을 권장합니다.")
    st.stop()

# [3. 진단 프로세스 상태 관리]
if 'stage' not in st.session_state: st.session_state.stage = 'input'
if 'topic' not in st.session_state: st.session_state.topic = ""
if 'raw_res' not in st.session_state: st.session_state.raw_res = ""

# --- PHASE 1: 주제 설정 및 지식 구조 해체 ---
if st.session_state.stage == 'input':
    st.title("🔍 Veritas AI: 정밀 진단 시스템")
    st.markdown(f"<div class='status-box'>Connected Engine: {active_model_name}</div>", unsafe_allow_html=True)
    st.write("막힌 개념의 뿌리를 추적하여 **진정한 페인포인트**를 도출합니다.")
    
    topic_input = st.text_input("진단받을 개념을 입력하세요:", placeholder="예: 근의 공식, 재귀함수, 양자역학 등")
    
    if st.button("진단 엔진 가동"):
        if topic_input:
            with st.spinner("지식의 위계 구조를 분석 중..."):
                prompt = f"""
                당신은 전과목 교육 진단 전문가입니다. 주제: '{topic_input}'
                1. 이 주제의 핵심 정의를 2문장 이내로 정리하세요.
                2. 이 주제를 이해하기 위해 반드시 필요한 '선행 지식' 5가지를 검증할 수 있는 구체적인 Yes/No 질문을 만드세요.
                질문 형식: '1. 질문내용'
                """
                res = safe_generate(prompt)
                if res:
                    st.session_state.raw_res = res.text
                    st.session_state.topic = topic_input
                    st.session_state.stage = 'testing'
                    st.rerun()

# --- PHASE 2: 5단계 역추적 진단 시뮬레이션 ---
elif st.session_state.stage == 'testing':
    st.subheader(f"🚩 '{st.session_state.topic}' 역진단 시뮬레이션")
    st.write("이해의 끈이 어디서 끊어졌는지 확인하기 위해 아래 질문에 답하세요.")
    
    with st.form("diagnosis_form"):
        lines = st.session_state.raw_res.split('\n')
        qs = [l.strip() for l in lines if l.strip() and l.strip()[0].isdigit() and ('.' in l or ')' in l)]
        
        user_responses = []
        for i, q in enumerate(qs[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태 체크", ["이해하고 있음(Yes)", "모름/모호함(No)"], key=f"ans_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_input("어떤 지점이 사고가 막히나요?", key=f"reason_{i}", placeholder="구체적인 이유를 적을수록 진단이 정확해집니다.")
            user_responses.append({"q": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.form_submit_button("최종 페인포인트 모델링"):
            st.session_state.user_responses = user_responses
            st.session_state.stage = 'report'
            st.rerun()

# --- PHASE 3: 최종 페인포인트 모델링 리포트 ---
elif st.session_state.stage == 'report':
    st.title("📋 지식 결손 정밀 진단서")
    
    with st.spinner("응답 패턴을 기반으로 당신의 '진짜 구멍'을 모델링 중..."):
        no_data = [d for d in st.session_state.user_responses if "No" in d['status']]
        
        if not no_data:
            st.success("해당 주제에 대한 지식 체계가 완벽합니다! 심화 단계로 나아가셔도 좋습니다.")
        else:
            final_prompt = f"""
            학습자가 '{st.session_state.topic}'에 대해 다음 질문들에 'No'라고 답했습니다:
            {no_data}
            
            사용자가 직접 적은 사유를 바탕으로 '진정한 페인포인트(Root Cause)'를 도출하세요.
            1. 발견된 결손 지점 (어느 단계의 논리가 무너졌는가)
            2. 인지적 오류 분석 (단순 지식이 부족한지, 개념을 오해하고 있는지 분석)
            3. 학습 우선순위 제언 (현재 진도를 멈추고 당장 되돌아가야 할 구체적인 기초 지점)
            """
            report = safe_generate(final_prompt)
            if report:
                st.markdown(f"<div class='diag-card' style='border-left: 10px solid #238636;'>{report.text}</div>", unsafe_allow_html=True)

    if st.button("새로운 주제 진단하기"):
        st.session_state.stage = 'input'
        st.rerun()
