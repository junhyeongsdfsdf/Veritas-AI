import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# [1. 시스템 환경 설정] 전문적인 진단 도구 느낌의 블랙/블루 테마
st.set_page_config(page_title="Veritas AI: Diagnostic Engine", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .diag-card { padding: 25px; border-radius: 12px; border: 1px solid #30363d; background-color: #161b22; margin-bottom: 20px; }
    .stButton>button { background-color: #238636; color: white; border-radius: 8px; height: 3.5rem; font-weight: bold; width: 100%; border: none; }
    .stButton>button:hover { background-color: #2ea043; }
    .status-text { color: #8b949e; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

# [2. 지능형 엔진 로더: 할당량/모델명 이슈 원천 차단]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System Verification Key", type="password")

if not api_key:
    st.info("💡 시스템 작동을 위해 API Key가 필요합니다. Secrets 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

def call_ai_robustly(model, prompt):
    """지수 백오프 전략을 사용한 무결점 호출 함수"""
    for attempt in range(5):
        try:
            return model.generate_content(prompt)
        except exceptions.ResourceExhausted: # 429 에러 대응
            wait = (attempt + 1) * 10 
            st.warning(f"⚠️ 서버 과부하 감지. {wait}초 후 자동 재시도합니다...")
            time.sleep(wait)
        except Exception as e:
            if "not_found" in str(e).lower() or "404" in str(e): # 404 에러 대응
                st.error("❌ 모델 경로 오류. 관리자가 모델명을 업데이트해야 합니다.")
                return None
            raise e
    return None

@st.cache_resource
def load_final_engine():
    # 가장 표준적이고 가벼운 모델부터 순차 연결
    for m_name in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            m = genai.GenerativeModel(m_name)
            m.generate_content("ping", generation_config={"max_output_tokens": 1})
            return m, m_name
        except:
            continue
    return None, None

engine, active_model = load_final_engine()

if not engine:
    st.error("❌ 현재 API 키로 구글 서버에 접속할 수 없습니다. 할당량이 완전히 소진되었거나 키가 잘못되었습니다.")
    st.stop()

# [3. 진단 스테이지 관리]
if 'stage' not in st.session_state: st.session_state.stage = 'init'

# --- STAGE 1: 주제 해체 및 정의 ---
if st.session_state.stage == 'init':
    st.title("🔍 Veritas AI")
    st.subheader("지식의 뿌리를 추적하여 결손 지점을 진단합니다.")
    
    topic = st.text_input("진단할 개념을 입력하세요:", placeholder="예: 근의 공식, 재귀함수, 양자역학 등")
    
    if st.button("전문 진단 엔진 가동"):
        if topic:
            with st.spinner("개념의 정의를 정리하고 지식 위계를 분석 중..."):
                prompt = f"""
                당신은 교육 진단 전문가입니다. 주제: '{topic}'
                1. 이 개념의 정의와 핵심 원리를 2문장으로 요약하세요.
                2. 이 개념을 이해하기 위해 필요한 '더 기초적인 하위 지식' 5가지를 검증할 Yes/No 질문을 만드세요.
                질문 형식: '1. 질문내용'
                """
                res = call_ai_robustly(engine, prompt)
                if res:
                    st.session_state.raw_data = res.text
                    st.session_state.topic = topic
                    st.session_state.stage = 'testing'
                    st.rerun()

# --- STAGE 2: 5단계 기초 역량 테스트 ---
elif st.session_state.stage == 'testing':
    st.subheader(f"🚩 '{st.session_state.topic}' 역진단 시뮬레이션")
    st.markdown("---")
    
    with st.form("diag_form"):
        lines = st.session_state.raw_data.split('\n')
        # 질문 파싱 (번호로 시작하는 줄 추출)
        qs = [l.strip() for l in lines if l.strip() and l.strip()[0].isdigit() and ('.' in l or ')' in l)]
        
        user_data = []
        for i, q in enumerate(qs[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태", ["알고 있음(Yes)", "모름/모호함(No)"], key=f"q_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_input("어떤 지점에서 사고가 막히나요?", key=f"t_{i}", placeholder="구체적인 이유를 적어주세요.")
            user_data.append({"q": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.form_submit_button("최종 페인포인트 분석"):
            st.session_state.user_data = user_data
            st.session_state.stage = 'report'
            st.rerun()

# --- STAGE 3: 최종 지식 결손 모델링 리포트 ---
elif st.session_state.stage == 'report':
    st.title("📋 지식 결손 정밀 진단서")
    
    with st.spinner("응답 패턴을 기반으로 당신의 '진짜 페인포인트'를 도출 중..."):
        no_items = [d for d in st.session_state.user_data if "No" in d['status']]
        
        if not no_items:
            st.success("해당 주제에 대한 기초가 탄탄합니다. 심화 학습으로 나아가셔도 좋습니다.")
        else:
            final_prompt = f"""
            학습자가 '{st.session_state.topic}'에 대해 다음 이유들로 'No'라고 답했습니다: {no_items}. 
            이 응답들을 종합 모델링하여 사용자가 현재 벽에 부딪힌 '진정한 페인포인트'를 진단하세요.
            1. 발견된 결손 지점: (어느 단계의 논리가 무너졌는가)
            2. 인지적 오류 분석: (왜 어려워하는지에 대한 사유 기반 분석)
            3. 학습 제언: (당장 복습해야 할 구체적인 지점)
            """
            report = call_ai_robustly(engine, final_prompt)
            if report:
                st.markdown(f"<div class='diag-card' style='border-left: 8px solid #238636;'>{report.text}</div>", unsafe_allow_html=True)
                
    if st.button("새로운 진단 시작"):
        st.session_state.stage = 'init'
        st.rerun()
