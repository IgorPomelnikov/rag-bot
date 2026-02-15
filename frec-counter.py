import os
import collections
import re

def get_word_frequency(folder_path):
    words_counter = collections.Counter()
    
    # Проходим по файлам
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read().lower()
                    # Находим только слова (буквы и цифры), игнорируя пунктуацию
                    words = re.findall(r'\b\w+\b', content)
                    words_counter.update(words)
            except Exception as e:
                print(f"Ошибка в файле {filename}: {e}")

    # Сортируем: .most_common() возвращает список кортежей (слово, частота)
    return words_counter.most_common()

# --- НАСТРОЙКИ ---
target_folder = './knowledge_base'  # Путь к папке

if __name__ == "__main__":
   result = get_word_frequency(target_folder)
    
   print(f"{'Слово':<20} | {'Частота':<10}")
   print("-" * 32)
   counter = 1
   for word, count in result:
      if(len(word) <4):
          continue
      if(counter > 200):
         break
      counter += 1
      print(f"{word:<20} | {count:<10}")
