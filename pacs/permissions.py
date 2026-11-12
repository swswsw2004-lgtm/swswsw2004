"""역할·담당 범위에 따른 접근 권한 검사.

화면에서 버튼을 숨기는 것과 별개로, repository.py의 모든 데이터 접근 함수가
이 모듈의 require_* 함수를 호출해 '실제 데이터 접근 경로'에서 권한을 검사합니다.

담당: 팀원1
"""
from __future__ import annotations

from .models import Case, Role, Status, User


class PermissionDenied(Exception):
    """권한 없는 요청. 화면에서는 사용자에게 사유를 안내합니다."""


def _is_assignee(user: User, case: Case) -> bool:
    return case.assignee_uid is not None and case.assignee_uid == user.uid


# ── 판정 함수 (True/False) ──────────────────────────────────
def can_view_case(user: User, case: Case) -> bool:
    if user.role in (Role.ADMIN, Role.REGISTRAR):
        return True
    if user.role == Role.REVIEWER:
        return _is_assignee(user, case)
    return False


def can_create_case(user: User) -> bool:
    return user.role in (Role.REGISTRAR, Role.ADMIN)


def can_upload_image(user: User, case: Case) -> bool:
    if user.role not in (Role.REGISTRAR, Role.ADMIN):
        return False
    # 검토가 끝난 케이스에는 영상을 추가하지 않습니다.
    return case.status in (Status.RECEIVED, Status.ASSIGNED, Status.NEEDS_REVISION)


def can_process_image(user: User, case: Case) -> bool:
    return (user.role == Role.REVIEWER and _is_assignee(user, case)
            and case.status == Status.IN_REVIEW)


def can_write_memo(user: User, case: Case) -> bool:
    if user.role == Role.ADMIN:
        return True
    return (user.role == Role.REVIEWER and _is_assignee(user, case)
            and case.status in (Status.IN_REVIEW, Status.NEEDS_REVISION))


def can_assign(user: User) -> bool:
    return user.role == Role.ADMIN


# ── 강제 함수 (실패 시 예외) ────────────────────────────────
def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionDenied(message)


def require_view(user: User, case: Case) -> None:
    require(can_view_case(user, case), "이 케이스를 조회할 권한이 없습니다.")


def require_upload(user: User, case: Case) -> None:
    require(can_upload_image(user, case),
            "영상 등록은 등록/관리 담당자만, 접수·배정·보완 요청 상태에서만 가능합니다.")


def require_process(user: User, case: Case) -> None:
    require(can_process_image(user, case),
            "영상 처리는 '검토 중' 상태에서 배정된 검토 담당자만 가능합니다.")


def require_memo(user: User, case: Case) -> None:
    require(can_write_memo(user, case), "이 케이스에 메모를 작성할 권한이 없습니다.")
