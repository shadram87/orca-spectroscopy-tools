"""Post-processing utilities for ORCA spectroscopy data."""

from .analysis import Extremum, find_extrema, subtract_spectra
from .io import Spectrum, load_two_column_data, prepare_spectrum

__all__ = [
    "Extremum",
    "Spectrum",
    "find_extrema",
    "load_two_column_data",
    "prepare_spectrum",
    "subtract_spectra",
]

__version__ = "0.1.0"
