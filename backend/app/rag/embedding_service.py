"""embedding_service.py — Lightweight in-memory lexical retrieval index.

ChromaDB's default embedding pipeline pulls in ONNX Runtime and loads an
embedding model into RAM, which pushed the Render free tier (512MB) over its
limit mid-simulation ("Instance failed: Ran out of memory"). This module
replaces it with a bounded pure-Python TF-IDF cosine index:

* no native dependencies, no model loading, no external services;
* a hard document cap so a long-running instance cannot grow without bound;
* candidate hits are handed to ``rag.reranker`` for Jaccard/term-frequency
  re-ranking, so the passages injected into agent prompts stay relevant.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, OrderedDict
from threading import Lock

from app.rag.document_loader import Document

logger = logging.getLogger(__name__)

# Enough for the seeded historical dataset plus a couple of scenarios' worth of
# chunks, while staying within a few MB of RAM.
MAX_DOCUMENTS = 300

_TOKEN_RE = re.compile(r"\b\w{3,25}\b", re.IGNORECASE)

_STOPWORDS = frozenset(
    """
    the and for that with this from into upon which their there than then when
    what where while about after before between during under over further once
    here why how all any both each few more most other some such only own same
    so very can will just should now also across an are was were be been being
    has have had do does did not but if as at by to is in of or
    """.split()
)


def _tokenize(text: str) -> list[str]:
    """Lower-case keyword tokens with stop-words removed."""
    return [
        token
        for token in (match.group(0).lower() for match in _TOKEN_RE.finditer(text))
        if token not in _STOPWORDS
    ]


class EmbeddingService:
    """Bounded in-memory TF-IDF index scored with cosine similarity."""

    def __init__(self, max_documents: int = MAX_DOCUMENTS):
        self._max_documents = max_documents
        self._lock = Lock()
        # doc id -> Document, insertion ordered for FIFO eviction.
        self._docs: OrderedDict[str, Document] = OrderedDict()
        # doc id -> term frequency counter.
        self._term_freq: dict[str, Counter] = {}
        # term -> number of documents containing that term.
        self._doc_freq: Counter = Counter()
        # doc id -> total token count (for length normalisation).
        self._doc_len: dict[str, int] = {}

    # ── indexing ───────────────────────────────────────────────────────────

    def add_documents(self, docs: list[Document]) -> None:
        if not docs:
            return
        with self._lock:
            for doc in docs:
                if doc.id in self._docs:
                    self._docs.move_to_end(doc.id)
                    continue
                counter = Counter(_tokenize(doc.content))
                self._docs[doc.id] = doc
                self._term_freq[doc.id] = counter
                self._doc_len[doc.id] = sum(counter.values())
                self._doc_freq.update(counter.keys())
            self._evict()

    def _evict(self) -> None:
        """Drop the oldest documents so RAM stays bounded."""
        while len(self._docs) > self._max_documents:
            old_id, _ = self._docs.popitem(last=False)
            freq = self._term_freq.pop(old_id, {})
            self._doc_len.pop(old_id, None)
            if freq:
                self._doc_freq.subtract(freq.keys())
                for term in [t for t, n in self._doc_freq.items() if n <= 0]:
                    del self._doc_freq[term]

    # ── querying ───────────────────────────────────────────────────────────

    def query_similar(self, query: str, n_results: int = 3) -> list[dict]:
        query_tokens = _tokenize(query)
        with self._lock:
            if not self._docs:
                return []

            ranked = self._rank(query_tokens)
            if not ranked:
                # No lexical match (e.g. stop-word-only query): fall back to
                # the most recently indexed documents so the agent always
                # receives some grounding context.
                ranked = [
                    (doc_id, 0.0) for doc_id in reversed(list(self._docs))
                ][:n_results]

            hits = []
            for doc_id, score in ranked[:n_results]:
                doc = self._docs[doc_id]
                hits.append(
                    {
                        "id": doc.id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        # The re-ranker treats smaller distance as better
                        # (similarity = 1 / (1 + distance)); mirror cosine
                        # distance here so scoring stays consistent.
                        "distance": max(0.0, 1.0 - score),
                    }
                )
            return hits

    def _rank(self, query_tokens: list[str]) -> list[tuple[str, float]]:
        """Score documents against the query with TF-IDF cosine similarity."""
        if not query_tokens:
            return []
        n_docs = len(self._docs)
        query_counts = Counter(query_tokens)

        idf: dict[str, float] = {
            term: math.log(1.0 + n_docs / self._doc_freq[term])
            for term in query_counts
            if self._doc_freq.get(term)
        }
        if not idf:
            return []

        query_weights = {term: query_counts[term] * idf[term] for term in idf}
        query_norm = math.sqrt(sum(w * w for w in query_weights.values())) or 1.0

        # Accumulate dot products over the query vocabulary only.
        dots: dict[str, float] = {}
        for term, q_weight in query_weights.items():
            for doc_id, freq in self._term_freq.items():
                tf = freq.get(term)
                if not tf:
                    continue
                doc_len = self._doc_len.get(doc_id) or 1
                dots[doc_id] = dots.get(doc_id, 0.0) + q_weight * (tf / doc_len) * idf[term]

        if not dots:
            return []

        ranked: list[tuple[str, float]] = []
        for doc_id, dot in dots.items():
            freq = self._term_freq[doc_id]
            doc_len = self._doc_len.get(doc_id) or 1
            norm_sq = sum(
                ((tf / doc_len) * idf[term]) ** 2
                for term, tf in freq.items()
                if term in idf
            )
            norm = math.sqrt(norm_sq) or 1.0
            ranked.append((doc_id, dot / (query_norm * norm)))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked


_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Return the process-wide singleton index (persists across scenarios)."""
    global _service
    if _service is None:
        _service = EmbeddingService()
        logger.info(
            "RAG Index | in-memory TF-IDF index initialised (cap=%d documents)",
            MAX_DOCUMENTS,
        )
    return _service

