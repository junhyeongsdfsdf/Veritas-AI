import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Veritas AI", layout="centered")

st.title("🔍 Veritas AI: ML 페인포인트 진단")

# 1. API 키 확인
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")

if not api_key:
    st.info("API Key가 필요합니다. 설정(Secrets)에 등록하거나 사이드바에 입력해주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 2. 모델 로드 및 구체적인 에러 확인
def get_working_model():
    # 2026년 기준 가장 최신/안정적인 모델명 리스트
    test_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    last_error = ""
    
    for name in test_models:
        try:
            model = genai.GenerativeModel(name)
            # 아주 짧은 테스트 문장으로 키가 작동하는지 확인
            model.generate_content("hi", generation_config={"max_output_tokens": 1})
            return model, None
        except Exception as e:
            last_error = str(e)
            continue
    return None, last_error

model, error_msg = get_working_model()

if model is None:
    st.error("❌ 사용 가능한 Gemini 모델을 찾을 수 없습니다.")
    st.warning(f"구글 서버의 응답: {error_msg}") # 이 부분이 핵심입니다!
    st.info("API 키가 'Google AI Studio'에서 생성된 것이 맞는지, 혹은 유효한지 확인해주세요.")
    st.stop()

# 3. 서비스 화면
user_input = st.text_area("설명을 적어주세요:", height=200, placeholder="예: Self-Attention이 왜 필요한가요?")

if st.button("진단 시작"):
    if user_input:
        with st.spinner("전문가가 분석 중입니다..."):
            try:
                response = model.generate_content(f"머신러닝 전문가로서 다음을 진단해줘: {user_input}")
                st.subheader("📋 Veritas 진단 리포트")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"오류 발생: {e}")
    else:
        st.warning("내용을 입력해주세요.")
