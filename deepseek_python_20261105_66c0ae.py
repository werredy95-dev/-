# -*- coding: utf-8 -*-
import os
import asyncio
import traceback
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

# =====================================================================
# ⚠️ ضع مفاتيحك هنا بين علامات التنصيص ⚠️
# =====================================================================

TELEGRAM_TOKEN = ""
GROQ_API_KEY = "g"

# =====================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "ضع_التوكن_الخاص_بالبوت_هنا":
    logger.error("خطأ: يرجى وضع توكن تيليجرام في الكود.")
    exit(1)
if not GROQ_API_KEY or GROQ_API_KEY == "ضع_مفتاح_Groq_هنا":
    logger.error("خطأ: يرجى وضع مفتاح Groq في الكود.")
    exit(1)

# النماذج الحديثة المتاحة حالياً في Groq
# النموذج الأساسي: ذكي جداً (GPT-OSS 120B)
# النموذج البديل: أسرع وخفيف (GPT-OSS 20B)
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

ai_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
    timeout=30.0
)

chat_histories = {}

SYSTEM_PROMPT = (
    "أنت مساعد ذكي، محترف، وودود. تجيب على الأسئلة بوضوح ودقة وباللغة العربية. "
    "تستخدم الإيموجيز بشكل مناسب لتكون تفاعلياً، ولكن دون مبالغة. "
    "إذا سئلت عن شيء لا تعرفه، قل ذلك بصراحة."
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"أهلاً بك يا {user_name}! 👋\n\n"
        "أنا مساعدك الذكي المدعوم بتقنية **Groq** فائقة السرعة. ⚡\n"
        "يمكنك سؤالي عن أي شيء، وسأجيبك فوراً.\n\n"
        "استخدم الأمر /clear لمسح ذاكرة المحادثة والبدء من جديد."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in chat_histories:
        del chat_histories[user_id]
    await update.message.reply_text("✅ تم مسح ذاكرة المحادثة بنجاح. يمكنك البدء من جديد!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        if user_id not in chat_histories:
            chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

        history = chat_histories[user_id]
        history.append({"role": "user", "content": user_text})

        if len(history) > 21:
            history = [history[0]] + history[-20:]
            chat_histories[user_id] = history

        response_text = None
        last_error = None

        for model_name in MODELS:
            if response_text: break
            
            logger.info(f"محاولة استخدام النموذج: {model_name}")
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await ai_client.chat.completions.create(
                        model=model_name,
                        messages=history,
                        temperature=0.7,
                        max_tokens=1024
                    )
                    response_text = response.choices[0].message.content
                    break
                    
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    logger.warning(f"فشل النموذج {model_name} (المحاولة {attempt+1}): {error_str}")
                    
                    if "429" in error_str or "503" in error_str or "rate_limit" in error_str.lower():
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        break

        if response_text:
            history.append({"role": "assistant", "content": response_text})
            await update.message.reply_text(response_text)
        else:
            logger.error(f"فشلت جميع النماذج. آخر خطأ: {last_error}")
            await update.message.reply_text(
                "⚠️ حدث خطأ مؤقت في الاتصال بالذكاء الاصطناعي. يرجى المحاولة بعد قليل."
            )

    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")

def main():
    logger.info("====================================")
    logger.info("🚀 جاري تشغيل البوت...")
    logger.info(f"🧠 النماذج المتاحة: {MODELS}")
    logger.info("====================================")

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()