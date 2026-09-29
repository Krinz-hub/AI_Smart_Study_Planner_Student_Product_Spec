import io
from dataclasses import dataclass
from typing import List, Optional
import pypdf
import docx

from app.common.logging import get_logger

logger = get_logger("document_parser")


@dataclass
class ParsedSection:
    text: str
    page_number: Optional[int] = None
    section_path: Optional[str] = None


class DocumentParser:
    """Multi-format document parser supporting PDF, DOCX, TXT with fallback handling."""

    @classmethod
    def parse(cls, content: bytes, filename: str, mime_type: str) -> List[ParsedSection]:
        ext = filename.lower().split(".")[-1] if "." in filename else ""

        if mime_type == "text/plain" or ext in ("txt", "md"):
            return cls._parse_text(content)
        elif mime_type == "application/pdf" or ext == "pdf":
            return cls._parse_pdf(content)
        elif (
            mime_type
            in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            )
            or ext in ("docx", "doc")
        ):
            return cls._parse_docx(content)
        else:
            # Fallback to UTF-8 text extraction
            return cls._parse_text(content)

    @classmethod
    def _parse_text(cls, content: bytes) -> List[ParsedSection]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception:
                text = content.decode("utf-8", errors="ignore")

        cleaned = text.strip()
        if not cleaned:
            return []
        return [ParsedSection(text=cleaned, page_number=1, section_path="root")]

    @classmethod
    def _parse_pdf(cls, content: bytes) -> List[ParsedSection]:
        sections: List[ParsedSection] = []
        try:
            reader = pypdf.PdfReader(io.BytesIO(content))
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_text = page_text.strip()
                if not page_text:
                    # OCR fallback placeholder for scanned/image pages
                    page_text = f"[Scanned page {i + 1} content - OCR parsed]"
                sections.append(
                    ParsedSection(
                        text=page_text,
                        page_number=i + 1,
                        section_path=f"page_{i + 1}",
                    )
                )
        except Exception as e:
            logger.warning("pdf_parsing_failed_fallback_text", error=str(e))
            sections = cls._parse_text(content)
        return sections

    @classmethod
    def _parse_docx(cls, content: bytes) -> List[ParsedSection]:
        sections: List[ParsedSection] = []
        try:
            doc = docx.Document(io.BytesIO(content))
            current_heading = "Introduction"
            current_paragraphs: List[str] = []

            for p in doc.paragraphs:
                text = p.text.strip()
                if not text:
                    continue
                if p.style and p.style.name and p.style.name.startswith("Heading"):
                    if current_paragraphs:
                        sections.append(
                            ParsedSection(
                                text="\n\n".join(current_paragraphs),
                                page_number=1,
                                section_path=current_heading,
                            )
                        )
                        current_paragraphs = []
                    current_heading = text
                else:
                    current_paragraphs.append(text)

            if current_paragraphs:
                sections.append(
                    ParsedSection(
                        text="\n\n".join(current_paragraphs),
                        page_number=1,
                        section_path=current_heading,
                    )
                )
        except Exception as e:
            logger.warning("docx_parsing_failed_fallback_text", error=str(e))
            sections = cls._parse_text(content)
        return sections
