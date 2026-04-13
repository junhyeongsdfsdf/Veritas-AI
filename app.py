import streamlit as st
import google.generativeai as genai

# [1. 시스템 환경 설정]
st.set_page_config(page_title="Veritas AI: Universal Diagnostician", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .diag-card { padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; background-color: white; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .stButton>button { background-color: #1a73e8; color: white; border-radius: 8px; height: 3.5rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# [2. API 연결부: 실시간 모델 리스트 동적 추출]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System Verification Key", type="password")

if not api_key:
    st.info("💡 시스템 작동을 위해 API Key가 필요합니다. Secrets 설정 혹은 사이드바를 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

@st.cache_resource
def get_best_available_model():
    """사용자 API 키가 현재 허용하는 모델 중 최적의 것을 자동 선택합니다."""
    try:
        # 내 API 키가 쓸 수 있는 모든 모델 목록을 가져옴
        available_models = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        # 선호 순서: 1.5-flash -> 1.5-pro -> 1.0-pro -> 리스트 중 첫 번째
        priority = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for target in priority:
            # 모델 명칭에 target 문구가 포함된 것을 탐색 (models/ 포함 여부 대응)
            for m in available_models:
                if target in m:
                    # 실제 작동 테스트
                    test_model = genai.GenerativeModel(m)
                    test_model.generate_content("ping", generation_config={"max_output_tokens": 1})
                    return m
        
        # 우선순위에 없으면 리스트 중 첫 번째 모델 선택
        if available_models:
            return available_models[0]
            
    except Exception as e:
        st.error(f"API 연결에 문제가 발생했습니다: {str(e)}")
        return None
    return None

model_name = get_best_available_model()

if not model_name:
    st.error("❌ 사용 가능한 Gemini 모델을 찾을 수 없습니다. API 키의 유효성을 다시 확인해주세요.")
    st.stop()

engine = genai.GenerativeModel(model_name)

# [3. 진단 프로세스 관리]
if 'process' not in st.session_state: st.session_state.process = 'init'

# --- PHASE 1: 주제 분석 및 지식 위계 분해 ---
if st.session_state.process == 'init':
    st.title("🔍 Veritas AI: 교육 결손 정밀 진단")
    st.write("학습 중 막힌 부분의 **'진정한 원인'**을 찾기 위해 지식의 뿌리를 추적합니다.")
    
    subject_topic = st.text_input("어떤 개념에서 막히셨나요?", placeholder="예: 근의 공식, 재귀함수, 한계효용 등")
    
    if st.button("진단 엔진 가동", use_container_width=True):
        if subject_topic:
            with st.spinner(f"[{model_name}] 엔진을 사용하여 지식 구조를 해체 중..."):
                try:
                    init_prompt = f"""
                    학습자가 '{subject_topic}'에 대해 이해가 안 된다고 합니다.
                    1. 이 주제의 핵심 정의를 2문장 이내로 정리하세요.
                    2. 이 주제를 이해하기 위해 반드시 사전에 알고 있어야 하는 '하위/기초 개념' 5개를 추출하세요.
                    3. 그 5개 개념을 바탕으로 학습자의 기초 체력을 검증할 수 있는 Yes/No 질문을 5개 생성하세요.
                    (질문은 반드시 '1. 질문내용' 형식으로 번호를 붙여주세요)
                    """
                    res = engine.generate_content(init_prompt)
                    st.session_state.raw_res = res.text
                    st.session_state.topic = subject_topic
                    st.session_state.process = 'diagnostic_test'
                    st.rerun()
                except Exception as e:
                    st.error(f"진단 생성 중 에러가 발생했습니다: {e}")

# --- PHASE 2: 5단계 역추적 진단 (사유 수집) ---
elif st.session_state.process == 'diagnostic_test':
    st.subheader(f"🚩 '{st.session_state.topic}' 진단 프로세스")
    
    with st.form("diagnosis_form"):
        lines = st.session_state.raw_res.split('\n')
        questions = [l.strip() for l in lines if l.strip() and (l.strip()[0].isdigit()) and '.' in l or ')' in l]
        
        user_responses = []
        for i, q in enumerate(questions[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태 체크", ["알고 있음(Yes)", "잘 모르겠음(No)"], key=f"ans_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_input("어느 부분이 모호한가요? (간단히 서술)", key=f"reason_{i}")
            user_responses.append({"question": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
        
        if st.form_submit_button("최종 결손 지점 분석"):
            st.session_state.user_responses = user_responses
            st.session_state.process = 'result_modeling'
            st.rerun()

# --- PHASE 3: 최종 페인포인트 모델링 결과 ---
elif st.session_state.process == 'result_modeling':
    st.title("📋 지식 결손 모델링 리포트")
    
    with st.spinner("응답 패턴을 기반으로 학습 결손 지점을 모델링 중..."):
        no_data = [d for d in st.session_state.user_responses if "No" in d['status']]
        
        analysis_prompt = f"""
        당신은 교육 진단 전문가입니다.
        주제: {st.session_state.topic}
        취약점 데이터: {no_data}
        
        사용자가 'No'라고 답한 사유를 바탕으로 '진정한 페인포인트(Root Cause)'를 도출하세요.
        1. 발견된 결손 지점 (어느 단계의 논리가 무너졌는가)
        2. 인지적 오류 분석 (왜 어려워하는지 사유 기반 분석)
        3. 학습 우선순위 제언 (당장 되돌아가야 할 구체적인 기초 지점)
        """
        
        try:
            final_report = engine.generate_content(analysis_prompt)
            st.markdown(f"<div class='diag-card' style='border-left: 5px solid #1a73e8;'>{final_report.text}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"분석 중 오류 발생: {e}")

    if st.button("새로운 주제 진단하기"):
        st.session_state.process = 'init'
        st.rerun()
