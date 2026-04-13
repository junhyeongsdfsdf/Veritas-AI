import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# [1. 시스템 최적화 설정]
st.set_page_config(page_title="Veritas AI | Diagnostic Engine", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .diag-card { padding: 25px; border-radius: 15px; border: 1px solid #dee2e6; background-color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .stButton>button { background-color: #1a73e8; color: white; border-radius: 8px; height: 3.5rem; font-weight: bold; width: 100%; border: none; }
    .stButton>button:hover { background-color: #1557b0; }
    </style>
    """, unsafe_allow_html=True)

# [2. 지능형 엔진 로더: 429 할당량 초과 자동 회복]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System API Key", type="password")

if not api_key:
    st.info("💡 시스템 작동을 위해 API Key가 필요합니다. Secrets 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

def call_ai_with_backoff(model, prompt, max_retries=5):
    """구글 서버의 속도 제한(429) 발생 시 지수 백오프 전략으로 재시도합니다."""
    for i in range(max_retries):
        try:
            return model.generate_content(prompt)
        except exceptions.ResourceExhausted:
            wait_time = (i + 1) * 5  # 재시도마다 대기 시간 증가 (5초, 10초...)
            st.warning(f"⚠️ 구글 서버 과부하로 {i+1}차 재시도 중... {wait_time}초 후 다시 시도합니다.")
            time.sleep(wait_time)
        except Exception as e:
            st.error(f"알 수 없는 오류 발생: {e}")
            return None
    return None

@st.cache_resource
def get_stable_engine():
    """가장 할당량이 넉넉한 1.5-flash 모델을 선점합니다."""
    try:
        m = genai.GenerativeModel('gemini-1.5-flash')
        # 연결 테스트
        m.generate_content("ping", generation_config={"max_output_tokens": 1})
        return m, "gemini-1.5-flash"
    except:
        # 플래시가 안 될 경우 프로 모델로 폴백
        try:
            m = genai.GenerativeModel('gemini-1.5-pro')
            return m, "gemini-1.5-pro"
        except:
            return None, None

engine, model_name = get_stable_engine()

if not engine:
    st.error("❌ 현재 API 키의 모든 할당량이 소진되었습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

# [3. 진단 프로세스 관리]
if 'stage' not in st.session_state: st.session_state.stage = 'init'

# --- PHASE 1: 주제 분석 및 지식 위계 분해 ---
if st.session_state.stage == 'init':
    st.title("🔍 Veritas AI: 교육 결손 정밀 진단")
    st.write(f"현재 엔진 **[{model_name}]** 가동 중. 학습의 뿌리를 추적합니다.")
    
    subject = st.text_input("진단할 개념:", placeholder="예: 근의 공식, 재귀함수, 양자역학 등")
    
    if st.button("지식 역추적 시작"):
        if subject:
            with st.spinner("지식의 계층 구조를 해체하여 진단 문항을 설계 중..."):
                prompt = f"'{subject}'을 이해하기 위해 반드시 알아야 할 하위 기초 지식 5가지를 찾고, 이를 검증할 Yes/No 질문 5개를 번호를 붙여 생성해줘."
                res = call_ai_with_backoff(engine, prompt)
                if res:
                    st.session_state.raw_data = res.text
                    st.session_state.topic = subject
                    st.session_state.stage = 'test'
                    st.rerun()

# --- PHASE 2: 5단계 역추적 진단 (사유 수집) ---
elif st.session_state.stage == 'test':
    st.subheader(f"🚩 '{st.session_state.topic}' 역진단 시뮬레이션")
    
    with st.form("diag_form"):
        lines = st.session_state.raw_data.split('\n')
        qs = [l.strip() for l in lines if l.strip() and l.strip()[0].isdigit() and ('.' in l or ')' in l)]
        
        results = []
        for i, q in enumerate(qs[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태", ["알고 있음(Yes)", "모름/모호함(No)"], key=f"q_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_input("어느 지점에서 사고가 막히나요? (모호한 이유 기술)", key=f"t_{i}")
            results.append({"q": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.form_submit_button("최종 페인포인트 모델링"):
            st.session_state.results = results
            st.session_state.stage = 'report'
            st.rerun()

# --- PHASE 3: 최종 루트-코즈 분석 리포트 ---
elif st.session_state.stage == 'report':
    st.title("📋 지식 결손 정밀 진단서")
    
    with st.spinner("응답 패턴 분석 및 페인포인트 도출 중..."):
        no_data = [r for r in st.session_state.results if "No" in r['status']]
        
        if not no_data:
            st.success("해당 주제에 대한 기초가 탄탄합니다.")
        else:
            final_prompt = f"사용자가 '{st.session_state.topic}'에 대해 다음 사유들로 'No'라고 답했습니다: {no_data}. 이 정보를 바탕으로 사용자의 '진정한 페인포인트'와 '당장 복습해야 할 기초 지점'을 정밀 진단해줘."
            report = call_ai_with_backoff(engine, final_prompt)
            if report:
                st.markdown(f"<div class='diag-card' style='border-left: 8px solid #1a73e8;'>{report.text}</div>", unsafe_allow_html=True)
                
    if st.button("새로운 진단 시작"):
        st.session_state.stage = 'init'
        st.rerun()
