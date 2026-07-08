"""Numerical analysis of one-dimensional spectra."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks


@dataclass(frozen=True)
class Extremum:
    """A detected spectral maximum or minimum."""

    wavelength_nm: float
    intensity: float
    kind: str
    prominence: float


def find_extrema(
    wavelength_nm: np.ndarray,
    intensity: np.ndarray,
    *,
    min_abs_height: float = 0.0,
    prominence: float | None = None,
    distance: int | None = None,
) -> list[Extremum]:
    """Find positive maxima and negative minima using SciPy peak detection."""
    if wavelength_nm.shape != intensity.shape:
        raise ValueError("Wavelength and intensity arrays must have the same shape.")
    if wavelength_nm.ndim != 1:
        raise ValueError("Spectrum arrays must be one-dimensional.")
    if len(wavelength_nm) < 3:
        return []
    if min_abs_height < 0:
        raise ValueError("min_abs_height must be non-negative.")

    maxima, max_properties = find_peaks(
        intensity,
        height=min_abs_height if min_abs_height > 0 else None,
        prominence=prominence,
        distance=distance,
    )
    minima, min_properties = find_peaks(
        -intensity,
        height=min_abs_height if min_abs_height > 0 else None,
        prominence=prominence,
        distance=distance,
    )

    max_prominences = max_properties.get("prominences", np.zeros(len(maxima)))
    min_prominences = min_properties.get("prominences", np.zeros(len(minima)))

    extrema = [
        Extremum(
            wavelength_nm=float(wavelength_nm[index]),
            intensity=float(intensity[index]),
            kind="maximum",
            prominence=float(max_prominences[position]),
        )
        for position, index in enumerate(maxima)
        if intensity[index] > 0
    ]
    extrema.extend(
        Extremum(
            wavelength_nm=float(wavelength_nm[index]),
            intensity=float(intensity[index]),
            kind="minimum",
            prominence=float(min_prominences[position]),
        )
        for position, index in enumerate(minima)
        if intensity[index] < 0
    )
    return sorted(extrema, key=lambda item: item.wavelength_nm)


def subtract_spectra(
    sample_wavelength_nm: np.ndarray,
    sample_intensity: np.ndarray,
    reference_wavelength_nm: np.ndarray,
    reference_intensity: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Subtract a reference spectrum after interpolation onto the sample grid.

    Only the overlapping wavelength interval is returned. This avoids the
    unsafe assumption that independently generated spectra have identical
    grid lengths and wavelength points.
    """
    if sample_wavelength_nm.shape != sample_intensity.shape:
        raise ValueError("Sample wavelength and intensity arrays must match.")
    if reference_wavelength_nm.shape != reference_intensity.shape:
        raise ValueError("Reference wavelength and intensity arrays must match.")

    sample_order = np.argsort(sample_wavelength_nm)
    reference_order = np.argsort(reference_wavelength_nm)
    sample_x = sample_wavelength_nm[sample_order]
    sample_y = sample_intensity[sample_order]
    reference_x = reference_wavelength_nm[reference_order]
    reference_y = reference_intensity[reference_order]

    lower = max(float(sample_x.min()), float(reference_x.min()))
    upper = min(float(sample_x.max()), float(reference_x.max()))
    if lower >= upper:
        raise ValueError("The sample and reference spectra do not overlap.")

    mask = (sample_x >= lower) & (sample_x <= upper)
    x_common = sample_x[mask]
    y_reference = np.interp(x_common, reference_x, reference_y)
    return x_common, sample_y[mask] - y_reference
