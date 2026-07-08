import numpy as np
import pytest

from orca_spectroscopy_tools.analysis import find_extrema, subtract_spectra


def test_find_extrema_detects_positive_and_negative_features() -> None:
    x = np.arange(7.0)
    y = np.array([0.0, 1.0, 0.0, -2.0, 0.0, 3.0, 0.0])

    extrema = find_extrema(x, y, min_abs_height=0.5)

    assert [(item.kind, item.wavelength_nm) for item in extrema] == [
        ("maximum", 1.0),
        ("minimum", 3.0),
        ("maximum", 5.0),
    ]


def test_subtract_interpolates_reference_grid() -> None:
    sample_x = np.array([400.0, 450.0, 500.0])
    sample_y = np.array([3.0, 4.0, 5.0])
    ref_x = np.array([400.0, 500.0])
    ref_y = np.array([1.0, 3.0])

    x, difference = subtract_spectra(sample_x, sample_y, ref_x, ref_y)

    assert np.allclose(x, sample_x)
    assert np.allclose(difference, [2.0, 2.0, 2.0])


def test_subtract_rejects_non_overlapping_spectra() -> None:
    with pytest.raises(ValueError, match="do not overlap"):
        subtract_spectra(
            np.array([300.0, 350.0]),
            np.array([1.0, 2.0]),
            np.array([400.0, 450.0]),
            np.array([1.0, 2.0]),
        )
