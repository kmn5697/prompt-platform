# views/1_prompt_improve.py
def render():
    import streamlit as st
    from core.config import SIM_THRESHOLD, TOP_K
    from services.embeddings import find_similar_cases
    from services.prompt_keywords import recommend_keywords
    from core import db  # save_expert_request / recommend_experts 등

    st.title("🛠️ 전문가에게 프롬프트 개선 요청하기")

    # -----------------------------
    # 로그인 체크
    # -----------------------------
    if st.session_state.get("user_id") is None:
        st.warning("로그인 후 사용할 수 있어요. 상단 Login을 눌러주세요.")
        st.stop()

    user_id = st.session_state.get("user_id")
    username = st.session_state.get("username")
    role = st.session_state.get("role")  # 'user' or 'expert'

    # -----------------------------
    # 입력
    # -----------------------------
    user_prompt = st.text_area("개선하고 싶은 프롬프트를 입력하세요.", height=150)

    # -----------------------------
    # 세션 초기화 (키워드/전문가 추천 관련)
    # -----------------------------
    if "recommended_keywords" not in st.session_state:
        st.session_state["recommended_keywords"] = []
    if "kw_selected" not in st.session_state:
        st.session_state["kw_selected"] = []
    if "other_kw_text" not in st.session_state:
        st.session_state["other_kw_text"] = ""
    if "cb_kw_other" not in st.session_state:
        st.session_state["cb_kw_other"] = False
    if "show_keyword_select" not in st.session_state:
        st.session_state["show_keyword_select"] = False

    # ✅ 전문가 추천 결과/선택
    if "recommended_experts" not in st.session_state:
        st.session_state["recommended_experts"] = []
    if "chosen_expert" not in st.session_state:
        st.session_state["chosen_expert"] = None  # expert_profiles.expert_name 저장
    if "chosen_expert_radio" not in st.session_state:
        st.session_state["chosen_expert_radio"] = None  # 라디오 선택 라벨

    CANDIDATE_KEYWORDS = [
        "목적 구체화",
        "출력 형식 명확화",
        "입력 조건 보완",
        "역할(Role) 설정",
        "제약 조건 추가",
        "단계별 요청",
        "예시 제공",
        "대상 수준 명시",
        "톤/스타일 지정",
        "언어/도구 명시",
    ]

    def reset_keyword_ui_state():
        st.session_state["recommended_keywords"] = []
        st.session_state["kw_selected"] = []
        st.session_state["cb_kw_other"] = False
        st.session_state["other_kw_text"] = ""
        st.session_state["show_keyword_select"] = False
        st.session_state["improve_keywords"] = []

        for k in CANDIDATE_KEYWORDS:
            key = f"cb_kw_{k}"
            if key in st.session_state:
                del st.session_state[key]
        if "other_kw_input" in st.session_state:
            del st.session_state["other_kw_input"]

        st.session_state["recommended_experts"] = []
        st.session_state["chosen_expert"] = None
        st.session_state["chosen_expert_radio"] = None

        if "expert_radio" in st.session_state:
            del st.session_state["expert_radio"]

    if not user_prompt.strip():
        reset_keyword_ui_state()

    # -----------------------------
    # 키워드 추천 + 선택
    # -----------------------------
    st.markdown("## 🔎 개선 키워드 추천")

    col1, col2 = st.columns([1, 3])
    with col1:
        rec_btn = st.button("개선 키워드 추천받기", disabled=not user_prompt.strip())
    with col2:
        st.caption("프롬프트를 입력하고 버튼을 누르면 아래에 ‘추천 키워드 선택’이 나타나.")

    if rec_btn:
        with st.spinner("개선 포인트를 분석 중입니다..."):
            rec = recommend_keywords(user_prompt)

        if not isinstance(rec, list):
            rec = []

        rec = [k for k in rec if k in CANDIDATE_KEYWORDS]

        st.session_state["recommended_keywords"] = rec
        st.session_state["kw_selected"] = rec
        st.session_state["cb_kw_other"] = False
        st.session_state["other_kw_text"] = ""
        st.session_state["show_keyword_select"] = True

        st.session_state["recommended_experts"] = []
        st.session_state["chosen_expert"] = None
        st.session_state["chosen_expert_radio"] = None
        if "expert_radio" in st.session_state:
            del st.session_state["expert_radio"]

    if st.session_state["show_keyword_select"]:
        st.markdown("### 🧩 추천 키워드 선택")

        options = st.session_state.get("recommended_keywords", [])
        if not options:
            options = CANDIDATE_KEYWORDS

        selected_set = set(st.session_state.get("kw_selected", []))

        cols = st.columns(3)
        new_selected = []
        for i, k in enumerate(options):
            checked = cols[i % 3].checkbox(
                k,
                value=(k in selected_set),
                key=f"cb_kw_{k}"
            )
            if checked:
                new_selected.append(k)

        other_checked = st.checkbox(
            "기타(직접 입력)",
            value=st.session_state["cb_kw_other"],
            key="cb_kw_other"
        )

        if other_checked:
            st.session_state["other_kw_text"] = st.text_input(
                "기타 키워드 입력",
                value=st.session_state["other_kw_text"],
                placeholder="예: 출력 길이 제한, 예시 2개 추가, 코드 주석 포함 등",
                key="other_kw_input"
            )
        else:
            st.session_state["other_kw_text"] = ""

        final_keywords = new_selected.copy()
        if other_checked and st.session_state["other_kw_text"].strip():
            final_keywords.append(st.session_state["other_kw_text"].strip())

        st.session_state["kw_selected"] = new_selected
        st.session_state["improve_keywords"] = final_keywords

        if final_keywords:
            st.success("선택된 개선 키워드: " + ", ".join(final_keywords))
        else:
            st.info("키워드를 체크하거나, '기타(직접 입력)'을 체크해서 입력해줘.")
    else:
        st.caption("‘개선 키워드 추천받기’를 누르면 추천 키워드 선택이 나타나.")

    st.divider()

    # -----------------------------
    # ✅ 전문가 추천 (최대 5명) + 1명 선택 (st.radio)
    # -----------------------------
    st.markdown("## 🧑‍🏫 당신의 프롬프트를 구체화할 수 있는 전문가")

    exclude_username = username if role == "expert" else None
    keywords_for_reco = st.session_state.get("improve_keywords", [])

    c1, c2 = st.columns([1, 3])
    with c1:
        reco_btn = st.button(
            "전문가 추천받기",
            disabled=(not user_prompt.strip()) or (not st.session_state.get("show_keyword_select", False))
        )
    with c2:
        st.caption("키워드를 선택한 뒤 ‘전문가 추천받기’를 누르면, 가장 적절한 전문가를 최대 5명까지 보여줄게.")

    if reco_btn:
        if not st.session_state.get("show_keyword_select", False):
            st.warning("먼저 '개선 키워드 추천받기'를 눌러 키워드를 선택해줘.")
            st.stop()

        if st.session_state.get("cb_kw_other", False) and (not st.session_state.get("other_kw_text", "").strip()):
            st.warning("'기타(직접 입력)'을 체크했으면 원하는 키워드를 입력해줘.")
            st.stop()

        with st.spinner("전문가를 추천 중입니다..."):
            recs = db.recommend_experts(
                keywords=keywords_for_reco,
                exclude_username=exclude_username,
                top_k=5
            )

        st.session_state["recommended_experts"] = recs
        st.session_state["chosen_expert"] = None
        st.session_state["chosen_expert_radio"] = None
        if "expert_radio" in st.session_state:
            del st.session_state["expert_radio"]

    recs = st.session_state.get("recommended_experts", [])

    if recs:
        st.markdown("### ✅ 추천된 전문가 목록 (1명 선택)")

        label_to_expert = {}
        labels = []
        for e in recs:
            uname = e.get("username") or e.get("expert_name") or "expert"
            expert_name = e.get("expert_name") or uname
            field = e.get("field") or ""
            specialty = e.get("specialty") or ""
            label = f"{uname} · {field} · {specialty}".strip()
            labels.append(label)
            label_to_expert[label] = expert_name

        prev_label = st.session_state.get("chosen_expert_radio")
        if prev_label not in labels:
            prev_label = None

        selected_label = st.radio(
            "전문가 1명을 선택해줘.",
            options=labels,
            index=labels.index(prev_label) if prev_label else 0,
            key="expert_radio"
        )

        chosen_expert = label_to_expert.get(selected_label)
        st.session_state["chosen_expert_radio"] = selected_label
        st.session_state["chosen_expert"] = chosen_expert

        st.success(f"선택된 전문가: {chosen_expert}")
    else:
        st.caption("아직 추천된 전문가가 없어. 키워드를 선택하고 ‘전문가 추천받기’를 눌러줘.")

    st.divider()

    # -----------------------------
    # 개선 요청하기
    # -----------------------------
    chosen = st.session_state.get("chosen_expert")
    submit_disabled = (
        (not user_prompt.strip())
        or (not st.session_state.get("show_keyword_select", False))
        or (chosen is None)
    )

    if st.button("개선 요청하기", type="primary", disabled=submit_disabled):
        if not user_prompt.strip():
            st.warning("프롬프트를 입력해 주세요.")
            st.stop()

        if not st.session_state.get("show_keyword_select", False):
            st.warning("먼저 '개선 키워드 추천받기'를 눌러 키워드를 선택해줘.")
            st.stop()

        if st.session_state.get("cb_kw_other", False) and (not st.session_state.get("other_kw_text", "").strip()):
            st.warning("'기타(직접 입력)'을 체크했으면 원하는 키워드를 입력해줘.")
            st.stop()

        chosen = st.session_state.get("chosen_expert")
        if not chosen:
            st.warning("먼저 전문가 1명을 선택해줘.")
            st.stop()

        keywords = st.session_state.get("improve_keywords", [])

        with st.spinner("유사 사례를 검색 중입니다..."):
            similar, query_emb = find_similar_cases(user_prompt)

        hits = [c for c in similar if c.get("similarity", 0) >= SIM_THRESHOLD]

        if hits:
            st.success("유사한 사례를 찾았습니다. (DB)")
            for c in hits[:TOP_K]:
                st.markdown(
                    f"**유사도:** {c['similarity']:.3f} | **전문가:** {c['expert']} | **사례 ID:** {c['case_id']}"
                )
                with st.expander("원문 프롬프트"):
                    st.text(c["original"])
                with st.expander("개선된 프롬프트"):
                    st.code(c["improved"])
                with st.expander("요약 피드백"):
                    st.text(c["summary"])
            st.stop()

        db.save_expert_request(
            user_id=user_id,
            original=user_prompt,
            embedding=query_emb,
            routed_expert=chosen,
            top_similarity=float(similar[0]["similarity"]) if similar else 0.0,
            keywords=",".join(keywords)
        )

        st.success(f"전달 완료 ✅ (선택 전문가: {chosen})")
        st.info("지금부터 이 요청은 ‘나의 개선 요청함’에서 확인할 수 있어. 전문가가 답변하면 상태가 완료로 바뀔 거야.")

        # ✅ [핵심 수정] st.switch_page() 쓰지 말고, Home.py 라우터가 이해하는 route로 이동
        st.session_state["route"] = "my_requests"
        st.rerun()
