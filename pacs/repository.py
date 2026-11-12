"""Firestore 데이터 접근 계층.

규칙:
  - 화면(views/)은 Firestore를 직접 호출하지 말고 반드시 이 모듈을 거칩니다.
  - 모든 함수는 첫 인자로 로그인한 User를 받고, permissions/workflow로 권한을 검사합니다.
    (Admin SDK는 Firestore 보안 규칙을 우회하므로, 여기서의 검사가 실제 접근 제어입니다.)

담당 구역:
  팀원1: assign_case, change_status, list_reviewers, _log_history
  팀원2: create_case, list_cases, get_case, add_image, list_images, load_image
  팀원4: save_processing, list_processings, add_memo, update_memo, list_memos
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

import cv2
import numpy as np
from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore as gcf

from . import config
from .firebase_client import get_db
from .models import Case, MODALITIES, Role, Status, User
from .permissions import (PermissionDenied, can_create_case, can_view_case,
                          require, require_memo, require_process, require_upload,
                          require_view)
from .processing import get_algorithm
from .storage import LocalStorage
from .validation import ROI, ValidationError, validate_image_upload, validate_roi
from .workflow import TransitionContext, check_transition

CASE_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,31}$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _storage() -> LocalStorage:
    return LocalStorage(config.storage_dir())


def _log_history(case_id: str, user: User, action: str, **detail: Any) -> None:
    get_db().collection("cases").document(case_id).collection("history").add({
        "action": action, "by_uid": user.uid, "by_email": user.email,
        "at": _now(), **detail,
    })


# ── 사용자 ──────────────────────────────────────────────────
def list_reviewers(user: User) -> list[dict[str, Any]]:
    require(user.role == Role.ADMIN, "관리 담당자만 담당자 목록을 볼 수 있습니다.")
    docs = get_db().collection("users").where("role", "==", Role.REVIEWER).stream()
    return [{"uid": d.id, **d.to_dict()} for d in docs]


# ── 케이스 ──────────────────────────────────────────────────
def create_case(user: User, case_id: str, modality: str, exam_date: str,
                description: str = "") -> str:
    require(can_create_case(user), "케이스 등록 권한이 없습니다.")
    case_id = case_id.strip().upper()
    if not CASE_ID_PATTERN.match(case_id):
        raise ValidationError("케이스 ID는 영문 대문자·숫자·하이픈 3~32자여야 합니다. (예: MOCK-0001)")
    if modality not in MODALITIES:
        raise ValidationError("검사 구분을 선택하세요.")
    ref = get_db().collection("cases").document(case_id)
    try:
        ref.create({
            "case_id": case_id, "modality": modality, "exam_date": exam_date,
            "description": description, "status": Status.RECEIVED,
            "assignee_uid": None, "created_by": user.uid,
            "created_at": _now(), "updated_at": _now(), "is_mock": True,
        })
    except AlreadyExists:
        raise ValidationError(f"이미 존재하는 케이스 ID입니다: {case_id}")
    _log_history(case_id, user, "create")
    return case_id


def get_case(user: User, case_id: str) -> Case:
    doc = get_db().collection("cases").document(case_id).get()
    if not doc.exists:
        raise ValidationError(f"케이스를 찾을 수 없습니다: {case_id}")
    case = Case.from_dict(doc.to_dict())
    require_view(user, case)
    return case


def list_cases(user: User, status: str | None = None, modality: str | None = None,
               keyword: str = "") -> list[Case]:
    q = get_db().collection("cases")
    if user.role == Role.REVIEWER:  # 검토자는 본인 배정 케이스만 조회 (DB 쿼리 단계에서 제한)
        q = q.where("assignee_uid", "==", user.uid)
    if status:
        q = q.where("status", "==", status)
    if modality:
        q = q.where("modality", "==", modality)
    cases = [Case.from_dict(d.to_dict()) for d in q.stream()]
    if keyword:
        kw = keyword.lower()
        cases = [c for c in cases if kw in c.case_id.lower() or kw in c.description.lower()]
    cases = [c for c in cases if can_view_case(user, c)]
    return sorted(cases, key=lambda c: c.case_id)


# ── 상태·배정 (팀원1) ──────────────────────────────────────
def change_status(user: User, case_id: str, to_status: str, reason: str = "",
                  new_assignee_uid: str | None = None) -> None:
    db = get_db()
    ref = db.collection("cases").document(case_id)
    memo_count = len(list(db.collection("memos").where("case_id", "==", case_id).limit(1).stream()))

    @gcf.transactional
    def _tx(tx: gcf.Transaction) -> str:
        snap = ref.get(transaction=tx)
        if not snap.exists:
            raise ValidationError("케이스가 없습니다.")
        case = Case.from_dict(snap.to_dict())
        require_view(user, case)
        ctx = TransitionContext(new_assignee_uid=new_assignee_uid,
                                memo_count=memo_count, reason=reason)
        check_transition(user, case, to_status, ctx)  # 트랜잭션 안에서 '현재' 상태 기준 검사
        update: dict[str, Any] = {"status": to_status, "updated_at": _now()}
        if new_assignee_uid:
            update["assignee_uid"] = new_assignee_uid
        tx.update(ref, update)
        return case.status

    from_status = _tx(db.transaction())
    _log_history(case_id, user, "status_change", from_status=from_status,
                 to_status=to_status, reason=reason, assignee_uid=new_assignee_uid)


def list_history(user: User, case_id: str) -> list[dict[str, Any]]:
    get_case(user, case_id)
    docs = (get_db().collection("cases").document(case_id).collection("history")
            .order_by("at").stream())
    return [d.to_dict() for d in docs]


# ── 영상 (팀원2) ────────────────────────────────────────────
def add_image(user: User, case_id: str, filename: str, data: bytes,
              source: str = "") -> str:
    case = get_case(user, case_id)
    require_upload(user, case)
    decoded = validate_image_upload(filename, data)
    sha = hashlib.sha256(data).hexdigest()

    db = get_db()
    dup = db.collection("images").where("case_id", "==", case_id).where("sha256", "==", sha).limit(1).stream()
    if any(True for _ in dup):
        raise ValidationError("같은 영상이 이미 이 케이스에 등록되어 있습니다.")

    storage = _storage()
    ext = ".png" if decoded.format == "PNG" else ".jpg"
    path = storage.save(data, f"originals/{case_id}", ext)
    try:
        _ts, ref = db.collection("images").add({
            "case_id": case_id, "path": path, "filename": filename,
            "format": decoded.format, "width": decoded.width, "height": decoded.height,
            "size_bytes": decoded.size_bytes, "sha256": sha, "source": source,
            "uploaded_by": user.uid, "uploaded_at": _now(),
        })
    except Exception:
        storage.delete(path)  # 보상 처리: DB 기록 실패 시 파일 삭제로 불일치 방지
        raise
    _log_history(case_id, user, "image_upload", image_id=ref.id, filename=filename)
    return ref.id


def list_images(user: User, case_id: str) -> list[dict[str, Any]]:
    get_case(user, case_id)
    docs = get_db().collection("images").where("case_id", "==", case_id).stream()
    return sorted(({"id": d.id, **d.to_dict()} for d in docs), key=lambda x: x["uploaded_at"])


def load_image(user: User, image: dict[str, Any]) -> np.ndarray:
    get_case(user, image["case_id"])
    data = _storage().read(image["path"])
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)


# ── 처리 이력 (팀원4) ───────────────────────────────────────
def save_processing(user: User, image: dict[str, Any], request_id: str,
                    algorithm_key: str, params: dict[str, Any], roi: ROI | None,
                    result: np.ndarray, stats: dict[str, Any] | None) -> tuple[str, bool]:
    """처리 결과를 저장. request_id 를 문서 ID로 써서 중복 저장(연속 클릭)을 막습니다.

    Returns: (processing_id, created)  — created=False 면 이미 저장된 요청.
    """
    case = get_case(user, image["case_id"])
    require_process(user, case)
    algo = get_algorithm(algorithm_key)
    clean_params = algo.validate_params(params)
    if roi:
        validate_roi(roi, result.shape)

    db = get_db()
    ref = db.collection("processings").document(request_id)
    if ref.get().exists:
        return request_id, False

    ok, png = cv2.imencode(".png", result)
    if not ok:
        raise ValidationError("결과 영상을 인코딩하지 못했습니다.")
    storage = _storage()
    path = storage.save(png.tobytes(), f"results/{case.case_id}", ".png")
    try:
        ref.create({
            "case_id": case.case_id, "image_id": image["id"],
            "algorithm": algo.key, "algorithm_version": algo.version,
            "params": clean_params, "roi": roi.to_dict() if roi else None,
            "stats": stats, "result_path": path,
            "executed_by": user.uid, "executed_at": _now(),
        })
    except AlreadyExists:
        storage.delete(path)
        return request_id, False
    except Exception:
        storage.delete(path)
        raise
    _log_history(case.case_id, user, "process", processing_id=request_id, algorithm=algo.key)
    return request_id, True


def list_processings(user: User, case_id: str, image_id: str | None = None) -> list[dict[str, Any]]:
    get_case(user, case_id)
    q = get_db().collection("processings").where("case_id", "==", case_id)
    if image_id:
        q = q.where("image_id", "==", image_id)
    return sorted(({"id": d.id, **d.to_dict()} for d in q.stream()),
                  key=lambda x: x["executed_at"], reverse=True)


def load_result(user: User, processing: dict[str, Any]) -> np.ndarray:
    get_case(user, processing["case_id"])
    data = _storage().read(processing["result_path"])
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)


# ── 메모·리포트 (팀원4) ─────────────────────────────────────
def add_memo(user: User, case_id: str, content: str, kind: str = "memo",
             image_id: str | None = None, processing_id: str | None = None) -> str:
    case = get_case(user, case_id)
    require_memo(user, case)
    if not content.strip():
        raise ValidationError("내용을 입력하세요.")
    if kind not in ("memo", "report"):
        raise ValidationError("메모 종류가 올바르지 않습니다.")
    _ts, ref = get_db().collection("memos").add({
        "case_id": case_id, "kind": kind, "content": content.strip(),
        "image_id": image_id, "processing_id": processing_id,
        "author_uid": user.uid, "author_email": user.email,
        "created_at": _now(), "updated_at": _now(), "edits": [],
    })
    _log_history(case_id, user, "memo_add", memo_id=ref.id, kind=kind)
    return ref.id


def update_memo(user: User, memo_id: str, content: str) -> None:
    ref = get_db().collection("memos").document(memo_id)
    snap = ref.get()
    if not snap.exists:
        raise ValidationError("메모를 찾을 수 없습니다.")
    memo = snap.to_dict()
    case = get_case(user, memo["case_id"])
    require_memo(user, case)
    if memo["author_uid"] != user.uid and user.role != Role.ADMIN:
        raise PermissionDenied("본인이 작성한 메모만 수정할 수 있습니다.")
    ref.update({
        "content": content.strip(), "updated_at": _now(),
        # 변경 이력: 이전 내용을 남겨 완료 후 수정도 추적 가능하게
        "edits": gcf.ArrayUnion([{"prev": memo["content"], "by": user.uid, "at": _now()}]),
    })
    _log_history(case.case_id, user, "memo_edit", memo_id=memo_id)


def list_memos(user: User, case_id: str) -> list[dict[str, Any]]:
    get_case(user, case_id)
    docs = get_db().collection("memos").where("case_id", "==", case_id).stream()
    return sorted(({"id": d.id, **d.to_dict()} for d in docs), key=lambda x: x["created_at"])
