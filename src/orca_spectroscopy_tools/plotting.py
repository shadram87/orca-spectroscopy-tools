"""Plotting functions for absorption, CD, and MCD spectra."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import matplotlib.pyplot as plt

from .analysis import Extremum
from .io import Spectrum


Y_LABELS = {
    "abs": "Absorption intensity (arb. units)",
    "cd": "CD intensity (arb. units)",
    "mcd": "MCD intensity (arb. units)",
    "spectrum": "Intensity (arb. units)",
}


def _save_figure(figure: plt.Figure, output_stem: Path, formats: Sequence[str]) -> list[Path]:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for extension in formats:
        output_path = output_stem.with_suffix(f".{extension}")
        kwargs: dict[str, object] = {"bbox_inches": "tight"}
        if extension == "png":
            kwargs["dpi"] = 300
        figure.savefig(output_path, **kwargs)
        saved.append(output_path)
    return saved


def plot_combined(
    spectra: Iterable[Spectrum],
    *,
    kind: str,
    wavelength_min: float,
    wavelength_max: float,
    output_stem: Path,
    formats: Sequence[str] = ("svg", "png"),
    line_width: float = 1.2,
    show: bool = False,
) -> list[Path]:
    """Plot several spectra of the same type in one figure."""
    figure, axis = plt.subplots(figsize=(10, 6))
    plotted = 0

    for spectrum in spectra:
        mask = (
            (spectrum.wavelength_nm >= wavelength_min)
            & (spectrum.wavelength_nm <= wavelength_max)
        )
        if not mask.any():
            continue
        axis.plot(
            spectrum.wavelength_nm[mask],
            spectrum.intensity[mask],
            linewidth=line_width,
            label=spectrum.label,
        )
        plotted += 1

    if plotted == 0:
        plt.close(figure)
        return []

    axis.axhline(0.0, linestyle="--", linewidth=0.8)
    axis.set_xlim(wavelength_min, wavelength_max)
    axis.set_xlabel("Wavelength (nm)")
    axis.set_ylabel(Y_LABELS.get(kind, Y_LABELS["spectrum"]))
    axis.set_title(f"Combined {kind.upper()} spectra")
    axis.legend(fontsize=8)
    figure.tight_layout()

    saved = _save_figure(figure, output_stem, formats)
    if show:
        plt.show()
    else:
        plt.close(figure)
    return saved


def plot_panel(
    spectra: Sequence[Spectrum],
    *,
    wavelength_min: float,
    wavelength_max: float,
    output_stem: Path,
    formats: Sequence[str] = ("svg", "png"),
    extrema: dict[str, Sequence[Extremum]] | None = None,
    show: bool = False,
) -> list[Path]:
    """Plot absorption, CD, and MCD spectra as aligned panels."""
    if not spectra:
        raise ValueError("At least one spectrum is required.")

    figure, axes = plt.subplots(
        len(spectra),
        1,
        sharex=True,
        figsize=(10, 2.8 * len(spectra)),
        squeeze=False,
    )

    for axis, spectrum in zip(axes[:, 0], spectra, strict=True):
        mask = (
            (spectrum.wavelength_nm >= wavelength_min)
            & (spectrum.wavelength_nm <= wavelength_max)
        )
        axis.plot(spectrum.wavelength_nm[mask], spectrum.intensity[mask], label=spectrum.label)
        axis.axhline(0.0, linestyle="--", linewidth=0.8)
        axis.set_ylabel(Y_LABELS.get(spectrum.kind, Y_LABELS["spectrum"]))
        axis.legend(fontsize=8)

        for item in (extrema or {}).get(spectrum.kind, []):
            if wavelength_min <= item.wavelength_nm <= wavelength_max:
                axis.plot(item.wavelength_nm, item.intensity, marker="o", linestyle="none")
                axis.annotate(
                    f"{item.wavelength_nm:.0f} nm",
                    (item.wavelength_nm, item.intensity),
                    xytext=(4, 4),
                    textcoords="offset points",
                    fontsize=7,
                )

    axes[-1, 0].set_xlabel("Wavelength (nm)")
    axes[-1, 0].set_xlim(wavelength_min, wavelength_max)
    figure.suptitle(spectra[0].label)
    figure.tight_layout()

    saved = _save_figure(figure, output_stem, formats)
    if show:
        plt.show()
    else:
        plt.close(figure)
    return saved
