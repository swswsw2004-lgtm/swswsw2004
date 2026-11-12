"""권한 규칙 테스트. 담당: 팀원1"""
import pytest

from pacs.models import Status
from pacs.permissions import (PermissionDenied, can_process_image, can_upload_image,
                              can_view_case, require_process)


def test_reviewer_sees_only_assigned(reviewer, other_reviewer, make_case):
    case = make_case(Status.ASSIGNED)
    assert can_view_case(reviewer, case)
    assert not can_view_case(other_reviewer, case)


def test_upload_blocked_after_review(registrar, make_case):
    assert can_upload_image(registrar, make_case(Status.RECEIVED))
    assert not can_upload_image(registrar, make_case(Status.IN_REVIEW))
    assert not can_upload_image(registrar, make_case(Status.COMPLETED))


def test_reviewer_cannot_upload(reviewer, make_case):
    assert not can_upload_image(reviewer, make_case(Status.RECEIVED))


def test_process_only_in_review_by_assignee(reviewer, other_reviewer, admin, make_case):
    assert can_process_image(reviewer, make_case(Status.IN_REVIEW))
    assert not can_process_image(reviewer, make_case(Status.ASSIGNED))
    assert not can_process_image(other_reviewer, make_case(Status.IN_REVIEW))
    with pytest.raises(PermissionDenied):
        require_process(admin, make_case(Status.IN_REVIEW))
