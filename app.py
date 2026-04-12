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

genai.configure(api_key=api_key)

# [수정 포인트] 사용 가능한 모델을 안전하게 선택합니다.
@st.cache_resource
def load_model():
    # 시도해볼 모델 목록
    model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    for name in model_names:
        try:
            model = genai.GenerativeModel(name)
            # 테스트 호출 (실제 작동하는지 확인)
            model.generate_content("test", generation_config={"max_output_tokens": 1})
            return model
        except:
            continue
    return None

model = load_model()

if model is None:
    st.error("사용 가능한 Gemini 모델을 찾을 수 없습니다. API 키 권한을 확인해주세요.")
    st.stop()

user_input = st.text_area("설명을 적어주세요:", height=200, placeholder="예: Self-Attention이 왜 필요한가요?")

if st.button("진단 시작"):
    if user_input:
        with st.spinner("전문가가 당신의 논리를 분석 중입니다..."):
            try:
                prompt = f"당신은 머신러닝 전문가입니다. 다음 설명을 진단하세요: {user_input}"
                response = model.generate_content(prompt)
                st.subheader("📋 Veritas 진단 리포트")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"진단 중 오류 발생: {e}")
    else:
        st.warning("내용을 입력해주세요.")
