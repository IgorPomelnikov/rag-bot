import chromadb
from chromadb.utils import embedding_functions

# 1. Подключаемся к той же папке
chroma_client = chromadb.PersistentClient(path="./my_vector_db")

# 2. Указываем ТУ ЖЕ модель эмбеддингов
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
   #  model_name="E:/models/paraphrase-multilingual-MiniLM-L12-v2"
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# 3. Получаем существующую коллекцию
collection = chroma_client.get_collection(
    name="kb_v1", 
    embedding_function=emb_fn
)


# 4. Цикл для общения (мини-чат)
print("База готова. Спрашивай что угодно (или напиши 'exit' для выхода):")

while True:
   user_query = input("\nВаш вопрос: ")
   if user_query.lower() in ['exit', 'quit', 'выход']:
      break
      
   results = collection.query(
      query_texts=[user_query],
      n_results=10
   )

   print("\n--- Найденные факты ---")
   for i, (doc, dist) in enumerate(zip(results['documents'][0],results['distances'][0])):
      source = results['metadatas'][0][i]['source']
      print(f"[{i+1}] Дистанция: {dist:.4f} | Текст: {doc}")
