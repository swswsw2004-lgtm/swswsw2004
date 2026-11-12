"""테스트 계정 생성 + 역할 등록.

사용 예:
  python scripts/create_user.py --key path/to/serviceAccount.json \
      --email reviewer1@test.com --password 'Passw0rd!' --role reviewer --name "검토자1"

역할: registrar(등록) / reviewer(검토) / admin(관리)
이미 있는 이메일이면 역할만 갱신합니다.
"""
import argparse

import firebase_admin
from firebase_admin import auth, credentials, firestore

ROLES = ("registrar", "reviewer", "admin")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="서비스 계정 JSON 경로 (커밋 금지)")
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--role", required=True, choices=ROLES)
    ap.add_argument("--name", default="")
    a = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(a.key))
    try:
        user = auth.get_user_by_email(a.email)
        print(f"기존 계정 사용: {user.uid}")
    except auth.UserNotFoundError:
        user = auth.create_user(email=a.email, password=a.password, display_name=a.name or None)
        print(f"계정 생성: {user.uid}")

    firestore.client().collection("users").document(user.uid).set(
        {"email": a.email, "role": a.role, "display_name": a.name}, merge=True)
    print(f"역할 등록 완료: {a.email} → {a.role}")


if __name__ == "__main__":
    main()
