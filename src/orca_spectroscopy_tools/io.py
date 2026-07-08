"""Input/output helpers for ORCA and orca_mapspc-style spectrum files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

AxisUnit = Literal["auto", "cm-1", "nm"]
SpectrumType = Literal["abs", "cd", "mcd"]


@dataclass(frozen=True)
class Spectrum:
    """A one-dimensional spectrum on a wavelength grid."""

    source: Path
    kind: str
    wavelength_nm: np.ndarray
    intensity: np.ndarray
    label: str

    def as_array(self) -> np.ndarray:
        """Return wavelength and intensity as a two-column array."""
        return np.column_stack((self.wavelength_nm, self.intensity))


def load_two_column_data(path: Path) -> np.ndarray:
    """Load the first two numerical columns from a text file.

    Blank lines, comment lines, and non-numerical header lines are ignored.
    Additional columns (for example polarized absorption components written by
    ``orca_mapspc``) are deliberately ignored by this first-version toolkit.
    """
    rows: list[tuple[float, float]] = []

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith(("#", "!", ";", "%")):
                continue

            fields = line.replace(",", " ").split()
            if len(fields) < 2:
                continue

            try:
                x_value = float(fields[0])
                intensity = float(fields[1])
            except ValueError:
                continue

            if np.isfinite(x_value) and np.isfinite(intensity):
                rows.append((x_value, intensity))

    if not rows:
        raise ValueError(f"No valid two-column numerical data found in {path}.")

    return np.asarray(rows, dtype=float)


def infer_axis_unit(path: Path, x_values: np.ndarray, requested: AxisUnit) -> Literal["cm-1", "nm"]:
    """Resolve whether the horizontal axis is wavenumber or wavelength."""
    if requested != "auto":
        return requested

    lower_name = path.name.lower()
    if ".nm." in lower_name or lower_name.endswith(".nm.dat"):
        return "nm"

    # UV/visible orca_mapspc files normally contain wavenumbers in the
    # thousands or tens of thousands of cm^-1. This fallback also makes plain
    # two-column wavelength files usable when their names do not contain 'nm'.
    median = float(np.median(np.abs(x_values)))
    return "cm-1" if median > 2_000.0 else "nm"


def wavenumber_to_wavelength(wavenumber_cm: np.ndarray) -> np.ndarray:
    """Convert wavenumber in cm^-1 to wavelength in nm."""
    if np.any(wavenumber_cm <= 0):
        raise ValueError("Wavenumbers must be greater than zero.")
    return 1.0e7 / wavenumber_cm


def spectrum_kind_from_name(path: Path) -> str:
    """Infer absorption, CD, or MCD from a conventional filename."""
    name = path.name.lower()
    for kind in ("mcd", "cd", "abs"):
        if f".{kind}." in name or name.endswith(f".{kind}.dat"):
            return kind
    return "spectrum"


def clean_label(path: Path, kind: str | None = None) -> str:
    """Create a readable label from a calculation filename."""
    label = path.name
    suffixes = (
        ".abs.nm.dat",
        ".cd.nm.dat",
        ".mcd.nm.dat",
        ".abs.dat",
        ".cd.dat",
        ".mcd.dat",
        ".dat",
        ".stk",
    )
    for suffix in suffixes:
        if label.lower().endswith(suffix):
            label = label[: -len(suffix)]
            break

    for token in (
        "TDDFT-CAM-B3LYP-",
        "CAM-B3LYP-",
        "-def2-SVP",
        "-Def2-SVP",
        "-def2",
        "-SVP",
        ".out",
    ):
        label = label.replace(token, "")

    label = label.replace("_", " ").strip("- ")
    return label or (kind or path.stem)


def prepare_spectrum(
    path: Path,
    *,
    axis_unit: AxisUnit = "auto",
    kind: str | None = None,
    label: str | None = None,
) -> Spectrum:
    """Load a spectrum and return it on an increasing wavelength grid."""
    raw = load_two_column_data(path)
    resolved_unit = infer_axis_unit(path, raw[:, 0], axis_unit)

    if resolved_unit == "cm-1":
        wavelength = wavenumber_to_wavelength(raw[:, 0])
    else:
        wavelength = raw[:, 0].copy()

    order = np.argsort(wavelength)
    wavelength = wavelength[order]
    intensity = raw[:, 1][order]

    resolved_kind = kind or spectrum_kind_from_name(path)
    return Spectrum(
        source=path,
        kind=resolved_kind,
        wavelength_nm=wavelength,
        intensity=intensity,
        label=label or clean_label(path, resolved_kind),
    )


def save_spectrum(spectrum: Spectrum, path: Path) -> None:
    """Write a spectrum as wavelength/intensity text data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(
        path,
        spectrum.as_array(),
        fmt="%.10g",
        header="Wavelength_nm Intensity",
        comments="# ",
    )


def discover_spectrum_files(input_dir: Path, kind: str) -> list[Path]:
    """Find raw and wavelength-converted files of one spectrum type."""
    candidates = list(input_dir.glob(f"*.{kind}.dat"))
    candidates.extend(input_dir.glob(f"*.{kind}.nm.dat"))
    return sorted({path for path in candidates if path.is_file()})
