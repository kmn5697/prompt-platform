# views/9_expert_requests.py
import streamlit as st
from core import db


def _fmt_ts(ts: int) -> str:
    """int(time.time()) -> 'YYYY-MM-DD HH:MM'"""
    try:
        import datetime
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "-"
    except Exception:
        return str(ts) if ts else "-"


def _require_expert_role() -> bool:
    logged_in = st.session_state.get("user_id") is not None
    role = st.session_state.get("role")
    if not logged_in:
        st.info("로그인 후 이용할 수 있어.")
        return False
    if role != "expert":
        st.warning("이 페이지는 전문가만 접근할 수 있어.")
        return False
    return True


def render():
    st.header("🧑‍🏫 나에게 분류된 프롬프트 개선 요청")

    if not _require_expert_role():
        return

    # ✅ 전문가 표시명: expert_name(프로필) 우선, 없으면 username
    expert_name = (st.session_state.get("expert_name") or st.session_state.get("username") or "expert")

    # ✅ [수정] 강등 규칙 안내 + 내 신뢰도 점수: 페이지 접속 시 바로 보이게
    st.markdown("### 📌 전문가 강등(신뢰도) 규칙")

    st.info(
        """
**신뢰도(Trust Score) 규칙**
- 전문가 신뢰도는 **기본 10점**에서 시작해.
- 전문가가 개선한 사례가 ‘사례 게시판’에 올라간 뒤,
  해당 글에서 **‘도움 안돼요’가 3개 이상**이면 **신뢰도 1점 감점**돼.
- **게시글 1개당 감점은 1회만 적용**돼. (3개 이상을 더 받아도 추가 감점 없음)
- 신뢰도가 **0점이 되면 전문가 → 일반 사용자로 자동 강등**돼.
        """.strip()
    )

    user_id = st.session_state.get("user_id")
    trust = None
    if user_id is not None:
        try:
            trust = db.get_trust_score_by_user_id(int(user_id))
        except Exception:
            trust = None

    if trust is None:
        st.caption("내 신뢰도: - / 10")
    else:
        if trust <= 2:
            st.error(f"내 신뢰도: {trust} / 10  ⚠️ (강등 위험)")
        elif trust <= 5:
            st.warning(f"내 신뢰도: {trust} / 10  (주의)")
        else:
            st.success(f"내 신뢰도: {trust} / 10")

    st.divider()

    tab_pending, tab_done = st.tabs(["🕒 대기중 요청", "✅ 완료된 요청"])

    # =========================
    # 1) Pending
    # =========================
    with tab_pending:
        st.subheader("대기중 요청")

        # ✅ "전체 요청"이 아니라 "나에게 라우팅된 요청"만 조회
        requests = db.list_expert_requests_for(expert_name=expert_name, status="pending")

        if not requests:
            st.info("현재 대기중인 요청이 없어.")
            return

        # 리스트에서 선택 -> 상세 보기
        options = []
        idx_to_req = {}
        for i, r in enumerate(requests):
            label = (
                f"#{r['id']} · 요청일 {_fmt_ts(r.get('created_at'))} · "
                f"키워드: {r.get('keywords') or '-'} · "
                f"유사도: {float(r.get('top_similarity') or 0.0):.3f}"
            )
            options.append(label)
            idx_to_req[label] = r

        sel = st.selectbox("요청 선택", options, key="expert_req_select_pending")
        req = idx_to_req.get(sel)
        if not req:
            return

        st.markdown("### 📩 요청 내용")
        st.caption(
            f"요청ID: {req['id']} · 사용자ID: {req['user_id']} · "
            f"라우팅: {req.get('routed_expert') or '-'} · "
            f"요청일: {_fmt_ts(req.get('created_at'))}"
        )
        if req.get("keywords"):
            st.write(f"**키워드**: {req['keywords']}")
        st.code(req.get("original") or "", language="text")

        st.markdown("---")
        st.markdown("### ✍️ 전문가 답변 작성")

        improved = st.text_area(
            "개선된 프롬프트(전문가 작성)",
            height=180,
            key=f"expert_improved_{req['id']}",
            placeholder="사용자의 목적/조건/출력 형식을 반영한 개선 프롬프트를 작성해줘."
        )
        summary = st.text_area(
            "피드백 요약(전문가 코멘트)",
            height=140,
            key=f"expert_summary_{req['id']}",
            placeholder="왜 이렇게 개선했는지, 핵심 수정 포인트를 짧게 정리해줘."
        )

        c1, c2, _ = st.columns([1.4, 1.2, 6])
        with c1:
            if st.button("✅ 개선 완료", type="primary", key=f"submit_done_{req['id']}"):
                if not improved.strip() or not summary.strip():
                    st.warning("개선된 프롬프트와 피드백 요약은 둘 다 작성해줘.")
                else:
                    db.mark_expert_request_done(
                        req_id=req["id"],
                        expert_improved=improved.strip(),
                        expert_summary=summary.strip(),
                        answered_expert=expert_name,
                    )
                    st.success("제출 완료! (done 처리됨)")
                    st.rerun()

        with c2:
            st.caption("※ 먼저 제출한 전문가 1명만 완료 처리돼(중복 방지).")

    # =========================
    # 2) Done
    # =========================
    with tab_done:
        st.subheader("완료된 요청")

        done_reqs = db.list_expert_requests_for(expert_name=expert_name, status="done")

        if not done_reqs:
            st.info("완료된 요청이 아직 없어.")
            return

        only_mine = st.checkbox("내가 답변한 요청만 보기", value=False, key="done_only_mine")
        if only_mine:
            done_reqs = [r for r in done_reqs if (r.get("answered_expert") == expert_name)]

        if not done_reqs:
            st.info("조건에 맞는 완료 요청이 없어.")
            return

        for r in done_reqs:
            with st.container(border=True):
                st.subheader(f"#{r['id']} · 완료")
                st.caption(
                    f"요청일: {_fmt_ts(r.get('created_at'))} · "
                    f"답변일: {_fmt_ts(r.get('updated_at'))} · "
                    f"라우팅: {r.get('routed_expert') or '-'} · "
                    f"답변 전문가: {r.get('answered_expert') or '-'}"
                )
                if r.get("keywords"):
                    st.write(f"**키워드**: {r['keywords']}")

                st.markdown("**요청 프롬프트(원문)**")
                st.code(r.get("original") or "", language="text")

                st.markdown("**개선된 프롬프트(전문가 작성)**")
                st.code(r.get("expert_improved") or "", language="text")

                st.markdown("**피드백 요약**")
                st.write(r.get("expert_summary") or "")
