"""영상 파일 저장소.

DB(Firestore)에는 파일 '위치'와 메타데이터만, 실제 파일은 여기에 저장합니다.
기본 구현은 JCloud의 영구 저장 디렉터리(STORAGE_DIR)를 사용합니다.
Firebase Storage로 바꾸려면 같은 메서드(save/read/delete)를 가진 클래스를 만들면 됩니다.

담당: 팀원2
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path


class StorageError(Exception):
    pass


class LocalStorage:
    def __init__(self, base_dir: str | os.PathLike):
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _abs(self, rel_path: str) -> Path:
        p = (self.base / rel_path).resolve()
        if self.base not in p.parents:
            raise StorageError("잘못된 파일 경로입니다.")
        return p

    def save(self, data: bytes, folder: str, ext: str) -> str:
        """파일을 새 이름으로 저장하고 상대 경로를 반환. 기존 파일은 절대 덮어쓰지 않음."""
        ext = ext if ext.startswith(".") else f".{ext}"
        rel = f"{folder}/{uuid.uuid4().hex}{ext}"
        dst = self._abs(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        try:
            tmp.write_bytes(data)
            os.replace(tmp, dst)  # 원자적 이동: 쓰다 만 파일이 남지 않게
        except OSError as e:
            tmp.unlink(missing_ok=True)
            raise StorageError(f"파일 저장 실패: {e}") from e
        return rel

    def read(self, rel_path: str) -> bytes:
        p = self._abs(rel_path)
        if not p.exists():
            raise StorageError(f"파일을 찾을 수 없습니다: {rel_path}")
        return p.read_bytes()

    def delete(self, rel_path: str) -> None:
        """보상 처리용: DB 기록 실패 시 방금 저장한 파일을 삭제."""
        self._abs(rel_path).unlink(missing_ok=True)

    def exists(self, rel_path: str) -> bool:
        return self._abs(rel_path).exists()
