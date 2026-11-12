"""알고리즘 공통 인터페이스: 파라미터 정의·검증과 실행."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from ..validation import ValidationError


class ParamError(ValidationError):
    """잘못된 처리 설정값."""


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    kind: str  # "int" | "float" | "bool" | "choice"
    default: Any
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: tuple[Any, ...] = ()
    help: str = ""

    def coerce(self, value: Any) -> Any:
        try:
            if self.kind == "int":
                v = int(value)
            elif self.kind == "float":
                v = float(value)
            elif self.kind == "bool":
                v = bool(value)
            else:
                v = value
        except (TypeError, ValueError):
            raise ParamError(f"'{self.label}' 값이 올바르지 않습니다: {value!r}")
        if self.kind in ("int", "float"):
            if self.min is not None and v < self.min or self.max is not None and v > self.max:
                raise ParamError(f"'{self.label}'은(는) {self.min}~{self.max} 범위여야 합니다. (입력: {v})")
        if self.kind == "choice" and v not in self.choices:
            raise ParamError(f"'{self.label}'은(는) {self.choices} 중 하나여야 합니다.")
        return v


@dataclass(frozen=True)
class Algorithm:
    key: str
    label: str
    purpose: str          # 처리 목적 (명암 조정 / 노이즈 제거 / 영역 추출 ...)
    version: str          # 결과 재현용. 구현을 바꾸면 버전을 올리세요.
    params: tuple[Param, ...]
    func: Callable[..., np.ndarray]
    description: str = ""
    owner: str = ""       # 담당 팀원 (보고서 개인 기여용)
    extra: dict[str, Any] = field(default_factory=dict)

    def defaults(self) -> dict[str, Any]:
        return {p.name: p.default for p in self.params}

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        unknown = set(params) - {p.name for p in self.params}
        if unknown:
            raise ParamError(f"알 수 없는 설정값: {', '.join(sorted(unknown))}")
        return {p.name: p.coerce(params.get(p.name, p.default)) for p in self.params}

    def apply(self, img: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
        if img is None or img.ndim != 2 or img.dtype != np.uint8:
            raise ParamError("입력 영상은 2차원 uint8 그레이스케일이어야 합니다.")
        clean = self.validate_params(params or {})
        out = self.func(img, **clean)
        assert out.shape == img.shape and out.dtype == np.uint8, "알고리즘 출력 형식 오류"
        return out
