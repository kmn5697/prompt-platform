# services/expert_qualification.py
import os
import pandas as pd
from typing import List, Tuple, Optional

CSV_PATH = os.path.join("data", "exp.data.csv")
REQUIRED_COLUMNS = ["name", "field", "expertise", "publications"]


def ensure_exp_csv():
    # 파일 없으면 새로 생성
    if not os.path.exists(CSV_PATH):
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        return

    # 컬럼 보정(안전장치)
    df = pd.read_csv(CSV_PATH)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[REQUIRED_COLUMNS]
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")


def infer_expert_domains(prompts: List[str]) -> Tuple[str, Optional[str]]:
    text = " ".join([p or "" for p in prompts]).lower()

    scores = {
        "교육형 프롬프트 전문가": 0,
        "입출력 명세 전문가": 0,
        "구조화 전문가": 0,
        "예외처리 감각": 0,
    }

    def add_if(words, key, pts=1):
        if any(w in text for w in words):
            scores[key] += pts

    add_if(["초보", "단계", "설명", "주석"], "교육형 프롬프트 전문가", 2)
    add_if(["input", "입력", "print", "출력", "예시", "예:"], "입출력 명세 전문가", 2)
    add_if(["형식", "조건", "정확히", "반드시", "포맷"], "구조화 전문가", 2)
    add_if(["예외", "오류", "에러", "숫자 아니면"], "예외처리 감각", 2)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary, pscore = ranked[0]
    secondary, sscore = ranked[1]

    if pscore == 0:
        return "구조화 전문가", None

    # 2등이 1등의 70% 이상이면 부 분야로 인정
    if sscore >= max(1, int(pscore * 0.7)):
        return primary, secondary
    return primary, None


def add_expert_to_exp_csv(name: str, primary_domain: str, secondary_domain: Optional[str]) -> bool:
    ensure_exp_csv()
    df = pd.read_csv(CSV_PATH)

    # 중복 방지
    if name in df["name"].astype(str).values:
        return False

    expertise = primary_domain + (f", {secondary_domain}" if secondary_domain else "")

    new_row = {
        "name": name,
        "field": "python",
        "expertise": expertise,
        "publications": "prompt_improvement",
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    return True
