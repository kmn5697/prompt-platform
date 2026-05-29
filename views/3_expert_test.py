def render():
    import time
    import streamlit as st

    from services.expert_test_bank import PROBLEMS, grade_problem
    from services.expert_qualification import infer_expert_domains, add_expert_to_exp_csv
    from core.db import promote_user_to_expert, get_expert_profile_by_user_id

    st.set_page_config(page_title="expert test", page_icon="✅", layout="centered")
    st.title("✅ Test를 통과하여 전문가가 되어봅시다.")

    # -----------------------------
    # 로그인 필수
    # -----------------------------
    if st.session_state.get("user_id") is None:
        st.warning("로그인 후 이용할 수 있어.")
        st.stop()

    user_id = st.session_state["user_id"]

    # 이미 전문가면 막기
    if st.session_state.get("role") == "expert":
        st.success("이미 전문가 계정이야! ✨")
        prof = get_expert_profile_by_user_id(user_id)
        if prof:
            st.caption(f"주 분야: {prof.get('field','')}")
            st.caption(f"전문성: {prof.get('specialty','')}")
        st.stop()

    # -----------------------------
    # 닉네임 입력
    # -----------------------------
    name = st.text_input("닉네임(또는 이름)", value=st.session_state.get("name", ""))
    if name:
        st.session_state["name"] = name

    st.divider()

    # -----------------------------
    # 문제 입력
    # -----------------------------
    answers = {}
    for p in PROBLEMS:
        st.subheader(p.title)
        st.code(p.bad_prompt)
        st.write("🔍 고쳐야 할 키워드")
        st.write("- " + "\n- ".join(p.keywords_to_fix))
        answers[p.id] = st.text_area(
            "개선된 프롬프트",
            key=f"expert_answer_{p.id}",
            height=110
        )
        st.divider()

    # -----------------------------
    # 제출 / 채점
    # -----------------------------
    if st.button("제출", type="primary"):
        if not name.strip():
            st.error("닉네임(또는 이름)을 입력해줘.")
            st.stop()

        all_correct = True
        st.subheader("📌 채점 결과")

        for pid, txt in answers.items():
            r = grade_problem(pid, txt)
            all_correct = all_correct and r["is_correct"]

            st.markdown(f"#### 문제 {pid}")
            if r["is_correct"]:
                st.success(f"정답 ✅ (충족 {r['score']}/{r['pass_min']} 이상)")
            else:
                st.error(f"오답 ❌ (충족 {r['score']}/{r['pass_min']} 이상 필요)")
                st.caption("빠진 항목: " + " / ".join(r["missing"]))

        st.divider()

        if not all_correct:
            st.warning("아직 올정답이 아니야. 빠진 항목을 채우고 다시 제출해줘.")
            st.stop()

        # =========================================================
        # ✅ 여기부터가 핵심: 풍선 + 축하 화면 절대 안 사라지게
        # =========================================================
        st.balloons()
        st.success("🎉 축하합니다. 전문가로 승급하셨습니다!")

        # -----------------------------
        # 전문 분야 추정
        # -----------------------------
        prompts = [answers[1], answers[2], answers[3]]
        primary, secondary = infer_expert_domains(prompts)

        st.write(f"🏷️ 주 분야: **{primary}**")
        st.write(f"🏷️ 부 분야: **{secondary if secondary else '없음'}**")

        # -----------------------------
        # DB 승급 + expert_profiles 생성 (권한의 핵심)
        # -----------------------------
        ok = promote_user_to_expert(
            user_id=user_id,
            primary_domain=primary,
            secondary_domain=secondary or "",
            field="python",
            publications="prompt_improvement",
            description="전문가 테스트 통과"
        )

        if not ok:
            st.error("DB 전문가 승급 실패. (users/DB 상태 확인 필요)")
            st.stop()

        # -----------------------------
        # CSV 저장 (선택)
        # -----------------------------
        add_expert_to_exp_csv(name.strip(), primary, secondary)

        # -----------------------------
        # 세션 즉시 반영 (권한/상단 카드)
        # -----------------------------
        st.session_state["role"] = "expert"
        st.session_state["expert_primary"] = primary
        st.session_state["expert_secondary"] = secondary or "없음"

        # -----------------------------
        # 프로필 생성 확인 (안전장치)
        # -----------------------------
        prof = get_expert_profile_by_user_id(user_id)
        if not prof:
            st.warning("전문가로 승급되었지만, 프로필이 아직 반영되지 않았어. 새로고침하면 나타날 수 있어.")
        else:
            st.info("✅ 이제 'expert requests'에서 프롬프트 요청을 받을 수 있어!")

        # -----------------------------
        # ❗️바로 rerun하면 풍선이 안 보이니까 잠깐 대기
        # -----------------------------
        time.sleep(1.3)
        st.rerun()
