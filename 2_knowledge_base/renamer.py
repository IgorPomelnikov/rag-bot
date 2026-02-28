import os
import re


def replace_words_in_files(folder_path, replacements):
    # Проходим по всем файлам в указанной папке
   for filename in os.listdir(folder_path):
      file_path = os.path.join(folder_path, filename)
      
      # Проверяем, что это файл, а не папка
      if os.path.isfile(file_path):
            try:
               # Читаем содержимое файла
               with open(file_path, 'r', encoding='utf-8') as file:
                  content = file.read()
               
               # Заменяем слова из словаря
               new_content = content
               for old_word, new_word in replacements.items():
                  new_content = re.sub(old_word, new_word, new_content, flags=re.IGNORECASE)
               
               # Если изменения были, перезаписываем файл
               if new_content != content:
                  with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                  print(f"Файл '{filename}' успешно обновлен.")
               else:
                  print(f"В файле '{filename}' замен не найдено.")



            except Exception as e:
               print(f"Ошибка при обработке файла {filename}: {e}")
         

# --- НАСТРОЙКИ ---
target_folder = './knowledge_base'  # Путь к твоей папке

"""
Меняем вселенную Ведьмака на вселенную Приключений шурика с примесью дурдома.
"""
my_replacements = {
    "Геральт": "Шурик",
    "Весимир": "Фёдор",
    "Цири": "Танечка",
    "охота": "рыбалка",
    "дикая": "культурная",
    "персонаж": "пациент",
    "ведьмака": "больного",
    "ведьмаку": "больному",
    "ведьмак": "больной",
    "больнойом": "больным",
    "скеллиге": "изолятор",
    "колдуньями": "санитарками",
    "новиграде": "Саратове",
    "новиград": "Саратов",
    "призрак": "блаженный", 
    "Агд": "Марин", 
    "Лютик": "Толик", 
    "ярл": "медбрат",
    "эльф": "скуф",
    "квест": "инцидент",
    "игры": "описания клинического случая",
    "меч": "мяч",
    "убий": "беспокой",
    "Ривии": "Москвы",
    "арен": "палат",
    "Островах":"изоляторах",
    "островитянин": "завсегдатый изолятора"




}

# Запуск
if __name__ == "__main__":
    replace_words_in_files(target_folder, my_replacements)
