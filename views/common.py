"""화면 공통 유틸."""
from contextlib import contextmanager

import streamlit as st

from pacs.models import Status
from pacs.permissions import PermissionDenied
from pacs.validation import ValidationError
from pacs.workflow import WorkflowError


def get_user():
    return st.session_state["user"]


@contextmanager
def handle_errors(success: str | None = None):
    """예상 가능한 오류는 사유를 안내하고, 그 외 오류는 일반 메시지로 표시."""
    try:
        yield
        if success:
            st.toast(success, icon="✅")
    except (PermissionDenied, WorkflowError) as e:
        st.error(f"⛔ {e}")
    except ValidationError as e:
        st.warning(f"⚠️ {e}")
    except Exception as e:  # noqa: BLE001
        st.error(f"처리 중 오류가 발생했습니다: {type(e).__name__}")
        st.exception(e)  # TODO: 배포 시에는 로그로만 남기도록 변경


def status_badge(status: str) -> str:
    colors = {Status.RECEIVED: "gray", Status.ASSIGNED: "blue", Status.IN_REVIEW: "orange",
              Status.NEEDS_REVISION: "red", Status.COMPLETED: "green"}
    return f":{colors.get(status, 'gray')}-badge[{Status.LABELS.get(status, status)}]"


def open_case(case_id: str):
    """케이스 상세 화면으로 이동 (app.py 가 등록한 Page 객체 사용)."""
    st.session_state["selected_case"] = case_id
    st.switch_page(st.session_state["pages"]["case"])
