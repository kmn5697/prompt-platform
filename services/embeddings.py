# services/embeddings.py
import json
import numpy as np
from typing import List, Tuple
from core.config import EMBED_MODEL, TOP_K
from services.openai_client import get_client
from core.db import list_cases_with_embeddings
from core import config

embed_model = config.EMBED_MODEL
top_k = config.TOP_K


client = get_client()

def get_embedding(text: str) -> List[float]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)

def find_similar_cases(prompt: str, top_k: int = TOP_K) -> Tuple[List[dict], List[float]]:
    query_emb = np.array(get_embedding(prompt), dtype=np.float32)
    rows = list_cases_with_embeddings()

    scored = []
    for case_id, original, improved, summary, expert_name, emb_json in rows:
        emb = np.array(json.loads(emb_json), dtype=np.float32)
        sim = cosine_sim(query_emb, emb)
        scored.append((sim, case_id, original, improved, summary, expert_name))

    scored.sort(reverse=True, key=lambda x: x[0])
    top = scored[:top_k]

    results = [{
        "similarity": sim,
        "case_id": case_id,
        "original": original,
        "improved": improved,
        "summary": summary,
        "expert": expert_name
    } for sim, case_id, original, improved, summary, expert_name in top]

    return results, query_emb.tolist()
