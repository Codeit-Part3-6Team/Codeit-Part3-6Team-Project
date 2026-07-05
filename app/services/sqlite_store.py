"""RAG 서비스용 SQLite 저장소.

run 관리, 대화 기록, 문서 메타데이터를 SQLite로 영속화합니다.
기존 파일시스템/인메모리 방식을 대체합니다.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

_DB_DIR = Path(__file__).resolve().parents[2] / "experiments" / "streamlit"
_DB_PATH = _DB_DIR / "rag_service.db"
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db() -> None:
    with _lock:
        conn = _get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'unknown',
                document_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                config_path TEXT,
                output_dir TEXT
            );
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_chat_history_run_id
                ON chat_history(run_id, created_at);
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                title TEXT,
                source_path TEXT,
                chunk_count INTEGER DEFAULT 0,
                PRIMARY KEY (run_id, document_id),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        conn.close()


_init_db()


# ── Run CRUD ──

def insert_run(
    run_id: str,
    status: str = "running",
    document_count: int = 0,
    chunk_count: int = 0,
    config_path: str | None = None,
    output_dir: str | None = None,
) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, created_at, status, document_count, chunk_count, config_path, output_dir) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, datetime.now().isoformat(), status, document_count, chunk_count, config_path, output_dir),
        )
        conn.commit()
        conn.close()


def update_run_status(run_id: str, status: str, document_count: int | None = None, chunk_count: int | None = None) -> None:
    with _lock:
        conn = _get_conn()
        if document_count is not None and chunk_count is not None:
            conn.execute(
                "UPDATE runs SET status = ?, document_count = ?, chunk_count = ? WHERE run_id = ?",
                (status, document_count, chunk_count, run_id),
            )
        else:
            conn.execute("UPDATE runs SET status = ? WHERE run_id = ?", (status, run_id))
        conn.commit()
        conn.close()


def list_runs() -> list[dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT run_id, created_at, status, document_count FROM runs ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [
        {"run_id": r[0], "created_at": r[1], "status": r[2], "documents": r[3]}
        for r in rows
    ]


def get_run(run_id: str) -> dict[str, Any] | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT run_id, created_at, status, document_count, chunk_count, config_path, output_dir FROM runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "run_id": row[0],
        "created_at": row[1],
        "status": row[2],
        "document_count": row[3],
        "chunk_count": row[4],
        "config_path": row[5],
        "output_dir": row[6],
    }


# ── Chat History CRUD ──

def add_chat_message(run_id: str, role: str, content: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO chat_history (run_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (run_id, role, content, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()


def get_chat_history(run_id: str, limit: int = 20) -> list[dict[str, str]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content FROM chat_history WHERE run_id = ? ORDER BY created_at ASC LIMIT ?",
        (run_id, limit),
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]


def clear_chat_history(run_id: str | None = None) -> None:
    with _lock:
        conn = _get_conn()
        if run_id:
            conn.execute("DELETE FROM chat_history WHERE run_id = ?", (run_id,))
        else:
            conn.execute("DELETE FROM chat_history")
        conn.commit()
        conn.close()


# ── Document CRUD ──

def upsert_documents(run_id: str, documents: list[dict[str, Any]]) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM documents WHERE run_id = ?", (run_id,))
        for doc in documents:
            conn.execute(
                "INSERT INTO documents (document_id, run_id, title, source_path, chunk_count) VALUES (?, ?, ?, ?, ?)",
                (
                    doc.get("document_id", ""),
                    run_id,
                    doc.get("title", ""),
                    doc.get("source_path", ""),
                    doc.get("chunk_count", 0),
                ),
            )
        conn.commit()
        conn.close()


def get_documents(run_id: str) -> list[dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT document_id, title, source_path, chunk_count FROM documents WHERE run_id = ?",
        (run_id,),
    ).fetchall()
    conn.close()
    return [
        {"document_id": r[0], "title": r[1], "source_path": r[2], "chunk_count": r[3]}
        for r in rows
    ]
