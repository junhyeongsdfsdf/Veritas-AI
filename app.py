import streamlit as st
import google.generativeai as genai

# [1. 시스템 설정] 전문적인 인터페이스 구현
st.set_page_config(page_title="Veritas AI | Diagnosis Engine", layout="centered")

# CSS를 통한 세련된 UI (전문 진단 도구 느낌 강조)
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .report-box { padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

# [2. 보안 및 모델 연결]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("API Key Verification", type="password")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.warning("시스템 작동을 위해 API Key가 필요합니다.")
    st.stop()

# [3. 세션 관리] 진단 단계 유지
if 'stage' not in st.session_state:
    st.session_state.stage = 'input'
if 'questions' not in st.session_state:
    st.session_state.questions = []

# --- PHASE 1: 주제 설정 및 타격 지점 생성 ---
if st.session_state.stage == 'input':
    st.title("🔍 Veritas AI")
    st.subheader("지식의 근본적 결함을 추적합니다.")
    topic = st.text_input("진단받고 싶은 머신러닝 개념을 입력하세요.", placeholder="예: Transformer의 Self-Attention")
    
    if st.button("전문 진단 시작"):
        if topic:
            with st.spinner("개념의 핵심 층위를 해체하여 질문을 구성 중..."):
                prompt = f"""
                당신은 ML 교육 전문가입니다. 주제: '{topic}'
                사용자가 이 개념의 '어느 지점'에서 막혔는지 정확히 파악하기 위한 질문 5개를 생성하세요.
                - 1번 질문: 이 개념의 존재 이유 (Why)
                - 2-3번 질문: 핵심 메커니즘의 작동 원리 (How)
                - 4-5번 질문: 파라미터나 구조적 특징의 인과관계 (Logic)
                질문은 '예/아니오'로 답할 수 있게 구체적으로 작성하세요.
                """
                res = model.generate_content(prompt)
                st.session_state.questions = [q.strip() for q in res.text.split('\n') if q.strip() and q[0].isdigit()]
                st.session_state.topic = topic
                st.session_state.stage = 'testing'
                st.rerun()

# --- PHASE 2: 정밀 진단 수행 (설명 수집) ---
elif st.session_state.stage == 'testing':
    st.title("📋 5단계 정밀 진단")
    st.info(f"주제: {st.session_state.topic}")
    
    with st.form("diagnosis_form"):
        user_data = []
        for i, q in enumerate(st.session_state.questions):
            st.markdown(f"**Q{i+1}. {q}**")
            ans = st.radio("이해 여부", ["Yes", "No"], key=f"ans_{i}", horizontal=True)
            reason = ""
            if ans == "No":
                reason = st.text_area("이 부분이 모호한 이유를 간단히 적어주세요.", 
                                      key=f"reason_{i}", placeholder="예: 수식은 알겠는데 쿼리와 키가 왜 곱해지는지 직관적으로 모르겠어요.")
            user_data.append({"q": q, "status": ans, "reason": reason})
        
        if st.form_submit_button("진단 리포트 생성"):
            st.session_state.user_data = user_data
            st.session_state.stage = 'report'
            st.rerun()

# --- PHASE 3: 페인포인트 역추적 결과 보고 ---
elif st.session_state.stage == 'report':
    st.title("🚨 진단 결과: 당신의 페인포인트")
    
    with st.spinner("작성하신 응답에서 지식의 단절 지점을 분석 중..."):
        no_items = [d for d in st.session_state.user_data if d['status'] == "No"]
        
        if not no_items:
            st.success("해당 주제에 대해 탄탄한 기본기를 갖추고 있습니다.")
        else:
            analysis_prompt = f"""
            사용자가 {st.session_state.topic} 학습 중 다음 질문들에 '모름'이라고 답했습니다.
            사용자가 직접 적은 사유를 바탕으로 '진짜 페인포인트'를 진단하세요.
            
            [사용자 응답 데이터]
            {no_items}
            
            [리포트 포함 내용]
            1. 논리적 단절 지점: 사용자가 어디서부터 이해의 끈을 놓쳤는지 정확히 명시.
            2. 근본적 원인(Root Cause): 단순히 개념을 모르는 게 아니라, 이 이면의 어떤 논리(예: 공간적 상관관계, 확률 정규화 등)를 오해하고 있는지 분석.
            3. 사고의 전환: 이 페인포인트를 극복하기 위해 가져야 할 새로운 관점 제시.
            """
            report = model.generate_content(analysis_prompt)
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            st.markdown(report.text)
            st.markdown('</div>', unsafe_allow_html=True)

    if st.button("다른 개념 진단하기"):
        st.session_state.stage = 'input'
        st.rerun()
