import os
import asyncio
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
ai_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
chat_histories = {}
SYSTEM_PROMPT = "أنت مساعد ذكي ومحترف. أجب باللغة العربية."

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! أنا بوتك الذكي.")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_histories.pop(update.effective_user.id, None)
    await update.message.reply_text("✅ تم مسح الذاكرة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        if uid not in chat_histories:
            chat_histories[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
        hist = chat_histories[uid]
        hist.append({"role": "user", "content": text})
        if len(hist) > 21: hist = [hist[0]] + hist[-20:]
        
        res_text = None
        for model in MODELS:
            try:
                res = await ai_client.chat.completions.create(model=model, messages=hist, max_tokens=1024)
                res_text = res.choices[0].message.content
                break
            except:
                await asyncio.sleep(2)
        
        if res_text:
            hist.append({"role": "assistant", "content": res_text})
            await update.message.reply_text(res_text)
        else:
            await update.message.reply_text("⚠️ السيرفر مزدحم، حاول لاحقاً.")
    except Exception:
        await update.message.reply_text("⚠️ حدث خطأ.")

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheck).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)