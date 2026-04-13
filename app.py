import streamlit as st
import google.generativeai as genai
import time
import random
from google.api_core import exceptions

# [1. 프리미엄 시스템 UI 설정]
st.set_page_config(page_title="Veritas AI: Universal Diagnosis", layout="centered")

st.markdown("""
    <style>
    /* 배경 및 기본 텍스트 */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    
    /* 진단 카드 디자인 */
    .diag-card { 
        padding: 30px; border-radius: 16px; border: 1px solid #30363d; 
        background-color: #161b22; margin-bottom: 25px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    /* 전문적인 버튼 디자인 */
    .stButton>button { 
        background: linear-gradient(90deg, #238636 0%, #2ea043 100%); 
        color: white; border-radius: 10px; height: 4rem; 
        font-weight: 800; width: 100%; border: none; font-size: 1.2rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(46, 160, 67, 0.4); }
    
    /* 상태 안내 메시지 디자인 */
    .status-msg {
        padding: 15px; border-radius: 10px; background: #0d1117;
        border: 1px dashed #1f6feb; color: #58a6ff;
        font-family: 'Courier New', monospace; margin-bottom: 20px;
    }
    
    /* 리포트 강조 */
    .report-highlight { border-left: 8px solid #238636; padding-left: 25px; font-size: 1.1rem; line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# [2. 지능형 엔진 로더: 모델 스캔 및 자동 매칭]
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("시스템 보안키 (API KEY)", type="password")

if not api_key:
    st.info("💡 Veritas AI 시스템 가동을 위해 API Key가 필요합니다.")
    st.stop()

genai.configure(api_key=api_key)

@st.cache_resource
def get_ultimate_engine():
    """사용자 키의 권한을 실시간 스캔하여 가장 강력하고 안정적인 모델을 선택합니다."""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        targets = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        for target in targets:
            match = [m for m in available_models if target in m]
            if match:
                model = genai.GenerativeModel(match[0])
                # 테스트 호출 (한도 확인)
                model.generate_content("test", generation_config={"max_output_tokens": 1})
                return model, match[0]
        if available_models:
            return genai.GenerativeModel(available_models[0]), available_models[0]
    except Exception:
        return None, None
    return None, None

engine, active_model_id = get_ultimate_engine()

# [3. 핵심 로직: 지능형 지연 및 무결점 호출 엔진]
def veritas_call(prompt, task_name="데이터 분석 중..."):
    """
    429 에러(할당량 초과)를 사전에 차단하기 위해 지능형 지연(Intelligent Delay)을 적용합니다.
    """
    if not engine: return None
    
    status_placeholder = st.empty()
    max_retries = 8
    
    for i in range(max_retries):
        try:
            # 1. 호출 전 강제 호흡 (무료 티어 보호용 쿨다운)
            time.sleep(2) 
            status_placeholder.markdown(f"<div class='status-msg'>📡 {task_name}</div>", unsafe_allow_html=True)
            
            return engine.generate_content(prompt)
            
        except exceptions.ResourceExhausted:
            # 할당량 초과 시, '에러'라고 말하지 않고 '정밀 분석 중'임을 강조하며 대기
            wait_time = (i + 1) * 10 + random.uniform(2, 5)
            for remaining in range(int(wait_time), 0, -1):
                status_placeholder.markdown(
                    f"<div class='status-msg'>🔍 [정밀 분석 단계] 지식의 위계 구조를 깊게 탐색 중입니다... ({remaining}s)</div>", 
                    unsafe_allow_html=True
                )
                time.sleep(1)
        except Exception as e:
            if i == max_retries - 1:
                st.error(f"⚠️ 시스템 연결 일시 중단: {str(e)}")
                return None
            time.sleep(3)
            
    status_placeholder.empty()
    return None

if not engine:
    st.error("❌ AI 엔진을 로드할 수 없습니다. API 키 상태를 확인해주세요.")
    st.stop()

# [4. 세션 상태 관리]
if 'stage' not in st.session_state: st.session_state.stage = 'input'
if 'data' not in st.session_state: st.session_state.data = {}

# --- PHASE 1: 개념 해체 및 위계 분석 ---
if st.session_state.stage == 'input':
    st.title("🔍 Veritas AI: 지식 결손 진단")
    st.write("학습자의 뇌 속에 꼬인 실타래를 풀어내어 **근본적인 페인포인트**를 도출합니다.")
    
    topic = st.text_input("진단할 학습 주제를 입력하세요:", placeholder="예: 근의 공식, 재귀함수, 양자역학 등")
    
    if st.button("전문 진단 프로세스 시작"):
        if topic:
            # 사용자님이 좋아하신 '그 문구'와 함께 연산 시작
            res = veritas_call(
                prompt=f"주제 '{topic}'의 핵심 정의를 2문장으로 요약하고, 이를 이해하기 위한 하위 기초 지식 5가지를 검증할 Yes/No 질문을 '1. 질문내용' 형식으로 만드세요.",
                task_name="지식의 위계 구조를 해체하고 진단 문항을 설계 중..."
            )
            if res:
                st.session_state.data['raw_questions'] = res.text
                st.session_state.data['topic'] = topic
                st.session_state.stage = 'testing'
                st.rerun()

# --- PHASE 2: 5단계 역추적 시뮬레이션 ---
elif st.session_state.stage == 'testing':
    st.subheader(f"🚩 '{st.session_state.data['topic']}' 역진단 시뮬레이션")
    st.write("아래 질문에 답하며 당신의 이해도가 어디서 단절되었는지 확인하십시오.")
    
    with st.form("diag_form"):
        lines = st.session_state.data['raw_questions'].split('\n')
        qs = [l.strip() for l in lines if l.strip() and l.strip()[0].isdigit()]
        
        responses = []
        for i, q in enumerate(qs[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            ans = st.radio("상태", ["이해함(Yes)", "모름/모호함(No)"], key=f"q_{i}", horizontal=True)
            reason = ""
            if "No" in ans:
                reason = st.text_input("사고가 막히는 구체적인 지점:", key=f"t_{i}", placeholder="예: 수식은 알겠는데 실제 의미가 헷갈려요.")
            responses.append({"q": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.form_submit_button("최종 페인포인트 분석 실행"):
            st.session_state.data['responses'] = responses
            st.session_state.stage = 'result'
            st.rerun()

# --- PHASE 3: 루트-코즈(Root-Cause) 정밀 리포트 ---
elif st.session_state.stage == 'result':
    st.title("📋 지식 결손 정밀 진단서")
    
    no_items = [r for r in st.session_state.data['responses'] if "No" in r['status']]
    
    if not no_items:
        st.success("🎉 해당 주제에 대한 지식 체계가 완벽합니다! 심화 단계로 진입하십시오.")
    else:
        # 리포트 생성 시에도 정밀 분석 메시지 출력
        report_res = veritas_call(
            prompt=f"학습자가 '{st.session_state.data['topic']}'에 대해 다음 사유로 'No'라고 답했습니다: {no_items}. 인지적 결손 지점과 당장 돌아가야 할 기초 단계를 정밀 분석하세요.",
            task_name="응답 패턴을 기반으로 인지적 구멍(Pain-point)을 모델링 중..."
        )
        if report_res:
            st.markdown(f"<div class='diag-card report-highlight'>{report_res.text}</div>", unsafe_allow_html=True)
            
    if st.button("다른 주제 진단하기"):
        st.session_state.stage = 'input'
        st.rerun()
