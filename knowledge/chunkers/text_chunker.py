"""Text chunking engine with configurable size and overlap.

Uses recursive character splitting on natural boundaries
(paragraphs, sentences, words) to produce semantically
meaningful chunks. Also provides sentence-based and
section-based chunking strategies.
"""

import hashlib
import logging
import re

from knowledge.models import Chunk, Document

logger = logging.getLogger(__name__)


class TextChunker:
    """Recursive text chunker with configurable size and overlap.

    Chunking strategies:
    - Fixed-size with overlap (default)
    - Sentence-based splitting
    - Section-based splitting (by headers)

    Pipeline:
    1. Split on double newlines (paragraphs)
    2. If any segment exceeds chunk_size, split on sentence boundaries
    3. If still too long, split on word boundaries
    """

    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 120) -> None:
        if chunk_overlap >= chunk_size:
            chunk_overlap = chunk_size // 2
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: Document) -> list[Chunk]:
        """Split a Document into a list of Chunks (fixed-size with overlap).

        Args:
            document: The Document to split.

        Returns:
            List of Chunk objects with metadata inherited from the document.
        """
        text = document.content
        chunks = self._split_text(text)
        result: list[Chunk] = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = hashlib.md5(
                f"{document.document_id}-{i}".encode(), usedforsecurity=False
            ).hexdigest()[:12]
            result.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    title=document.title,
                    source=document.source,
                    category=document.category,
                    content=chunk_text.strip(),
                    chunk_number=i + 1,
                    date=document.date,
                    region=document.region,
                    keywords=document.keywords,
                )
            )
        return result

    def chunk_by_sentences(self, document: Document, max_sentences: int = 5) -> list[Chunk]:
        """Split a document into chunks by sentences.

        Args:
            document: The Document to split.
            max_sentences: Maximum number of sentences per chunk.

        Returns:
            List of Chunk objects.
        """
        if not document.content.strip():
            return []

        sentences = re.split(r"(?<=[.!?])\s+", document.content)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: list[Chunk] = []
        chunk_number = 1
        for i in range(0, len(sentences), max_sentences):
            group = sentences[i : i + max_sentences]
            chunk_text = " ".join(group)
            chunk_id = hashlib.md5(
                f"{document.document_id}-sent-{i}".encode(), usedforsecurity=False
            ).hexdigest()[:12]
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    title=document.title,
                    source=document.source,
                    category=document.category,
                    content=chunk_text,
                    chunk_number=chunk_number,
                    date=document.date,
                    region=document.region,
                    keywords=document.keywords,
                )
            )
            chunk_number += 1

        return chunks

    def chunk_by_sections(self, document: Document) -> list[Chunk]:
        """Split a document into chunks by section headers.

        Detects common markdown-like headers (#, ##, ===, ---).

        Args:
            document: The Document to split.

        Returns:
            List of Chunk objects with section headers.
        """
        if not document.content.strip():
            return []

        pattern = re.compile(r"^(#{1,6}\s+.*)$|^(.+)\n[=\-]+\s*$", re.MULTILINE)
        sections: list[tuple[str, str]] = []
        last_pos = 0
        last_header = "root"

        for match in pattern.finditer(document.content):
            if match.start() > last_pos:
                content = document.content[last_pos : match.start()].strip()
                if content:
                    sections.append((last_header, content))
            header = match.group(1) or match.group(2)
            last_header = header.strip()
            last_pos = match.end()

        remaining = document.content[last_pos:].strip()
        if remaining:
            sections.append((last_header, remaining))

        if not sections and document.content.strip():
            sections.append(("root", document.content.strip()))

        chunks: list[Chunk] = []
        for i, (header, content) in enumerate(sections):
            chunk_id = hashlib.md5(
                f"{document.document_id}-sec-{i}".encode(), usedforsecurity=False
            ).hexdigest()[:12]
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    title=document.title,
                    source=document.source,
                    category=document.category,
                    content=f"{header}\n\n{content}" if header != "root" else content,
                    chunk_number=i + 1,
                    date=document.date,
                    region=document.region,
                    keywords=document.keywords,
                )
            )

        return chunks

    def _split_text(self, text: str) -> list[str]:
        """Split text recursively on natural boundaries.

        Strategy:
        1. Split on double newlines (paragraphs)
        2. If any segment exceeds chunk_size, split on single newlines
        3. If still too long, split on sentence boundaries
        4. If still too long, split on word boundaries
        """
        if self._count_tokens(text) <= self.chunk_size:
            return [text]

        segments = self._split_on_paragraphs(text)
        result: list[str] = []
        for seg in segments:
            if self._count_tokens(seg) <= self.chunk_size:
                result.append(seg)
            else:
                result.extend(self._split_on_sentences(seg))
        return self._apply_overlap(self._merge_small_chunks(result))

    def _split_on_paragraphs(self, text: str) -> list[str]:
        return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    def _split_on_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""
        for sent in sentences:
            candidate = f"{current} {sent}".strip() if current else sent
            if self._count_tokens(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if self._count_tokens(sent) > self.chunk_size:
                    chunks.extend(self._split_on_words(sent))
                    current = ""
                else:
                    current = sent
        if current:
            chunks.append(current)
        return chunks

    def _split_on_words(self, text: str) -> list[str]:
        words = text.split()
        chunks: list[str] = []
        current: list[str] = []
        for word in words:
            candidate = current + [word]
            if self._count_tokens(" ".join(candidate)) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(" ".join(current))
                current = [word]
        if current:
            chunks.append(" ".join(current))
        return chunks

    def _merge_small_chunks(self, chunks: list[str]) -> list[str]:
        if len(chunks) <= 1:
            return chunks
        merged: list[str] = []
        buffer = ""
        for chunk in chunks:
            candidate = f"{buffer}\n\n{chunk}".strip() if buffer else chunk
            if self._count_tokens(candidate) <= self.chunk_size:
                buffer = candidate
            else:
                if buffer:
                    merged.append(buffer)
                buffer = chunk
        if buffer:
            merged.append(buffer)
        return merged

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        if len(chunks) <= 1 or self.chunk_overlap <= 0:
            return chunks
        result: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            curr = chunks[i]
            overlap_text = self._extract_overlap(prev)
            if overlap_text:
                result.append(f"{overlap_text}\n{curr}")
            else:
                result.append(curr)
        return result

    def _extract_overlap(self, text: str) -> str:
        tokens = text.split()
        overlap_tokens_count = min(self.chunk_overlap, len(tokens))
        return " ".join(tokens[-overlap_tokens_count:])

    @staticmethod
    def _count_tokens(text: str) -> int:
        return len(text.split())

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Roughly estimate token count from character count.

        Uses a simple 4 characters per token heuristic,
        which is reasonable for English text.
        """
        return max(1, len(text) // 4)
