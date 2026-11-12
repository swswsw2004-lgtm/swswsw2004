"""케이스 상세: 상태 변경, 영상 등록, 이미지 뷰어, 영상처리·ROI, 메모·이력.

담당: 팀원1(상태 변경 영역), 팀원2(영상 등록), 팀원3(뷰어·ROI), 팀원4(처리 이력·메모)
화면이 커지면 섹션별로 views/sections/*.py 로 분리하세요.
"""
import uuid

import numpy as np
import pandas as pd
import streamlit as st

from pacs import repository as repo
from pacs.models import Status
from pacs.permissions import can_process_image, can_upload_image, can_write_memo
from pacs.processing import REGISTRY
from pacs.roi import compute_stats, draw_roi, histogram
from pacs.validation import ROI
from pacs.workflow import available_transitions

from .common import get_user, handle_errors, status_badge


# ── 상태 변경 (팀원1) ───────────────────────────────────────
def _status_section(user, case):
    st.markdown(f"### {case.case_id} {status_badge(case.status)}")
    st.caption(f"{case.modality} · 검사일 {case.exam_date} · {case.description}")
    actions = available_transitions(user, case)
    if not actions:
        return
    reason = st.text_input("사유 (보완 요청·완료 취소 시 필수)", key="status_reason")
    cols = st.columns(len(actions))
    for col, (to, rule) in zip(cols, actions):
        if to == Status.ASSIGNED:
            continue  # 배정은 '배정·진행 현황' 화면에서
        if col.button(rule.label, key=f"tr-{to}"):
            with handle_errors(success=f"상태 변경: {Status.LABELS[to]}"):
                repo.change_status(user, case.case_id, to, reason=reason)
                st.rerun()


# ── 영상 등록 (팀원2) ───────────────────────────────────────
def _upload_section(user, case):
    if not can_upload_image(user, case):
        return
    with st.expander("영상 등록 (PNG/JPEG)"):
        with st.form("upload", clear_on_submit=True):
            f = st.file_uploader("영상 파일", type=["png", "jpg", "jpeg"])
            source = st.text_input("데이터 출처 (공개 데이터셋 이름·라이선스)")
            ok = st.form_submit_button("등록")
        if ok and f is not None:
            with handle_errors(success="영상이 등록되었습니다."):
                repo.add_image(user, case.case_id, f.name, f.getvalue(), source)
                st.rerun()


# ── 뷰어 (팀원3) ────────────────────────────────────────────
def _view_window(img: np.ndarray, zoom: float, cx: float, cy: float) -> np.ndarray:
    """확대 배율과 중심점(0~1)으로 보여줄 영역을 잘라냄. 원본은 변경하지 않음."""
    h, w = img.shape[:2]
    vw, vh = max(1, int(w / zoom)), max(1, int(h / zoom))
    x0 = int(np.clip(cx * w - vw / 2, 0, w - vw))
    y0 = int(np.clip(cy * h - vh / 2, 0, h - vh))
    return img[y0:y0 + vh, x0:x0 + vw]


def _viewer_controls():
    if st.button("화면 초기화"):
        for k in ("zoom", "cx", "cy"):
            st.session_state.pop(k, None)
    c1, c2, c3 = st.columns(3)
    zoom = c1.slider("확대", 1.0, 8.0, 1.0, 0.5, key="zoom")
    cx = c2.slider("가로 이동", 0.0, 1.0, 0.5, 0.01, key="cx")
    cy = c3.slider("세로 이동", 0.0, 1.0, 0.5, 0.01, key="cy")
    return zoom, cx, cy


def _roi_controls(shape) -> ROI | None:
    h, w = shape[:2]
    use = st.checkbox("ROI 사용")
    if not use:
        return None
    c = st.columns(4)
    x = c[0].number_input("x", 0, w - 1, w // 4)
    y = c[1].number_input("y", 0, h - 1, h // 4)
    rw = c[2].number_input("너비", 2, w, max(2, w // 4))
    rh = c[3].number_input("높이", 2, h, max(2, h // 4))
    return ROI(int(x), int(y), int(rw), int(rh))


def _hist_chart(original, result, roi):
    df = pd.DataFrame({"원본": histogram(original, roi), "처리 결과": histogram(result, roi)})
    st.line_chart(df, height=200)


# ── 영상처리·이력 (팀원4) ───────────────────────────────────
def _param_inputs(algo):
    values = {}
    for p in algo.params:
        k = f"p-{algo.key}-{p.name}"
        if p.kind == "int":
            values[p.name] = st.slider(p.label, int(p.min), int(p.max), int(p.default), int(p.step or 1), key=k, help=p.help)
        elif p.kind == "float":
            values[p.name] = st.slider(p.label, float(p.min), float(p.max), float(p.default), float(p.step or 0.1), key=k, help=p.help)
        elif p.kind == "bool":
            values[p.name] = st.checkbox(p.label, p.default, key=k, help=p.help)
        else:
            values[p.name] = st.selectbox(p.label, p.choices, index=p.choices.index(p.default), key=k, help=p.help)
    return values


def _image_section(user, case):
    images = repo.list_images(user, case.case_id)
    if not images:
        st.info("등록된 영상이 없습니다.")
        return
    image = st.selectbox("영상 선택", images,
                         format_func=lambda i: f"{i['filename']} ({i['width']}x{i['height']}, {i['format']})")
    original = repo.load_image(user, image)

    left, right = st.columns([1, 2])
    with left:
        st.markdown("#### 처리 설정")
        algo_key = st.selectbox("알고리즘", list(REGISTRY), format_func=lambda k: f"{REGISTRY[k].label} · {REGISTRY[k].purpose}")
        algo = REGISTRY[algo_key]
        params = _param_inputs(algo)
        roi = _roi_controls(original.shape)

    result = None
    with handle_errors():
        result = algo.apply(original, params)

    with right:
        st.markdown("#### 뷰어 (원본 | 처리 결과)")
        zoom, cx, cy = _viewer_controls()
        a, b = st.columns(2)
        show_o = draw_roi(original, roi) if roi else original
        a.image(_view_window(show_o, zoom, cx, cy), caption="원본 (변경되지 않음)", width="stretch")
        if result is not None:
            show_r = draw_roi(result, roi) if roi else result
            b.image(_view_window(show_r, zoom, cx, cy), caption=f"{algo.label} 결과", width="stretch")

    if result is None:
        return

    stats = None
    with handle_errors():
        if roi:
            s_o, s_r = compute_stats(original, roi), compute_stats(result, roi)
            st.markdown("#### ROI 분석")
            st.dataframe(pd.DataFrame({"원본": s_o, "처리 결과": s_r}).T, width="stretch")
            stats = {"original": s_o, "result": s_r}
        _hist_chart(original, result, roi)

    # 중복 저장 방지: 화면 상태가 바뀔 때까지 같은 request_id 를 사용
    sig = (image["id"], algo_key, tuple(sorted(params.items())), roi)
    if st.session_state.get("req_sig") != sig:
        st.session_state["req_sig"] = sig
        st.session_state["req_id"] = uuid.uuid4().hex

    if can_process_image(user, case):
        if st.button("처리 결과 저장", type="primary"):
            with handle_errors():
                pid, created = repo.save_processing(user, image, st.session_state["req_id"],
                                                    algo_key, params, roi, result, stats)
                st.success("저장되었습니다." if created else "이미 저장된 결과입니다. (중복 저장 방지)")
    else:
        st.caption("결과 저장은 '검토 중' 상태에서 배정된 검토 담당자만 가능합니다.")

    with st.expander("이 영상의 처리 이력"):
        rows = repo.list_processings(user, case.case_id, image["id"])
        if rows:
            st.dataframe(pd.DataFrame([{
                "시간": r["executed_at"], "알고리즘": r["algorithm"], "버전": r["algorithm_version"],
                "파라미터": r["params"], "ROI": r["roi"], "실행자": r["executed_by"],
            } for r in rows]), width="stretch")
        else:
            st.caption("처리 이력이 없습니다.")


def _memo_section(user, case):
    st.markdown("#### 메모·리포트")
    for m in repo.list_memos(user, case.case_id):
        icon = "📝" if m["kind"] == "memo" else "📄"
        st.markdown(f"{icon} **{m['author_email']}** · {m['created_at']:%Y-%m-%d %H:%M}"
                    + (f" (수정 {len(m['edits'])}회)" if m["edits"] else ""))
        st.write(m["content"])
    if can_write_memo(user, case):
        with st.form("memo", clear_on_submit=True):
            kind = st.radio("종류", ["memo", "report"], horizontal=True,
                            format_func=lambda k: "검토 메모" if k == "memo" else "요약 리포트")
            content = st.text_area("내용")
            if st.form_submit_button("저장"):
                with handle_errors(success="저장되었습니다."):
                    repo.add_memo(user, case.case_id, content, kind)
                    st.rerun()


def _history_section(user, case):
    with st.expander("변경 이력"):
        rows = repo.list_history(user, case.case_id)
        st.dataframe(pd.DataFrame(rows), width="stretch")


def render():
    user = get_user()
    st.title("🩻 케이스 상세·뷰어")
    case_id = st.session_state.get("selected_case")
    if not case_id:
        st.info("업무 목록에서 케이스를 선택하세요.")
        return
    with handle_errors():
        case = repo.get_case(user, case_id)
        _status_section(user, case)
        _upload_section(user, case)
        st.divider()
        _image_section(user, case)
        st.divider()
        _memo_section(user, case)
        _history_section(user, case)
