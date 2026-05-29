# core/config.py
from pathlib import Path

# 프로젝트 루트 기준(파일 위치가 core/config.py 라는 전제)
BASE_DIR = Path(__file__).resolve().parent.parent

# DB 경로
DB_PATH = str(BASE_DIR / "data" / "app.db")

# 모델 이름
EMBED_MODEL = "text-embedding-3-small"
GEN_MODEL   = "gpt-4o-mini"

# 유사도 설정
SIM_THRESHOLD = 0.82
TOP_K = 3
