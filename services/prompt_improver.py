# services/prompt_improver.py
from typing import Tuple
from core.config import GEN_MODEL
from services.openai_client import get_client

client = get_client()

def classify_expert(prompt: str) -> str:
    system = (
        "너는 '프롬프트 개선' 상담을 위한 라우터다. "
        "다음 전문가 중 하나만 선택해라: kim, park, hwang, cha, lee.\n"
        "- kim: ambiguous in meaning\n"
        "- park: a lack of conditions\n"
        "- hwang: Output Format Undetermined\n"
        "- cha: Implementation method not determined\n"
        "- lee: Answer Difficulty Undetermined\n"
        "출력은 반드시 전문가 이름 하나만(영문 소문자) 출력."
    )
    resp = client.responses.create(
        model=GEN_MODEL,
        input=[{"role":"system","content":system},
               {"role":"user","content":f"사용자 프롬프트:\n{prompt}\n\n어느 전문가가 가장 적절해?"}],
        temperature=0
    )
    text = resp.output_text.strip().lower()
    return text if text in ["kim","park","hwang","cha","lee"] else "kim"

def generate_improvement(prompt: str, expert_name: str) -> Tuple[str, str]:
    system = "너는 프롬프트 개선 전문가다. 사용자의 원문 프롬프트를 더 명확하고 실행가능하게 개선한다."
    user = f"""
전문가: {expert_name}

사용자 원문 프롬프트:
\"\"\"{prompt}\"\"\"

요구:
1) 개선된 프롬프트 1개를 제시 (따옴표 없이)
2) 전문가 피드백 요약 3줄 이내

출력 형식(정확히 지켜):
[IMPROVED_PROMPT]
...
[SUMMARY]
- ...
- ...
- ...
""".strip()

    resp = client.responses.create(
        model=GEN_MODEL,
        input=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.3
    )
    out = resp.output_text.strip()

    if "[IMPROVED_PROMPT]" in out and "[SUMMARY]" in out:
        improved = out.split("[IMPROVED_PROMPT]", 1)[1].split("[SUMMARY]", 1)[0].strip()
        summary_block = out.split("[SUMMARY]", 1)[1].strip()
        summary_lines = [ln.strip("- ").strip() for ln in summary_block.splitlines() if ln.strip()]
        summary = "\n".join([f"- {s}" for s in summary_lines[:3]])
        return improved, summary

    return out, "- 요약 형식이 예상과 달라 자동 요약이 적용되지 않았습니다."
