import re
import time
import logging
import random
import urllib.parse
from typing import List, Dict

import streamlit as st
from openai import OpenAI

# ==========================================
# 1) CONFIG & PREMIUM STYLING
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Veritas AI | Smart Diagnostic",
    page_icon="🔍",
    layout="centered",
)

st.markdown("""
<style>
.stApp {
    background-color: #0d1117;
    color: #c9d1d9;
}
.main-title {
    color: #58a6ff;
    font-size: 2.5rem;
    font-weight: 800;
    text-align: center;
}
.diag-card {
    padding: 1.2rem;
    border: 1px solid #30363d;
    border-radius: 12px;
    margin-bottom: 1rem;
    background:#161b22;
}
/* 진단 결과용 대형 중앙 제목 스타일 */
.result-header {
    color: #58a6ff;
    font-size: 3.5rem;
    font-weight: 900;
    text-align: center;
    margin-top: 2.5rem;
    margin-bottom: 2.5rem;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2) INTELLIGENT DOMAIN INFERENCE (완전 복구)
# ==========================================
UNIVERSAL_DIAGNOSTIC_DIMENSIONS = ["핵심 의미", "구조 분해", "원리 설명", "응용 적용", "예방 가능성"]

def infer_input_type(user_input: str) -> str:
    """사용자가 입력한 텍스트의 성격을 분석하여 도메인을 추론합니다."""
    text = user_input.strip().lower()
    # 코딩 도메인 추론
    if any(sym in text for sym in ["def ", "for ", "while ", "{", "}", ";"]): 
        return "code"
    # 문제 상황 도메인 추론
    if any(k in text for k in ["error", "bug", "안돼", "왜", "막혀", "실패"]): 
        return "problem"
    # 문장/언어 도메인 추론
    if len(text.split()) >= 4: 
        return "sentence"
    # 일반 개념 도메인
    return "concept"

def extract_learning_facets(user_input: str) -> List[str]:
    """도메인별로 학습자가 막힐 수 있는 지능형 지표(Facets)를 추출합니다."""
    input_type = infer_input_type(user_input)
    facet_map = {
        "concept": [
            "개념의 핵심 메커니즘을 타인에게 설명 가능한지",
            "세부 구성 요소들 간의 상호작용을 구분하는지",
            "동작 원리의 논리적 인과관계를 이해하는지",
            "변칙적인 새로운 사례에 개념을 대입 가능한지",
            "유사한 고난도 개념과 논리적으로 비교 가능한지",
        ],
        "code": [
            "데이터의 복합적인 흐름과 변수 변화를 추적 가능한지",
            "제어문의 임계 조건 및 예외 처리 기준을 설명 가능한지",
            "발생 가능한 에러 원인을 논리적으로 재현하는지",
            "유사한 아키텍처에 해당 로직을 수정 적용이 가능한지",
            "더 나은 성능과 안정적인 구조로 개선할 수 있는지",
        ],
        "sentence": [
            "문장의 심층적인 맥락과 함축적 의미를 파악하는지",
            "복잡한 통사 구조와 어순의 상관관계를 분석 가능한지",
            "다른 문맥에서도 본래 의미를 유지하며 표현 가능한지",
            "미세한 뉘앙스 차이를 논리적으로 구분하는지",
            "고급 문장 구조를 직접 설계하고 재구성할 수 있는지",
        ],
        "problem": [
            "문제의 근본 원인을 논리적 가설로 정의 가능한지",
            "병목 현상이 발생하는 정확한 지점을 특정하는지",
            "해결 과정을 논리적 단계별로 타당하게 설명 가능한지",
            "환경이 변화된 상황에도 해결책을 유연하게 적용 가능한지",
            "구조적인 재발 방지책을 설계하고 검증 가능한지",
        ],
    }
    return facet_map.get(input_type, UNIVERSAL_DIAGNOSTIC_DIMENSIONS)

def build_fallback_questions(topic: str) -> List[str]:
    """AI 엔진이 실패할 경우, 도메인 추론을 기반으로 고수준 질문을 직접 생성합니다."""
    facets = extract_learning_facets(topic)
    # [사용자 요청] 라벨 없이 깔끔하게 질문 생성
    templates = [
        "{idx}. 현재 '{facet}' 관점에서 본인의 장악력이 완벽하다고 확신하시나요?",
        "{idx}. 이 원리가 복합적인 변수로 작용할 때도 결과 예측이 가능합니까?",
        "{idx}. 해당 과정에서 발생할 수 있는 잠재적 오류를 논리적으로 설명할 수 있나요?",
        "{idx}. 유사하지만 완전히 다른 맥락에서도 이 메커니즘을 적용 가능합니까?",
        "{idx}. 다음 단계에서 발생할 수 있는 구조적 문제를 사전에 차단할 수 있나요?",
    ]
    return [templates[i].format(idx=i + 1, facet=facet) for i, facet in enumerate(facets[:5])]

def extract_questions(raw: str) -> List[str]:
    """AI가 생성한 텍스트에서 번호가 붙은 질문만 정규표현식으로 추출합니다."""
    lines = raw.split("\n")
    results = [l.strip() for l in lines if re.match(r"^\d+[.)]", l.strip())]
    return results[:5]

# ==========================================
# 3) GPT-5.4 ENGINE (고난도 질문 생성)
# ==========================================
class VeritasEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-5.4" # 사용자님 지정 모델

    def generate_questions(self, topic: str) -> List[str]:
        # [사용자 요청] 질문 수준 상향 및 라벨/별표(**) 제거 지시
        prompt = f"""
        당신은 인지 심리학과 교육 공학을 전공한 전문 평가 위원입니다.
        주제: {topic}

        미션:
        1. 단순 암기 여부가 아닌, 개념의 본질적인 원리, 인과관계, 제약 조건을 깊이 있게 묻는 **고난도 Yes/No 질문** 5개를 생성하세요.
        2. 질문의 난이도를 높여 학습자가 자신의 논리적 허점을 스스로 깨닫게 만드세요.
        3. 문장 앞에 '**이해**', '**구조**', '**응용**'과 같은 라벨이나 별표(**)를 **절대** 붙이지 마세요.
        4. 오직 '1. [질문 내용]' 형식으로만 출력하세요.

        출력 예시:
        1. 특정 조건이 변화했을 때 전체 시스템에 미치는 영향을 논리적으로 예측할 수 있나요?
        """
        response = self.client.responses.create(
            model=self.model_name,
            input=prompt,
        )
        return extract_questions(response.output_text.strip())

# ==========================================
# 4) ANALYSIS ENGINE (1, 3, 4번 전용)
# ==========================================
def local_root_cause_analysis(topic: str, weak_points: List[Dict]) -> str:
    """AI 분석 실패 시 로컬에서 1, 3, 4번 항목을 생성합니다."""
    concepts = ["- 핵심 메커니즘의 인과관계 재정립", "- 임계 조건 및 반례 데이터 분석", "- 구조적 아키텍처에 대한 심층 복습"]
    return f"""
## 1. 결손 지점
'{topic}'에 대한 심층적 추론 단계에서 사고의 단절이 확인되었습니다.

## 3. 놓친 핵심 개념
{chr(10).join(concepts)}

## 4. 바로 해야 할 학습 액션
- 개념의 정의를 넘어, 작동 원리를 타인에게 완벽히 설명할 수 있을 때까지 복습해보세요.
""".strip()

# ==========================================
# 5) SESSION & 6) API KEY
# ==========================================
if "stage" not in st.session_state: st.session_state.stage = "ready"
if "data" not in st.session_state: st.session_state.data = {}

api_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input("OPENAI API KEY", type="password")
if not api_key:
    st.warning("시스템 가동을 위해 API KEY가 필요합니다.")
    st.stop()
engine = VeritasEngine(api_key)

# ==========================================
# 7) READY PAGE (60초 사투 로직 포함)
# ==========================================
if st.session_state.stage == "ready":
    st.markdown("""
    <div style='position: relative; display: inline-block; width: 100%; text-align: center;'>
        <div class='main-title'>Veritas AI</div>
        <div style='position: absolute; right: 28%; bottom: -8px; font-size: 0.8rem; color: #8b949e;'>by Jun</div>
    </div>
    """, unsafe_allow_html=True)

    topic = st.text_input("진단할 학습 주제를 입력하세요", placeholder="예: 탄젠트의 원리, SQL JOIN 연산, 재귀함수...")

    if st.button("전문 진단 엔진 가동"):
        if topic:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            progress_text.markdown("### 고난도 진단 문항을 설계 중입니다... 🤗")
            start_time, questions = time.time(), []

            # 사용자님이 강조하신 60초 사투 루프
            while time.time() - start_time < 60:
                elapsed = time.time() - start_time
                progress_bar.progress(min(int((elapsed / 60) * 100), 100))
                try:
                    questions = engine.generate_questions(topic)
                    if len(questions) >= 5: break
                except Exception as e:
                    logger.warning(f"AI 시도 실패: {e}")
                time.sleep(2)

            # 60초 사투 후에도 실패 시 지능형 Fallback 가동
            if len(questions) < 5: 
                questions = build_fallback_questions(topic)
            
            progress_bar.progress(100)
            st.session_state.data = {"topic": topic, "questions": questions}
            st.session_state.stage = "testing"
            st.rerun()

# ==========================================
# 8) TESTING PAGE
# ==========================================
elif st.session_state.stage == "testing":
    st.subheader(f"🔍 심층 진단 주제: {st.session_state.data['topic']}")
    with st.form("test_form"):
        responses = []
        for i, q in enumerate(st.session_state.data["questions"]):
            st.markdown(f"<div class='diag-card'><b>{q}</b></div>", unsafe_allow_html=True)
            ans = st.radio(f"q{i}", ["Yes", "No"], horizontal=True, label_visibility="collapsed", key=f"radio_{i}")
            reason = st.text_input(f"사고가 막힌 구체적 지점 {i+1}", key=f"reason_{i}") if ans == "No" else ""
            responses.append({"question": q, "answer": ans, "reason": reason})

        if st.form_submit_button("최종 결손 모델링 시작"):
            st.session_state.data["responses"] = responses
            st.session_state.stage = "analysis"
            st.rerun()

# ==========================================
# 9) ANALYSIS PAGE (제목 중앙 배치 및 1, 3, 4번 출력)
# ==========================================
elif st.session_state.stage == "analysis":
    # [사용자 요청] 제목을 정중앙에 거대하게 배치 (3.5rem)
    st.markdown("<div class='result-header'>진단 결과 ☺️</div>", unsafe_allow_html=True)

    weak_points = [x for x in st.session_state.data["responses"] if x["answer"] == "No"]

    if not weak_points:
        st.success("🎉 축하합니다! 모든 고난도 추론 단계를 통과하셨습니다. 학습 구조가 매우 견고합니다.")
    else:
        with st.spinner("인지적 단절 부위를 정밀 분석 중입니다..."):
            report = None
            try:
                # [사용자 요청] 2번 '왜 어려운지' 제외 및 1, 3, 4번만 생성 지시
                analysis_prompt = f"""
                당신은 학습 결손 진단 전문가입니다. 주제: {st.session_state.data['topic']}
                학습자가 어려워한 문항과 사유: {weak_points}
                
                아래 **3가지 항목으로만** 분석 리포트를 작성하세요. (2번 '왜 어려운지'는 절대 포함하지 마세요)
                ## 1. 결손 지점
                ## 3. 놓친 핵심 개념
                ## 4. 바로 해야 할 학습 액션 (각 문장에 챗지피티 검색이 가능하도록 구체적으로 작성)
                """
                response = engine.client.responses.create(model=engine.model_name, input=analysis_prompt)
                report = response.output_text.strip()
            except: pass

            if not report: 
                report = local_root_cause_analysis(st.session_state.data["topic"], weak_points)

        # 4번 항목의 각 문장에 챗지피티 자동 검색 링크 입히기
        if "## 4. 바로 해야 할 학습 액션" in report:
            main_body, action_part = report.split("## 4. 바로 해야 할 학습 액션")
            st.markdown(main_body)
            st.markdown("## 4. 바로 해야 할 학습 액션 (클릭 시 ChatGPT 검색 연동)")
            
            actions = re.split(r'\n|- |\* |\d+\. ', action_part.strip())
            for act in actions:
                clean_act = act.strip()
                if len(clean_act) > 5:
                    encoded_q = urllib.parse.quote(clean_act)
                    st.markdown(f"- [{clean_act}](https://chatgpt.com/?q={encoded_q})")
        else:
            st.markdown(report)

    if st.button("새 주제 진단"):
        st.session_state.clear()
        st.rerun()
