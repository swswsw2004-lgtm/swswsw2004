"""케이스 상태 전이 규칙 (상태전이도의 코드 버전).

docs/architecture.md 의 상태전이도와 반드시 일치시켜 주세요.
각 전이는 (현재 상태, 다음 상태) → 실행 가능한 역할 + 조건 으로 정의됩니다.

담당: 팀원1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Case, Role, Status, User


class WorkflowError(Exception):
    """허용되지 않은 상태 변경."""


@dataclass(frozen=True)
class TransitionContext:
    """전이 조건 판단에 필요한 추가 정보 (DB에서 조회해 채워 넣음)."""
    new_assignee_uid: str | None = None
    memo_count: int = 0
    reason: str = ""


Condition = Callable[[User, Case, TransitionContext], str | None]
# 조건 함수: 통과하면 None, 실패하면 사유 문자열 반환


def _needs_assignee(_u: User, _c: Case, ctx: TransitionContext) -> str | None:
    return None if ctx.new_assignee_uid else "배정할 검토 담당자를 선택하세요."


def _must_be_assignee(u: User, c: Case, _ctx: TransitionContext) -> str | None:
    return None if c.assignee_uid == u.uid else "배정된 담당자만 실행할 수 있습니다."


def _assignee_or_admin(u: User, c: Case, _ctx: TransitionContext) -> str | None:
    if u.role == Role.ADMIN or c.assignee_uid == u.uid:
        return None
    return "배정된 담당자 또는 관리자만 실행할 수 있습니다."


def _needs_memo(u: User, c: Case, ctx: TransitionContext) -> str | None:
    err = _must_be_assignee(u, c, ctx)
    if err:
        return err
    return None if ctx.memo_count > 0 else "완료하려면 검토 메모/리포트를 1개 이상 작성해야 합니다."


def _needs_reason(_u: User, _c: Case, ctx: TransitionContext) -> str | None:
    return None if ctx.reason.strip() else "사유를 입력해야 합니다."


def _all(*conds: Condition) -> Condition:
    def check(u: User, c: Case, ctx: TransitionContext) -> str | None:
        for cond in conds:
            err = cond(u, c, ctx)
            if err:
                return err
        return None
    return check


@dataclass(frozen=True)
class Transition:
    roles: tuple[str, ...]
    condition: Condition | None = None
    label: str = ""


TRANSITIONS: dict[tuple[str, str], Transition] = {
    (Status.RECEIVED, Status.ASSIGNED):
        Transition((Role.ADMIN,), _needs_assignee, "담당자 배정"),
    (Status.ASSIGNED, Status.IN_REVIEW):
        Transition((Role.REVIEWER,), _must_be_assignee, "검토 시작"),
    (Status.IN_REVIEW, Status.COMPLETED):
        Transition((Role.REVIEWER,), _needs_memo, "검토 완료"),
    (Status.IN_REVIEW, Status.NEEDS_REVISION):
        Transition((Role.REVIEWER, Role.ADMIN),
                   _all(_assignee_or_admin, _needs_reason), "보완 요청"),
    (Status.NEEDS_REVISION, Status.IN_REVIEW):
        Transition((Role.REVIEWER,), _must_be_assignee, "재검토 시작"),
    (Status.COMPLETED, Status.IN_REVIEW):
        Transition((Role.ADMIN,), _needs_reason, "완료 취소(재검토)"),
}


def check_transition(user: User, case: Case, to_status: str,
                     ctx: TransitionContext | None = None) -> Transition:
    """전이가 가능하면 Transition을 반환, 아니면 WorkflowError."""
    ctx = ctx or TransitionContext()
    if to_status not in Status.ALL:
        raise WorkflowError(f"알 수 없는 상태입니다: {to_status}")
    key = (case.status, to_status)
    rule = TRANSITIONS.get(key)
    if rule is None:
        raise WorkflowError(
            f"'{Status.LABELS.get(case.status, case.status)}' → "
            f"'{Status.LABELS[to_status]}' 변경은 허용되지 않습니다.")
    if user.role not in rule.roles:
        raise WorkflowError(f"'{user.role_label}' 역할은 '{rule.label}'을(를) 실행할 수 없습니다.")
    if rule.condition:
        err = rule.condition(user, case, ctx)
        if err:
            raise WorkflowError(err)
    return rule


def available_transitions(user: User, case: Case) -> list[tuple[str, Transition]]:
    """현재 사용자가 '역할상' 실행 가능한 전이 목록 (조건은 실행 시 검사)."""
    return [
        (to, rule) for (frm, to), rule in TRANSITIONS.items()
        if frm == case.status and user.role in rule.roles
    ]
