import streamlit as st
import google.generativeai as genai
import time

# [1. 시스템 설정]
st.set_page_config(page_title="Veritas AI | 교육 결손 진단", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .diag-card { padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; background-color: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .stButton>button { background-color: #1a73e8; color: white; border-radius: 8px; height: 3.5rem; font-weight: bold; width: 100%; border: none; }
    </style>
    """, unsafe_allow_html=True)

# [2. API 연결: 가장 안전한 모델 고정]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System API Key", type="password")

if not api_key:
    st.info("💡 작동을 위해 API Key가 필요합니다. Secrets 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

@st.cache_resource
def get_engine():
    # 무료 티어에서 가장 넉넉한 'gemini-1.5-flash'를 사용합니다.
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # 연결 확인용 테스트
        model.generate_content("test", generation_config={"max_output_tokens": 1})
        return model
    except Exception as e:
        st.error(f"⚠️ 엔진 연결 실패: {e}")
        return None

engine = get_engine()
if not engine: st.stop()

# [3. 진단 프로세스 관리]
if 'stage' not in st.session_state: st.session_state.stage = 'init'

# --- PHASE 1: 주제 분석 및 질문 생성 ---
if st.session_state.stage == 'init':
    st.title("🔍 Veritas AI: 정밀 결손 진단")
    st.write("막힌 개념을 입력하면, 기초 연산부터 어디가 문제인지 역추적합니다.")
    
    subject = st.text_input("진단할 개념을 입력하세요:", placeholder="예: 근의 공식, 재귀함수, 양자역학 등")
    
    if st.button("진단 엔진 가동"):
        if subject:
            with st.spinner("지식의 뿌리를 추적 중... (잠시만 기다려주세요)"):
                try:
                    prompt = f"사용자가 '{subject}'을 모른다고 합니다. 이 개념을 이해하기 위해 반드시 알아야 할 하위 기초 지식 5가지를 찾고, 이를 검증할 구체적인 Yes/No 질문 5개를 번호를 붙여 생성해줘."
                    res = engine.generate_content(prompt)
                    st.session_state.raw_data = res.text
                    st.session_state.topic = subject
                    st.session_state.stage = 'test'
                    st.rerun()
                except Exception as e:
                    if "429" in str(e):
                        st.error("🚨 구글 서버의 요청 한도를 초과했습니다. 약 1분 후 다시 시도해주세요.")
                    else:
                        st.error(f"에러 발생: {r'https://ai.google.dev/gemini-api/docs/rate-limits' if '429' in str(e) else e}")

# --- PHASE 2: 5단계 역추적 진단 ---
elif st.session_state.stage == 'test':
    st.subheader(f"🚩 '{st.session_state.topic}' 역진단 테스트")
    
    with st.form("diag_form"):
        lines = st.session_state.raw_data.split('\n')
        qs = [l.strip() for l in lines if l.strip() and l.strip()[0].isdigit()]
        
        results = []
        for i, q in enumerate(qs[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태", ["알고 있음(Yes)", "모름/모호함(No)"], key=f"q_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_input("어느 지점이 헷갈리나요? (짧게 입력)", key=f"t_{i}")
            results.append({"q": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.form_submit_button("최종 페인포인트 모델링"):
            st.session_state.results = results
            st.session_state.stage = 'report'
            st.rerun()

# --- PHASE 3: 최종 결과 리포트 ---
elif st.session_state.stage == 'report':
    st.title("📋 지식 결손 정밀 진단서")
    
    with st.spinner("인지 구조를 분석 중..."):
        no_data = [r for r in st.session_state.results if "No" in r['status']]
        
        if not no_data:
            st.success("해당 주제에 대한 지식 체계가 탄탄합니다.")
        else:
            try:
                final_prompt = f"학습자가 '{st.session_state.topic}'에 대해 다음 이유들로 'No'라고 답했습니다: {no_data}. 이 정보를 바탕으로 사용자의 '진정한 페인포인트'와 '당장 복습해야 할 기초 지점'을 분석해줘."
                report = engine.generate_content(final_prompt)
                st.markdown(f"<div class='diag-card' style='border-left: 8px solid #1a73e8;'>{report.text}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error("리포트 생성 중 에러가 발생했습니다. 잠시 후 다시 시도해 주세요.")
                
    if st.button("새로운 진단 시작"):
        st.session_state.stage = 'init'
        st.rerun()
