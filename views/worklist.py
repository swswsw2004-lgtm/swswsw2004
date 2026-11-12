"""업무 목록: 처리할 업무 / 완료된 업무 구분, 검색·필터. 담당: 팀원1(목록), 팀원2(검색·필터)"""
import streamlit as st

from pacs import repository as repo
from pacs.models import MODALITIES, Status

from .common import get_user, handle_errors, open_case, status_badge


def _table(cases, key_prefix: str):
    if not cases:
        st.info("해당하는 케이스가 없습니다.")
        return
    for c in cases:
        cols = st.columns([2, 1.2, 1.2, 1.2, 3, 1])
        cols[0].markdown(f"**{c.case_id}**")
        cols[1].markdown(status_badge(c.status))
        cols[2].write(c.modality)
        cols[3].write(c.exam_date)
        cols[4].write(c.description[:40])
        if cols[5].button("열기", key=f"{key_prefix}-{c.case_id}"):
            open_case(c.case_id)


def render():
    user = get_user()
    st.title("📋 업무 목록")

    f1, f2, f3 = st.columns([2, 1, 1])
    keyword = f1.text_input("검색 (케이스 ID·설명)")
    modality = f2.selectbox("검사 구분", ["전체", *MODALITIES])
    status = f3.selectbox("상태", ["전체", *Status.ALL], format_func=lambda s: Status.LABELS.get(s, s))

    cases = []
    with handle_errors():
        cases = repo.list_cases(
            user,
            status=None if status == "전체" else status,
            modality=None if modality == "전체" else modality,
            keyword=keyword,
        )

    todo = [c for c in cases if c.status in Status.OPEN]
    done = [c for c in cases if c.status == Status.COMPLETED]
    t1, t2 = st.tabs([f"처리할 업무 ({len(todo)})", f"완료된 업무 ({len(done)})"])
    with t1:
        _table(todo, "todo")
    with t2:
        _table(done, "done")
