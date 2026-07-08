"""Command-line interface for ORCA Spectroscopy Tools."""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import Sequence

from .analysis import find_extrema, subtract_spectra
from .io import (
    Spectrum,
    discover_spectrum_files,
    prepare_spectrum,
    save_spectrum,
)
from .plotting import plot_combined, plot_panel

LOGGER = logging.getLogger("orca_spectra")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orca-spectra",
        description=(
            "Convert, plot, compare, and analyse ORCA/orca_mapspc-style "
            "absorption, CD, and MCD spectrum files."
        ),
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed processing messages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plot_parser = subparsers.add_parser("plot", help="Create combined plots for a directory of spectra.")
    plot_parser.add_argument("input_dir", nargs="?", type=Path, default=Path.cwd())
    plot_parser.add_argument("--output-dir", type=Path, default=None)
    plot_parser.add_argument("--types", nargs="+", choices=("abs", "cd", "mcd"), default=("abs", "cd", "mcd"))
    plot_parser.add_argument("--x-unit", choices=("auto", "cm-1", "nm"), default="auto")
    plot_parser.add_argument("--wavelength-min", type=float, default=200.0)
    plot_parser.add_argument("--wavelength-max", type=float, default=800.0)
    plot_parser.add_argument("--formats", nargs="+", choices=("svg", "png", "pdf"), default=("svg", "png"))
    plot_parser.add_argument("--write-converted", action="store_true")
    plot_parser.add_argument("--find-peaks", action="store_true")
    plot_parser.add_argument("--min-peak-height", type=float, default=0.0)
    plot_parser.add_argument("--prominence", type=float, default=None)
    plot_parser.add_argument("--show", action="store_true")
    plot_parser.set_defaults(handler=run_plot)

    subtract_parser = subparsers.add_parser("subtract", help="Subtract a reference spectrum from a sample spectrum.")
    subtract_parser.add_argument("sample", type=Path)
    subtract_parser.add_argument("reference", type=Path)
    subtract_parser.add_argument("--output", type=Path, default=Path("subtracted.mcd.nm.dat"))
    subtract_parser.add_argument("--x-unit", choices=("auto", "cm-1", "nm"), default="auto")
    subtract_parser.add_argument("--plot", action="store_true", help="Also save a comparison figure.")
    subtract_parser.add_argument("--formats", nargs="+", choices=("svg", "png", "pdf"), default=("svg", "png"))
    subtract_parser.set_defaults(handler=run_subtract)

    panel_parser = subparsers.add_parser("panel", help="Create aligned absorption/CD/MCD panels.")
    panel_parser.add_argument("--abs", dest="abs_file", type=Path)
    panel_parser.add_argument("--cd", dest="cd_file", type=Path)
    panel_parser.add_argument("--mcd", dest="mcd_file", type=Path)
    panel_parser.add_argument("--output", type=Path, default=Path("spectra_panel"))
    panel_parser.add_argument("--x-unit", choices=("auto", "cm-1", "nm"), default="auto")
    panel_parser.add_argument("--wavelength-min", type=float, default=200.0)
    panel_parser.add_argument("--wavelength-max", type=float, default=800.0)
    panel_parser.add_argument("--formats", nargs="+", choices=("svg", "png", "pdf"), default=("svg", "png"))
    panel_parser.add_argument("--mark-peaks", action="store_true")
    panel_parser.add_argument("--min-peak-height", type=float, default=0.0)
    panel_parser.add_argument("--prominence", type=float, default=None)
    panel_parser.add_argument("--show", action="store_true")
    panel_parser.set_defaults(handler=run_panel)

    return parser


def _validate_range(minimum: float, maximum: float) -> None:
    if minimum >= maximum:
        raise ValueError("The minimum wavelength must be smaller than the maximum wavelength.")


def _write_peak_report(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ("file", "spectrum_type", "extremum", "wavelength_nm", "intensity", "prominence")
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_plot(args: argparse.Namespace) -> int:
    _validate_range(args.wavelength_min, args.wavelength_max)
    input_dir = args.input_dir.expanduser().resolve()
    if not input_dir.is_dir():
        raise ValueError(f"Input directory does not exist: {input_dir}")

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else input_dir / "results"
    )
    figure_dir = output_dir / "figures"
    converted_dir = output_dir / "converted"
    peak_rows: list[dict[str, object]] = []
    total_files = 0

    for kind in args.types:
        spectra: list[Spectrum] = []
        for path in discover_spectrum_files(input_dir, kind):
            try:
                spectrum = prepare_spectrum(path, axis_unit=args.x_unit, kind=kind)
            except (OSError, ValueError) as exc:
                LOGGER.warning("Skipping %s: %s", path.name, exc)
                continue

            spectra.append(spectrum)
            total_files += 1

            if args.write_converted and ".nm." not in path.name.lower():
                save_spectrum(spectrum, converted_dir / f"{path.stem}.nm.dat")

            if args.find_peaks:
                for item in find_extrema(
                    spectrum.wavelength_nm,
                    spectrum.intensity,
                    min_abs_height=args.min_peak_height,
                    prominence=args.prominence,
                ):
                    peak_rows.append(
                        {
                            "file": path.name,
                            "spectrum_type": kind,
                            "extremum": item.kind,
                            "wavelength_nm": f"{item.wavelength_nm:.6g}",
                            "intensity": f"{item.intensity:.6g}",
                            "prominence": f"{item.prominence:.6g}",
                        }
                    )

        saved = plot_combined(
            spectra,
            kind=kind,
            wavelength_min=args.wavelength_min,
            wavelength_max=args.wavelength_max,
            output_stem=figure_dir / f"all_{kind}_spectra",
            formats=args.formats,
            show=args.show,
        )
        for path in saved:
            LOGGER.info("Saved %s", path)

    if args.find_peaks:
        report_path = output_dir / "spectral_extrema.csv"
        _write_peak_report(peak_rows, report_path)
        LOGGER.info("Saved %s", report_path)

    if total_files == 0:
        LOGGER.error("No matching spectrum files were found in %s", input_dir)
        return 1
    return 0


def run_subtract(args: argparse.Namespace) -> int:
    sample = prepare_spectrum(args.sample, axis_unit=args.x_unit, kind="mcd")
    reference = prepare_spectrum(args.reference, axis_unit=args.x_unit, kind="mcd")
    wavelength, intensity = subtract_spectra(
        sample.wavelength_nm,
        sample.intensity,
        reference.wavelength_nm,
        reference.intensity,
    )
    difference = Spectrum(
        source=args.output,
        kind="mcd",
        wavelength_nm=wavelength,
        intensity=intensity,
        label=f"{sample.label} minus {reference.label}",
    )
    save_spectrum(difference, args.output)
    LOGGER.info("Saved %s", args.output)

    if args.plot:
        plot_combined(
            (sample, reference, difference),
            kind="mcd",
            wavelength_min=float(wavelength.min()),
            wavelength_max=float(wavelength.max()),
            output_stem=args.output.with_suffix("").with_name(args.output.stem + "_comparison"),
            formats=args.formats,
        )
    return 0


def run_panel(args: argparse.Namespace) -> int:
    _validate_range(args.wavelength_min, args.wavelength_max)
    requested = (("abs", args.abs_file), ("cd", args.cd_file), ("mcd", args.mcd_file))
    spectra = [
        prepare_spectrum(path, axis_unit=args.x_unit, kind=kind)
        for kind, path in requested
        if path is not None
    ]
    if not spectra:
        raise ValueError("Provide at least one of --abs, --cd, or --mcd.")

    extrema = None
    if args.mark_peaks:
        extrema = {
            spectrum.kind: find_extrema(
                spectrum.wavelength_nm,
                spectrum.intensity,
                min_abs_height=args.min_peak_height,
                prominence=args.prominence,
            )
            for spectrum in spectra
        }

    plot_panel(
        spectra,
        wavelength_min=args.wavelength_min,
        wavelength_max=args.wavelength_max,
        output_stem=args.output,
        formats=args.formats,
        extrema=extrema,
        show=args.show,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    try:
        return int(args.handler(args))
    except (OSError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return 2
