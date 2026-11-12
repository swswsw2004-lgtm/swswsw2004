"""교육용 웹 PACS 핵심 패키지.

- 순수 로직(models, permissions, workflow, validation, processing, roi)은
  Firebase·Streamlit 없이 import 가능하도록 유지합니다. (pytest 대상)
- Firebase 연동(auth, firebase_client, repository)과 저장소(storage)는 별도 모듈입니다.
"""
