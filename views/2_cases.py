# views/2_cases.py
import streamlit as st
from core import db


def _fmt_ts(ts: int) -> str:
    try:
        import datetime
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def render():
    st.header("📌 프롬프트 개선 사례 게시판")

    logged_in = st.session_state.get("user_id") is not None
    user_id = st.session_state.get("user_id")

    # -------------------------
    # (1) 업로드 폼
    # -------------------------
    with st.expander("✍️ 개선 사례 업로드", expanded=False):
        if not logged_in:
            st.info("로그인 후 업로드할 수 있어.")
        else:
            title = st.text_input("제목", key="case_title")
            before_p = st.text_area("Before (개선 전 프롬프트)", height=130, key="case_before")
            after_p = st.text_area("After (개선 후 프롬프트)", height=130, key="case_after")
            feedback = st.text_area("전문가 피드백 요약(선택)", height=120, key="case_feedback")

            if st.button("게시물 업로드", type="primary", key="case_submit"):
                if not title.strip() or not before_p.strip() or not after_p.strip():
                    st.warning("제목/Before/After는 필수야.")
                else:
                    post_id = db.create_case_post(
                        author_user_id=user_id,
                        title=title.strip(),
                        before_prompt=before_p.strip(),
                        after_prompt=after_p.strip(),
                        expert_feedback=feedback.strip()
                    )
                    if post_id == -1:
                        st.error("업로드에 실패했어. DB 상태를 확인해줘.")
                    else:
                        st.success("업로드 완료!")
                        st.rerun()

    st.divider()

    # -------------------------
    # (2) 게시물 목록
    # -------------------------
    posts = db.list_case_posts(limit=100)

    if not posts:
        st.info("아직 게시물이 없어. 첫 게시물을 올려봐 🙂")
        return

    for post in posts:
        post_id = post["id"]

        # ✅ 카운트는 DB 함수가 아니라 게시물 컬럼에서 바로 읽음
        like_cnt = int(post.get("like_count") or 0)
        dislike_cnt = int(post.get("dislike_count") or 0)

        author_id = post.get("author_user_id")
        is_mine = logged_in and (author_id == user_id)

        with st.container(border=True):
            # ✅ 제목 + (내 글이면) 삭제 버튼을 같은 줄에
            title_col, action_col = st.columns([8, 2], vertical_alignment="center")

            with title_col:
                st.subheader(post["title"])

            with action_col:
                if is_mine:
                    if st.button("🗑️ 삭제", key=f"del_{post_id}", use_container_width=True):
                        st.session_state[f"confirm_del_{post_id}"] = True
                        st.rerun()

            author = post.get("author_username") or "unknown"
            st.caption(f"작성자: {author} · 작성일: {_fmt_ts(post['created_at'])}")

            # ✅ 삭제 확인 UI
            if is_mine and st.session_state.get(f"confirm_del_{post_id}", False):
                st.warning("진짜 삭제할거야? 삭제하면 복구 안 돼.")
                c_yes, c_no = st.columns([1, 1])

                with c_yes:
                    if st.button("삭제", key=f"del_yes_{post_id}", type="primary", use_container_width=True):
                        ok = db.delete_case_post(post_id, user_id)
                        st.session_state.pop(f"confirm_del_{post_id}", None)
                        if ok:
                            st.success("삭제 완료!")
                        else:
                            st.error("삭제 실패(권한/DB 확인)")
                        st.rerun()

                with c_no:
                    if st.button("취소", key=f"del_no_{post_id}", use_container_width=True):
                        st.session_state.pop(f"confirm_del_{post_id}", None)
                        st.rerun()

            st.markdown("**Before**")
            st.code(post["before_prompt"], language="text")

            st.markdown("**After**")
            st.code(post["after_prompt"], language="text")

            if post.get("expert_feedback"):
                st.markdown("**전문가 피드백 요약**")
                st.write(post["expert_feedback"])

            # 버튼 row (✅ 문구 포함)
            c1, c2, c3, _ = st.columns([2.0, 2.0, 1.2, 6])

            with c1:
                if st.button(f"👍 도움이 돼요 {like_cnt}", key=f"like_{post_id}"):
                    db.increment_reaction(post_id, "like")
                    st.rerun()

            with c2:
                if st.button(f"👎 도움 안돼요 {dislike_cnt}", key=f"dislike_{post_id}"):
                    db.increment_reaction(post_id, "dislike")
                    st.rerun()

            with c3:
                if st.button("💬 댓글", key=f"toggle_comments_{post_id}"):
                    k = f"open_comments_{post_id}"
                    st.session_state[k] = not st.session_state.get(k, False)
                    st.rerun()

            # 댓글 영역
            if st.session_state.get(f"open_comments_{post_id}", False):
                st.markdown("---")

                if logged_in:
                    comment_text = st.text_input("댓글 입력", key=f"comment_input_{post_id}")
                    if st.button("댓글 등록", key=f"comment_submit_{post_id}"):
                        if comment_text.strip():
                            cid = db.add_comment(post_id, user_id, comment_text.strip())
                            if cid == -1:
                                st.error("댓글 등록 실패")
                            st.rerun()
                        else:
                            st.warning("댓글을 입력해줘.")
                else:
                    st.info("댓글 작성은 로그인 후 가능해.")

                comments = db.list_comments(post_id)

                if comments:
                    for cm in comments:
                        uname = cm.get("username") or "unknown"
                        st.write(f"- **{uname}**: {cm['comment']}  ·  {_fmt_ts(cm['created_at'])}")
                else:
                    st.caption("아직 댓글이 없어.")
