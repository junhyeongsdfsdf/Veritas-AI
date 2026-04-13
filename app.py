import streamlit as st
import google.generativeai as genai
import time

# [1. 시스템 최적화 설정]
st.set_page_config(page_title="Veritas AI | Diagnostic Engine", layout="centered")

# 전문적인 UI 스타일링
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .diag-card { padding: 25px; border-radius: 15px; border: 1px solid #dee2e6; background-color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .stButton>button { background-color: #1a73e8; color: white; border-radius: 8px; height: 3.5rem; font-weight: bold; width: 100%; border: none; }
    .stButton>button:hover { background-color: #1557b0; }
    </style>
    """, unsafe_allow_html=True)

# [2. 지능형 모델 선택 엔진: 빡대가리 탈출 로직]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System API Key", type="password")

if not api_key:
    st.info("💡 작동을 위해 API Key가 필요합니다. Secrets 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

@st.cache_resource
def get_intelligent_engine():
    """
    1차원적 접근이 아닌, 실시간 권한 조회를 통한 자동 모델 매칭 로직.
    할당량 초과(429)나 모델 없음(404) 발생 시 즉시 대안을 찾습니다.
    """
    try:
        # 1. 내 키가 쓸 수 있는 실제 모델 리스트 확보
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 2. 선호도 순서 (최신 -> 안정)
        # 3.1이나 1.5-pro가 터질 것을 대비해 flash와 pro 순차 배치
        target_list = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro', 'models/gemini-1.5-flash']
        
        for target in target_list:
            # 리스트에 있는지 확인
            matches = [m for m in available_models if target in m]
            if matches:
                selected_name = matches[0]
                try:
                    m = genai.GenerativeModel(selected_name)
                    # 실제 작동 테스트 (Quota 확인용)
                    m.generate_content("ping", generation_config={"max_output_tokens": 1})
                    return m, selected_name
                except Exception:
                    continue # 할당량 초과나 에러 시 다음 모델로 이동
                    
        # 3. 만약 위 리스트가 다 안되면, 내 키가 가진 권한 중 아무거나 첫 번째꺼 사용
        if available_models:
            return genai.GenerativeModel(available_models[0]), available_models[0]
            
    except Exception as e:
        st.error(f"연결 엔진 구성 실패: {e}")
    return None, None

engine, active_model = get_intelligent_engine()

if not engine:
    st.error("❌ 구글 서버에서 사용 가능한 모델을 확보하지 못했습니다.")
    st.info("API 키가 무료 티어 제한에 걸렸거나, 구글 AI 스튜디오 설정에 문제가 있을 수 있습니다.")
    st.stop()

# [3. 진단 프로세스 관리]
if 'stage' not in st.session_state: st.session_state.stage = 'init'

# --- PHASE 1: 주제 분석 및 지식 위계 분해 ---
if st.session_state.stage == 'init':
    st.title("🔍 Veritas AI: 교육 결손 정밀 진단")
    st.write(f"현재 최적화된 엔진 **[{active_model}]**이 대기 중입니다.")
    
    subject = st.text_input("진단할 개념:", placeholder="예: 양자역학, 이차방정식, 재귀함수 등")
    
    if st.button("지식 역추적 시작"):
        if subject:
            with st.spinner("개념의 뿌리를 추적하여 진단 문항을 설계 중..."):
                try:
                    prompt = f"'{subject}'을 이해하기 위해 반드시 알아야 할 하위 기초 지식 5가지를 찾고, 이를 검증할 Yes/No 질문 5개를 번호를 붙여 생성해줘."
                    res = engine.generate_content(prompt)
                    st.session_state.raw_data = res.text
                    st.session_state.topic = subject
                    st.session_state.stage = 'test'
                    st.rerun()
                except Exception as e:
                    st.error(f"데이터 생성 실패 (Quota 이슈일 수 있습니다): {e}")

# --- PHASE 2: 5단계 역추적 진단 ---
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
                reason = st.text_input("어떤 부분이 이해되지 않는지 구체적으로 기술하세요:", key=f"t_{i}")
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
            st.success("해당 주제에 대한 기초가 탄탄합니다. 다음 단계로 넘어가셔도 좋습니다.")
        else:
            final_prompt = f"사용자가 '{st.session_state.topic}'에 대해 다음 사유들로 'No'라고 답했습니다: {no_data}. 이 정보를 바탕으로 사용자의 '진정한 페인포인트'와 '당장 복습해야 할 기초 지점'을 정밀 진단해줘."
            try:
                report = engine.generate_content(final_prompt)
                st.markdown(f"<div class='diag-card' style='border-left: 8px solid #1a73e8;'>{report.text}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"리포트 생성 중 오류: {e}")
                
    if st.button("새로운 진단 시작"):
        st.session_state.stage = 'init'
        st.rerun()
