"""관리 담당자: 담당자 배정·진행 현황. 담당: 팀원1"""
from collections import Counter

import streamlit as st

from pacs import repository as repo
from pacs.models import Status

from .common import get_user, handle_errors


def render():
    user = get_user()
    st.title("🗂️ 배정·진행 현황")

    cases, reviewers = [], []
    with handle_errors():
        cases = repo.list_cases(user)
        reviewers = repo.list_reviewers(user)

    counts = Counter(c.status for c in cases)
    cols = st.columns(len(Status.ALL))
    for col, s in zip(cols, Status.ALL):
        col.metric(Status.LABELS[s], counts.get(s, 0))

    st.subheader("배정 대기 케이스")
    waiting = [c for c in cases if c.status == Status.RECEIVED]
    if not waiting:
        st.info("배정 대기 중인 케이스가 없습니다.")
    if not reviewers:
        st.warning("등록된 검토 담당자가 없습니다. scripts/create_user.py 로 계정을 만드세요.")
        return
    names = {r["uid"]: r.get("display_name") or r.get("email", r["uid"]) for r in reviewers}
    for c in waiting:
        a, b, d = st.columns([2, 3, 1])
        a.markdown(f"**{c.case_id}** · {c.modality} · {c.exam_date}")
        uid = b.selectbox("검토 담당자", list(names), format_func=names.get,
                          key=f"assign-{c.case_id}", label_visibility="collapsed")
        if d.button("배정", key=f"btn-{c.case_id}"):
            with handle_errors(success=f"{c.case_id} 배정 완료"):
                repo.change_status(user, c.case_id, Status.ASSIGNED, new_assignee_uid=uid)
                st.rerun()
