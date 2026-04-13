import streamlit as st
import google.generativeai as genai
import time
import random
import logging
from google.api_core import exceptions

# [1. 시스템 로그 및 초기 설정]
logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="Veritas AI: Diagnostic Engine", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .diag-card { padding: 25px; border-radius: 12px; border: 1px solid #30363d; background-color: #161b22; margin-bottom: 20px; }
    .stButton>button { 
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%); 
        color: white; border-radius: 8px; height: 3.8rem; font-weight: bold; width: 100%; border: none; font-size: 1.1rem;
    }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(46, 160, 67, 0.4); }
    .error-box { padding: 20px; border-radius: 8px; border-left: 5px solid #f85149; background: #21262d; color: #f85149; margin-bottom: 20px; }
    .status-text { color: #8b949e; font-size: 0.85rem; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# [2. 지능형 엔진 로더: 404/429/500 에러 원천 봉쇄]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("시스템 API 키", type="password")

if not api_key:
    st.info("💡 시스템 구동을 위해 Google AI Studio API Key가 필요합니다. Secrets 설정을 확인해 주세요.")
    st.stop()

genai.configure(api_key=api_key)

@st.cache_resource
def get_invincible_model():
    """사용자 키가 허용하는 모델을 실시간으로 스캔하여 가장 안정적인 엔진을 확보합니다."""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 무료 티어 안정성 순위: Flash 1.5 -> Pro 1.5 -> Pro 1.0
        priority_targets = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for target in priority_targets:
            match = [m for m in available_models if target in m]
            if match:
                selected_model = match[0]
                try:
                    m = genai.GenerativeModel(selected_model)
                    # 실제 연결 테스트
                    m.generate_content("ping", generation_config={"max_output_tokens": 1})
                    return m, selected_model
                except: continue
        
        if available_models:
            return genai.GenerativeModel(available_models[0]), available_models[0]
    except Exception as e:
        st.error(f"연결 엔진 구성 실패: {e}")
    return None, None

engine, active_model_id = get_invincible_model()

def robust_call(prompt, max_retries=10):
    """
    무료 티어의 429 에러를 극복하기 위한 '지능형 대기 시스템'.
    재시도 간격을 지수적으로 늘리며(Exponential Backoff), 비굴할 정도로 끝까지 시도합니다.
    """
    if not engine: return None
    
    placeholder = st.empty()
    for i in range(max_retries):
        try:
            # 무료 티어는 연산 간격이 최소 4초 이상이어야 안전합니다.
            if i > 0: time.sleep(random.uniform(2, 4))
            return engine.generate_content(prompt)
        except exceptions.ResourceExhausted: # 429 에러
            wait_time = (i + 1) * 12 + random.uniform(1, 5)
            placeholder.warning(f"⏳ 구글 서버 할당량(Quota) 초과. {int(wait_time)}초 후 시스템이 스스로 재시도합니다... ({i+1}/{max_retries})")
            time.sleep(wait_time)
            placeholder.empty()
        except Exception as e:
            if i == max_retries - 1:
                st.markdown(f"<div class='error-box'>최종 연결 실패: {str(e)}</div>", unsafe_allow_html=True)
                return None
            time.sleep(3)
    return None

if not engine:
    st.markdown("<div class='error-box'>❌ 사용 가능한 AI 모델을 확보하지 못했습니다. 키 권한을 확인하세요.</div>", unsafe_allow_html=True)
    st.stop()

# [3. 세션 상태 관리: 꼬임 방지]
if 'process_stage' not in st.session_state: st.session_state.process_stage = 'init'
if 'topic_data' not in st.session_state: st.session_state.topic_data = {}

# --- PHASE 1: 주제 해체 및 지식 위계 분석 ---
if st.session_state.process_stage == 'init':
    st.title("🔍 Veritas AI: 정밀 결손 진단")
    st.markdown(f"<span class='status-text'>Active Engine: {active_model_id}</span>", unsafe_allow_html=True)
    st.write("막힌 개념의 뿌리를 추적하여 **진정한 페인포인트**를 도출합니다.")
    
    user_topic = st.text_input("진단할 개념을 입력하세요:", placeholder="예: 근의 공식, 재귀함수, 양자역학 등")
    
    if st.button("진단 엔진 가동"):
        if user_topic:
            with st.spinner("지식의 위계 구조를 해체하고 진단 문항을 설계 중..."):
                # 무료 티어 보호를 위한 강제 쿨다운
                time.sleep(2)
                prompt = f"""
                당신은 전과목 교육 진단 전문가입니다. 주제: '{user_topic}'
                1. 이 주제의 핵심 정의를 2문장 이내로 정리하세요.
                2. 이 주제를 이해하기 위해 반드시 사전에 알고 있어야 하는 '하위 기초 개념' 5가지를 검증할 수 있는 구체적인 Yes/No 질문을 만드세요.
                질문 형식: '1. 질문내용'
                """
                res = robust_call(prompt)
                if res:
                    st.session_state.topic_data['raw_questions'] = res.text
                    st.session_state.topic_data['current_topic'] = user_topic
                    st.session_state.process_stage = 'test_stage'
                    st.rerun()

# --- PHASE 2: 5단계 역추적 진단 시뮬레이션 ---
elif st.session_state.process_stage == 'test_stage':
    st.subheader(f"🚩 '{st.session_state.topic_data['current_topic']}' 역진단 시뮬레이션")
    st.write("이해의 끈이 어디서 끊어졌는지 확인하기 위해 아래 질문에 정직하게 답하세요.")
    
    with st.form("diagnosis_form"):
        lines = st.session_state.topic_data['raw_questions'].split('\n')
        qs = [l.strip() for l in lines if l.strip() and l.strip()[0].isdigit() and ('.' in l or ')' in l)]
        
        user_responses = []
        for i, q in enumerate(qs[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태 체크", ["알고 있음(Yes)", "모름/모호함(No)"], key=f"user_ans_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_area("어떤 지점이 헷갈리나요? (짧게 입력)", key=f"user_reason_{i}", placeholder="예: 수식은 알겠는데 실제 데이터가 어떻게 흐르는지 모르겠어요.")
            user_responses.append({"q": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.form_submit_button("최종 페인포인트 모델링"):
            st.session_state.topic_data['final_responses'] = user_responses
            st.session_state.process_stage = 'result_stage'
            st.rerun()

# --- PHASE 3: 최종 루트-코즈(Root-Cause) 분석 리포트 ---
elif st.session_state.process_stage == 'result_stage':
    st.title("📋 지식 결손 정밀 진단서")
    
    with st.spinner("응답 패턴과 사유를 결합하여 '진짜 구멍'을 모델링 중..."):
        no_data = [r for r in st.session_state.topic_data['final_responses'] if "No" in r['status']]
        
        if not no_data:
            st.success("🎉 해당 주제에 대한 지식 체계가 완벽합니다! 심화 단계로 나아가셔도 좋습니다.")
        else:
            final_prompt = f"""
            학습자가 '{st.session_state.topic_data['current_topic']}'에 대해 다음 사유들로 'No'라고 답했습니다:
            {no_data}
            
            사용자의 주관적 설명을 바탕으로 '진정한 페인포인트(Root Cause)'를 도출하세요.
            1. 발견된 결손 지점: (어느 단계의 논리가 무너졌는가)
            2. 인지적 오류 분석: (단순 지식 부족인지, 개념의 본질을 오해하고 있는지 분석)
            3. 학습 우선순위 제언: (현재 진도를 멈추고 당장 되돌아가야 할 구체적인 지점)
            """
            # 마지막 단계 호출 전 충분한 시간차
            time.sleep(3)
            report_res = robust_call(final_prompt)
            if report_res:
                st.markdown(f"<div class='diag-card' style='border-left: 10px solid #238636;'>{report_res.text}</div>", unsafe_allow_html=True)

    if st.button("새로운 진단 시작"):
        # 세션 초기화
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
