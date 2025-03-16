"""PDF text extraction module."""

import logging
import os
import re
import tempfile
from io import BytesIO

import pdfplumber
import pytesseract
import requests
from pdf2image import convert_from_path
from PIL import ImageEnhance

from scraper.config.config import PENALTY_PATTERNS

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Class for extracting and processing text from PDF documents."""

    def extract_settlement(self, text_data, url=None):
        """Extract settlement amount from text."""
        if not text_data:
            return None

        text = text_data["text"]

        # The penalty is located in the ORDER section usually.
        for pattern in PENALTY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).strip()
                try:
                    amount_str = amount_str.replace("S", "5")
                    amount_str = amount_str.replace("s", "5")
                    amount_str = re.sub(r"[^\d.,]", "", amount_str)
                    amount = float(amount_str.replace(",", ""))
                    logger.info(f"Found settlement amount: ${amount:,.2f}")
                    return amount
                except ValueError:
                    continue

        # Log a longer preview for debugging
        preview = text.replace("\n", " ").strip()
        logger.warning(f"No settlement amount found. Text preview: {preview}")
        if url:
            logger.warning(f"No settlement amount found in {url}")
        return None

    def extract_from_pdf(self, url):
        """Extract text from PDF using multiple methods."""
        try:
            response = requests.get(url)
            pdf_content = BytesIO(response.content)

            # We want to try to extract the text with pdfplumber.
            pdfplumber_text = self._extract_with_pdfplumber(pdf_content)

            # Check if pdfplumber got meaningful text (more than just numbers/short
            # strings).
            if pdfplumber_text and len(pdfplumber_text.strip()) > 200:
                logger.info("Successfully extracted meaningful text with pdfplumber")
                return {"text": pdfplumber_text}

            # If pdfplumber returned None, empty string, or very little text, try OCR.
            logger.info(
                f"Limited text found with pdfplumber "
                f"({len(pdfplumber_text.strip()) if pdfplumber_text else 0} chars), "
                f"trying OCR..."
            )

            # Reset buffer position.
            pdf_content.seek(0)
            ocr_text = self._extract_with_ocr(pdf_content)

            if ocr_text and len(ocr_text.strip()) > 200:
                logger.info("Successfully extracted meaningful text with OCR")
                # OCR can hallucinate, so I want to clean the text before returning.
                cleaned_text = self._clean_ocr_text(ocr_text)
                return {"text": cleaned_text}

            logger.warning("Both text extraction methods failed")
            return None

        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return None

    def _clean_ocr_text(self, text):
        """Clean up OCR text to fix common recognition errors."""
        # Fix common substitutions, but only for non-numeric text
        fixes = [
            # Zero to O.
            (r"(?<!\d)0(?!\d)", "O"),
            # 1 to I
            (r"(?<!\d)1(?!\d)", "I"),
            # Dollar to S only if not before a number.
            (r"(?<!\$)\$(?!\d)", "S"),
            # 8 to B.
            (r"(?<!\d)8(?!\d)", "B"),
            # 5 to S
            (r"(?<!\d)5(?!\d)", "S"),
        ]

        for old, new in fixes:
            text = re.sub(old, new, text)

        return text

    def _extract_with_ocr(self, pdf_content):
        """Extract text from PDF using OCR.

        This method is used as a fallback when pdfplumber fails to extract text.

        Args:
            pdf_content: PDF content as BytesIO object.

        Returns:
            Extracted text as a string or None if extraction failed.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                tmp_pdf.write(pdf_content.read())
                tmp_pdf_path = tmp_pdf.name

            try:
                # Convert PDF to images with higher DPI.
                images = convert_from_path(tmp_pdf_path, dpi=400)
                pages_text = []

                for i, image in enumerate(images):
                    try:
                        # Enhance image for better OCR.
                        image = image.convert("L")
                        enhancer = ImageEnhance.Contrast(image)
                        image = enhancer.enhance(2.0)
                        enhancer = ImageEnhance.Sharpness(image)
                        image = enhancer.enhance(2.0)

                        # OCR configuration.
                        custom_config = r'''--oem 3 --psm 6
                            -c preserve_interword_spaces=1
                            -c tessedit_do_invert=0
                            -c tessedit_char_blacklist="|~`"'''

                        page_text = pytesseract.image_to_string(
                            image, config=custom_config
                        )

                        if page_text.strip():
                            pages_text.append(page_text)
                            logger.info(
                                f"Successfully extracted text from page {i + 1}"
                            )
                        else:
                            logger.warning(f"Page {i + 1} extracted no text with OCR")

                    except Exception as e:
                        logger.error(f"OCR failed for page {i + 1}: {str(e)}")
                        continue

                # Here we combine all the pages.
                if pages_text:
                    full_text = "\n\n".join(pages_text)
                    logger.info(
                        f"Successfully extracted {len(full_text)} characters total "
                        f"from {len(pages_text)} pages"
                    )
                    return full_text

                return None

            finally:
                try:
                    os.unlink(tmp_pdf_path)
                except Exception as e:
                    logger.error(f"Failed to delete temporary file: {str(e)}")

        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            return None

    def _extract_with_pdfplumber(self, pdf_content):
        """Extract text using pdfplumber.

        Args:
            pdf_content: PDF content as BytesIO object.

        Returns:
            Extracted text as a string or None if extraction failed.
        """
        try:
            with pdfplumber.open(pdf_content) as pdf:
                text = ""
                total_pages = len(pdf.pages)
                logger.info(f"Processing PDF with {total_pages} pages")

                for i, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if not page_text:
                        logger.warning(f"Page {i} extracted no text")
                        continue
                    text += page_text + "\n"

                if text:
                    logger.info(f"Successfully extracted {len(text)} characters total")

                return text.strip()

        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return None
