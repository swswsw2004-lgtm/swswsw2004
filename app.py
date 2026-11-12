"""교육용 웹 PACS — Streamlit 진입점.

실행: streamlit run app.py
"""
import streamlit as st

from pacs.auth import AuthError, verify
from pacs.models import Role

st.set_page_config(page_title="교육용 웹 PACS", page_icon="🩻", layout="wide")


def current_user():
    """세션의 토큰을 매 실행마다 검증. 실패하면 로그인 화면으로."""
    session = st.session_state.get("session")
    if not session:
        return None
    try:
        user, session = verify(session)
        st.session_state["session"] = session  # 토큰이 갱신되었을 수 있음
        return user
    except AuthError as e:
        st.session_state.pop("session", None)
        st.warning(str(e))
        return None


user = current_user()

if user is None:
    from views import login
    pg = st.navigation([st.Page(login.render, title="로그인", icon="🔐")])
    pg.run()
    st.stop()

st.session_state["user"] = user

from views import admin, case_detail, case_register, worklist  # noqa: E402

case_page = st.Page(case_detail.render, title="케이스 상세·뷰어", icon="🩻", url_path="case")
st.session_state["pages"] = {"case": case_page}  # 다른 화면에서 st.switch_page 로 이동할 때 사용

pages = [
    st.Page(worklist.render, title="업무 목록", icon="📋", url_path="worklist", default=True),
    case_page,
]
if user.role in (Role.REGISTRAR, Role.ADMIN):
    pages.append(st.Page(case_register.render, title="케이스 등록", icon="➕", url_path="register"))
if user.role == Role.ADMIN:
    pages.append(st.Page(admin.render, title="배정·진행 현황", icon="🗂️", url_path="admin"))

with st.sidebar:
    st.markdown(f"**{user.display_name or user.email}**  \n{user.role_label}")
    if st.button("로그아웃", width="stretch"):
        st.session_state.clear()
        st.rerun()
    st.caption("⚠️ 교육용 모의 케이스입니다. 분석 수치는 실제 진단 결과가 아닙니다.")

st.navigation(pages).run()
