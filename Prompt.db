# views/4_my_requests.py
import streamlit as st
from core import db


def _fmt_ts(ts: int) -> str:
    try:
        import datetime
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "-"
    except Exception:
        return str(ts) if ts else "-"


def _norm_status(s: str) -> str:
    return (s or "").strip().lower()


def _status_badge(s: str) -> str:
    s = _norm_status(s)
    if s == "pending":
        return "🕒 대기중"
    if s == "done":
        return "✅ 완료"
    if s == "all":
        return "📦 전체"
    return s or "-"


def render():
    st.header("📬 내가 전문가에게 개선을 요청한 프롬프트")

    if st.session_state.get("user_id") is None:
        st.info("로그인 후 이용할 수 있어.")
        return

    user_id = st.session_state["user_id"]

    tab_all, tab_pending, tab_done = st.tabs(["전체", "대기중", "완료"])

    def show(status: str):
        items = db.list_my_expert_requests(user_id=user_id, status=status)

        if not items:
            st.info("표시할 요청이 없어.")
            return

        for r in items:
            req_id = r.get("id", "-")
            raw_status = r.get("status", "-")
            routed_expert = r.get("routed_expert") or "-"
            answered_expert = r.get("answered_expert") or "-"
            created_at = r.get("created_at")
            updated_at = r.get("updated_at")

            original_prompt = (
                r.get("original_prompt")
                or r.get("original")
                or r.get("prompt")
                or ""
            )

            # ✅ [수정] 탭(status)까지 포함해서 키 충돌 방지
            del_key = f"del_confirm_{status}_{req_id}"
            st.session_state.setdefault(del_key, False)

            with st.container(border=True):

                top_l, top_r = st.columns([8, 2], vertical_alignment="center")
                with top_l:
                    st.subheader(f"요청 #{req_id} · {_status_badge(raw_status)}")
                with top_r:
                    # ✅ [수정] key에 status 포함
                    if st.button("🗑️ 삭제", key=f"del_btn_{status}_{req_id}", use_container_width=True):
                        st.session_state[del_key] = True

                st.caption(
                    f"요청일: {_fmt_ts(created_at)} · "
                    f"선택 전문가: {routed_expert} · "
                    f"답변 전문가: {answered_expert} · "
                    f"답변일: {_fmt_ts(updated_at)}"
                )

                # ✅ [수정] 삭제 확인 버튼 key도 status 포함
                if st.session_state.get(del_key, False):
                    st.warning("진짜 삭제할 거야? 삭제하면 복구 안 돼.")
                    c1, c2, _ = st.columns([2.2, 2.2, 5.6])
                    with c1:
                        if st.button("삭제 확정", type="primary", key=f"del_ok_{status}_{req_id}", use_container_width=True):
                            ok = db.delete_my_expert_request(user_id=user_id, req_id=int(req_id))
                            if ok:
                                st.success("삭제 완료!")
                            else:
                                st.error("삭제 실패(권한 없거나 이미 삭제됨).")
                            st.session_state[del_key] = False
                            st.rerun()
                    with c2:
                        if st.button("취소", key=f"del_cancel_{status}_{req_id}", use_container_width=True):
                            st.session_state[del_key] = False
                            st.rerun()

                if r.get("keywords"):
                    st.write(f"**키워드**: {r.get('keywords')}")

                st.markdown("**내가 요청한 프롬프트**")
                st.code(original_prompt, language="text")

                if _norm_status(raw_status) == "done":
                    improved_prompt = r.get("expert_improved") or ""
                    expert_summary = r.get("expert_summary") or ""

                    st.markdown("**개선된 프롬프트(전문가 답변)**")
                    st.code(improved_prompt, language="text")

                    st.markdown("**피드백 요약**")
                    st.write(expert_summary)

                    st.divider()

                    # ✅ 공유 UI (키도 status 포함해서 안전하게)
                    share_key = f"share_open_{status}_{req_id}"
                    st.session_state.setdefault(share_key, False)

                    c1, _ = st.columns([2.2, 7.8])
                    with c1:
                        if st.button("📚 사례 게시판에 공유", key=f"btn_share_{status}_{req_id}", use_container_width=True):
                            st.session_state[share_key] = True

                    if st.session_state.get(share_key, False):
                        st.markdown("#### 공유 설정")

                        default_title = f"프롬프트 개선 사례 #{req_id}"
                        title = st.text_input(
                            "게시물 제목",
                            value=default_title,
                            key=f"share_title_{status}_{req_id}",
                            placeholder="예) 파이썬 입력/출력 예시 개선"
                        )

                        with st.expander("공유될 내용 미리보기", expanded=False):
                            st.markdown("**Before (요청 프롬프트)**")
                            st.code(original_prompt, language="text")
                            st.markdown("**After (개선된 프롬프트)**")
                            st.code(improved_prompt, language="text")
                            st.markdown("**전문가 피드백 요약**")
                            st.write(expert_summary)

                        cc1, cc2, _ = st.columns([2.2, 2.2, 5.6])
                        with cc1:
                            if st.button("✅ 공유 확정", type="primary", key=f"share_confirm_{status}_{req_id}", use_container_width=True):
                                post_id = db.create_case_post(
                                    author_user_id=user_id,
                                    title=(title or default_title).strip(),
                                    before_prompt=original_prompt,
                                    after_prompt=improved_prompt,
                                    expert_feedback=expert_summary,
                                    expert_name=(r.get("answered_expert") or r.get("routed_expert") or "").strip(),  # ✅ 핵심
                                )

                                if post_id == -1:
                                    st.error("공유에 실패했어. 잠시 후 다시 시도해줘.")
                                else:
                                    st.success("사례 게시판에 공유 완료! 🎉")
                                    st.session_state[share_key] = False
                                    st.session_state["route"] = "cases"
                                    st.rerun()

                        with cc2:
                            if st.button("취소", key=f"share_cancel_{status}_{req_id}", use_container_width=True):
                                st.session_state[share_key] = False
                                st.rerun()
                else:
                    st.info("아직 전문가 답변이 등록되지 않았어.")

    with tab_all:
        show("all")
    with tab_pending:
        show("pending")
    with tab_done:
        show("done")
