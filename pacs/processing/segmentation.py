"""영역 추출: Otsu 이진화.

담당: 팀원4
원리: 히스토그램을 두 클래스로 나눌 때 클래스 간 분산이 최대가 되는 임계값을
      자동으로 찾아 이진화합니다. 사전 블러로 잡음 영향을 줄일 수 있습니다.
"""
import cv2
import numpy as np

from .base import Algorithm, Param


def _otsu(img: np.ndarray, blur_ksize: int, invert: bool) -> np.ndarray:
    src = cv2.GaussianBlur(img, (blur_ksize, blur_ksize), 0) if blur_ksize > 1 else img
    mode = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _thr, out = cv2.threshold(src, 0, 255, mode + cv2.THRESH_OTSU)
    return out


OTSU = Algorithm(
    key="otsu",
    label="Otsu 이진화",
    purpose="영역·경계 추출",
    version="1.0",
    params=(
        Param("blur_ksize", "사전 블러 커널", "choice", 5, choices=(1, 3, 5, 7, 9),
              help="1이면 블러 없음. 클수록 잡음에 강하지만 작은 구조가 사라집니다."),
        Param("invert", "반전", "bool", False),
    ),
    func=_otsu,
    owner="팀원4",
)
