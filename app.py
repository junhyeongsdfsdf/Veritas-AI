import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Veritas AI", layout="centered")

st.title("🔍 Veritas AI: ML 페인포인트 진단")
st.write("트랜스포머(Transformer)의 핵심 원리를 설명해보세요.")

# Secrets 확인
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")

if not api_key:
    st.info("API Key가 필요합니다. 설정(Secrets)에 등록하거나 사이드바에 입력해주세요.")
    st.stop()

# AI 설정
genai.configure(api_key=api_key)

# 가장 호환성이 높은 모델 이름으로 설정합니다.
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except:
    model = genai.GenerativeModel('gemini-pro')

user_input = st.text_area("설명을 적어주세요:", height=200, placeholder="예: Self-Attention이 왜 필요한가요?")

if st.button("진단 시작"):
    if user_input:
        with st.spinner("전문가가 당신의 논리를 분석하고 있습니다..."):
            try:
                prompt = f"""
                당신은 머신러닝 교육 전문가입니다. 사용자의 설명을 듣고 지식의 결함을 진단하세요.
                
                [분석 항목]
                1. 개념의 정확성 (0-100점)
                2. 누락된 핵심 키워드
                3. 논리적 오류 지점
                4. 페인포인트 역추적 결과
                
                사용자 설명: {user_input}
                """
                response = model.generate_content(prompt)
                st.subheader("📋 Veritas 진단 리포트")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"모델 연결 오류: {e}")
                st.info("API 키가 올바른지, 혹은 Google AI Studio에서 사용 가능한 모델인지 확인해주세요.")
    else:
        st.warning("내용을 입력해주세요.")
