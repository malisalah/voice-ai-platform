"""Text chunking with overlap and metadata."""

import re
from typing import List

from structlog import get_logger

from config import settings

logger = get_logger(__name__)


class Chunker:
    """Text chunker with configurable size and overlap."""

    def __init__(
        self,
        max_words: int | None = None,
        max_chars: int | None = None,
        overlap_words: int | None = None,
        sentence_sensitive: bool = True,
    ):
        # Use config defaults if not specified
        self.max_words = max_words or settings.POCKETFLOW_CHUNK_SIZE
        self.max_chars = max_chars or (self.max_words * 6)  # ~6 chars per word avg
        self.overlap_words = overlap_words or settings.POCKETFLOW_CHUNK_OVERLAP
        self.sentence_sensitive = sentence_sensitive

    def chunk(self, text: str, page_url: str) -> List[dict]:
        """Chunk text into overlapping segments with metadata."""
        if not text:
            return []

        # Tokenize into sentences if sentence-sensitive
        if self.sentence_sensitive:
            sentences = self._split_into_sentences(text)
            return self._group_sentences(sentences, page_url)

        # Simple word-based chunking
        words = text.split()
        return self._group_words(words, page_url)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Improved sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _group_sentences(self, sentences: List[str], page_url: str) -> List[dict]:
        """Group sentences into chunks with overlap."""
        chunks = []
        current_chunk = []
        current_word_count = 0
        current_char_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())
            sentence_chars = len(sentence)

            # Check if adding this sentence exceeds limits
            if (
                current_word_count + sentence_words > self.max_words
                or current_char_count + sentence_chars > self.max_chars
            ):
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunk = self._create_chunk(chunk_text, page_url, len(chunks))
                    # Never produce empty chunks
                    if chunk["word_count"] > 0:
                        chunks.append(chunk)

                    # Add overlap
                    if self.overlap_words > 0 and current_chunk:
                        overlap_sentences = []
                        overlap_words = 0
                        for prev_sent in reversed(current_chunk):
                            if overlap_words + len(prev_sent.split()) <= self.overlap_words:
                                overlap_sentences.insert(0, prev_sent)
                                overlap_words += len(prev_sent.split())
                            else:
                                break
                        current_chunk = overlap_sentences
                        current_word_count = overlap_words
                        current_char_count = sum(len(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_word_count += sentence_words
            current_char_count += sentence_chars

        # Add final chunk - never produce empty chunks
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = self._create_chunk(chunk_text, page_url, len(chunks))
            if chunk["word_count"] > 0:
                chunks.append(chunk)

        return chunks

    def _group_words(self, words: List[str], page_url: str) -> List[dict]:
        """Group words into chunks."""
        chunks = []
        current_chunk = []

        for word in words:
            current_chunk.append(word)

            if len(current_chunk) >= self.max_words:
                chunk_text = " ".join(current_chunk)
                chunk = self._create_chunk(chunk_text, page_url, len(chunks))
                if chunk["word_count"] > 0:
                    chunks.append(chunk)

                # Add overlap
                if self.overlap_words > 0:
                    overlap = current_chunk[-self.overlap_words:]
                    current_chunk = overlap
                else:
                    current_chunk = []

        # Add remaining words - never produce empty chunks
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = self._create_chunk(chunk_text, page_url, len(chunks))
            if chunk["word_count"] > 0:
                chunks.append(chunk)

        return chunks

    def _create_chunk(self, text: str, page_url: str, chunk_index: int) -> dict:
        """Create a chunk with metadata."""
        words = text.split()
        sentences = re.split(r"[.!?]+", text)

        return {
            "content": text.strip(),
            "page_url": page_url,
            "chunk_index": chunk_index,
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "char_count": len(text),
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }

    def chunk_with_context(
        self, text: str, page_url: str, include_prev: bool = True
    ) -> List[dict]:
        """Chunk text with optional context from previous chunk."""
        chunks = self.chunk(text, page_url)

        if not include_prev or len(chunks) <= 1:
            return chunks

        # Add context from previous chunk to each chunk
        for i in range(1, len(chunks)):
            prev_content = chunks[i - 1]["content"]
            chunks[i]["overlap_context"] = prev_content[-100:]  # Last 100 chars

        return chunks
