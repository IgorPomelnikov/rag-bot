import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
GOLDEN_SET_PATH = BASE_DIR / "golden_set.json"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"

CHROMA_DIR = ROOT_DIR / "3_vector_DB" / "my_vector_db"
COLLECTION_NAME = "kb_v1"
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

RUN_LLM = os.getenv("RUN_LLM", "0") == "1"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LLM_MODEL", "local-model")
N_RESULTS = int(os.getenv("N_RESULTS", "10"))

ABSTAIN_MARKERS = [
    "не знаю",
    "не найдено",
    "нет данных",
    "недостаточно информации",
    "не могу ответить",
]


def is_abstain(answer_text: str) -> bool:
    lowered = answer_text.lower()
    return any(marker in lowered for marker in ABSTAIN_MARKERS)


def is_successful_answer(answer_text: str, chunks_found: bool) -> bool:
    if not chunks_found:
        return False
    if is_abstain(answer_text):
        return False
    return len(answer_text.strip()) >= 40


def compose_context(top_chunks: list[tuple[str, dict[str, Any]]]) -> str:
    lines = []
    for idx, (doc, meta) in enumerate(top_chunks, start=1):
        source = meta.get("source", "unknown")
        lines.append(f"[{idx}] Источник[{source}] Текст: {doc}")
    return "\n\n".join(lines)


def generate_answer_with_llm(question: str, top_chunks: list[tuple[str, dict[str, Any]]]) -> str:
    context = compose_context(top_chunks)
    prompt = (
        "Ты RAG-ассистент. Отвечай только на основе контекста. "
        "Если контекста недостаточно, явно напиши 'Недостаточно информации'.\n\n"
        f"Контекст:\n{context}\n\n"
        f"Вопрос: {question}\n"
    )
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


def generate_fallback_answer(question: str, top_chunks: list[tuple[str, dict[str, Any]]]) -> str:
    if not top_chunks:
        return "Недостаточно информации в базе знаний."
    preview = top_chunks[0][0][:240]
    source = top_chunks[0][1].get("source", "unknown")
    return f"По найденным данным ({source}) можно ответить так: {preview}"


def evaluate_case(case: dict[str, Any], sources: list[str], answer_text: str, chunks_found: bool) -> bool:
    should_answer = bool(case["should_answer"])
    if should_answer:
        return chunks_found and is_successful_answer(answer_text, chunks_found)
    return (not chunks_found) or is_abstain(answer_text)


def main():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_log_path = LOGS_DIR / f"golden_run_{timestamp}.jsonl"
    report_path = REPORTS_DIR / f"golden_report_{timestamp}.json"

    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        golden_cases = json.load(f)

    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=emb_fn)

    total = 0
    correct = 0
    known_total = 0
    known_correct = 0
    missing_total = 0
    missing_correct = 0
    no_chunks_count = 0

    for case in golden_cases:
        total += 1
        question = case["question"]
        expected_sources = case.get("expected_sources", [])

        results = collection.query(query_texts=[question], n_results=N_RESULTS)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        top_chunks: list[tuple[str, dict[str, Any]]] = []
        for doc, meta in zip(docs, metas):
            if doc:
                top_chunks.append((str(doc), meta or {}))
            if len(top_chunks) >= 5:
                break

        chunks_found = len(top_chunks) > 0
        if not chunks_found:
            no_chunks_count += 1

        sources = []
        for _, meta in top_chunks:
            source = meta.get("source")
            if source and source not in sources:
                sources.append(source)

        if RUN_LLM:
            answer_text = generate_answer_with_llm(question, top_chunks)
        else:
            answer_text = generate_fallback_answer(question, top_chunks)

        eval_ok = evaluate_case(case, sources, answer_text, chunks_found)
        if eval_ok:
            correct += 1

        if case["should_answer"]:
            known_total += 1
            if eval_ok:
                known_correct += 1
        else:
            missing_total += 1
            if eval_ok:
                missing_correct += 1

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "id": case["id"],
            "question": question,
            "topic": case["topic"],
            "should_answer": case["should_answer"],
            "expected_sources": expected_sources,
            "found_sources": sources,
            "chunks_found": chunks_found,
            "answer_length": len(answer_text),
            "successful_answer": is_successful_answer(answer_text, chunks_found),
            "answer_text": answer_text,
            "is_correct": eval_ok,
        }
        with open(run_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    report = {
        "run_log_path": str(run_log_path),
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "known_total": known_total,
        "known_correct": known_correct,
        "known_recall": round(known_correct / known_total, 4) if known_total else 0.0,
        "missing_total": missing_total,
        "missing_correct_rejections": missing_correct,
        "missing_rejection_rate": round(missing_correct / missing_total, 4) if missing_total else 0.0,
        "no_chunks_count": no_chunks_count,
        "run_with_llm": RUN_LLM,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Golden test completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
