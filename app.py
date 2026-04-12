import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Veritas AI", layout="centered")
st.title("🔍 Veritas AI: ML 진단")

# 1. API 키 확인
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")

if not api_key:
    st.info("사이드바나 Secrets에 API 키를 넣어주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 2. 작동 가능한 모델 자동 탐색 (핵심 로직)
@st.cache_resource
def get_model():
    try:
        # 내 API 키가 쓸 수 있는 모델 목록을 가져옵니다.
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 우선순위: flash -> pro -> 일반 gemini
        for target in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
            if target in available_models:
                return genai.GenerativeModel(target)
        # 목록에 있는 것 중 아무거나 첫 번째꺼 선택
        return genai.GenerativeModel(available_models[0])
    except Exception as e:
        return str(e)

result = get_model()

if isinstance(result, str):
    st.error(f"❌ API 연결 실패: {result}")
    st.stop()
else:
    model = result
    st.success(f"✅ 연결 성공: {model.model_name}")

# 3. 서비스 화면
user_input = st.text_area("설명을 적어주세요:", placeholder="예: Self-Attention이 왜 필요한가요?")

if st.button("진단 시작"):
    if user_input:
        with st.spinner("분석 중..."):
            try:
                response = model.generate_content(f"머신러닝 전문가로서 다음을 진단해줘: {user_input}")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"에러 발생: {e}")
