import time
import requests
import html2text

def parse_to_markdown(page_name):
    url = "https://vedmak.fandom.com/api.php"
    
    # Параметры API:
    # prop=text - получаем само содержимое
    # redirects=1 - если ввели "Геральт", перекинет на "Геральт из Ривии"
    params = {
        "action": "parse",
        "page": page_name,
        "format": "json",
        "prop": "text",
        "redirects": 1,
        "disableeditsection": 1,  # Убираем ссылки [править] сразу на уровне API
        "disablestylededuplication": 1,
        "disablelimitreport": 1
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return f"Ошибка: {data['error']['info']}"

        # Получаем HTML контент
        html_content = data["parse"]["text"]["*"]
        title = data["parse"]["title"]

        # Настройка конвертера Markdown
        h = html2text.HTML2Text()
        h.ignore_links = True        # Сохраняем ссылки (полезно для цитирования в RAG)
        h.ignore_images = True       # Картинки для текста обычно не нужны
        h.body_width = 0             # Не ограничивать длину строки
        h.strong_mark = "__"         # Жирный шрифт
        
        markdown_text = h.handle(html_content)

        # Добавляем заголовок в начало
        result = f"# {title}\n\n{markdown_text}"
        return result

    except Exception as e:
        return f"Произошла ошибка: {e}"

def get_all_characters():
    URL = "https://vedmak.fandom.com/api.php"
    
    PARAMS = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Категория:Персонажи_(Ведьмак_3)",
        "cmlimit": "max", # Автоматически возьмет 500
        "format": "json"
    }

    all_characters = []
    
    while True:
        r = requests.get(url=URL, params=PARAMS)
        data = r.json()

        # Собираем названия страниц
        pages = data.get("query", {}).get("categorymembers", [])
        for page in pages:
            all_characters.append(page["title"])

        # Если персонажей больше 500, API вернет 'continue'
        if "continue" in data:
            PARAMS.update(data["continue"])
        else:
            break

    return all_characters

# Пример использования
if __name__ == "__main__":

   characters = get_all_characters()
   for character in characters:
      md_data = parse_to_markdown(character)
      
      # Сохраняем для RAG
      with open(f"vedmak_characters/{character}1.md", "w", encoding="utf-8") as f:
         f.write(md_data)
      time.sleep(.1)
      print(f"Готово! Страница '{character}' сохранена в формате Markdown.")
