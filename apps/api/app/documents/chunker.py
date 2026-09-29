import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from app.documents.parser import ParsedSection


@dataclass
class TextChunk:
    chunk_index: int
    text: str
    page_number: Optional[int]
    section_path: Optional[str]
    metadata_json: Dict[str, Any]


class DocumentChunker:
    """Chunks structured document sections with semantic windowing and metadata tagging."""

    def __init__(
        self,
        max_chunk_chars: int = 800,
        chunk_overlap_chars: int = 120,
    ):
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars

    def chunk_sections(self, sections: List[ParsedSection]) -> List[TextChunk]:
        chunks: List[TextChunk] = []
        chunk_idx = 0

        for sec in sections:
            paragraphs = [p.strip() for p in sec.text.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [sec.text.strip()] if sec.text.strip() else []

            current_text = ""
            for p in paragraphs:
                if len(current_text) + len(p) + 2 <= self.max_chunk_chars:
                    if current_text:
                        current_text += "\n\n" + p
                    else:
                        current_text = p
                else:
                    if current_text:
                        chunks.append(
                            self._create_chunk(
                                chunk_idx=chunk_idx,
                                text=current_text,
                                page_number=sec.page_number,
                                section_path=sec.section_path,
                            )
                        )
                        chunk_idx += 1
                        # Retain overlap
                        overlap_start = max(0, len(current_text) - self.chunk_overlap_chars)
                        overlap = current_text[overlap_start:].strip()
                        current_text = f"{overlap}\n\n{p}" if overlap else p
                    else:
                        # Single paragraph exceeds max_chunk_chars: split by sentence
                        sentences = re.split(r"(?<=[.!?])\s+", p)
                        for s in sentences:
                            if len(current_text) + len(s) + 1 <= self.max_chunk_chars:
                                current_text += (" " if current_text else "") + s
                            else:
                                if current_text:
                                    chunks.append(
                                        self._create_chunk(
                                            chunk_idx=chunk_idx,
                                            text=current_text,
                                            page_number=sec.page_number,
                                            section_path=sec.section_path,
                                        )
                                    )
                                    chunk_idx += 1
                                current_text = s

            if current_text.strip():
                chunks.append(
                    self._create_chunk(
                        chunk_idx=chunk_idx,
                        text=current_text.strip(),
                        page_number=sec.page_number,
                        section_path=sec.section_path,
                    )
                )
                chunk_idx += 1

        return chunks

    def _create_chunk(
        self,
        chunk_idx: int,
        text: str,
        page_number: Optional[int],
        section_path: Optional[str],
    ) -> TextChunk:
        words = text.split()
        return TextChunk(
            chunk_index=chunk_idx,
            text=text,
            page_number=page_number,
            section_path=section_path,
            metadata_json={
                "char_count": len(text),
                "word_count": len(words),
                "page_number": page_number,
                "section_path": section_path,
                "untrusted_source": True,  # Prompt injection quarantine indicator
            },
        )
