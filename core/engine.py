"""
core/engine.py
==============
Centralized interface for the Fayda conversion engine.

This file serves as the abstraction layer between the Django application
and the underlying conversion engine (`fayda_converter_v2.py`). It has been
updated to support destination paste overrides (output_zones) required by 
the Field Adjustment Studio workspace.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Tuple, Dict, Any, Optional

from core.exceptions import ConversionFailedError, UnsupportedFileTypeError
from core.constants import LANDSCAPE_W, LANDSCAPE_H, APPROACH_ONE

logger = logging.getLogger(__name__)


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ConversionResult:
    """Structured result returned by run_conversion()."""
    output_bytes: bytes
    width: int
    height: int
    approach: str
    # Note: populated with (0,0) if engine metadata extraction is not supported
    original_size_one: Tuple[int, int] = (0, 0)
    original_size_two: Tuple[int, int] = (0, 0)


# ─── Private Helpers ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_engine():
    """Lazy-load the conversion engine and cache the reference."""
    try:
        from fayda_converter_v2 import convert_bytes as _convert_bytes
        return _convert_bytes
    except ImportError as e:
        raise ImportError(
            "fayda_converter_v2.py not found. Ensure it exists in the project root."
        ) from e


def _invoke_engine(
    file_bytes_one: bytes,
    filename_one: str,
    file_bytes_two: bytes,
    filename_two: str,
    approach: str,
    watermark: bool,
    width: int,
    height: int,
    custom_zones: Optional[Dict[str, Any]] = None,
    output_zones: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Private internal helper to unify engine calls and exception handling."""
    engine_func = _get_engine()
    
    logger.info(
        "Engine: starting conversion | approach=%s | file1=%s (%d bytes) | file2=%s (%d bytes) | custom_zones=%s | output_zones=%s",
        approach, filename_one, len(file_bytes_one), filename_two, len(file_bytes_two), 
        "Yes" if custom_zones else "No", "Yes" if output_zones else "No"
    )

    try:
        output = engine_func(
            file_bytes_one=file_bytes_one,
            filename_one=filename_one,
            file_bytes_two=file_bytes_two,
            filename_two=filename_two,
            approach=approach,
            watermark=watermark,
            width=width,
            height=height,
            custom_zones=custom_zones,  # Forward source-extraction overrides down
            output_zones=output_zones,  # Forward destination paste overrides down
        )
        logger.info("Engine: conversion successful | bytes_out=%d", len(output))
        return output

    except (UnsupportedFileTypeError, ConversionFailedError):
        # Explicit domain errors: pass through
        raise
    except Exception as e:
        logger.exception("Engine: unexpected failure for files: %s, %s", filename_one, filename_two)
        raise ConversionFailedError(original=e) from e


# ─── Public API ───────────────────────────────────────────────────────────────

def convert_bytes(
    file_bytes_one: bytes,
    filename_one: str,
    file_bytes_two: bytes,
    filename_two: str,
    approach: str = APPROACH_ONE,
    watermark: bool = False,
    width: int = LANDSCAPE_W,
    height: int = LANDSCAPE_H,
    custom_zones: Optional[Dict[str, Any]] = None,
    output_zones: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Primary API: Convert dual raw bytes into a single landscape JPEG."""
    return _invoke_engine(
        file_bytes_one=file_bytes_one,
        filename_one=filename_one,
        file_bytes_two=file_bytes_two,
        filename_two=filename_two,
        approach=approach,
        watermark=watermark,
        width=width,
        height=height,
        custom_zones=custom_zones,
        output_zones=output_zones
    )


def run_conversion(
    file_bytes_one: bytes,
    filename_one: str,
    file_bytes_two: bytes,
    filename_two: str,
    approach: str = APPROACH_ONE,
    watermark: bool = False,
    width: int = LANDSCAPE_W,
    height: int = LANDSCAPE_H,
    custom_zones: Optional[Dict[str, Any]] = None,
    output_zones: Optional[Dict[str, Any]] = None,
) -> ConversionResult:
    """Extended API: Returns ConversionResult with layout metadata."""
    output = _invoke_engine(
        file_bytes_one=file_bytes_one,
        filename_one=filename_one,
        file_bytes_two=file_bytes_two,
        filename_two=filename_two,
        approach=approach,
        watermark=watermark,
        width=width,
        height=height,
        custom_zones=custom_zones,
        output_zones=output_zones
    )
    
    return ConversionResult(
        output_bytes=output,
        width=width,
        height=height,
        approach=approach
    )


def health_check_engine() -> bool:
    """Verifies the conversion engine interface is importable."""
    try:
        _get_engine()
        return True
    except ImportError:
        logger.error("Engine health check failed: fayda_converter_v2.py missing.")
        return False