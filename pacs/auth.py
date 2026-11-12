"""Firebase Authentication 로그인.

Python에는 Firebase '클라이언트' 로그인 SDK가 없으므로
  1) Identity Toolkit REST API 로 이메일/비밀번호 로그인 → ID 토큰 발급
  2) firebase-admin 으로 ID 토큰 검증 (매 요청마다)
  3) Firestore users/{uid} 문서에서 역할(role) 조회
방식을 사용합니다.

담당: 팀원1
"""
from __future__ import annotations

from dataclasses import dataclass

import requests
from firebase_admin import auth as admin_auth

from . import config
from .firebase_client import get_app, get_db
from .models import Role, User

SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
REFRESH_URL = "https://securetoken.googleapis.com/v1/token"

_ERROR_MESSAGES = {
    "EMAIL_NOT_FOUND": "이메일 또는 비밀번호가 올바르지 않습니다.",
    "INVALID_PASSWORD": "이메일 또는 비밀번호가 올바르지 않습니다.",
    "INVALID_LOGIN_CREDENTIALS": "이메일 또는 비밀번호가 올바르지 않습니다.",
    "USER_DISABLED": "비활성화된 계정입니다.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "로그인 시도가 너무 많습니다. 잠시 후 다시 시도하세요.",
}


class AuthError(Exception):
    pass


@dataclass
class Session:
    id_token: str
    refresh_token: str
    uid: str


def sign_in(email: str, password: str) -> Session:
    try:
        r = requests.post(
            SIGN_IN_URL,
            params={"key": config.firebase_web_api_key()},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=10,
        )
    except requests.RequestException as e:
        raise AuthError("인증 서버에 연결할 수 없습니다.") from e
    if r.status_code != 200:
        code = r.json().get("error", {}).get("message", "")
        raise AuthError(_ERROR_MESSAGES.get(code.split(" ")[0], f"로그인 실패: {code}"))
    data = r.json()
    return Session(data["idToken"], data["refreshToken"], data["localId"])


def refresh(session: Session) -> Session:
    r = requests.post(
        REFRESH_URL,
        params={"key": config.firebase_web_api_key()},
        data={"grant_type": "refresh_token", "refresh_token": session.refresh_token},
        timeout=10,
    )
    if r.status_code != 200:
        raise AuthError("로그인이 만료되었습니다. 다시 로그인하세요.")
    d = r.json()
    return Session(d["id_token"], d["refresh_token"], d["user_id"])


def verify(session: Session) -> tuple[User, Session]:
    """토큰을 검증하고 (필요하면 갱신) 역할 정보를 담은 User를 반환."""
    get_app()
    try:
        decoded = admin_auth.verify_id_token(session.id_token)
    except admin_auth.ExpiredIdTokenError:
        session = refresh(session)
        decoded = admin_auth.verify_id_token(session.id_token)
    except Exception as e:
        raise AuthError("유효하지 않은 로그인 정보입니다. 다시 로그인하세요.") from e

    uid = decoded["uid"]
    doc = get_db().collection("users").document(uid).get()
    if not doc.exists:
        raise AuthError("역할이 등록되지 않은 계정입니다. 관리자에게 문의하세요.")
    profile = doc.to_dict()
    role = profile.get("role")
    if role not in Role.ALL:
        raise AuthError(f"알 수 없는 역할입니다: {role}")
    user = User(uid=uid, email=decoded.get("email", ""), role=role,
                display_name=profile.get("display_name", ""))
    return user, session
