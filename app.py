import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="Veritas AI", layout="centered")

st.title("🔍 Veritas AI: ML 페인포인트 진단")
st.write("트랜스포머(Transformer)의 핵심 원리를 설명해보세요.")

# --- 보안 설정 섹션 ---
# 1. 먼저 서버 설정(Secrets)에 키가 있는지 확인합니다.
# 2. 없다면(로컬 테스트용) 사이드바에서 입력을 받습니다.
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")

if not api_key:
    st.info("API Key가 필요합니다. 설정에서 등록하거나 사이드바에 입력해주세요.")
    st.stop() # 키가 없으면 여기서 실행 중단

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-pro')

# --- 서비스 로직 ---
user_input = st.text_area("설명을 적어주세요:", height=200, placeholder="예: Self-Attention에서 Query, Key, Value의 역할은 무엇인가요?")

if st.button("진단 시작"):
    if user_input:
        with st.spinner("전문가가 당신의 논리를 분석하고 있습니다..."):
            # 기술적 완성도를 보여주는 프롬프트
            prompt = f"""
            당신은 세계 최고의 머신러닝 아키텍트입니다. 
            사용자의 설명을 듣고 '지식의 탑'이 무너지지 않았는지 검증하세요.
            
            [분석 가이드라인]
            1. 개념의 정확성 (0-100점)
            2. 누락된 핵심 매커니즘 (예: Scaling, Masking 등)
            3. 논리적 오류: 잘못 이해하고 있는 인과관계 지적
            4. 페인포인트 역추적: 이 오류가 발생한 근본적인 하위 개념(예: 선형대수, 확률) 제시
            
            사용자 설명: {user_input}
            """
            response = model.generate_content(prompt)
            st.subheader("📋 Veritas 진단 리포트")
            st.markdown(response.text)
