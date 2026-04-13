import streamlit as st
import google.generativeai as genai

# [1. 시스템 설정]
st.set_page_config(page_title="Veritas AI | 지식 결손 진단기", layout="centered")

# [2. 보안 및 모델 연결]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("System API Key", type="password")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.warning("API Key를 입력해주세요.")
    st.stop()

# 세션 상태 관리 (진단 단계 유지)
if 'stage' not in st.session_state: st.session_state.stage = 'start'
if 'topic' not in st.session_state: st.session_state.topic = ""
if 'definition' not in st.session_state: st.session_state.definition = ""
if 'questions' not in st.session_state: st.session_state.questions = []

# --- STAGE 1: 주제 정의 및 기초 설명 ---
if st.session_state.stage == 'start':
    st.title("🔍 Veritas AI: 지식 결손 진단")
    st.write("막히는 개념을 입력하면, 기초 연산부터 어디가 문제인지 역추적합니다.")
    
    topic = st.text_input("지금 이해가 안 되는 개념은 무엇인가요?", placeholder="예: 근의 공식")
    
    if st.button("진단 시작"):
        if topic:
            with st.spinner("개념의 정의를 정리하고 진단 문항을 생성 중..."):
                # 1. 정의 생성
                def_res = model.generate_content(f"'{topic}'의 정의와 핵심 공식을 아주 핵심만 짧게 설명해줘.")
                st.session_state.definition = def_res.text
                
                # 2. 기초 역진단 질문 5개 생성 (Yes/No용)
                q_prompt = f"사용자가 '{topic}'을 모른다고 합니다. 이 개념을 풀기 위해 반드시 알아야 하는 '더 기초적인 연산이나 원리' 5가지를 Yes/No 질문으로 만드세요. 번호를 붙여서 작성하세요."
                q_res = model.generate_content(q_prompt)
                
                st.session_state.questions = [q.strip() for q in q_res.text.split('\n') if q.strip() and q[0].isdigit()]
                st.session_state.topic = topic
                st.session_state.stage = 'drill'
                st.rerun()

# --- STAGE 2: 5가지 역진단 질문 (Yes/No + 사유 수집) ---
elif st.session_state.stage == 'drill':
    st.subheader(f"📖 {st.session_state.topic}의 핵심 정의")
    st.info(st.session_state.definition)
    st.markdown("---")
    st.subheader("🎯 기초 역량 진단 (5-Step)")
    st.write("이 공식의 토대가 되는 아래 기초 원리들을 정말 알고 있는지 체크해보세요.")

    with st.form("diagnosis_form"):
        user_data = []
        for i, q in enumerate(st.session_state.questions):
            st.markdown(f"**Q{i+1}. {q}**")
            ans = st.radio("상태", ["알고 있음(Yes)", "모름/헷갈림(No)"], key=f"ans_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_area("어느 부분이 왜 이해가 안 가는지 짧게 적어주세요:", key=f"reason_{i}", placeholder="예: 제곱근 안의 숫자가 음수일 때 어떻게 하는지 모르겠어요.")
            user_data.append({"q": q, "status": ans, "reason": reason})
        
        if st.form_submit_button("최종 진단 리포트 생성"):
            st.session_state.user_data = user_data
            st.session_state.stage = 'result'
            st.rerun()

# --- STAGE 3: 최종 페인포인트 분석 (Verdict) ---
elif st.session_state.stage == 'result':
    st.title("📋 지식 결손 정밀 진단서")
    
    with st.spinner("당신의 학습 구멍(Pain-point)을 모델링 중..."):
        no_items = [d for d in st.session_state.user_data if "No" in d['status']]
        
        # AI가 'No'라고 한 부분들을 종합 분석하여 진짜 원인을 찾음
        analysis_prompt = f"""
        당신은 학습자의 '인지적 구멍'을 찾는 전문가입니다.
        주제: {st.session_state.topic}
        
        [사용자 응답 데이터]
        {no_items}
        
        사용자가 'No'라고 답한 기초 원리들과 그 사유를 종합하여, 
        이 사용자가 '{st.session_state.topic}'을 이해하지 못하는 **진짜 근본적인 결손 지점(Pain-point)**을 진단하세요.
        
        진단 결과에는 다음이 포함되어야 합니다:
        1. 당신의 고장 난 지점 (정확한 위치 선정)
        2. 왜 이곳이 고장 났는가에 대한 논리적 분석
        3. 이 구멍을 메우기 위해 당장 복습해야 할 '과거의 연산' 한 가지
        """
        
        final_report = model.generate_content(analysis_prompt)
        st.markdown(f'<div style="padding:20px; border-radius:10px; border-left:5px solid #ff4b4b; background-color:#fff5f5;">{final_report.text}</div>', unsafe_allow_html=True)

    if st.button("다시 진단하기"):
        st.session_state.stage = 'start'
        st.rerun()
