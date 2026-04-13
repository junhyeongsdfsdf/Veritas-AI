import streamlit as st
import google.generativeai as genai

# [1. 시스템 환경 설정]
st.set_page_config(page_title="Veritas AI: Universal Diagnostician", layout="centered")

# 전문 진단 도구 느낌의 UI 스타일링
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .diag-card { padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; background-color: white; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .highlight { color: #1a73e8; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# [2. API 모델 연결]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System Verification Key", type="password")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.info("💡 시스템 작동을 위해 API Key가 필요합니다.")
    st.stop()

# [3. 진단 프로세스 관리]
if 'process' not in st.session_state: st.session_state.process = 'init'

# --- PHASE 1: 주제 분석 및 지식 위계 분해 ---
if st.session_state.process == 'init':
    st.title("🔍 Veritas AI: 교육 결손 정밀 진단")
    st.write("학습 중 막힌 부분의 **'진정한 원인'**을 찾기 위해 지식의 뿌리를 추적합니다.")
    
    subject_topic = st.text_input("어떤 개념에서 막히셨나요?", placeholder="예: 양자역학의 이중슬릿 실험, 파이썬의 재귀함수, 경제의 한계 효용 등")
    
    if st.button("진단 엔진 가동", use_container_width=True):
        if subject_topic:
            with st.spinner("지식의 계층 구조를 해체하는 중..."):
                # AI에게 해당 주제를 이해하기 위한 '선행 지식 위계'를 생성하게 함
                init_prompt = f"""
                학습자가 '{subject_topic}'에 대해 이해가 안 된다고 합니다.
                1. 이 주제의 핵심 정의를 2문장 이내로 정리하세요.
                2. 이 주제를 이해하기 위해 반드시 사전에 알고 있어야 하는 '하위/기초 개념' 5개를 추출하세요.
                3. 그 5개 개념을 바탕으로 학습자의 기초 체력을 검증할 수 있는 Yes/No 질문을 5개 생성하세요.
                질문은 번호를 붙여서 출력하세요.
                """
                res = model.generate_content(init_prompt)
                
                # 데이터 파싱 및 세션 저장
                st.session_state.raw_res = res.text
                st.session_state.topic = subject_topic
                st.session_state.process = 'diagnostic_test'
                st.rerun()

# --- PHASE 2: 5단계 역추적 진단 (사유 수집) ---
elif st.session_state.process == 'diagnostic_test':
    st.subheader(f"🚩 '{st.session_state.topic}' 진단 프로세스")
    st.write("현재 막힌 지점의 토대가 되는 기초 원리들을 점검합니다.")
    st.markdown("---")

    with st.form("diagnosis_form"):
        # AI 응답에서 질문 부분만 추출 (간단한 파싱 로직)
        questions = [line for line in st.session_state.raw_res.split('\n') if line.strip() and line[0].isdigit()]
        
        user_responses = []
        for i, q in enumerate(questions[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태 체크", ["이해하고 있음(Yes)", "잘 모르겠음(No)"], key=f"ans_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_input("어떤 부분이 모호한지 짧게 적어주세요 (예: 용어가 낯설다, 원리가 이해 안 된다 등)", key=f"reason_{i}")
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
        당신은 전 과목 통합 교육 진단 전문가입니다.
        주제: {st.session_state.topic}
        학습자의 취약점 데이터: {no_data}
        
        위 데이터를 바탕으로 학습자가 현재 주제를 이해하지 못하는 '진정한 페인포인트(Root Cause)'를 도출하세요.
        - 단순한 지식 나열이 아니라, '어느 단계의 논리'가 무너졌는지를 정확히 진단해야 합니다.
        - 결과 리포트 형식:
          1. 발견된 결손 지점 (어느 시대/어느 단계/어느 연산인가)
          2. 인지적 오류 분석 (사용자가 왜 이 부분을 어려워하는지 사유를 바탕으로 분석)
          3. 학습 우선순위 제언 (현재 진도를 멈추고 당장 되돌아가야 할 구체적인 지점)
        """
        
        final_report = model.generate_content(analysis_prompt)
        
        st.markdown(f"<div class='diag-card' style='border-left: 5px solid #1a73e8;'>{final_report.text}</div>", unsafe_allow_html=True)

    if st.button("새로운 주제 진단하기"):
        st.session_state.process = 'init'
        st.rerun()
