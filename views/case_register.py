"""케이스 등록 화면. 담당: 팀원2"""
from datetime import date

import streamlit as st

from pacs import repository as repo
from pacs.models import MODALITIES

from .common import get_user, handle_errors, open_case


def render():
    user = get_user()
    st.title("➕ 케이스 등록")
    st.caption("실제 환자 정보는 입력하지 마세요. 모의 ID만 사용합니다. (예: MOCK-0001)")

    with st.form("new_case"):
        case_id = st.text_input("모의 케이스 ID")
        modality = st.selectbox("검사 구분", MODALITIES)
        exam_date = st.date_input("검사일", value=date.today())
        description = st.text_area("설명 (선택)")
        submitted = st.form_submit_button("등록", type="primary")

    if submitted:
        created = None
        with handle_errors(success="케이스가 등록되었습니다."):
            created = repo.create_case(user, case_id, modality, exam_date.isoformat(), description)
        if created:
            open_case(created)
