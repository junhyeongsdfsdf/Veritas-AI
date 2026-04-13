import streamlit as st
import google.generativeai as genai
import time
import random
import logging
from google.api_core import exceptions

# ==========================================
# 1. 시스템 아키텍처 및 로깅 설정
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# [UI 설정] 전문적인 다크 테마 및 고대비 스타일
st.set_page_config(
    page_title="Veritas AI | Root-Cause Diagnostic System",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* 메인 배경 및 폰트 */
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    
    /* 헤더 스타일 */
    .main-title { color: #58a6ff; font-weight: 800; font-size: 2.8rem; margin-bottom: 0.5rem; text-align: center; }
    .sub-title { color: #8b949e; font-size: 1.1rem; text-align: center; margin-bottom: 2rem; }
    
    /* 진단 카드 디자인 */
    .diag-card { 
        padding: 2rem; border-radius: 12px; border: 1px solid #30363d; 
        background-color: #161b22; margin-bottom: 1.5rem; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        transition: transform 0.2s ease;
    }
    .diag-card:hover { border-color: #58a6ff; }
    
    /* 버튼 럭셔리 스타일 */
    .stButton>button { 
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%); 
        color: white; border-radius: 8px; height: 4rem; 
        font-weight: bold; width: 100%; border: none; font-size: 1.2rem;
        box-shadow: 0 4px 15px rgba(35, 134, 54, 0.3);
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(46, 160, 67, 0.5); }
    
    /* 상태 안내 및 프로그레스 */
    .status-panel {
        padding: 1rem; border-radius: 8px; background: #010409;
        border-left: 5px solid #1f6feb; color: #58a6ff;
        font-family: 'Consolas', monospace; margin: 1rem 0;
    }
    
    /* 리포트 결과 강조 */
    .verdict-box { 
        border: 2px solid #238636; border-left: 10px solid #238636; 
        padding: 2rem; background: #0d1117; border-radius: 8px;
        line-height: 1.8; color: #e6edf3;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 지능형 멀티 모델 오케스트레이터 (방탄 로직)
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("ENTER SYSTEM ACCESS KEY", type="password")

if not api_key:
    st.markdown("<div class='main-title'>Veritas AI</div>", unsafe_allow_html=True)
    st.info("💡 시스템 가동을 위해 API Key가 필요합니다. 사이드바 혹은 Secrets를 확인하세요.")
    st.stop()

genai.configure(api_key=api_key)

class VeritasEngine:
    """모든 기술적 변수를 통제하고 자가 복구하는 핵심 엔진"""
    def __init__(self):
        self.model = None
        self.model_name = ""
        self.initialize_engine()

    def initialize_engine(self):
        """API 권한 내 최적 모델 자동 매칭 (404/403 원천 차단)"""
        # 가장 안정적인 모델 우선순위
        candidates = [
            'gemini-1.5-flash', 
            'gemini-1.5-pro', 
            'gemini-pro',
            'models/gemini-1.5-flash',
            'models/gemini-pro'
        ]
        
        for name in candidates:
            try:
                m = genai.GenerativeModel(name)
                # 실제 호출 테스트 (가장 확실한 검증)
                m.generate_content("test", generation_config={"max_output_tokens": 1})
                self.model = m
                self.model_name = name
                return
            except Exception:
                continue
        
        # 목록에서 동적으로 찾기
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if available:
                self.model = genai.GenerativeModel(available[0])
                self.model_name = available[0]
        except:
            pass

    def call(self, prompt, status_msg="데이터 분석 중..."):
        """429 할당량 초과 및 서버 불안정 시 지능형 재시도 로직"""
        if not self.model:
            return "엔진 로드 실패"

        placeholder = st.empty()
        max_retries = 10
        
        for i in range(max_retries):
            try:
                # 쿨다운: 무료 티어의 분당 요청 제한(RPM) 보호
                time.sleep(2) 
                placeholder.markdown(f"<div class='status-panel'>📡 {status_msg}</div>", unsafe_allow_html=True)
                
                response = self.model.generate_content(prompt)
                placeholder.empty()
                return response.text
                
            except exceptions.ResourceExhausted:
                # 429 에러 시 사용자에게 분석의 깊이를 알리며 대기
                wait_time = (i + 1) * 12 + random.uniform(1, 5)
                for sec in range(int(wait_time), 0, -1):
                    placeholder.markdown(
                        f"<div class='status-panel'>🔍 [심층 분석] 지식의 위계 구조를 탐색 중입니다. 잠시만 기다려주십시오... ({sec}s)</div>", 
                        unsafe_allow_html=True
                    )
                    time.sleep(1)
            except Exception as e:
                if i == max_retries - 1:
                    st.error(f"최종 호출 실패: {e}")
                    return None
                time.sleep(3)
        return None

# 엔진 인스턴스 생성
v_engine = VeritasEngine()

if not v_engine.model:
    st.error("❌ AI 엔진 로드 실패. API 키의 유효성 혹은 구글 서버 상태를 확인하십시오.")
    st.stop()

# ==========================================
# 3. 진단 프로세스 관리 (Session State)
# ==========================================
if 'stage' not in st.session_state: st.session_state.stage = 'ready'
if 'veritas_data' not in st.session_state: st.session_state.veritas_data = {}

# ==========================================
# 4. PHASE 1: 주제 해체 및 기초 역추적 질문 생성
# ==========================================
if st.session_state.stage == 'ready':
    st.markdown("<div class='main-title'>Veritas AI</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>학습자의 지식 결손 지점을 추적하는 인지 공학 솔루션</div>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<div class='diag-card'>", unsafe_allow_html=True)
        topic = st.text_input("진단할 학습 주제를 입력하세요:", placeholder="예: 근의 공식, 재귀함수, 양자역학...")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.button("전문 진단 엔진 가동"):
            if topic:
                res_text = v_engine.call(
                    prompt=f"""
                    당신은 교육 공학 전문가입니다. 주제: '{topic}'
                    1. 이 개념의 정의를 학습자가 이해하기 쉽게 2문장으로 요약하세요.
                    2. 이 개념을 풀기 위해 반드시 사전에 완벽히 알고 있어야 하는 '하위/기초 지식' 5가지를 검증할 수 있는 구체적인 Yes/No 질문을 만드세요.
                    형식: '1. 질문내용' (반드시 번호를 붙여 5개 생성)
                    """,
                    status_msg="지식의 위계 구조를 해체하고 진단 문항을 설계 중..."
                )
                if res_text:
                    st.session_state.veritas_data['topic'] = topic
                    st.session_state.veritas_data['raw_questions'] = res_text
                    st.session_state.stage = 'testing'
                    st.rerun()

# ==========================================
# 5. PHASE 2: 5단계 인지 검증 (사유 수집)
# ==========================================
elif st.session_state.stage == 'testing':
    st.markdown(f"### 🚩 주제: {st.session_state.veritas_data['topic']}")
    st.write("지식의 사다리가 어디서 끊어졌는지 확인합니다. 아래 질문에 대해 **본인의 실제 이해도**를 답하십시오.")
    
    with st.form("diagnosis_form"):
        # 파싱 로직: 번호로 시작하는 질문만 추출
        lines = st.session_state.veritas_data['raw_questions'].split('\n')
        questions = [l.strip() for l in lines if l.strip() and l.strip()[0].isdigit() and ('.' in l or ')' in l)]
        
        user_responses = []
        for i, q in enumerate(questions[:5]):
            st.markdown(f"<div class='diag-card'><b>{q}</b>", unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                ans = st.radio("상태", ["알고 있음(Yes)", "모름/모호함(No)"], key=f"q_{i}", horizontal=True)
            
            reason = ""
            if "No" in ans:
                reason = st.text_area("어느 지점에서 사고가 막히나요? (구체적으로 적을수록 진단이 정확해집니다)", key=f"t_{i}", placeholder="예: 수식은 알겠는데 이항 과정이 헷갈려요.")
            
            user_responses.append({"q": q, "status": ans, "reason": reason})
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.form_submit_button("최종 페인포인트 모델링"):
            st.session_state.veritas_data['responses'] = user_responses
            st.session_state.stage = 'analysis'
            st.rerun()

# ==========================================
# 6. PHASE 3: 최종 루트-코즈(Root-Cause) 정밀 리포트
# ==========================================
elif st.session_state.stage == 'analysis':
    st.markdown("### 📋 Veritas AI 정밀 진단서")
    
    with st.spinner("응답 패턴과 서술 사유를 결합하여 지식의 구멍을 모델링 중..."):
        no_data = [r for r in st.session_state.veritas_data['responses'] if "No" in r['status']]
        
        if not no_data:
            st.success("🎉 해당 주제에 대한 기초가 탄탄합니다! 심화 단계로 진입하십시오.")
        else:
            final_report = v_engine.call(
                prompt=f"""
                학습자가 '{st.session_state.veritas_data['topic']}'에 대해 다음 사유들로 'No'라고 답했습니다: {no_data}.
                사용자의 주관적 설명을 분석하여 챗봇식 설명이 아닌, 전문가의 '진단'을 내리세요.
                
                [필수 포함 항목]
                1. 결손 지점 (어느 단계의 논리가 무너졌는가)
                2. 인지적 오류 분석 (사용자가 이 부분을 어려워하는 진짜 이유)
                3. 학습 제언 (당장 되돌아가서 메워야 할 기초 지점)
                """,
                status_msg="지식 결손 지점(Pain-point) 최종 도출 중..."
            )
            if final_report:
                st.markdown(f"<div class='verdict-box'>{final_report}</div>", unsafe_allow_html=True)
                
    if st.button("새로운 진단 시작"):
        # 세션 초기화 후 재시작
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# ==========================================
# [추가 코드: 시스템 안정성 가이드]
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ System Status")
    st.markdown(f"**Engine:** `{v_engine.model_name}`")
    st.markdown("---")
    st.write("본 시스템은 구글 서버의 Quota 제한을 지능적으로 회피하도록 설계되었습니다. 대기 시간이 발생하더라도 브라우저를 닫지 말고 잠시만 기다려주십시오.")
