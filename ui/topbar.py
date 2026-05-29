# ui/topbar.py
import streamlit as st
from passlib.hash import bcrypt

from core.db import fetch_user, create_user, get_expert_profile_by_user_id


def _ensure_topbar_session_defaults():
    # 다른 곳에서 이미 setdefault 해도 괜찮음(안전)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("username", None)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("expert_name", None)
    st.session_state.setdefault("expert_primary", "")
    st.session_state.setdefault("expert_secondary", "")
    st.session_state.setdefault("show_login_dialog", False)


def _parse_specialty_to_domains(specialty: str) -> tuple[str, str]:
    """
    specialty 예시:
    - "주 분야=교육형 프롬프트 전문가 | 부 분야=입출력 명세 전문가"
    - 또는 "입출력 명세 전문가" (한 줄)
    """
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
            elif p.startswith("부 분야="):
                secondary = p.replace("부 분야=", "").strip() or "없음"
        return primary, secondary

    return s, "없음"


def _load_expert_profile_into_session(user_id: int):
    """
    role=expert일 때만 호출 권장.
    expert_profiles에서 specialty를 읽어 주/부 분야를 세션에 저장.
    """
    prof = get_expert_profile_by_user_id(user_id)
    if not prof:
        # role은 expert인데 프로필이 없는 경우(권한 페이지에서 막힘)
        st.session_state["expert_name"] = None
        st.session_state["expert_primary"] = "미정"
        st.session_state["expert_secondary"] = "없음"
        return

    st.session_state["expert_name"] = prof.get("expert_name")
    primary, secondary = _parse_specialty_to_domains(prof.get("specialty", ""))
    st.session_state["expert_primary"] = primary
    st.session_state["expert_secondary"] = secondary


def login_ui_dialog():
    st.subheader("로그인")
    with st.form("login_form_dialog", clear_on_submit=False):
        username = st.text_input("아이디", key="login_username")
        password = st.text_input("비밀번호", type="password", key="login_password")
        submitted = st.form_submit_button("로그인")

    if not submitted:
        return

    row = fetch_user(username)
    if not row:
        st.error("존재하지 않는 사용자입니다.")
        return

    # ✅ core/db.py fetch_user는 (id, username, password_hash, role) 4개 반환
    # 혹시 예전 코드로 3개 반환하는 경우도 대비(방어)
    try:
        user_id, _uname, pw_hash, role = row
    except ValueError:
        user_id, _uname, pw_hash = row
        role = "user"

    if not bcrypt.verify(password, pw_hash):
        st.error("비밀번호가 올바르지 않습니다.")
        return

    # ✅ 로그인 성공: 세션에 DB 기준 role 세팅
    st.session_state["user_id"] = user_id
    st.session_state["username"] = username
    st.session_state["role"] = role

    # ✅ 전문가면 프로필도 같이 로드(상단 뱃지/권한 페이지용)
    if role == "expert":
        _load_expert_profile_into_session(user_id)
    else:
        st.session_state["expert_name"] = None
        st.session_state["expert_primary"] = ""
        st.session_state["expert_secondary"] = ""

    st.session_state["show_login_dialog"] = False
    st.rerun()


def register_ui_dialog():
    st.subheader("회원가입")
    with st.form("register_form_dialog", clear_on_submit=False):
        username = st.text_input("아이디", key="reg_username")
        password = st.text_input("비밀번호", type="password", key="reg_password")
        password2 = st.text_input("비밀번호 확인", type="password", key="reg_password2")
        submitted = st.form_submit_button("회원가입")

    if not submitted:
        return

    if not username or not password:
        st.error("아이디/비밀번호를 입력해줘.")
        return

    if password != password2:
        st.error("비밀번호가 일치하지 않습니다.")
        return

    # create_user는 기본 role='user'로 만들도록 되어 있을 가능성이 큼
    # 너 프로젝트에서 expert 가입은 Home.py에서 처리 중이니,
    # 여기서는 안전하게 일반 가입만 진행(필요하면 role 선택 UI를 추가해도 됨)
    if create_user(username, password):
        st.success("회원가입 완료! 이제 로그인하세요.")
    else:
        st.error("이미 존재하는 아이디입니다.")


def show_login_dialog():
    @st.dialog("Login / Sign up")
    def _dialog():
        tabs = st.tabs(["로그인", "회원가입"])
        with tabs[0]:
            login_ui_dialog()
        with tabs[1]:
            register_ui_dialog()

        if st.button("닫기", key="close_login_dialog"):
            st.session_state["show_login_dialog"] = False
            st.rerun()

    _dialog()


def top_right_auth_controls():
    _ensure_topbar_session_defaults()

    st.markdown("""
    <style>
      /* 오른쪽 헤더 영역 */
      .topbar {
          display: flex;
          justify-content: flex-end;
          align-items: center;
          height: 64px;
          padding-top: 10px;
          gap: 10px;
      }

      /* 버튼 폭이 너무 넓어지는 것 방지 */
      div.stButton > button {
          width: auto !important;
          min-width: 120px;
          max-width: 160px;
          padding: 0.45rem 1rem;
          white-space: nowrap;
      }

      .userpill {
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(0,0,0,0.06);
          font-size: 14px;
          white-space: nowrap;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="topbar">', unsafe_allow_html=True)

    # ✅ "user_id" 키 존재 여부가 아니라, 실제 로그인 여부(None이 아닌지)로 판단해야 함
    logged_in = st.session_state.get("user_id") is not None

    if logged_in:
        st.markdown(
            f'<span class="userpill">👤 {st.session_state.get("username","")}</span>',
            unsafe_allow_html=True
        )

        if st.button("Logout", key="top_logout"):
            # 로그아웃은 필요한 키만 정리 (st.session_state.clear()는 다른 설정까지 날릴 수 있음)
            for k in [
                "user_id", "username", "role", "expert_name", "expert_primary", "expert_secondary",
                "show_login_dialog"
            ]:
                st.session_state[k] = None if k in ("user_id", "username", "role", "expert_name") else ""
            st.session_state["show_login_dialog"] = False
            st.rerun()
    else:
        if st.button("Login", key="top_login"):
            st.session_state["show_login_dialog"] = True

    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("show_login_dialog", False):
        show_login_dialog()


def render_expert_badge():
    """
    ✅ HTML은 반드시 st.markdown(..., unsafe_allow_html=True)로만 출력
    ✅ user_id가 None이면 바로 return (오류 방지)
    """
    if st.session_state.get("role") != "expert":
        return

    if st.session_state.get("user_id") is None:
        return

    username = st.session_state.get("username") or str(st.session_state.get("user_id"))
    primary = st.session_state.get("expert_primary") or "미정"
    secondary = st.session_state.get("expert_secondary") or "없음"
    secondary_display = secondary.strip() if str(secondary).strip() else "없음"

    html = f"""
    <div style="
        display:flex;
        justify-content:flex-end;
        align-items:center;
        margin:6px 0 10px 0;
        width:100%;
    ">
      <div style="
          padding:10px 14px;
          border-radius:18px;
          background: linear-gradient(135deg, #fff2f6 0%, #f3f7ff 100%);
          border:1px solid #ffd1e1;
          box-shadow: 0 6px 16px rgba(0,0,0,0.06);
          font-family: 'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
          max-width:360px;
          width:100%;
      ">
        <div style="font-size:13px; font-weight:900; color:#ff5a8a; margin-bottom:6px;">
          &lt;전문가 계정&gt; ✨
        </div>

        <div style="display:flex; flex-wrap:wrap; gap:10px; font-size:13px; color:#333;">
          <span style="background:#ffffff; border:1px dashed #ffb3cd; padding:6px 10px; border-radius:14px;
                       white-space:normal; word-break:break-word; overflow-wrap:anywhere;">
            🌟 <b>주 분야</b>: {primary}
          </span>

          <span style="background:#ffffff; border:1px dashed #b9d3ff; padding:6px 10px; border-radius:14px;
                       white-space:normal; word-break:break-word; overflow-wrap:anywhere;">
            💎 <b>부 분야</b>: {secondary_display}
          </span>

          <span style="background:#ffffff; border:1px dashed #c9f1d8; padding:6px 10px; border-radius:14px;
                       white-space:normal; word-break:break-word; overflow-wrap:anywhere;">
            🧸 <b>아이디</b>: {username}
          </span>
        </div>
      </div>
    </div>
    """

    # ✅✅✅ 핵심: HTML은 markdown으로만!
    st.markdown(html, unsafe_allow_html=True)
