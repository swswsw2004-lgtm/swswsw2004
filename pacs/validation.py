"""입력 검증: 업로드 파일, ROI.

담당: 팀원2 (파일 검증), 팀원3 (ROI 검증)
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

SUPPORTED_EXTENSIONS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20MB
MIN_SIDE = 16
MAX_SIDE = 8192


class ValidationError(ValueError):
    """사용자에게 그대로 보여줄 수 있는 입력 오류."""


@dataclass(frozen=True)
class DecodedImage:
    array: np.ndarray  # 2D uint8 그레이스케일
    format: str
    width: int
    height: int
    size_bytes: int


def validate_image_upload(filename: str, data: bytes) -> DecodedImage:
    """지원 형식인지, 실제로 열리는 이미지인지 확인하고 그레이스케일로 디코딩."""
    name = (filename or "").lower()
    ext = next((e for e in SUPPORTED_EXTENSIONS if name.endswith(e)), None)
    if ext is None:
        raise ValidationError(
            f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(sorted(set(SUPPORTED_EXTENSIONS.values())))}")
    if not data:
        raise ValidationError("빈 파일입니다.")
    if len(data) > MAX_FILE_BYTES:
        raise ValidationError(f"파일이 너무 큽니다. 최대 {MAX_FILE_BYTES // (1024 * 1024)}MB까지 가능합니다.")

    buf = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValidationError("이미지를 열 수 없습니다. 파일이 손상되었거나 확장자와 내용이 다릅니다.")
    h, w = img.shape[:2]
    if min(h, w) < MIN_SIDE or max(h, w) > MAX_SIDE:
        raise ValidationError(f"이미지 크기가 허용 범위({MIN_SIDE}~{MAX_SIDE}px)를 벗어났습니다: {w}x{h}")
    return DecodedImage(img, SUPPORTED_EXTENSIONS[ext], w, h, len(data))


@dataclass(frozen=True)
class ROI:
    x: int
    y: int
    w: int
    h: int

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


def validate_roi(roi: ROI, image_shape: tuple[int, ...], min_size: int = 2) -> ROI:
    """ROI가 영상 범위 안에 있고 최소 크기 이상인지 확인."""
    h_img, w_img = image_shape[:2]
    if roi.w < min_size or roi.h < min_size:
        raise ValidationError(f"ROI 크기는 최소 {min_size}x{min_size} 이상이어야 합니다.")
    if roi.x < 0 or roi.y < 0 or roi.x + roi.w > w_img or roi.y + roi.h > h_img:
        raise ValidationError(
            f"ROI가 영상 범위({w_img}x{h_img})를 벗어났습니다: x={roi.x}, y={roi.y}, w={roi.w}, h={roi.h}")
    return roi
