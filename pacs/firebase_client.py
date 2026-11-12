"""Firebase Admin SDK 초기화 (서버 측). 앱 전체에서 한 번만 초기화합니다."""
from __future__ import annotations

from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore

from . import config


@lru_cache
def get_app() -> firebase_admin.App:
    if firebase_admin._apps:
        return firebase_admin.get_app()
    cred = credentials.Certificate(config.service_account_info())
    return firebase_admin.initialize_app(cred)


def get_db():
    get_app()
    return firestore.client()
