"""영상처리 알고리즘 레지스트리.

새 알고리즘 추가 방법:
  1) processing/ 아래에 모듈을 만들고 Algorithm 객체를 정의
  2) 아래 REGISTRY 에 등록
  3) tests/test_processing.py 에 테스트 추가

주의: 같은 알고리즘의 파라미터만 바꾼 것은 1종으로 셉니다.
"""
from __future__ import annotations

from .base import Algorithm, Param, ParamError
from .contrast import CLAHE
from .denoise import BILATERAL
from .segmentation import OTSU

REGISTRY: dict[str, Algorithm] = {a.key: a for a in (CLAHE, BILATERAL, OTSU)}


def get_algorithm(key: str) -> Algorithm:
    if key not in REGISTRY:
        raise ParamError(f"알 수 없는 알고리즘입니다: {key}")
    return REGISTRY[key]


__all__ = ["Algorithm", "Param", "ParamError", "REGISTRY", "get_algorithm"]
