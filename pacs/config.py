"""설정값 로딩. 비밀값은 .streamlit/secrets.toml (Git 제외)에서 읽습니다."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any


@lru_cache
def _secrets() -> dict[str, Any]:
    try:
        import streamlit as st
        return dict(st.secrets)
    except Exception:
        return {}


def get(key: str, default: Any = None) -> Any:
    """환경변수 → secrets.toml → 기본값 순으로 조회."""
    env = os.environ.get(key.upper())
    if env is not None:
        return env
    return _secrets().get(key, default)


def firebase_web_api_key() -> str:
    key = get("firebase_web_api_key")
    if not key:
        raise RuntimeError("firebase_web_api_key 가 설정되지 않았습니다. README의 설정 방법을 확인하세요.")
    return key


def storage_dir() -> str:
    return get("storage_dir", "./data/storage")


def service_account_info() -> dict[str, Any]:
    info = _secrets().get("firebase_service_account")
    if not info:
        raise RuntimeError("[firebase_service_account] 가 secrets.toml 에 없습니다.")
    return dict(info)
