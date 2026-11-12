"""명암·분포 조정: CLAHE (Contrast Limited Adaptive Histogram Equalization).

담당: 팀원2
원리: 영상을 타일로 나눠 각 타일에서 히스토그램 평활화를 하되,
      clip limit으로 히스토그램 상한을 제한해 잡음 증폭을 억제합니다.
"""
import cv2
import numpy as np

from .base import Algorithm, Param


def _clahe(img: np.ndarray, clip_limit: float, tile_grid: int) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    return clahe.apply(img)


CLAHE = Algorithm(
    key="clahe",
    label="CLAHE (적응형 히스토그램 평활화)",
    purpose="명암·분포 조정",
    version="1.0",
    params=(
        Param("clip_limit", "Clip limit", "float", 2.0, 0.5, 10.0, 0.5,
              help="클수록 대비가 강해지지만 잡음도 함께 강조됩니다."),
        Param("tile_grid", "타일 개수(한 변)", "int", 8, 2, 16, 1,
              help="작을수록 전역적, 클수록 국소적으로 대비를 조정합니다."),
    ),
    func=_clahe,
    owner="팀원2",
)
