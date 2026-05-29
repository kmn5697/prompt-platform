# Home.py (Router Version: views 기반)
import importlib.util
import os
from typing import Optional

import streamlit as st

# ✅ [수정] create_user 추가
from core.db import init_db, authenticate_user, get_expert_profile_by_user_id, create_user
from ui.sidebar import render_role_based_sidebar  # ✅ 버튼 기반 라우팅으로 수정된 sidebar가 필요


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="Mirong's Python Prompt Lab",
    page_icon="🧪",
    layout="wide",
)

st.markdown("""
<style>
/* ✅ 전체 본문(메인) 상단 여백 */
.block-container { 
  padding-top: 2.2rem;   /* ← 여기 숫자만 조절하면 됨 (1.8~3.0 추천) */
  padding-bottom: 1.5rem; 
}

/* ✅ 타이틀(h1) 여백도 자연스럽게 */
h1 { 
  margin-bottom: 0.4rem; 
  margin-top: 0.6rem;    /* ← 너무 붙는 느낌 방지 */
}

/* ✅ 캡션 배경/여백 제거는 유지 */
[data-testid="stCaptionContainer"] { 
  background: none !important; 
  padding: 0 !important; 
  margin: 0 !important; 
}

/* ✅ 사이드바 상단도 같이 내려주기 */
[data-testid="stSidebarContent"] {
  padding-top: 1.2rem;
}
</style>
""", unsafe_allow_html=True)



# -----------------------------
# 세션 기본값
# -----------------------------
def ensure_session_defaults():
    st.session_state.setdefault("route", "home")          # ✅ 라우팅 키
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("username", None)
    st.session_state.setdefault("role", None)             # 'user' or 'expert'
    st.session_state.setdefault("expert_name", None)
    st.session_state.setdefault("expert_primary", "")
    st.session_state.setdefault("expert_secondary", "")
    st.session_state.setdefault("show_login_dialog", False)

ensure_session_defaults()


# -----------------------------
# 전문가 프로필 specialty 파싱
# -----------------------------
def parse_specialty_to_domains(specialty: str) -> tuple[str, str]:
    s = (specialty or "").strip()
    if not s:
        return "미정", "없음"

    if "주 분야=" in s:
        primary = "미정"
        secondary = "없음"
        parts = [p.strip() for p in s.split("|")]
        for p in parts:
            if p.startswith("주 분야="):
                primary = p.replace("주 분야=", "").strip() or "미정"
            if p.startswith("부 분야="):
                secondary = p.replace("부 분야=", "").strip() or "없음"
        return primary, secondary

    return s, "없음"


def load_expert_profile_into_session(user_id: int):
    prof = get_expert_profile_by_user_id(user_id)
    if not prof:
        st.session_state["expert_name"] = None
        st.session_state["expert_primary"] = "미정"
        st.session_state["expert_secondary"] = "없음"
        return

    st.session_state["expert_name"] = prof.get("expert_name")
    p, s = parse_specialty_to_domains(prof.get("specialty", ""))
    st.session_state["expert_primary"] = p
    st.session_state["expert_secondary"] = s


# -----------------------------
# 로그인/회원가입 다이얼로그
# -----------------------------
@st.dialog("Login")
def login_dialog():
    st.subheader("로그인 / 회원가입")

    tab_login, tab_signup = st.tabs(["로그인", "회원가입(일반 사용자)"])

    # -------------------------
    # 1) 로그인 탭
    # -------------------------
    with tab_login:
        username = st.text_input("아이디", key="dlg_login_username")
        password = st.text_input("비밀번호", type="password", key="dlg_login_password")

        if st.button("로그인", type="primary", key="dlg_login_btn"):
            auth = authenticate_user(username, password)
            if not auth:
                st.error("아이디 또는 비밀번호가 틀렸어.")
                return

            st.session_state["user_id"] = auth["user_id"]
            st.session_state["username"] = username
            st.session_state["role"] = auth["role"]

            if auth["role"] == "expert":
                load_expert_profile_into_session(auth["user_id"])
            else:
                st.session_state["expert_name"] = None
                st.session_state["expert_primary"] = ""
                st.session_state["expert_secondary"] = ""

            st.success("로그인 성공! 🎉")
            st.rerun()

    # -------------------------
    # 2) 회원가입 탭 (일반 사용자만)
    # -------------------------
    with tab_signup:
        new_username = st.text_input("아이디(새로 만들기)", key="dlg_signup_username")
        new_password = st.text_input("비밀번호", type="password", key="dlg_signup_password")
        new_password2 = st.text_input("비밀번호 확인", type="password", key="dlg_signup_password2")

        st.caption("※ 회원가입은 일반 사용자로만 가능해. 전문가가 되려면 테스트를 합격해야 승급돼.")

        if st.button("회원가입", type="primary", key="dlg_signup_btn"):
            u = (new_username or "").strip()
            p1 = new_password or ""
            p2 = new_password2 or ""

            if not u:
                st.warning("아이디를 입력해줘.")
                return
            if len(u) < 3:
                st.warning("아이디는 3자 이상으로 해줘.")
                return
            if not p1:
                st.warning("비밀번호를 입력해줘.")
                return
            if len(p1) < 4:
                st.warning("비밀번호는 4자 이상으로 해줘.")
                return
            if p1 != p2:
                st.warning("비밀번호 확인이 일치하지 않아.")
                return

            ok = create_user(username=u, password=p1, role="user")  # ✅ 무조건 user로 생성
            if not ok:
                st.error("이미 존재하는 아이디야. 다른 아이디로 해줘.")
                return

            st.success("회원가입 완료! 이제 로그인해줘 🙂")

            # (선택) 회원가입 후 로그인 탭에 아이디 자동 채우기
            st.session_state["dlg_login_username"] = u


def logout():
    st.session_state["user_id"] = None
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.session_state["expert_name"] = None
    st.session_state["expert_primary"] = ""
    st.session_state["expert_secondary"] = ""
    st.session_state["route"] = "home"
    st.rerun()


def render_login_or_logout_button():
    """
    Home 타이틀과 같은 row(같은 st.columns)에서 호출될 버튼 렌더러.
    """
    if st.session_state.get("user_id") is None:
        if st.button("Login", key="open_login", use_container_width=True):
            login_dialog()
    else:
        if st.button("Logout", key="logout_btn", use_container_width=True):
            logout()


# -----------------------------
# views 모듈 로더 (파일명 숫자 포함도 OK)
# -----------------------------
def import_view_module_from_path(path: str):
    """
    views 폴더의 파일을 동적으로 import해서 module 반환.
    파일명이 '1_prompt_improve.py'처럼 숫자로 시작해도 문제없음.
    """
    module_name = "view_" + os.path.basename(path).replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def route_to_view(route: str):
    """
    route 값에 따라 views/* 의 render()를 호출
    """
    base = os.path.join(os.path.dirname(__file__), "views")

    # ✅ route -> 파일 매핑 (너 파일명에 맞게)
    mapping = {
        "home": None,
        "prompt_improve": os.path.join(base, "1_prompt_improve.py"),
        "cases": os.path.join(base, "2_cases.py"),
        "expert_test": os.path.join(base, "3_expert_test.py"),
        "expert_requests": os.path.join(base, "9_expert_requests.py"),

        # ✅ 나의 개선 요청함 route 키 통일
        "my_requests": os.path.join(base, "4_my_requests.py"),
    }

    path = mapping.get(route)
    if path is None:
        return  # home은 아래에서 처리

    if not os.path.exists(path):
        st.error(f"뷰 파일을 찾을 수 없어: {path}")
        return

    mod = import_view_module_from_path(path)
    if not hasattr(mod, "render"):
        st.error(f"{os.path.basename(path)}에 render() 함수가 없어.")
        return

    mod.render()


# -----------------------------
# Home 화면
# -----------------------------
def render_home():
    left, right = st.columns([8, 2], vertical_alignment="center")

    with left:
        st.title("Mirong's Python Prompt Lab")
        st.caption("AI를 통해 원하는 응답을 얻고싶나요? 전문가가 여러분의 프롬프트를 개선해드리겠습니다.")

    with right:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        render_login_or_logout_button()

    try:
        from ui.components import showcase_examples_card
        showcase_examples_card()
    except Exception:
        st.info("홈 컴포넌트를 불러오지 못했어. ui/components.py 확인해줘.")


# -----------------------------
# 권한 가드 (views 라우팅 전)
# -----------------------------
def enforce_route_permissions(route: str) -> str:
    """
    로그인/role에 따라 접근 가능한 route를 제한
    - 로그인 전: home, cases만 허용
    - user: home, prompt_improve, cases, expert_test, my_requests
    - expert: home, prompt_improve, cases, expert_requests, my_requests
    """
    logged_in = st.session_state.get("user_id") is not None
    role = st.session_state.get("role") or "user"

    if not logged_in:
        if route not in ("home", "cases"):
            return "home"
        return route

    if role == "expert":
        allowed = {"home", "prompt_improve", "cases", "expert_requests", "my_requests"}
    else:
        allowed = {"home", "prompt_improve", "cases", "expert_test", "my_requests"}

    return route if route in allowed else "home"


# -----------------------------
# main
# -----------------------------
def main():
    init_db()

    render_role_based_sidebar()

    # ✅ 사이드바 Login 버튼이 눌리면 다이얼로그 띄우기
    if st.session_state.get("show_login_dialog", False):
        st.session_state["show_login_dialog"] = False
        login_dialog()

    route = st.session_state.get("route", "home")

    # ✅ 예전/혼용 route 값 정규화
    if route in ("4_my_requests", "4_4_my_requests", "my_request", "my-requests"):
        route = "my_requests"

    route = enforce_route_permissions(route)
    st.session_state["route"] = route

    if route == "home":
        render_home()
    else:
        route_to_view(route)


if __name__ == "__main__":
    main()
