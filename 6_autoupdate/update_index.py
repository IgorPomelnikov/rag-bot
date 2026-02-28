import os
import json
import hashlib
import logging
import time
import sys

from chromadb.utils import embedding_functions
import chromadb
from chonkie import SentenceChunker

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.join(SCRIPT_DIR, "..", "2_knowledge_base", "knowledge_base")
VECTOR_DB_DIR = os.path.join(SCRIPT_DIR, "..", "3_vector_DB", "my_vector_db")
MANIFEST_PATH = os.path.join(SCRIPT_DIR, ".manifest.json")

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "kb_v1"

CHUNK_SIZE = 300
CHUNK_OVERLAP = 50

logger = logging.getLogger("update_index")


def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def scan_documents(kb_dir: str, old_manifest: dict):
    """Compare current files against the manifest to find new, modified, and deleted documents."""
    current_files = {}
    for fname in os.listdir(kb_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(kb_dir, fname)
        if os.path.isfile(fpath):
            current_files[fname] = file_md5(fpath)

    new_files = []
    modified_files = []
    unchanged_files = []

    for fname, md5 in current_files.items():
        if fname not in old_manifest:
            new_files.append(fname)
        elif old_manifest[fname] != md5:
            modified_files.append(fname)
        else:
            unchanged_files.append(fname)

    deleted_files = [f for f in old_manifest if f not in current_files]

    return current_files, new_files, modified_files, deleted_files, unchanged_files


def delete_chunks_for_file(collection, filename: str):
    """Remove all chunks belonging to a given source file."""
    existing = collection.get(where={"source": filename})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        logger.info("Удалено %d чанков для '%s'", len(existing["ids"]), filename)


def upsert_file(collection, chunker, kb_dir: str, filename: str) -> int:
    """Chunk a file and upsert its chunks into the collection. Returns chunk count."""
    fpath = os.path.join(kb_dir, filename)
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        logger.warning("Файл '%s' пуст, пропуск", filename)
        return 0

    chunks = chunker.chunk(text)
    ids = [f"{filename}_{i}" for i in range(len(chunks))]
    docs = [c.text for c in chunks]
    metas = [{"source": filename, "chunk_id": i} for i in range(len(chunks))]

    if docs:
        collection.upsert(documents=docs, metadatas=metas, ids=ids)

    return len(docs)


def main():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, log_level, logging.INFO),
    )

    logger.info("=== Запуск обновления индекса ===")
    start = time.perf_counter()

    kb_dir = os.path.normpath(KB_DIR)
    if not os.path.isdir(kb_dir):
        logger.error("Директория базы знаний не найдена: %s", kb_dir)
        sys.exit(1)

    old_manifest = load_manifest()
    current_files, new_files, modified_files, deleted_files, unchanged_files = scan_documents(kb_dir, old_manifest)

    logger.info(
        "Сканирование: всего=%d, новых=%d, изменённых=%d, удалённых=%d, без изменений=%d",
        len(current_files), len(new_files), len(modified_files), len(deleted_files), len(unchanged_files),
    )

    if not new_files and not modified_files and not deleted_files:
        logger.info("Изменений не обнаружено — обновление не требуется")
        elapsed = time.perf_counter() - start
        logger.info("Завершено за %.2f сек", elapsed)
        return

    logger.info("Загрузка модели эмбеддингов: %s", EMBED_MODEL)
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)

    chunker = SentenceChunker(tokenizer="character", chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    db_dir = os.path.normpath(VECTOR_DB_DIR)
    chroma_client = chromadb.PersistentClient(path=db_dir)
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=emb_fn)

    total_added = 0
    total_deleted_chunks = 0

    for fname in deleted_files:
        logger.info("Удаление устаревшего документа: %s", fname)
        existing = collection.get(where={"source": fname})
        total_deleted_chunks += len(existing["ids"])
        delete_chunks_for_file(collection, fname)

    for fname in modified_files:
        logger.info("Обновление изменённого документа: %s", fname)
        delete_chunks_for_file(collection, fname)
        n = upsert_file(collection, chunker, kb_dir, fname)
        total_added += n
        logger.info("  -> добавлено %d чанков", n)

    for fname in new_files:
        logger.info("Индексация нового документа: %s", fname)
        n = upsert_file(collection, chunker, kb_dir, fname)
        total_added += n
        logger.info("  -> добавлено %d чанков", n)

    save_manifest(current_files)

    elapsed = time.perf_counter() - start
    logger.info("=== Обновление завершено ===")
    logger.info("Добавлено/обновлено чанков: %d", total_added)
    logger.info("Удалено чанков: %d", total_deleted_chunks)
    logger.info("Время: %.2f сек", elapsed)


if __name__ == "__main__":
    main()
