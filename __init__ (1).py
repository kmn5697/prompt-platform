# services/expert_test_bank.py
import re
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ExpertTestProblem:
    id: int
    title: str
    bad_prompt: str
    keywords_to_fix: List[str]


# ✅ 3문제만
PROBLEMS: List[ExpertTestProblem] = [
    ExpertTestProblem(
        id=1,
        title="문제 1) 글자 출력",
        bad_prompt="파이썬으로 글자 출력해줘",
        keywords_to_fix=["어떤 글자?", "코드로 보여줄지?", "결과 예시 포함?", "몇 번 출력? (선택)"],
    ),
    ExpertTestProblem(
        id=2,
        title="문제 2) 더하기",
        bad_prompt="숫자 두 개 더해줘",
        keywords_to_fix=["입력 방식(input 등)", "출력 방식(print 등)", "예시 포함", "변수 이름 (선택)"],
    ),
    ExpertTestProblem(
        id=3,
        title="문제 3) 여러 번 출력",
        bad_prompt="여러 번 출력해줘",
        keywords_to_fix=["무엇을 출력?", "몇 번?", "반복 방식(for/반복문)", "주석/설명 (선택)"],
    ),
]


def _has_quote_text(s: str) -> bool:
    return bool(re.search(r"(['\"]).+?\1", s))


def _has_number(s: str) -> bool:
    return bool(re.search(r"\d+", s))


def _has_any(s: str, kws: List[str]) -> bool:
    s = (s or "").lower()
    return any(k.lower() in s for k in kws)


def grade_problem(problem_id: int, user_prompt: str, pass_min: int = 2) -> Dict:
    """
    ✅ 매우 쉬운 기준:
    - 각 문제의 조건 4개 중 pass_min(기본 2개) 이상 충족하면 정답

    returns:
      {
        "is_correct": bool,
        "matched": [...],
        "missing": [...],
        "score": int,
        "pass_min": int
      }
    """
    t = (user_prompt or "").strip()
    checks = []

    if problem_id == 1:
        checks = [
            ("어떤 글자(따옴표)", _has_quote_text(t)),
            ("코드로 요구", _has_any(t, ["코드", "python", "파이썬"])),
            ("예시 요구", _has_any(t, ["예시", "출력 예시", "예:"])),
            ("횟수(숫자/반복)", _has_number(t) or _has_any(t, ["반복", "몇 번", "for"])),
        ]
    elif problem_id == 2:
        checks = [
            ("입력 방식", _has_any(t, ["input", "입력"])),
            ("출력 방식", _has_any(t, ["print", "출력"])),
            ("예시", _has_any(t, ["예시", "예:"])),
            ("변수 언급", _has_any(t, ["변수", "a", "b", "x", "y"])),
        ]
    elif problem_id == 3:
        checks = [
            ("무엇을 출력(따옴표)", _has_quote_text(t)),
            ("몇 번(숫자)", _has_number(t) or _has_any(t, ["n번", "N번", "몇 번"])),
            ("반복 방식", _has_any(t, ["for", "반복문", "반복"])),
            ("주석/설명", _has_any(t, ["주석", "설명"])),
        ]
    else:
        raise ValueError("Invalid problem_id")

    matched = [label for label, ok in checks if ok]
    missing = [label for label, ok in checks if not ok]

    score = len(matched)
    is_correct = score >= pass_min

    return {
        "is_correct": is_correct,
        "matched": matched,
        "missing": missing,
        "score": score,
        "pass_min": pass_min,
    }


__all__ = ["PROBLEMS", "grade_problem", "ExpertTestProblem"]
