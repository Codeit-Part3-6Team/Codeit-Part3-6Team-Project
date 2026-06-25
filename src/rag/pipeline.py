from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.artifacts import (
    prepare_experiment_dir,
    resolve_experiment_dir,
    write_failure_artifact,
    write_run_info,
    write_run_status,
)
from src.config import load_config, write_config_copy, write_json
from src.rag.document_loader import load_documents
from src.rag.engines import build_rag_engine
from src.utils.paths import ensure_dir


DOCUMENT_COLUMNS = ["document_id", "title", "source_path", "page", "section", "text"]
CHUNK_COLUMNS = [
    "chunk_id",
    "document_id",
    "source_path",
    "page_start",
    "page_end",
    "section",
    "text",
    "token_count",
]
EVALUATION_COLUMNS = [
    "question",
    "expected_answer",
    "expected_chunk_ids",
    "retrieved_chunk_ids",
    "citation_chunk_ids",
    "answer",
    "retrieval_hit",
    "retrieval_rank",
    "answer_contains_expected",
    "citation_correct",
    "status",
]


def run_rag_ingest(config_path: str | Path, project_root: str | Path = ".") -> dict[str, int]:
    """RAG 원본 문서를 읽고 document/chunk/embedding 산출물을 저장합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = prepare_experiment_dir(root, config, check_existing=True)

    _write_run_status(output_dir, "rag_ingest", "running")
    try:
        rag_cfg = config.get("rag", {})
        checkpoint_cfg = rag_cfg.get("checkpoint", {})
        resume_enabled = bool(checkpoint_cfg.get("enabled", True) and checkpoint_cfg.get("resume", True))
        loader_cfg = config.get("rag", {}).get("loader", {})
        raw_docs_dir = config["paths"]["raw_docs_dir"]
        documents_path = output_dir / "parsed_documents.csv"
        chunks_path = output_dir / "chunks.csv"
        embeddings_path = output_dir / "embeddings.jsonl"
        engine = build_rag_engine(config, output_dir)

        write_config_copy(config_path, output_dir)
        # RAG resume은 현재 stage 단위입니다.
        # 이미 저장된 artifact가 있으면 해당 stage를 다시 계산하지 않고 재사용합니다.
        if resume_enabled and documents_path.exists():
            documents = _read_csv(documents_path)
        else:
            documents = load_documents(root, raw_docs_dir, loader_cfg.get("file_types", ["txt"]), csv_file=loader_cfg.get("csv_file"))
            _write_csv(documents_path, documents, DOCUMENT_COLUMNS)
        _write_rag_ingest_checkpoint(output_dir, "documents", documents=len(documents))

        if resume_enabled and chunks_path.exists():
            chunks = _read_csv(chunks_path)
        else:
            chunks = engine.chunk_documents(documents)
            _write_csv(chunks_path, chunks, CHUNK_COLUMNS)
        _write_rag_ingest_checkpoint(output_dir, "chunks", documents=len(documents), chunks=len(chunks))

        if resume_enabled and embeddings_path.exists():
            embeddings = _read_jsonl(embeddings_path)
        else:
            embeddings = engine.embed_chunks(chunks)
            _write_jsonl(embeddings_path, embeddings)
        _write_rag_ingest_checkpoint(
            output_dir,
            "embeddings",
            documents=len(documents),
            chunks=len(chunks),
            embeddings=len(embeddings),
        )
        write_run_info(output_dir, config)
        result = {"documents": len(documents), "chunks": len(chunks), "embeddings": len(embeddings)}
        _write_run_status(output_dir, "rag_ingest", "success", result=result)
        return result
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_ingest", exc)
        raise


def run_rag_retrieve(
    config_path: str | Path,
    project_root: str | Path,
    question: str,
) -> dict[str, Any]:
    """저장된 chunk를 읽어 질문에 대한 검색 결과를 JSON 호환 dict로 반환합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)
    _write_run_status(output_dir, "rag_retrieve", "running")
    try:
        return _run_rag_retrieve_checked(config_path, root, config, output_dir, question)
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_retrieve", exc)
        raise


def _run_rag_retrieve_checked(
    config_path: Path,
    root: Path,
    config: dict[str, Any],
    output_dir: Path,
    question: str,
) -> dict[str, Any]:
    chunks_path = output_dir / "chunks.csv"
    embeddings_path = output_dir / "embeddings.jsonl"
    if not chunks_path.exists() or not embeddings_path.exists():
        # 사용자가 retrieve부터 실행해도 최소 파이프라인은 자동으로 준비되게 합니다.
        run_rag_ingest(config_path, root)

    retriever_cfg = config.get("rag", {}).get("retriever", {})
    chunks = _read_csv(chunks_path)
    method = retriever_cfg.get("method", "keyword")
    engine = build_rag_engine(config, output_dir)
    retrieved = engine.retrieve(
        question,
        chunks,
        _read_jsonl(embeddings_path),
    )
    payload = {
        "question": question,
        "top_k": int(retriever_cfg.get("top_k", 3)),
        "retriever_method": method,
        "retrieved_chunks": retrieved,
    }
    _append_jsonl(output_dir / "retrieval_results.jsonl", payload)
    _write_run_status(output_dir, "rag_retrieve", "success", result={"retrieved": len(retrieved)})
    return payload


def run_rag_chat(config_path: str | Path, project_root: str | Path, question: str) -> dict[str, Any]:
    """검색 결과를 바탕으로 추출형 답변과 citation을 생성합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)
    _write_run_status(output_dir, "rag_chat", "running")
    try:
        retrieval = run_rag_retrieve(config_path, root, question)
        answer = build_rag_engine(config, output_dir).answer(question, retrieval["retrieved_chunks"])
        _append_jsonl(output_dir / "answers.jsonl", answer)
        _write_run_status(output_dir, "rag_chat", "success", result={"status": answer["status"]})
        return answer
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_chat", exc)
        raise


def run_rag_agent(
    config_path: str | Path | dict[str, Any],
    project_root: str | Path = ".",
    question: str | None = None,
) -> dict[str, Any]:
    """agent.enabled config에 따라 Agent Loop를 실행합니다.

    agent.enabled가 False이면 기존 run_rag_chat과 동일하게 동작합니다.
    agent.enabled가 True이면 AgentRunner를 통해 Phase DAG를 실행합니다.

    Args:
        config_path: config 파일 경로(str/Path) 또는 config dict
        project_root: 프로젝트 루트
        question: 초기 질문

    Returns:
        AgentRunner.run() 결과 또는 run_rag_chat() 결과
    """
    root = Path(project_root)
    if isinstance(config_path, dict):
        config = config_path
    else:
        config_path = _resolve_path(root, config_path)
        config = load_config(config_path)
    agent_cfg = config.get("agent", {})

    if not agent_cfg.get("enabled", False):
        if question is None:
            return {"state": {}, "phase_results": [], "step_count": 0, "status": "disabled"}
        if isinstance(config_path, dict):
            raise ValueError("config_path as dict is not supported when agent.enabled is False")
        return run_rag_chat(config_path, root, question)

    from src.rag.agent import AgentRunner

    output_dir = None
    if isinstance(config_path, (str, Path)):
        output_dir = resolve_experiment_dir(root, config)  # type: ignore[arg-type]
        ensure_dir(output_dir)
        _write_run_status(output_dir, "rag_agent", "running")
    try:
        runner = AgentRunner(config, root)
        result = runner.run(question, output_dir=output_dir)
        if output_dir:
            _write_run_status(output_dir, "rag_agent", "success", result={"status": result.get("status", "ok")})
        return result
    except Exception as exc:
        if output_dir:
            _write_failure_artifact(output_dir, "rag_agent", exc)
        raise


# ===== 멀티턴 대화 지원 =====
_CHAT_HISTORY: dict[str, list[dict[str, str]]] = {}


def run_rag_chat_with_history(
    config_path: str | Path,
    project_root: str | Path,
    question: str,
    thread_id: str = "default",
) -> dict[str, Any]:
    """이전 대화 맥락을 유지하며 답변을 생성합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)

    memory_cfg = config.get("rag", {}).get("answerer", {}).get("memory", {})
    memory_enabled = bool(memory_cfg.get("enabled", False))

    if not memory_enabled:
        return run_rag_chat(config_path, root, question)

    _write_run_status(output_dir, "rag_chat", "running")
    try:
        history = _CHAT_HISTORY.setdefault(thread_id, [])

        # 이전 대화를 컨텍스트로 포함하여 검색
        context_question = question
        if history:
            prev = "\n".join(
                f"Q: {h['question']}\nA: {h.get('answer', '')[:200]}"
                for h in history[-3:]
            )
            context_question = f"이전 대화:\n{prev}\n\n현재 질문: {question}"

        retrieval = run_rag_retrieve(config_path, root, context_question)
        answer = build_rag_engine(config, output_dir).answer(question, retrieval["retrieved_chunks"])

        # 대화 기록 저장
        history.append({"question": question, "answer": answer.get("answer", "")})
        if len(history) > 10:
            history.pop(0)

        _append_jsonl(output_dir / "answers.jsonl", answer)
        _write_run_status(output_dir, "rag_chat", "success", result={"status": answer["status"], "thread": thread_id})
        return answer
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_chat", exc)
        raise


def run_rag_evaluation(config_path: str | Path, project_root: str | Path = ".") -> dict[str, float]:
    """작은 평가 질문 세트로 retrieval/answer/citation metric을 계산합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)
    _write_run_status(output_dir, "rag_evaluation", "running")
    try:
        questions_path = _resolve_path(root, config.get("evaluation", {}).get("questions_path", ""))
        if not questions_path.exists():
            raise FileNotFoundError(f"RAG evaluation questions not found: {questions_path}")

        rows = _read_csv(questions_path)
        result_rows: list[dict[str, str]] = []
        analysis_rows: list[dict[str, str]] = []
        engine = build_rag_engine(config, output_dir)
        for row in rows:
            retrieval = run_rag_retrieve(config_path, root, row["question"])
            answer = engine.answer(row["question"], retrieval["retrieved_chunks"])
            _append_jsonl(output_dir / "answers.jsonl", answer)
            expected_chunk_ids = _split_expected_ids(row["expected_chunk_ids"])
            retrieved_ids = {str(item["chunk_id"]) for item in retrieval["retrieved_chunks"]}
            citation_ids = {str(item["chunk_id"]) for item in answer["citations"]}
            retrieved_with_rank = [
                (str(item["chunk_id"]), int(item.get("rank", 0)))
                for item in retrieval["retrieved_chunks"]
            ]
            retrieval_rank = 0
            for cid, rank in sorted(retrieved_with_rank, key=lambda x: x[1]):
                if cid in expected_chunk_ids:
                    retrieval_rank = rank
                    break
            retrieval_hit = retrieval_rank > 0
            answer_contains_expected = _normalize_for_match(row["expected_answer"]) in _normalize_for_match(answer["answer"])
            citation_correct = bool(expected_chunk_ids & citation_ids)

            judge_enabled = config.get("evaluation", {}).get("llm_judge", {}).get("enabled", False)
            judge_ok = False
            if judge_enabled:
                try:
                    from src.rag.judge import judge_binary_from_config
                    judge_ok = judge_binary_from_config(config, row["expected_answer"], answer["answer"])
                except Exception:
                    pass

            result_rows.append(
                {
                    "question": row["question"],
                    "retrieval_hit": str(retrieval_hit).lower(),
                    "retrieval_rank": str(retrieval_rank),
                    "answer_contains_expected": str(answer_contains_expected).lower(),
                    "citation_correct": str(citation_correct).lower(),
                    "judge_correct": str(judge_ok).lower(),
                    "status": answer["status"],
                }
            )
            analysis_rows.append(
                {
                    "question": row["question"],
                    "expected_answer": row["expected_answer"],
                    "expected_chunk_ids": _join_ids(expected_chunk_ids),
                    "retrieved_chunk_ids": _join_ids(retrieved_ids),
                    "citation_chunk_ids": _join_ids(citation_ids),
                    "answer": answer["answer"],
                    "retrieval_hit": str(retrieval_hit).lower(),
                    "retrieval_rank": str(retrieval_rank),
                    "answer_contains_expected": str(answer_contains_expected).lower(),
                    "citation_correct": str(citation_correct).lower(),
                    "judge_correct": str(judge_ok).lower(),
                    "status": answer["status"],
                }
            )

        metrics = _calculate_metrics(result_rows)
        _write_csv(
            output_dir / "evaluation_results.csv",
            result_rows,
            ["question", "retrieval_hit", "retrieval_rank", "answer_contains_expected", "citation_correct", "judge_correct", "status"],
        )
        _write_error_analysis(output_dir, analysis_rows)
        write_json(output_dir / "metrics.json", metrics)
        _write_run_status(output_dir, "rag_evaluation", "success", result=metrics)
        return metrics
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_evaluation", exc)
        raise


def _calculate_metrics(rows: list[dict[str, str]]) -> dict[str, float]:
    total = len(rows) or 1
    answered_rows = [r for r in rows if r["status"] != "not_found"]
    answered_total = len(answered_rows) or 1
    mrr = 0.0
    hit_at_1 = hit_at_3 = hit_at_5 = 0
    for r in rows:
        rank = int(r.get("retrieval_rank", 0) or 0)
        if rank > 0:
            mrr += 1.0 / rank
            if rank == 1:
                hit_at_1 += 1
            if rank <= 3:
                hit_at_3 += 1
            if rank <= 5:
                hit_at_5 += 1
    return {
        "retrieval_hit_rate": _ratio(rows, "retrieval_hit", total),
        "retrieval_mrr": round(mrr / total, 4),
        "retrieval_hit_at_1": round(hit_at_1 / total, 4),
        "retrieval_hit_at_3": round(hit_at_3 / total, 4),
        "retrieval_hit_at_5": round(hit_at_5 / total, 4),
        "citation_correct_rate": _ratio(rows, "citation_correct", total),
        "judge_correct_rate": _ratio(rows, "judge_correct", total),
        "not_found_rate": sum(row["status"] == "not_found" for row in rows) / total,
        "diagnostic": {
            "answer_contains_expected_rate": _ratio(rows, "answer_contains_expected", total),
            "judge_on_answered_rate": _ratio(answered_rows, "judge_correct", answered_total),
            "retrieval_failure_rate": sum(r["retrieval_hit"] == "false" for r in rows) / total,
            "answerer_gave_up_rate": sum(
                r["retrieval_hit"] == "true" and r["status"] == "not_found" for r in rows
            ) / total,
            "answerer_error_rate": sum(
                r["retrieval_hit"] == "true"
                and r["status"] == "answered"
                and r["judge_correct"] == "false"
                for r in rows
            ) / total,
        },
    }


def _normalize_for_match(text: str) -> str:
    """쉼표·공백·따옴표 제거. substring 매칭 정확도 보정."""
    import re

    text = text.strip('"').strip("'")
    text = re.sub(r"[\s,]+", "", text)
    return text


def _ratio(rows: list[dict[str, str]], column: str, total: int) -> float:
    return sum(row[column] == "true" for row in rows) / total


def _split_expected_ids(value: str) -> set[str]:
    return {item.strip() for item in value.replace("|", ",").replace(";", ",").split(",") if item.strip()}


def _join_ids(values: set[str]) -> str:
    return "|".join(sorted(values))


def _write_error_analysis(output_dir: Path, rows: list[dict[str, str]]) -> None:
    """RAG 평가 결과를 실패 유형별 오답노트 CSV로 나눠 저장합니다."""
    # 검색 실패와 답변 근거 실패를 분리해야 retriever를 고칠지 answerer를 고칠지 판단하기 쉽습니다.
    bad_retrievals = [row for row in rows if row["retrieval_hit"] != "true"]
    unsupported_answers = [
        row
        for row in rows
        if row["status"] == "answered"
        and (row["citation_correct"] != "true" or row["answer_contains_expected"] != "true")
    ]
    failed_questions = [row for row in rows if row["status"] != "answered"]

    _write_csv(output_dir / "bad_retrievals.csv", bad_retrievals, EVALUATION_COLUMNS)
    _write_csv(output_dir / "unsupported_answers.csv", unsupported_answers, EVALUATION_COLUMNS)
    _write_csv(output_dir / "failed_questions.csv", failed_questions, EVALUATION_COLUMNS)


def _write_run_status(
    output_dir: str | Path,
    operation: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: dict[str, str] | None = None,
) -> None:
    write_run_status(output_dir, operation, status, result=result, error=error)


def _write_failure_artifact(output_dir: str | Path, operation: str, exc: Exception) -> None:
    """실패 원인과 traceback을 파일로 남긴 뒤 호출부가 예외를 다시 올리게 합니다."""
    write_failure_artifact(output_dir, operation, exc)


def _write_rag_ingest_checkpoint(output_dir: str | Path, stage: str, **counts: int) -> None:
    """RAG ingest 단계별 완료 상태를 남겨 다음 실행에서 산출물을 재사용할 수 있게 합니다."""
    payload = {
        "operation": "rag_ingest",
        "stage": stage,
        "counts": counts,
        "artifacts": {
            "documents": "parsed_documents.csv",
            "chunks": "chunks.csv",
            "embeddings": "embeddings.jsonl",
        },
    }
    write_json(Path(output_dir) / "rag_ingest_checkpoint.json", payload)


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    import csv as _csv
    _csv.field_size_limit(int(1e9))
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(_csv.DictReader(f))


def _write_csv(path: str | Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    all_columns = columns + [k for k in sorted(rows[0]) if k not in columns] if rows else columns
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _append_jsonl(path: str | Path, payload: dict[str, Any]) -> None:
    import json

    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    import json

    with Path(path).open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    import json

    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate
