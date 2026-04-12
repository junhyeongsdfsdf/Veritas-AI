# Veritas AI: ML 페인포인트 진단 엔진

> **"학습의 완성은 타인에게 설명하는 과정에서 비로소 증명됩니다."**
> 
> Veritas AI는 사용자가 머신러닝 개념을 직접 설명하면, 이를 분석하여 지식의 공백(Pain-point)을 정밀하게 진단하는 AI 학습 보조 도구입니다.

---

## 1. 기획 의도 (Project Intent)
단순한 정답 확인 방식은 학습자가 '안다고 착각하는' 인지적 오류를 발견하기 어렵습니다. 본 프로젝트는 학습자가 자신의 언어로 개념을 풀어서 설명하는 **'역설명(Reverse-Explanation)'** 방식을 통해, 논리적 비약과 핵심 매커니즘의 누락을 추적하여 학습자가 무엇을 보완해야 하는지 명확히 인지하게 돕는 데 주안점을 두었습니다.

---

## 2. 주요 기능 (Key Features)
* **설명 기반 지식 진단**: 트랜스포머, 어텐션 등 복잡한 ML 아키텍처를 대상으로 사용자의 설명을 심층 분석합니다.
* **지식 결함 역추적 (Backtracking)**: 특정 오답의 근본 원인이 되는 기초 개념(예: 선형대수, 확률론 등)을 역추적하여 근본적인 페인포인트를 짚어냅니다.
* **정밀 진단 리포트 생성**: 
  - 기술적 무결성을 바탕으로 한 개념 정확도(%) 산출
  - 누락된 필수 핵심 키워드 검출
  - 논리적 오류 지점 지적 및 개인화된 보완 학습 방향 제언

---

## 3. 기술 스택 (Tech Stack)
| 구분 | 사용 기술 |
| :--- | :--- |
| **Language** | Python 3.9+ |
| **LLM Engine** | Google Gemini 1.5 Flash (Generative AI) |
| **Framework** | Streamlit |
| **Deployment** | Streamlit Community Cloud |
| **Library** | `google-generativeai`, `streamlit` |

---

## 4. 시스템 로직 (Logic Flow)
1. **Input**: 사용자가 특정 머신러닝 주제에 대해 자유롭게 설명 입력
2. **Analysis**: Gemini API를 통한 프롬프트 엔지니어링 기반의 지식 구조 해체
3. **Detection**: 지식 그래프 기반 데이터 대조를 통한 논리 결함 및 키워드 누락 확인
4. **Report**: 최종 진단 결과 및 개인화된 학습 로드맵 생성

---

## 5. 시작하기 (Quick Start)

### 저장소 복제 및 라이브러리 설치
```bash
git clone [https://github.com/junhyeongsdfsdf/Veritas-AI.git](https://github.com/junhyeongsdfsdf/Veritas-AI.git)
pip install -r requirements.txt
