from pathlib import Path

import numpy as np

from orca_spectroscopy_tools.io import load_two_column_data, prepare_spectrum


def test_loader_ignores_header_comments_and_extra_columns(tmp_path: Path) -> None:
    path = tmp_path / "example.abs.dat"
    path.write_text(
        "header text\n# comment\n20000 1.5 9 8 7\n25000 2.0 4 3 2\n",
        encoding="utf-8",
    )

    data = load_two_column_data(path)

    assert data.shape == (2, 2)
    assert np.allclose(data[:, 1], [1.5, 2.0])


def test_prepare_spectrum_converts_and_sorts_wavenumber(tmp_path: Path) -> None:
    path = tmp_path / "example.cd.dat"
    path.write_text("25000 2\n20000 1\n", encoding="utf-8")

    spectrum = prepare_spectrum(path, axis_unit="cm-1")

    assert np.allclose(spectrum.wavelength_nm, [400.0, 500.0])
    assert np.allclose(spectrum.intensity, [2.0, 1.0])
    assert spectrum.kind == "cd"


def test_auto_detects_nm_filename(tmp_path: Path) -> None:
    path = tmp_path / "example.mcd.nm.dat"
    path.write_text("400 -1\n500 2\n", encoding="utf-8")

    spectrum = prepare_spectrum(path)

    assert np.allclose(spectrum.wavelength_nm, [400.0, 500.0])
