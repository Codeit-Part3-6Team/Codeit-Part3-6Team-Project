"""워크스페이스 채팅 질의를 백그라운드 job으로 실행합니다."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock, Thread
from uuid import uuid4
from typing import Any

from .frontend_adapter import chat_ask


_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_chat_job(
    question: str,
    run_id: str | None,
    selected_doc_ids: list[str] | None,
    titles: list[str] | None,
) -> str:
    """채팅 질의 job을 시작하고 job_id를 반환합니다."""
    job_id = uuid4().hex
    job = {
        "job_id": job_id,
        "status": "running",
        "question": question,
        "run_id": run_id,
        "selected_doc_ids": list(selected_doc_ids or []),
        "titles": list(titles or []),
        "answer": "",
        "sources": [],
        "error": None,
        "created_at": _now_iso(),
        "finished_at": None,
    }
    with _jobs_lock:
        _jobs[job_id] = job
    Thread(target=_run_chat_job, args=(job_id,), daemon=True, name=f"chat-job-{job_id[:8]}").start()
    return job_id


def get_chat_job(job_id: str | None) -> dict[str, Any] | None:
    """job 상태 사본을 반환합니다."""
    if not job_id:
        return None
    with _jobs_lock:
        job = _jobs.get(job_id)
        return deepcopy(job) if job else None


def clear_chat_job(job_id: str | None) -> None:
    """완료되었거나 더 이상 표시하지 않을 job을 제거합니다."""
    if not job_id:
        return
    with _jobs_lock:
        _jobs.pop(job_id, None)


def _run_chat_job(job_id: str) -> None:
    with _jobs_lock:
        job = deepcopy(_jobs.get(job_id))
    if not job:
        return

    try:
        answer, sources = chat_ask(
            str(job.get("question") or ""),
            job.get("run_id"),
            job.get("selected_doc_ids") or None,
            job.get("titles") or [],
        )
        update = {
            "status": "done",
            "answer": str(answer or "").strip(),
            "sources": list(sources or []),
            "error": None,
            "finished_at": _now_iso(),
        }
    except Exception as exc:  # pragma: no cover - 방어용 안전망
        update = {
            "status": "failed",
            "answer": "",
            "sources": [],
            "error": str(exc),
            "finished_at": _now_iso(),
        }

    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(update)
