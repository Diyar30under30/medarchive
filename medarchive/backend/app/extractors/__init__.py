"""Extractors package. Importing it registers every extractor via @register.

Adding a new format = add a module here and import it; the dispatcher resolves
it by FileFormat with no core changes (extensibility requirement).
"""
from app.extractors import base  # noqa: F401
from app.extractors import xlsx  # noqa: F401
from app.extractors import docx_tracked  # noqa: F401
from app.extractors import pdf_text  # noqa: F401
from app.extractors import pdf_scan_ocr  # noqa: F401

from app.extractors.base import (  # noqa: F401
    ExtractedRow,
    ExtractionResult,
    Extractor,
    get_extractor,
    register,
    registered_formats,
)
