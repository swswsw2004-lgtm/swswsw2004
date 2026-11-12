"""ROI 특징값 계산과 표시.

담당: 팀원3
"""
from __future__ import annotations

import cv2
import numpy as np

from .validation import ROI, validate_roi


def crop(img: np.ndarray, roi: ROI) -> np.ndarray:
    validate_roi(roi, img.shape)
    return img[roi.y:roi.y + roi.h, roi.x:roi.x + roi.w]


def compute_stats(img: np.ndarray, roi: ROI) -> dict[str, float]:
    """ROI 영역의 기본 통계. Firestore에 그대로 저장할 수 있게 float로 반환."""
    region = crop(img, roi).astype(np.float64)
    return {
        "mean": round(float(region.mean()), 4),
        "std": round(float(region.std()), 4),
        "var": round(float(region.var()), 4),
        "min": float(region.min()),
        "max": float(region.max()),
        "area_px": int(region.size),
    }


def histogram(img: np.ndarray, roi: ROI | None = None, bins: int = 256) -> np.ndarray:
    region = crop(img, roi) if roi else img
    hist, _ = np.histogram(region, bins=bins, range=(0, 256))
    return hist


def draw_roi(img: np.ndarray, roi: ROI, color=(255, 80, 80), thickness: int = 2) -> np.ndarray:
    """그레이스케일 영상 위에 ROI 사각형을 그린 RGB 영상 반환 (원본은 변경하지 않음)."""
    rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB) if img.ndim == 2 else img.copy()
    cv2.rectangle(rgb, (roi.x, roi.y), (roi.x + roi.w - 1, roi.y + roi.h - 1), color, thickness)
    return rgb
