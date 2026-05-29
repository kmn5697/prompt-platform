# services/expert_registry.py
import csv
from typing import List, Dict, Optional

def load_experts(csv_path: str) -> List[Dict[str, str]]:
    """
    exp.data.csv 컬럼 예시: name, field, expertise, publications
    """
    experts = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            experts.append({
                "name": (row.get("name") or "").strip(),
                "field": (row.get("field") or "").strip(),
                "expertise": (row.get("expertise") or "").strip(),
                "publications": (row.get("publications") or "").strip(),
            })
    # name 없는 행 제거
    return [e for e in experts if e["name"]]

def find_expert(experts: List[Dict[str, str]], name: str) -> Optional[Dict[str, str]]:
    name = (name or "").strip().lower()
    for e in experts:
        if e["name"].lower() == name:
            return e
    return None
