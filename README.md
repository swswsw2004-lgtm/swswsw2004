# 🩻 교육용 웹 PACS (초급프로젝트 PBL Term Project)

공개 영상과 **모의 케이스**로 동작하는 교육용 웹 PACS 프로토타입입니다.
영상 저장·검색·조회, 이미지 뷰어, 영상처리 알고리즘 3종 + ROI 분석, 검토 업무 흐름, 메모·리포트·이력, 팀 특화 기능을 제공합니다.

> ⚠️ 실제 환자 정보는 사용하지 않습니다. 모든 분석 수치는 교육용 결과이며 진단·임상 성능을 의미하지 않습니다.

| 항목 | 내용 |
|---|---|
| 개발 | Python 3.11+ · Streamlit |
| 로그인 | Firebase Authentication (이메일/비밀번호) |
| DB | Cloud Firestore |
| 영상 파일 | JCloud 영구 저장 디렉터리 (`storage_dir`) |
| 배포 | JCloud |
| 지원 형식 | PNG, JPEG (그레이스케일로 변환해 처리) · DICOM 미지원 |

## 폴더 구조

```
app.py                  Streamlit 진입점 (로그인 확인, 역할별 메뉴)
pacs/                   핵심 로직
  models.py             역할·상태 상수, User/Case 모델
  permissions.py        역할·담당 범위별 권한 검사
  workflow.py           상태 전이 규칙 (상태전이도의 코드 버전)
  validation.py         업로드 파일·ROI 입력 검증
  roi.py                ROI 통계·히스토그램
  processing/           영상처리 알고리즘 (CLAHE, Bilateral, Otsu)
  storage.py            영상 파일 저장 (원본 덮어쓰기 금지)
  auth.py               Firebase 로그인·토큰 검증
  repository.py         Firestore 데이터 접근 (모든 함수에서 권한 검사)
views/                  화면 (업무 목록, 케이스 등록·상세·뷰어, 배정 현황)
tests/                  pytest 자동화 테스트
scripts/create_user.py  테스트 계정 생성·역할 등록
deploy/pacs.service     JCloud 상시 실행용 systemd 예시
docs/                   설계 문서, 협업 규칙, 기여 기록
firestore.rules         Firestore 보안 규칙 (클라이언트 직접 접근 차단)
```

## 1. 설치

이 저장소는 [uv](https://docs.astral.sh/uv/)로 의존성을 관리합니다.

```bash
git clone https://github.com/swswsw2004-lgtm/swswsw2004.git && cd swswsw2004
uv sync                          # .venv 생성 + 의존성 설치 (pyproject.toml / uv.lock 기준)
```

uv가 없는 환경에서는 `python -m venv .venv && pip install -r requirements.txt` 로도 설치할 수 있습니다.
의존성을 추가할 때는 `uv add 패키지명` 후, `uv export --no-dev --no-hashes --format requirements-txt -o requirements.txt` 로 requirements.txt 도 갱신해 주세요.

## 2. Firebase 설정 (팀에서 1회)

1. [Firebase 콘솔](https://console.firebase.google.com)에서 프로젝트 생성
2. **Authentication** → 로그인 방법 → **이메일/비밀번호** 사용 설정
3. **Firestore Database** 생성 → 규칙 탭에 `firestore.rules` 내용 붙여넣기 (또는 `firebase deploy --only firestore`)
4. 프로젝트 설정 → 일반 → **웹 API 키** 복사
5. 프로젝트 설정 → 서비스 계정 → **새 비공개 키 생성** (JSON 다운로드, **절대 커밋 금지**)
6. `.streamlit/secrets.toml.example` 을 `.streamlit/secrets.toml` 로 복사하고 4·5번 값을 채움
   - 비밀키는 팀 메신저 등 저장소 밖으로만 공유하세요.

## 3. 테스트 계정 만들기

```bash
uv run python scripts/create_user.py --key serviceAccount.json --email admin1@test.com    --password '...' --role admin     --name 관리자1
uv run python scripts/create_user.py --key serviceAccount.json --email reg1@test.com      --password '...' --role registrar --name 등록자1
uv run python scripts/create_user.py --key serviceAccount.json --email reviewer1@test.com --password '...' --role reviewer  --name 검토자1
```

테스트 계정 비밀번호는 저장소에 적지 말고 LMS 제출란에만 작성합니다.

## 4. 로컬 실행 · 테스트

```bash
uv run streamlit run app.py   # http://localhost:8501
uv run pytest -q              # Firebase 없이 실행되는 단위 테스트
```

## 5. 시연 흐름

1. **등록자** 로그인 → 케이스 등록(`MOCK-0001`) → 영상 업로드(출처 기입)
2. **관리자** 로그인 → 배정·진행 현황 → 검토자 배정
3. **검토자** 로그인 → 업무 목록 → 케이스 열기 → 검토 시작
4. 알고리즘·파라미터 조절 → ROI 지정 → 원본/결과 비교 → 결과 저장
5. 메모·리포트 작성 → 검토 완료 → 완료된 업무 탭에서 다시 조회

## 6. JCloud 배포

```bash
# VM 접속 후
git clone https://github.com/swswsw2004-lgtm/swswsw2004.git && cd swswsw2004
uv sync && source .venv/bin/activate     # 또는 pip install -r requirements.txt
# .streamlit/secrets.toml 생성 (storage_dir 는 영구 저장 디스크 경로로)
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

- 상시 실행: `deploy/pacs.service` 참고 (systemd)
- 방화벽/보안 그룹에서 8501 포트 허용
- **앱 재시작 후에도 영상·기록이 다시 조회되는지 반드시 확인**
- 제출 시 `git rev-parse HEAD` 의 커밋과 배포된 버전이 같아야 합니다.

## 7. 데이터 출처

`docs/data_sources.md` 에 사용한 공개 데이터셋의 이름·URL·라이선스·이용 조건을 기록합니다.

## 8. AI·외부 자료 활용

초기 저장소 구조는 AI(Claude)의 도움을 받아 작성했으며, 이후 팀원이 직접 수정·검증한 내용은 각 PR과 `docs/contributions.md` 에 기록합니다.
