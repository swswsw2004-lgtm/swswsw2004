"""로그인 화면. 담당: 팀원1"""
import streamlit as st

from pacs.auth import AuthError, sign_in, verify


def render():
    st.title("🩻 교육용 웹 PACS")
    st.caption("공개 영상과 모의 케이스로 동작하는 교육용 시스템입니다.")
    with st.form("login"):
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary")
    if submitted:
        try:
            session = sign_in(email.strip(), password)
            verify(session)  # 역할 미등록 계정은 여기서 거절
            st.session_state["session"] = session
            st.rerun()
        except AuthError as e:
            st.error(str(e))
