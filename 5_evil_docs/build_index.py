import os
from chromadb.utils import embedding_functions
import chromadb
from chonkie import SentenceChunker
import time


EMBED_MODEL = "E:/models/paraphrase-multilingual-MiniLM-L12-v2"
# EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)

# 2. Инициализируем чанкер правильно (под токены)
chunker = SentenceChunker(
    tokenizer="character",
    chunk_size=30,   
    chunk_overlap=15
)

chroma_client = chromadb.PersistentClient(path="../3_vector_DB/my_vector_db")
collection = chroma_client.get_or_create_collection(name="kb_v1", embedding_function=emb_fn)


def process_and_upload(directory):
   total_chunks = 0
   for filename in os.listdir(directory):
      if not filename.endswith(".md"):
         continue
         
      path = os.path.join(directory, filename)
      with open(path, 'r', encoding='utf-8') as f:
         text = f.read()
         
      chunks = chunker.chunk(text)
      
      # Готовим батч для одного файла
      ids = [f"{filename}_{i}" for i in range(len(chunks))]
      docs = [c.text for c in chunks]
      metas = [{"source": filename, "chunk_id": i} for i in range(len(chunks))]
      
      # Добавляем в базу (тут можно добавить проверку на пустой docs)
      if docs:
         collection.add(documents=docs, metadatas=metas, ids=ids)
         print(f"Indexed: {filename} ({len(docs)} chunks)")
         total_chunks += len(docs)
   return total_chunks   

start = time.perf_counter()
total_chunks = process_and_upload("./evil_docs")
end = time.perf_counter()
print(f"Проиндексировано {total_chunks} чанков! Время выполнения: {end - start} секунд")
