
#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging

import os
from dotenv import load_dotenv
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder
import chromadb
from openai import OpenAI


chroma_client = chromadb.PersistentClient(path="../3_vector_DB/my_vector_db")
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="E:/models/paraphrase-multilingual-MiniLM-L12-v2"
    # model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
collection = chroma_client.get_collection(
    name="kb_v1", 
    embedding_function=emb_fn
)
# reranker = CrossEncoder('mixedbread-ai/mxbai-rerank-base-v1') 
reranker = CrossEncoder('E:/models/mxbai-rerank-base-v1') 
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html( # pyright: ignore[reportOptionalMemberAccess]
        rf"Hi {user.mention_html()}!", # type: ignore
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_query = update.message.text
    results = collection.query(
        query_texts=[user_query],
        n_results=10
    )

    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    pairs = [[user_query, doc] for doc in documents]
    scores = await reranker.predict(pairs)
    reranked_results = sorted(
        zip(documents, scores, metadatas), 
        key=lambda x: x[1], 
        reverse=True
    )

    print("\n--- Найденные факты ---")
    for i, (doc, dist) in enumerate(zip(results['documents'][0],results['distances'][0])):
        source = results['metadatas'][0][i]['source']
        print(f"[{i+1}] Дистанция: {dist:.4f} | Текст: {doc}")
     
    results_encoded = ""

    for i, (doc, score, meta) in enumerate(reranked_results):
    # Ограничим вывод, скажем, топ-5 самыми релевантными
        if i >= 5: break 
        results_encoded = f"{results_encoded}[{i+1}] Источник[{meta['source']}] Релевантность: {score:.4f} | Текст: {doc}\n\n"

    promp_template = str()
    with open('./prompt_template.txt', 'r', encoding='utf-8') as file:
                promp_template = file.read() or str()
    prompt = promp_template.replace("{{docs}}", results_encoded)
    prompt = prompt.replace("{{user_question}}", user_query)
    
    print(prompt)
    response = client.chat.completions.create(
        model="local-model", # LM Studio игнорирует это имя и использует загруженную модель
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )
    await update.message.reply_text(response.choices[0].message.content)


def main() -> None:
    BOT_TOKEN_FILE:str = os.getenv("BOT_TOKEN_FILE") or str()
    __token:str=""
    if os.path.isfile(BOT_TOKEN_FILE):
        try:
            # Читаем содержимое файла
            with open(BOT_TOKEN_FILE, 'r', encoding='utf-8') as file:
                __token = file.read() or str()
        except Exception as e:
               print(f"Ошибка при обработке файла {BOT_TOKEN_FILE}: {e}")

    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(__token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()