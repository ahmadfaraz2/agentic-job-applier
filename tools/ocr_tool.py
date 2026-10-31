"""
OCR Tool for Ahmad Faraz Antigravity Assistant.
Extracts high-fidelity text from screenshots of LinkedIn job posts, hiring posters,
and announcements using Windows native hardware-accelerated OCR (winocr).
"""

from __future__ import annotations

import io
import logging
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

async def extract_text_from_image_bytes(image_bytes: bytes, lang: str = "en") -> str:
    """Extracts clean text from image bytes using Windows native OCR.
    
    Preserves line breaks and spatial structure for accurate job parsing.
    """
    try:
        import winocr
        img = Image.open(io.BytesIO(image_bytes))
        op = winocr.recognize_pil(img, lang)
        res = await op
        if not res or not res.lines:
            return ""
        lines = [line.text.strip() for line in res.lines if line.text.strip()]
        extracted = "\n".join(lines)
        logger.info(f"Successfully extracted {len(lines)} lines of text from image via native OCR.")
        return extracted
    except Exception as e:
        logger.error(f"Error extracting text from image via OCR: {e}", exc_info=True)
        return ""
