from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List

from aegis_ai.common.config import settings
from aegis_ai.orchestration.state import IncidentContext
from aegis_ai.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
}


@dataclass(frozen=True)
class DocumentInput:
    text: str | None = None
    path: str | None = None
    filename: str | None = None
    content_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]


def run_rag(ctx: IncidentContext) -> IncidentContext:
    """Run the RAG pipeline to index documents and retrieve context."""

    payload = ctx.payload
    docs_payload = payload.get("rag_documents")
    query = payload.get("rag_query") or payload.get("query") or ctx.summary

    if docs_payload:
        documents = _coerce_documents(docs_payload)
        indexed = index_documents(documents)
        payload["rag_indexed"] = indexed

    if query:
        retrieved = retrieve_context(query, top_k=settings.rag_top_k)
        payload["rag_results"] = retrieved
        payload["rag_context"] = _format_context(retrieved)

    return ctx


def _coerce_documents(raw: Iterable[Any]) -> List[DocumentInput]:
    documents: List[DocumentInput] = []
    for item in raw:
        if isinstance(item, DocumentInput):
            documents.append(item)
            continue
        documents.append(
            DocumentInput(
                text=item.get("text"),
                path=item.get("path"),
                filename=item.get("filename"),
                content_type=item.get("content_type"),
                metadata=item.get("metadata", {}),
            )
        )
    return documents


def index_documents(documents: Iterable[DocumentInput]) -> dict[str, Any]:
    collection = get_vectorstore()
    indexed_chunks = 0
    indexed_documents = 0

    for document in documents:
        text, metadata = extract_text(document)
        if not text:
            logger.warning("Skipping empty document: %s", metadata.get("source"))
            continue

        chunks = chunk_text(
            text,
            max_chars=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
            max_chunks=settings.rag_max_chunks,
        )
        if not chunks:
            continue

        doc_chunks = _build_chunks(chunks, metadata)
        collection.add(
            documents=[chunk.text for chunk in doc_chunks],
            metadatas=[chunk.metadata for chunk in doc_chunks],
            ids=[chunk.chunk_id for chunk in doc_chunks],
        )
        indexed_chunks += len(doc_chunks)
        indexed_documents += 1

    return {"documents": indexed_documents, "chunks": indexed_chunks}


def retrieve_context(query: str, top_k: int) -> List[dict[str, Any]]:
    if not query.strip():
        return []
    collection = get_vectorstore()
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output: List[dict[str, Any]] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        output.append(
            {
                "text": text,
                "metadata": metadata,
                "distance": distance,
            }
        )
    return output


def _format_context(results: Iterable[dict[str, Any]]) -> str:
    blocks: List[str] = []
    for result in results:
        metadata = result.get("metadata", {})
        source = metadata.get("source", "unknown")
        blocks.append(f"Source: {source}\n{result.get('text', '').strip()}")
    return "\n\n".join(blocks)


def extract_text(document: DocumentInput) -> tuple[str, dict[str, Any]]:
    metadata = dict(document.metadata)
    source = document.path or document.filename or metadata.get("source") or "in-memory"
    metadata.setdefault("source", source)

    if document.text is not None:
        metadata.setdefault("doc_type", "text")
        return normalize_text(document.text), metadata

    if not document.path:
        return "", metadata

    path = Path(document.path)
    metadata.setdefault("filename", document.filename or path.name)
    doc_type = _infer_doc_type(path, document.content_type)
    metadata.setdefault("doc_type", doc_type)

    if path.stat().st_size > settings.rag_max_doc_bytes:
        raise ValueError(f"Document exceeds size limit: {path}")

    if doc_type == "pdf":
        text = _extract_pdf_text(path)
    elif doc_type == "docx":
        text = _extract_docx_text(path)
    elif doc_type == "yaml":
        text = _extract_yaml_text(path)
    else:
        text = _extract_plain_text(path)

    return normalize_text(text), metadata


def _infer_doc_type(path: Path, content_type: str | None) -> str:
    if content_type:
        lowered = content_type.lower()
        if "pdf" in lowered:
            return "pdf"
        if "word" in lowered or "docx" in lowered:
            return "docx"
        if "yaml" in lowered:
            return "yaml"
        if "markdown" in lowered:
            return "markdown"

    return SUPPORTED_EXTENSIONS.get(path.suffix.lower(), "text")


def _extract_plain_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("pypdf is required to parse PDF documents.") from exc

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("python-docx is required to parse DOCX documents.") from exc

    doc = Document(str(path))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def _extract_yaml_text(path: Path) -> str:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("PyYAML is required to parse YAML documents.") from exc

    data = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore"))
    return yaml.safe_dump(data, default_flow_style=False)


def normalize_text(text: str) -> str:
    cleaned = text.replace("\x00", " ")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def chunk_text(text: str, max_chars: int, overlap: int, max_chunks: int) -> List[str]:
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if not current:
            return
        chunks.append(current.strip())
        if overlap > 0:
            current = current[-overlap:]
        else:
            current = ""

    for paragraph in paragraphs:
        units = _split_into_sentences(paragraph)
        for unit in units:
            if len(unit) > max_chars:
                for part in _split_long_text(unit, max_chars, overlap):
                    if len(chunks) >= max_chunks:
                        return chunks
                    chunks.append(part)
                current = ""
                continue

            if len(current) + len(unit) + 1 > max_chars and current:
                flush()
                if len(chunks) >= max_chunks:
                    return chunks

            if current:
                current = f"{current} {unit}".strip()
            else:
                current = unit

        if len(current) > max_chars:
            flush()
            if len(chunks) >= max_chunks:
                return chunks

    if current:
        chunks.append(current.strip())

    return chunks[:max_chunks]


def _split_into_sentences(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _split_long_text(text: str, max_chars: int, overlap: int) -> List[str]:
    if max_chars <= 0:
        return [text]
    parts: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        parts.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, 0)
    return parts


def _build_chunks(chunks: Iterable[str], metadata: dict[str, Any]) -> List[DocumentChunk]:
    output: List[DocumentChunk] = []
    source = str(metadata.get("source", "unknown"))
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    chunks_list = list(chunks)
    total = len(chunks_list)
    for index, chunk in enumerate(chunks_list):
        chunk_id = _make_chunk_id(source_hash, index, chunk)
        chunk_metadata = dict(metadata)
        chunk_metadata.update({"chunk_index": index, "chunk_total": total})
        output.append(DocumentChunk(chunk_id=chunk_id, text=chunk, metadata=chunk_metadata))
    return output


def _make_chunk_id(source_hash: str, index: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{source_hash}-{index}-{digest}"
