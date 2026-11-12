"""알고리즘·ROI 계산 테스트. 담당: 각 알고리즘 담당자"""
import numpy as np
import pytest

from pacs.processing import REGISTRY, ParamError, get_algorithm
from pacs.roi import compute_stats, histogram
from pacs.validation import ROI


def test_at_least_three_distinct_purposes():
    assert len({a.purpose for a in REGISTRY.values()}) >= 3


@pytest.mark.parametrize("key", list(REGISTRY))
def test_default_params_keep_shape_and_original(key, sample_image):
    before = sample_image.copy()
    out = get_algorithm(key).apply(sample_image)
    assert out.shape == sample_image.shape and out.dtype == np.uint8
    assert np.array_equal(sample_image, before), "원본을 변경하면 안 됩니다"


def test_param_out_of_range():
    with pytest.raises(ParamError, match="범위"):
        get_algorithm("clahe").validate_params({"clip_limit": 100})


def test_unknown_param_and_algorithm():
    with pytest.raises(ParamError):
        get_algorithm("clahe").validate_params({"foo": 1})
    with pytest.raises(ParamError):
        get_algorithm("nope")


def test_clahe_increases_contrast(sample_image):
    out = get_algorithm("clahe").apply(sample_image, {"clip_limit": 4.0, "tile_grid": 8})
    assert out.std() > sample_image.std()


def test_bilateral_reduces_noise_in_flat_area(sample_image):
    roi = ROI(2, 2, 16, 16)  # 원 바깥 평탄 영역
    out = get_algorithm("bilateral").apply(sample_image)
    assert compute_stats(out, roi)["std"] < compute_stats(sample_image, roi)["std"]


def test_otsu_is_binary(sample_image):
    out = get_algorithm("otsu").apply(sample_image)
    assert set(np.unique(out)) <= {0, 255}


def test_roi_stats_and_histogram(sample_image):
    roi = ROI(10, 10, 20, 30)
    s = compute_stats(sample_image, roi)
    assert s["area_px"] == 600
    assert histogram(sample_image, roi).sum() == 600
