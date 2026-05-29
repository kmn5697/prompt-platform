# core/db.py
import os
import json
import time
import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from passlib.hash import bcrypt
from core.config import DB_PATH

# DB 폴더 생성
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


# -----------------------------
# Connection helpers
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _dict_factory(cursor, row):
    """sqlite row -> dict"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# -----------------------------
# DB Init / Seed
# -----------------------------
def init_db(experts_seed: Optional[List[Dict[str, str]]] = None):
    """
    - users: role 포함(user/expert)
    - expert_profiles: 전문가 프로필(전문가 이름/field/설명 등)
    - cases: 유사사례 DB (expert_name 포함)
    - expert_requests: 유사사례 없을 때 전문가에게 전달되는 요청 큐
    - usage_logs: 사용 기록

    ✅ Cases 게시판:
    - cases_posts: 개선 사례 게시판 게시물 (+ like/dislike 카운트)
    - cases_comments: 댓글

    ✅ Expert Requests:
    - routed_expert: 선택된 전문가 1명(expert_profiles.expert_name)에게만 전달
    - answered_expert: 답변한 전문가(username/expert_name) 저장
    - updated_at: 전문가 답변 작성 시각 저장(년월일시분 표시용)

    ✅ Expert 추천:
    - list_all_experts(), recommend_experts() 제공
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user','expert')),
        created_at INTEGER NOT NULL
    );

    -- 전문가 프로필: users의 role='expert'인 계정과 1:1
    CREATE TABLE IF NOT EXISTS expert_profiles (
        user_id INTEGER PRIMARY KEY,
        expert_name TEXT UNIQUE NOT NULL,   -- routed_expert 매칭 키 (여기선 username으로 통일 권장)
        field TEXT,
        specialty TEXT,
        description TEXT,
        publications TEXT,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        original_prompt TEXT NOT NULL,
        improved_prompt TEXT NOT NULL,
        summary TEXT NOT NULL,
        expert_name TEXT NOT NULL,
        embedding_json TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    -- 전문가 요청 큐 (유사사례 없을 때 저장)
    CREATE TABLE IF NOT EXISTS expert_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        original_prompt TEXT NOT NULL,
        embedding BLOB,
        routed_expert TEXT NOT NULL,  -- ✅ 선택된 전문가 1명 (expert_profiles.expert_name)
        top_similarity REAL DEFAULT 0.0,
        keywords TEXT,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','done')),
        expert_improved TEXT,
        expert_summary TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    /* =========================================================
       ✅ Cases 게시판용 테이블
       ========================================================= */

    -- 게시물
    CREATE TABLE IF NOT EXISTS cases_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_user_id INTEGER,
        title TEXT NOT NULL,
        before_prompt TEXT NOT NULL,
        after_prompt TEXT NOT NULL,
        expert_feedback TEXT,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(author_user_id) REFERENCES users(id)
    );

    -- 댓글
    CREATE TABLE IF NOT EXISTS cases_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        comment TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(post_id) REFERENCES cases_posts(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # ✅ 기존 DB에 like/dislike 컬럼이 없으면 추가
    try:
        cur.execute("ALTER TABLE cases_posts ADD COLUMN like_count INTEGER NOT NULL DEFAULT 0;")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE cases_posts ADD COLUMN dislike_count INTEGER NOT NULL DEFAULT 0;")
    except sqlite3.OperationalError:
        pass

    # ✅ expert_profiles에 trust_score 컬럼이 없으면 추가
    try:
        cur.execute("ALTER TABLE expert_profiles ADD COLUMN trust_score INTEGER NOT NULL DEFAULT 10;")
    except sqlite3.OperationalError:
        pass

    # ✅ cases_posts에 expert_name 컬럼이 없으면 추가 (이 사례를 개선한 전문가)
    try:
        cur.execute("ALTER TABLE cases_posts ADD COLUMN expert_name TEXT;")
    except sqlite3.OperationalError:
        pass

    # ✅ cases_posts에 penalty_applied 컬럼이 없으면 추가 (싫어요 3개 감점 1회 적용 여부)
    try:
        cur.execute("ALTER TABLE cases_posts ADD COLUMN penalty_applied INTEGER NOT NULL DEFAULT 0;")
    except sqlite3.OperationalError:
        pass


    # ✅ expert_requests에 answered_expert 컬럼이 없으면 추가
    try:
        cur.execute("ALTER TABLE expert_requests ADD COLUMN answered_expert TEXT;")
    except sqlite3.OperationalError:
        pass

    # experts_seed는 지금 구조상 users FK 때문에 바로 insert 못함(너 주석대로 OK)
    if experts_seed:
        pass

    conn.commit()
    conn.close()


# -----------------------------
# Users / Auth
# -----------------------------
def create_user(username: str, password: str, role: str = "user") -> bool:
    """
    role: 'user' or 'expert'
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username, bcrypt.hash(password), role, int(time.time()))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def fetch_user(username: str):
    """
    returns: (id, username, password_hash, role) or None
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, role FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    row = fetch_user(username)
    if not row:
        return None
    user_id, _, pw_hash, role = row
    if bcrypt.verify(password, pw_hash):
        return {"user_id": user_id, "role": role}
    return None


def set_user_role(user_id: int, role: str) -> bool:
    """
    ✅ 승급에 사용: user -> expert
    """
    if role not in ("user", "expert"):
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def get_username_by_user_id(user_id: int) -> Optional[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


# -----------------------------
# Expert profile (for expert accounts)
# -----------------------------
def upsert_expert_profile(
    username: str,
    expert_name: str,
    field: str = "",
    specialty: str = "",
    description: str = "",
    publications: str = ""
) -> bool:
    """
    전문가 계정(username)이 존재해야 하고, role='expert'여야 함.
    expert_name은 routed_expert 매칭 키로 쓰임(여기서는 username으로 통일 권장)
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, role FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    user_id, role = row
    if role != "expert":
        conn.close()
        return False

    now = int(time.time())
    cur.execute("""
        INSERT INTO expert_profiles (user_id, expert_name, field, specialty, description, publications, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            expert_name=excluded.expert_name,
            field=excluded.field,
            specialty=excluded.specialty,
            description=excluded.description,
            publications=excluded.publications
    """, (user_id, expert_name, field, specialty, description, publications, now))

    conn.commit()
    conn.close()
    return True


def list_all_experts() -> List[Dict[str, Any]]:
    """
    ✅ 회원가입 완료(전문가 승급 + 프로필 등록)된 전문가 전체 리스트
    """
    conn = get_conn()
    conn.row_factory = _dict_factory
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id AS user_id, u.username, u.role,
               ep.expert_name, ep.field, ep.specialty, ep.description
        FROM users u
        JOIN expert_profiles ep ON ep.user_id = u.id
        WHERE u.role='expert'
        ORDER BY ep.expert_name ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def recommend_experts(
    keywords: List[str],
    exclude_username: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    ✅ 키워드 기반 전문가 추천 (최대 top_k)
    - specialty/field/description에 키워드가 포함되면 점수 가산
    - 전문가가 요청하는 경우 자기 자신(exclude_username)은 추천에서 제외 가능
    """
    experts = list_all_experts()

    kws = [k.strip() for k in (keywords or []) if k and k.strip()]
    if not kws:
        out = []
        for e in experts:
            if exclude_username and e.get("username") == exclude_username:
                continue
            e2 = dict(e)
            e2["score"] = 0
            out.append(e2)
        return out[:top_k]

    scored: List[Dict[str, Any]] = []
    for e in experts:
        if exclude_username and e.get("username") == exclude_username:
            continue

        field = (e.get("field") or "").lower()
        specialty = (e.get("specialty") or "").lower()
        desc = (e.get("description") or "").lower()
        text = f"{field} {specialty} {desc}"

        score = 0
        for kw in kws:
            k = kw.lower()
            if k in specialty:
                score += 3
            elif k in field:
                score += 2
            elif k in desc:
                score += 1

        e2 = dict(e)
        e2["score"] = score
        scored.append(e2)

    scored.sort(key=lambda x: (x["score"], (x.get("expert_name") or "")), reverse=True)
    return scored[:top_k]


def get_expert_profile_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT expert_name, field, specialty, description, publications
        FROM expert_profiles
        WHERE user_id=?
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "expert_name": row[0],
        "field": row[1],
        "specialty": row[2],
        "description": row[3],
        "publications": row[4],
    }


def get_expert_profile_by_name(expert_name: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, expert_name, field, specialty, description, publications
        FROM expert_profiles
        WHERE expert_name=?
    """, (expert_name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "user_id": row[0],
        "expert_name": row[1],
        "field": row[2],
        "specialty": row[3],
        "description": row[4],
        "publications": row[5],
    }


# -----------------------------
# ✅ Expert upgrade (핵심 추가)
# -----------------------------
def promote_user_to_expert(
    user_id: int,
    primary_domain: str,
    secondary_domain: str = "",
    field: str = "python",
    publications: str = "prompt_improvement",
    description: str = ""
) -> bool:
    """
    ✅ 전문가 테스트 합격 시 호출하면 끝.
    - users.role을 expert로 변경
    - expert_profiles upsert 생성
    - expert_name은 username(아이디)로 통일
    - specialty에는 '주 분야|부 분야' 형태로 저장
    """
    username = get_username_by_user_id(user_id)
    if not username:
        return False

    ok = set_user_role(user_id, "expert")
    if not ok:
        return False

    expert_name = username

    sec = secondary_domain.strip() if secondary_domain else ""
    specialty = f"주 분야={primary_domain}"
    if sec:
        specialty += f" | 부 분야={sec}"
    else:
        specialty += " | 부 분야=없음"

    return upsert_expert_profile(
        username=username,
        expert_name=expert_name,
        field=field,
        specialty=specialty,
        description=description,
        publications=publications
    )


# -----------------------------
# Cases (유사사례 DB)
# -----------------------------
def list_cases_with_embeddings() -> List[Tuple]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, original_prompt, improved_prompt, summary, expert_name, embedding_json, created_at
        FROM cases
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def save_case(user_id: int, original: str, improved: str, summary: str, expert_name: str, embedding):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cases (user_id, original_prompt, improved_prompt, summary, expert_name, embedding_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        original,
        improved,
        summary,
        expert_name,
        json.dumps(embedding),
        int(time.time())
    ))
    conn.commit()
    conn.close()


# -----------------------------
# Expert Requests (전문가 처리 큐)
# -----------------------------
def save_expert_request(
    user_id: int,
    original: str,
    embedding,
    routed_expert: str = "ALL",
    top_similarity: float = 0.0,
    keywords: str = ""
):
    import numpy as np

    conn = get_conn()
    cur = conn.cursor()

    if embedding is None:
        emb_bytes = None
    elif isinstance(embedding, bytes):
        emb_bytes = embedding
    elif isinstance(embedding, list):
        emb_bytes = np.array(embedding, dtype="float32").tobytes()
    else:
        emb_bytes = embedding.tobytes()

    now = int(time.time())

    cur.execute("""
        INSERT INTO expert_requests
        (user_id, original_prompt, embedding, routed_expert, top_similarity, keywords, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        user_id,
        original,
        emb_bytes,
        routed_expert,
        float(top_similarity),
        keywords,
        now
    ))

    conn.commit()
    conn.close()


def list_expert_requests_for(expert_name: str, status: str = "pending") -> List[Dict[str, Any]]:
    """
    ✅ 특정 전문가(=expert_name)에게 라우팅된 요청만 조회

    ✅ [수정]
    - routed_expert='ALL' 로 들어간 요청도 전문가 요청함에서 보이게 포함
      (routed_expert가 ALL이면 '전체 공개 큐'처럼 동작)
    """
    conn = get_conn()
    cur = conn.cursor()

    # ✅ [수정] routed_expert='ALL' 포함
    cur.execute("""
        SELECT id, user_id, original_prompt, keywords, top_similarity, status,
               expert_improved, expert_summary, answered_expert,
               created_at, updated_at
        FROM expert_requests
        WHERE status=?
          AND (routed_expert=? OR routed_expert='ALL')
        ORDER BY created_at DESC
    """, (status, expert_name))

    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "user_id": r[1],
            "original": r[2],
            "keywords": r[3] or "",
            "top_similarity": r[4],
            "status": r[5],
            "expert_improved": r[6],
            "expert_summary": r[7],
            "answered_expert": r[8],
            "created_at": r[9],
            "updated_at": r[10],
        })
    return out


def get_expert_request(req_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, original_prompt, routed_expert, keywords, status,
               expert_improved, expert_summary, answered_expert, created_at, updated_at
        FROM expert_requests
        WHERE id=?
    """, (req_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0],
        "user_id": r[1],
        "original": r[2],
        "routed_expert": r[3],
        "keywords": r[4] or "",
        "status": r[5],
        "expert_improved": r[6],
        "expert_summary": r[7],
        "answered_expert": r[8],
        "created_at": r[9],
        "updated_at": r[10],
    }


def mark_expert_request_done(req_id: int, expert_improved: str, expert_summary: str, answered_expert: str):
    """
    ✅ 전문가 답변 제출
    - answered_expert 저장
    - updated_at에 "답변 시각" 저장
    - 이미 done이면 덮어쓰지 않게 status='pending' 조건
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE expert_requests
        SET status='done',
            expert_improved=?,
            expert_summary=?,
            answered_expert=?,
            updated_at=?
        WHERE id=? AND status='pending'
    """, (
        expert_improved,
        expert_summary,
        answered_expert,
        int(time.time()),
        req_id
    ))
    conn.commit()
    conn.close()


# -----------------------------
# Usage logs
# -----------------------------
def add_usage_log(user_id: int, content: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usage_logs (user_id, content, created_at) VALUES (?, ?, ?)",
        (user_id, content, int(time.time()))
    )
    conn.commit()
    conn.close()


def list_usage_logs(user_id: int, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, content, created_at FROM usage_logs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# =========================================================
# ✅ Cases 게시판 기능 - 게시물/좋아요/싫어요(누적)/댓글
# =========================================================

def create_case_post(
    author_user_id: int,
    title: str,
    before_prompt: str,
    after_prompt: str,
    expert_feedback: str = "",
    expert_name: str = ""   # ✅ [추가]
) -> int:
    """
    게시물 생성. 성공 시 post_id 반환, 실패 시 -1
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        now = int(time.time())
        cur.execute("""
            INSERT INTO cases_posts
            (author_user_id, title, before_prompt, after_prompt, expert_feedback, expert_name,
             created_at, like_count, dislike_count, penalty_applied)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
        """, (author_user_id, title, before_prompt, after_prompt, expert_feedback, (expert_name or "").strip(), now))
        conn.commit()
        return int(cur.lastrowid)
    except Exception:
        return -1
    finally:
        conn.close()


def list_case_posts(limit: int = 100) -> List[Dict[str, Any]]:
    """
    게시물 목록(최신순)
    """
    conn = get_conn()
    conn.row_factory = _dict_factory
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.author_user_id, u.username AS author_username,
               p.title, p.before_prompt, p.after_prompt, p.expert_feedback,
               p.like_count, p.dislike_count,
               p.created_at
        FROM cases_posts p
        LEFT JOIN users u ON u.id = p.author_user_id
        ORDER BY p.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_case_post(post_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    conn.row_factory = _dict_factory
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.author_user_id, u.username AS author_username,
               p.title, p.before_prompt, p.after_prompt, p.expert_feedback,
               p.like_count, p.dislike_count,
               p.created_at
        FROM cases_posts p
        LEFT JOIN users u ON u.id = p.author_user_id
        WHERE p.id=?
    """, (post_id,))
    row = cur.fetchone()
    conn.close()
    return row


def delete_case_post(post_id: int, requester_user_id: int) -> bool:
    """
    작성자만 삭제 가능하도록 가드
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT author_user_id FROM cases_posts WHERE id=?", (post_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    author_id = row[0]
    if author_id != requester_user_id:
        conn.close()
        return False

    cur.execute("DELETE FROM cases_posts WHERE id=?", (post_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def increment_reaction(post_id: int, reaction: str) -> bool:
    """
    ✅ 누를 때마다 무조건 +1 누적
    reaction: 'like' or 'dislike'

    ✅ [추가 룰]
    - dislike_count가 3 이상이 되고 penalty_applied=0이면,
      해당 게시글의 expert_name 전문가 trust_score 1 감점 + penalty_applied=1 처리
    - trust_score가 0이면 전문가 → 일반 사용자로 강등
    """
    if reaction not in ("like", "dislike"):
        return False

    conn = get_conn()
    cur = conn.cursor()

    try:
        if reaction == "like":
            cur.execute("""
                UPDATE cases_posts
                SET like_count = like_count + 1
                WHERE id=?
            """, (post_id,))
            conn.commit()
            return cur.rowcount > 0

        # dislike
        cur.execute("""
            UPDATE cases_posts
            SET dislike_count = dislike_count + 1
            WHERE id=?
        """, (post_id,))

        # ✅ dislike 후 현재 상태 조회
        cur.execute("""
            SELECT dislike_count, penalty_applied, expert_name
            FROM cases_posts
            WHERE id=?
        """, (post_id,))
        row = cur.fetchone()
        if not row:
            conn.commit()
            return False

        dislike_count = int(row[0] or 0)
        penalty_applied = int(row[1] or 0)
        expert_name = (row[2] or "").strip()

        # ✅ 감점 조건: 3개 이상 + 아직 감점 적용 안 됨 + 전문가 정보 있음
        if dislike_count >= 3 and penalty_applied == 0 and expert_name:
            # penalty_applied 먼저 찍어두고
            cur.execute("""
                UPDATE cases_posts
                SET penalty_applied = 1
                WHERE id=? AND penalty_applied=0
            """, (post_id,))

            # 커밋 전에 같은 커넥션으로 점수 감점 수행(원자성 유지)
            # -> 아래 함수는 별도 커넥션 쓰니까, 여기서는 직접 처리하는 게 더 깔끔하지만
            #    최소 수정으로 가려면 커밋 후 함수 호출해도 OK.
            conn.commit()

            # 감점 + 강등
            decrement_trust_score_and_maybe_demote(expert_name, dec=1)
            return True

        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()



def add_comment(post_id: int, user_id: int, comment: str) -> int:
    """
    댓글 추가. 성공 시 comment_id 반환, 실패 시 -1
    """
    comment = (comment or "").strip()
    if not comment:
        return -1

    conn = get_conn()
    cur = conn.cursor()
    try:
        now = int(time.time())
        cur.execute("""
            INSERT INTO cases_comments (post_id, user_id, comment, created_at)
            VALUES (?, ?, ?, ?)
        """, (post_id, user_id, comment, now))
        conn.commit()
        return int(cur.lastrowid)
    except Exception:
        return -1
    finally:
        conn.close()


def list_comments(post_id: int, limit: int = 200) -> List[Dict[str, Any]]:
    """
    댓글 목록(오래된 순)
    """
    conn = get_conn()
    conn.row_factory = _dict_factory
    cur = conn.cursor()

    cur.execute("""
        SELECT c.id, c.post_id, c.user_id, u.username AS username, c.comment, c.created_at
        FROM cases_comments c
        LEFT JOIN users u ON u.id = c.user_id
        WHERE c.post_id=?
        ORDER BY c.created_at ASC
        LIMIT ?
    """, (post_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_comment(comment_id: int, requester_user_id: int) -> bool:
    """
    댓글 삭제: 작성자만
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM cases_comments WHERE id=?", (comment_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    author_id = row[0]
    if author_id != requester_user_id:
        conn.close()
        return False

    cur.execute("DELETE FROM cases_comments WHERE id=?", (comment_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def list_my_expert_requests(user_id: int, status: str = "all") -> List[Dict[str, Any]]:
    conn = get_conn()
    conn.row_factory = _dict_factory
    cur = conn.cursor()

    if status == "all":
        cur.execute("""
            SELECT id, user_id, original_prompt, keywords, status,
                   routed_expert, expert_improved, expert_summary,
                   answered_expert, created_at, updated_at
            FROM expert_requests
            WHERE user_id=?
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cur.execute("""
            SELECT id, user_id, original_prompt, keywords, status,
                   routed_expert, expert_improved, expert_summary,
                   answered_expert, created_at, updated_at
            FROM expert_requests
            WHERE user_id=? AND status=?
            ORDER BY created_at DESC
        """, (user_id, status))

    rows = cur.fetchall()
    conn.close()
    return rows

def list_expert_requests_all(status: str = "pending") -> List[Dict[str, Any]]:
    """
    ✅ (관리/디버깅용) expert_requests 전체 조회
    status: 'pending' | 'done' | 'all'
    """
    conn = get_conn()
    conn.row_factory = _dict_factory
    cur = conn.cursor()

    if status == "all":
        cur.execute("""
            SELECT id, user_id, original_prompt, keywords, top_similarity, status,
                   routed_expert, expert_improved, expert_summary, answered_expert,
                   created_at, updated_at
            FROM expert_requests
            ORDER BY created_at DESC
        """)
    else:
        cur.execute("""
            SELECT id, user_id, original_prompt, keywords, top_similarity, status,
                   routed_expert, expert_improved, expert_summary, answered_expert,
                   created_at, updated_at
            FROM expert_requests
            WHERE status=?
            ORDER BY created_at DESC
        """, (status,))

    rows = cur.fetchall()
    conn.close()
    return rows

def delete_my_expert_request(user_id: int, req_id: int) -> bool:
    """
    ✅ 사용자가 자기 요청(req_id)만 삭제 가능
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM expert_requests WHERE id=? AND user_id=?",
        (req_id, user_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok

def get_expert_user_id_by_expert_name(expert_name: str) -> Optional[int]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM expert_profiles WHERE expert_name=?", (expert_name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def decrement_trust_score_and_maybe_demote(expert_name: str, dec: int = 1) -> Optional[int]:
    """
    ✅ expert_name의 trust_score를 dec만큼 감점.
    ✅ 0이 되면 users.role을 'user'로 강등.
    return: 감점 후 trust_score (실패 시 None)
    """
    user_id = get_expert_user_id_by_expert_name(expert_name)
    if not user_id:
        return None

    conn = get_conn()
    cur = conn.cursor()

    # 현재 점수
    cur.execute("SELECT trust_score FROM expert_profiles WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    cur_score = int(row[0] or 0)
    new_score = max(0, cur_score - int(dec))

    cur.execute(
        "UPDATE expert_profiles SET trust_score=? WHERE user_id=?",
        (new_score, user_id)
    )

    # 0점이면 강등
    if new_score <= 0:
        cur.execute("UPDATE users SET role='user' WHERE id=? AND role='expert'", (user_id,))

    conn.commit()
    conn.close()
    return new_score

def get_trust_score_by_user_id(user_id: int) -> Optional[int]:
    """
    ✅ 전문가 신뢰도 점수 조회 (expert_profiles.trust_score)
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT trust_score FROM expert_profiles WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return int(row[0]) if row[0] is not None else None
    finally:
        conn.close()
