"""Firebase 서비스 계정 JSON + 웹 API 키 → .streamlit/secrets.toml 생성.

사용 예 (저장소 폴더에서):
  uv run python scripts/make_secrets.py --key serviceAccount.json --api-key AIza...

이미 secrets.toml 이 있으면 덮어쓰지 않습니다. (--force 로 덮어쓰기)
"""
import argparse
import json
from pathlib import Path

REQUIRED = ("type", "project_id", "private_key", "client_email")


def toml_str(value) -> str:
    # JSON 문자열 표기는 TOML 기본 문자열과 호환됩니다 (\n, \uXXXX 이스케이프 포함)
    return json.dumps(str(value))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="Firebase 서비스 계정 JSON 파일 경로")
    ap.add_argument("--api-key", required=True, help="Firebase 웹 API 키 (AIza 로 시작)")
    ap.add_argument("--storage-dir", default="./data/storage")
    ap.add_argument("--out", default=".streamlit/secrets.toml")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    info = json.loads(Path(a.key).read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in info]
    if missing:
        raise SystemExit(f"서비스 계정 JSON이 아닌 것 같습니다. 없는 항목: {missing}")
    if not a.api_key.startswith("AIza"):
        raise SystemExit("웹 API 키는 보통 'AIza'로 시작합니다. 값을 다시 확인하세요.")

    out = Path(a.out)
    if out.exists() and not a.force:
        raise SystemExit(f"{out} 가 이미 있습니다. 덮어쓰려면 --force 를 붙이세요.")

    lines = [
        "# scripts/make_secrets.py 로 생성됨 — 절대 커밋하지 마세요",
        f"firebase_web_api_key = {toml_str(a.api_key)}",
        f"storage_dir = {toml_str(a.storage_dir)}",
        "",
        "[firebase_service_account]",
        *(f"{k} = {toml_str(v)}" for k, v in info.items()),
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"생성 완료: {out}  (프로젝트: {info['project_id']})")


if __name__ == "__main__":
    main()
