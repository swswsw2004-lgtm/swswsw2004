"""입력 검증 테스트. 담당: 팀원2(파일), 팀원3(ROI)"""
import cv2
import numpy as np
import pytest

from pacs.validation import ROI, ValidationError, validate_image_upload, validate_roi


def _png(img):
    return cv2.imencode(".png", img)[1].tobytes()


def test_valid_png(sample_image):
    d = validate_image_upload("a.PNG", _png(sample_image))
    assert (d.width, d.height, d.format) == (128, 128, "PNG")


def test_color_jpeg_is_converted_to_gray():
    color = np.zeros((64, 64, 3), np.uint8)
    data = cv2.imencode(".jpg", color)[1].tobytes()
    assert validate_image_upload("x.jpg", data).array.ndim == 2


@pytest.mark.parametrize("name", ["a.gif", "a.dcm", "a", ""])
def test_unsupported_extension(name, sample_image):
    with pytest.raises(ValidationError, match="지원하지 않는"):
        validate_image_upload(name, _png(sample_image))


def test_corrupted_file():
    with pytest.raises(ValidationError, match="열 수 없습니다"):
        validate_image_upload("fake.png", b"not an image at all")


def test_empty_file():
    with pytest.raises(ValidationError, match="빈 파일"):
        validate_image_upload("a.png", b"")


def test_too_small_image():
    with pytest.raises(ValidationError, match="크기"):
        validate_image_upload("a.png", _png(np.zeros((4, 4), np.uint8)))


@pytest.mark.parametrize("roi", [ROI(-1, 0, 10, 10), ROI(120, 0, 10, 10), ROI(0, 0, 1, 10)])
def test_invalid_roi(roi):
    with pytest.raises(ValidationError):
        validate_roi(roi, (128, 128))


def test_valid_roi_on_edge():
    validate_roi(ROI(118, 118, 10, 10), (128, 128))
