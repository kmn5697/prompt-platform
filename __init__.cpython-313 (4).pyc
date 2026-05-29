# ui/sidebar.py
import streamlit as st
from core import db  # 전문가 신뢰도 표시용 (로그인 후에만 사용)


def _set_route(route: str):
    st.session_state["route"] = route
    st.rerun()


def _logout():
    st.session_state["user_id"] = None
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.session_state["expert_name"] = None
    st.session_state["expert_primary"] = ""
    st.session_state["expert_secondary"] = ""
    st.session_state["route"] = "home"
    st.rerun()


def _menu_button(label: str, route: str, icon: str = ""):
    current = st.session_state.get("route", "home")
    is_active = (current == route)

    btn_label = f"{icon} {label}".strip()
    if st.button(
        btn_label,
        key=f"nav_{route}",
        use_container_width=True,
        type="secondary" if not is_active else "primary",
    ):
        _set_route(route)


# ✅ [추가] 로그인 전용 하단 박스 (Login 버튼)
def _render_login_box():
    st.divider()
    with st.container(border=True):
        st.markdown("### 🔐 로그인")
        st.caption("로그인하면 더 많은 메뉴가 열려.")

        if st.button("Login", key="sidebar_login_btn", use_container_width=True, type="primary"):
            # ✅ Home.py가 이 플래그를 보고 login_dialog()를 열어주게 함
            st.session_state["show_login_dialog"] = True
            st.rerun()


def _render_account_box():
    logged_in = st.session_state.get("user_id") is not None
    if not logged_in:
        return

    user_id = st.session_state.get("user_id")
    role = st.session_state.get("role") or "user"
    username = st.session_state.get("username") or "-"
    primary = (st.session_state.get("expert_primary") or "").strip()
    secondary = (st.session_state.get("expert_secondary") or "").strip()

    role_label = "전문가" if role == "expert" else "일반 사용자"

    if role == "expert":
        if primary and secondary and secondary != "없음":
            domain = f"{primary} / {secondary}"
        elif primary:
            domain = primary
        else:
            domain = "미정"
    else:
        domain = "해당 없음"

    trust_score = None
    if role == "expert" and user_id is not None:
        try:
            trust_score = db.get_trust_score_by_user_id(int(user_id))
        except Exception:
            trust_score = None

    st.divider()
    with st.container(border=True):
        st.markdown("### 👤 내 계정")
        st.markdown(f"- **구분**: {role_label}")
        st.markdown(f"- **아이디**: `{username}`")
        st.markdown(f"- **전문 분야**: {domain}")

        if role == "expert":
            if trust_score is None:
                st.markdown("- **신뢰도**: - / 10")
            else:
                st.markdown(f"- **신뢰도**: **{trust_score} / 10**")

        st.button(
            "Logout",
            key="sidebar_logout_btn",
            use_container_width=True,
            type="primary",
            on_click=_logout,
        )


def render_role_based_sidebar():
    role = st.session_state.get("role", None)
    logged_in = st.session_state.get("user_id") is not None

    with st.sidebar:
        st.markdown("## 🧭 메뉴")

        # -------------------------
        # ✅ 로그인 전
        # -------------------------
        if not logged_in:
            _menu_button("홈", "home", "🏠")
            _menu_button("사례 게시판", "cases", "📚")

            # ✅ [추가] 사이드바 하단 Login 버튼 박스
            _render_login_box()
            return

        # -------------------------
        # ✅ 로그인 후
        # -------------------------
        _menu_button("홈", "home", "🏠")
        _menu_button("프롬프트 개선 요청하기", "prompt_improve", "🛠️")
        _menu_button("사례 게시판", "cases", "📚")

        if role == "expert":
            _menu_button("사용자의 개선 요청", "expert_requests", "📥")
            _menu_button("나의 개선 요청함", "my_requests", "📬")
        else:
            _menu_button("전문가 테스트", "expert_test", "🧪")
            _menu_button("나의 개선 요청함", "my_requests", "📬")

        _render_account_box()
