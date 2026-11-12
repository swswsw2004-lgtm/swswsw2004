"""공통 상수와 데이터 모델.

담당: 팀원1 (역할·상태 정의) — 팀 합의 후 변경할 때는 Issue로 먼저 논의하세요.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── 사용자 역할 ─────────────────────────────────────────────
class Role:
    REGISTRAR = "registrar"  # 등록 담당자: 케이스·영상 접수
    REVIEWER = "reviewer"    # 검토 담당자: 처리·비교·메모
    ADMIN = "admin"          # 관리 담당자: 배정·진행 현황

    ALL = (REGISTRAR, REVIEWER, ADMIN)
    LABELS = {
        REGISTRAR: "등록 담당자",
        REVIEWER: "검토 담당자",
        ADMIN: "관리 담당자",
    }


# ── 케이스 상태 ─────────────────────────────────────────────
class Status:
    RECEIVED = "received"              # 접수
    ASSIGNED = "assigned"              # 배정
    IN_REVIEW = "in_review"            # 검토 중
    NEEDS_REVISION = "needs_revision"  # 보완 요청
    COMPLETED = "completed"            # 완료

    ALL = (RECEIVED, ASSIGNED, IN_REVIEW, NEEDS_REVISION, COMPLETED)
    LABELS = {
        RECEIVED: "접수",
        ASSIGNED: "배정",
        IN_REVIEW: "검토 중",
        NEEDS_REVISION: "보완 요청",
        COMPLETED: "완료",
    }
    # 업무 목록에서 '처리할 업무'로 분류되는 상태
    OPEN = (RECEIVED, ASSIGNED, IN_REVIEW, NEEDS_REVISION)


MODALITIES = ("X-ray", "CT", "MRI", "US", "기타")


@dataclass(frozen=True)
class User:
    uid: str
    email: str
    role: str
    display_name: str = ""

    @property
    def role_label(self) -> str:
        return Role.LABELS.get(self.role, self.role)


@dataclass
class Case:
    case_id: str
    status: str = Status.RECEIVED
    assignee_uid: str | None = None
    created_by: str = ""
    modality: str = ""
    exam_date: str = ""
    description: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Case":
        known = {"case_id", "status", "assignee_uid", "created_by",
                 "modality", "exam_date", "description"}
        return cls(
            **{k: data.get(k) for k in known if k in data},
            extra={k: v for k, v in data.items() if k not in known},
        )
