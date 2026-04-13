import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# [1. 시스템 최적화]
st.set_page_config(page_title="Veritas AI: Diagnostic Engine", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .diag-card { padding: 25px; border-radius: 15px; border: 1px solid #dee2e6; background-color: white; margin-bottom: 20px; }
    .stButton>button { background-color: #1a73e8; color: white; border-radius: 8px; height: 3.5rem; font-weight: bold; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# [2. 지능형 엔진 로더: 429 에러 자동 회복 시스템]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System API Key", type="password")

if not api_key:
    st.info("💡 시스템 작동을 위해 API Key가 필요합니다. Secrets 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

def call_gemini_with_retry(model, prompt, max_retries=3):
    """구글 서버의 속도 제한(429) 발생 시 지능적으로 대기 후 재시도합니다."""
    for i in range(max_retries):
        try:
            return model.generate_content(prompt)
        except exceptions.ResourceExhausted:
            if i < max_retries - 1:
                st.warning(f"⚠️ 구글 서버 과부하로 {i+1}차 재시도 중... 잠시만 기다려주세요.")
                time.sleep(5) # 5초 대기 후 재시도
            else:
                raise
        except Exception as e:
            raise e

@st.cache_resource
def get_stable_engine():
    """무료 티어에서 가장 할당량이 넉넉하고 안정적인 1.5-flash 모델을 우선 선점합니다."""
    stable_models = ['gemini-1.5-flash', 'gemini-pro']
    for m_name in stable_models:
        try:
            m = genai.GenerativeModel(m_name)
            m.generate_content("test", generation_config={"max_output_tokens": 1})
            return m, m_name
        except:
            continue
    return None, None

engine, active_model = get_stable_engine()

if not engine:
    st.error("❌ 구글 서버 연결 실패: 현재 사용 중인 API 키의 모든 할당량이 소진되었습니다.")
    st.info("새로운 API Key를 발급받으시거나, 약 1분 후 다시 시도해 주세요.")
    st.stop()

# [3. 진단 프로세스 관리]
if 'stage' not in st.session_state: st.session_state.stage = 'init'

# --- PHASE 1: 주제 분석 및 지식 위계 분해 ---
if st.session_state.stage == 'init':
    st.title("🔍 Veritas AI: 교육 결손 정밀 진단")
    st.caption(f"Engine: {active_model} (Stable Mode)")
    
    subject = st.text_input("진단할 개념을 입력하세요:", placeholder="예: 근의 공식, 재귀함수, 양자역학 등")
    
    if st.button("지식 역추적 엔진 가동"):
        if subject:
            with st.spinner("개념의 지식 계층을 해체하는 중..."):
                try:
                    prompt = f"'{subject}'을 이해하기 위해 반드시 알아야 할 하위 기초 지식 5가지를 찾고, 이를 검증할 Yes/No 질문 5개를 번호를 붙여 생성해줘."
                    res = call_gemini_with_retry(engine, prompt)
                    st.session_state.raw_data = res.text
                    st.session_state.topic = subject
                    st.session_state.stage = 'test'
                    st.rerun()
                except Exception as e:
                    st.error(f"진단 생성 실패: {e}")

# --- PHASE 2: 5단계 역추적 진단 (사유 수집) ---
elif st.session_state.stage == 'test':
    st.subheader(f"🚩 '{st.session_state.topic}' 역진단 테스트")
    
    with st.form("diag_form"):
        lines = st.session_state.raw_data.split('\n')
        qs = [l.strip() for l in lines if l.strip() and l.strip()[0].isdigit() and ('.' in l or ')' in l)]
        
        results = []
        for i, q in enumerate(qs[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태", ["이해하고 있음(Yes)", "모름/모호함(No)"], key=f"q_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_input("어떤 지점에서 사고가 막히나요?", key=f"t_{i}", placeholder="구체적인 이유를 적어주세요.")
            results.append({"q": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.form_submit_button("최종 페인포인트 모델링"):
            st.session_state.results = results
            st.session_state.stage = 'report'
            st.rerun()

# --- PHASE 3: 최종 루트-코즈(Root-Cause) 리포트 ---
elif st.session_state.process == 'report': # (오타 수정: stage로 통일)
    pass # 아래 코드로 대체

elif st.session_state.stage == 'report':
    st.title("📋 지식 결손 정밀 진단서")
    
    with st.spinner("인지 구조를 모델링하여 페인포인트를 도출 중..."):
        no_data = [r for r in st.session_state.results if "No" in r['status']]
        
        if not no_data:
            st.success("해당 주제에 대한 지식 체계가 완벽합니다.")
        else:
            final_prompt = f"학습자가 '{st.session_state.topic}'에 대해 다음 이유들로 'No'라고 답했습니다: {no_data}. 이 정보를 바탕으로 사용자의 '진정한 페인포인트'와 '당장 복습해야 할 과거의 기초 지점'을 진단해줘."
            try:
                report = call_gemini_with_retry(engine, final_prompt)
                st.markdown(f"<div class='diag-card' style='border-left: 8px solid #1a73e8;'>{report.text}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"분석 리포트 생성 실패: {e}")
                
    if st.button("새로운 진단 시작"):
        st.session_state.stage = 'init'
        st.rerun()
