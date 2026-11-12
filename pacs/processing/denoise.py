"""노이즈 제거: Bilateral 필터.

담당: 팀원3
원리: 공간 거리와 밝기 차이를 함께 가중치로 사용해,
      경계(밝기 차이가 큰 곳)는 보존하면서 평탄한 영역의 잡음을 줄입니다.
"""
import cv2
import numpy as np

from .base import Algorithm, Param


def _bilateral(img: np.ndarray, d: int, sigma_color: float, sigma_space: float) -> np.ndarray:
    return cv2.bilateralFilter(img, d, sigma_color, sigma_space)


BILATERAL = Algorithm(
    key="bilateral",
    label="Bilateral 필터",
    purpose="노이즈 제거·평활화",
    version="1.0",
    params=(
        Param("d", "이웃 지름(px)", "int", 9, 3, 15, 2),
        Param("sigma_color", "밝기 시그마", "float", 75.0, 5.0, 150.0, 5.0,
              help="클수록 밝기 차이가 큰 픽셀끼리도 섞여 경계가 흐려집니다."),
        Param("sigma_space", "공간 시그마", "float", 75.0, 5.0, 150.0, 5.0),
    ),
    func=_bilateral,
    owner="팀원3",
)
