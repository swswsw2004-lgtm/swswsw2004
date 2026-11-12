import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pacs.models import Case, Role, Status, User  # noqa: E402


@pytest.fixture
def admin():
    return User("u-admin", "admin@test.com", Role.ADMIN)


@pytest.fixture
def registrar():
    return User("u-reg", "reg@test.com", Role.REGISTRAR)


@pytest.fixture
def reviewer():
    return User("u-rev", "rev@test.com", Role.REVIEWER)


@pytest.fixture
def other_reviewer():
    return User("u-rev2", "rev2@test.com", Role.REVIEWER)


@pytest.fixture
def make_case():
    def _make(status=Status.RECEIVED, assignee="u-rev"):
        return Case(case_id="MOCK-0001", status=status, assignee_uid=assignee)
    return _make


@pytest.fixture
def sample_image():
    """그라디언트 + 원 + 가우시안 잡음이 있는 합성 영상 (재현성을 위해 seed 고정)."""
    rng = np.random.default_rng(0)
    h, w = 128, 128
    yy, xx = np.mgrid[0:h, 0:w]
    img = (xx / w * 120 + 40).astype(np.float64)
    img[(yy - 64) ** 2 + (xx - 64) ** 2 < 30 ** 2] += 80
    img += rng.normal(0, 12, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)
