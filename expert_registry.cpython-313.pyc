import json
from openai import OpenAI
from core.config import GEN_MODEL

client = OpenAI()

CANDIDATE_KEYWORDS = [
    "목적 구체화",
    "출력 형식 명확화",
    "입력 조건 보완",
    "역할(Role) 설정",
    "제약 조건 추가",
    "단계별 요청",
    "예시 제공",
    "대상 수준 명시",
    "톤/스타일 지정",
    "언어/도구 명시"
]

def recommend_keywords(prompt: str, max_keywords: int = 3):
    """
    프롬프트를 분석해 개선이 필요한 키워드를 추천한다.
    - 반드시 list[str] 형태로 반환
    - 짧거나 모호한 프롬프트라도 최소 1개는 추천
    """

    system = f"""
너는 프롬프트 작성 코치다.

아래 프롬프트를 보고, 개선이 필요한 관점의 키워드를 추천하라.

선택 가능한 키워드:
{", ".join(CANDIDATE_KEYWORDS)}

규칙:
- 프롬프트가 짧거나 모호하면, 개선 효과가 큰 키워드를 우선 추천한다
- 최대 {max_keywords}개
- 반드시 JSON 배열만 출력한다
- 설명, 문장, 텍스트는 절대 포함하지 않는다

출력 예시:
["목적 구체화", "출력 형식 명확화"]
"""

    res = client.chat.completions.create(
        model=GEN_MODEL,
        messages=[
            {"role": "system", "content": system.strip()},
            {"role": "user", "content": prompt.strip()}
        ],
        temperature=0.2
    )

    content = (res.choices[0].message.content or "").strip()

    # 🔑 핵심: 무조건 JSON 배열로 파싱
    try:
        data = json.loads(content)
        if isinstance(data, list) and data:
            return [k for k in data if k in CANDIDATE_KEYWORDS][:max_keywords]
    except Exception:
        pass

    # 🔁 파싱 실패 or 빈 결과면 기본 추천
    return ["목적 구체화", "출력 형식 명확화"][:max_keywords]
