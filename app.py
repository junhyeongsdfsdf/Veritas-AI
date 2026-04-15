def build_smart_diagnosis_from_no(weak_points: List[Dict]) -> Dict:
    """
    사용자의 No 응답만 기반으로
    놓친 개념 / 개념 설명 / 추가 학습 포인트를 똑똑하게 생성
    """
    weak_text = " ".join(
        [f"{x['question']} {x.get('reason', '')}" for x in weak_points]
    )

    missed = []
    explanations = []
    extras = []

    # 수학
    if any(k in weak_text for k in ["공식", "함수", "방정식", "근의"]):
        missed.append("공식 구조 이해")
        explanations.append("공식은 단순 암기가 아니라 각 항이 어떤 역할을 하는지 이해해야 응용이 가능합니다.")
        extras.extend(["변수 관계", "대입 순서", "예외 조건"])

    # 프로그래밍
    if any(k in weak_text for k in ["코드", "반복", "조건", "에러", "버그", "python", "java", "c"]):
        missed.append("조건 흐름 추적")
        explanations.append("코드 실행 순서와 조건 분기를 머릿속으로 따라가는 힘이 부족한 상태입니다.")
        extras.extend(["if 조건", "반복문 종료", "디버깅 순서"])

    # 언어 / 문장
    if any(k in weak_text for k in ["문장", "영어", "어순", "문법"]):
        missed.append("문장 구조 분석")
        explanations.append("문장의 핵심 의미보다 구조를 먼저 파악해야 응용력이 생깁니다.")
        extras.extend(["어순", "시제", "표현 비교"])

    # 기본 fallback
    if not missed:
        missed = ["핵심 개념 구조화"]
        explanations = ["개념은 알고 있지만 구조적으로 연결되지 않아 응용 단계에서 막히는 상태입니다."]
        extras = ["기초 정의", "적용 예시", "실수 패턴"]

    return {
        "missed": missed[:3],
        "explanation": explanations[:3],
        "extra": extras[:5]
    }
