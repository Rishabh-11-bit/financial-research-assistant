"""Load raw SEC filing HTML/TXT/PDF and split into chunks."""
from __future__ import annotations

import logging
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    BSHTMLLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document

from src.config import get_settings

logger = logging.getLogger(__name__)


def _loader_cls(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader
    if suffix in {".htm", ".html"}:
        return BSHTMLLoader
    return TextLoader


def load_documents(source_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for fpath in source_dir.rglob("*"):
        # full-submission.txt is raw EDGAR SGML (embedded HTML + encoded exhibits); the
        # primary-document.html next to it holds the same filing as clean text
        if fpath.name == "full-submission.txt" and any(fpath.parent.glob("primary-document.*")):
            continue
        if fpath.is_file() and fpath.suffix.lower() in {".pdf", ".htm", ".html", ".txt"}:
            try:
                loader_cls = _loader_cls(fpath)
                kwargs = {"open_encoding": "utf-8"} if loader_cls is BSHTMLLoader else {}
                loader = loader_cls(str(fpath), **kwargs)
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata.setdefault("source", str(fpath))
                docs.extend(loaded)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", fpath, exc)
    logger.info("Loaded %d raw documents from %s", len(docs), source_dir)
    return docs


def split_documents(docs: list[Document]) -> list[Document]:
    cfg = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info("Split into %d chunks", len(chunks))
    return chunks
