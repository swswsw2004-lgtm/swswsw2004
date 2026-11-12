"""상태 전이 규칙 테스트. 담당: 팀원1"""
import pytest

from pacs.models import Status
from pacs.workflow import TransitionContext, WorkflowError, available_transitions, check_transition


def test_admin_assigns_with_assignee(admin, make_case):
    case = make_case(Status.RECEIVED, assignee=None)
    check_transition(admin, case, Status.ASSIGNED, TransitionContext(new_assignee_uid="u-rev"))


def test_assign_requires_assignee(admin, make_case):
    with pytest.raises(WorkflowError, match="담당자"):
        check_transition(admin, make_case(Status.RECEIVED, None), Status.ASSIGNED)


def test_registrar_cannot_assign(registrar, make_case):
    with pytest.raises(WorkflowError):
        check_transition(registrar, make_case(Status.RECEIVED, None), Status.ASSIGNED,
                         TransitionContext(new_assignee_uid="u-rev"))


def test_only_assignee_starts_review(reviewer, other_reviewer, make_case):
    case = make_case(Status.ASSIGNED)
    check_transition(reviewer, case, Status.IN_REVIEW)
    with pytest.raises(WorkflowError, match="배정된 담당자"):
        check_transition(other_reviewer, case, Status.IN_REVIEW)


def test_complete_requires_memo(reviewer, make_case):
    case = make_case(Status.IN_REVIEW)
    with pytest.raises(WorkflowError, match="메모"):
        check_transition(reviewer, case, Status.COMPLETED, TransitionContext(memo_count=0))
    check_transition(reviewer, case, Status.COMPLETED, TransitionContext(memo_count=1))


def test_skip_states_not_allowed(reviewer, make_case):
    with pytest.raises(WorkflowError, match="허용되지 않습니다"):
        check_transition(reviewer, make_case(Status.RECEIVED), Status.COMPLETED)


def test_reopen_completed_needs_admin_and_reason(admin, reviewer, make_case):
    case = make_case(Status.COMPLETED)
    with pytest.raises(WorkflowError):
        check_transition(reviewer, case, Status.IN_REVIEW, TransitionContext(reason="재확인"))
    with pytest.raises(WorkflowError, match="사유"):
        check_transition(admin, case, Status.IN_REVIEW)
    check_transition(admin, case, Status.IN_REVIEW, TransitionContext(reason="재확인 필요"))


def test_available_transitions_by_role(reviewer, admin, make_case):
    case = make_case(Status.IN_REVIEW)
    assert {t for t, _ in available_transitions(reviewer, case)} == {Status.COMPLETED, Status.NEEDS_REVISION}
    assert {t for t, _ in available_transitions(admin, case)} == {Status.NEEDS_REVISION}
