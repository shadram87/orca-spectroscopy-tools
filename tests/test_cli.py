from pathlib import Path

from orca_spectroscopy_tools.cli import main


def test_plot_command_creates_figure_and_peak_report(tmp_path: Path) -> None:
    (tmp_path / "molecule.cd.dat").write_text(
        "20000 0\n22222.222 1\n25000 0\n28571.429 -1\n33333.333 0\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "plot",
            str(tmp_path),
            "--types",
            "cd",
            "--formats",
            "png",
            "--find-peaks",
            "--wavelength-min",
            "300",
            "--wavelength-max",
            "500",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "results/figures/all_cd_spectra.png").exists()
    assert (tmp_path / "results/spectral_extrema.csv").exists()
