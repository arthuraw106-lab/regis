# Modified Regis Bot - نسخه بهبود یافته
import telebot
from telebot.types import BotCommand
import os
import time
from openai import OpenAI

TELEGRAM_BOT_TOKEN = "8808603871:AAGf0SdMEjwlhgZToPMraOCCbpUwTjqYipU"
API_KEY = "fe_oa_2162df958833ddb1bd8f520fe074a4553a05b0814c60e978"

BASE_URL = "https://api.freemodel.dev/v1"
MODEL = "gpt-5.5"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

bot.set_my_commands([
    BotCommand("regis", "هممممم"),
])

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# حافظه هر کاربر
memory = {}
MAX_MEMORY = 200  # تعداد پیام‌های اخیر

SYSTEM_PROMPT = """
You are Regis (رجیس), a teenage Iranian programming assistant.
Personality: friendly, chill, and slightly playful teenage coder.
You speak naturally like an experienced developer friend.
You stay respectful and helpful.

Professional Role: Expert in software engineering, backend, frontend, DevOps, databases, architecture, debugging and system design.
All generated code must be production-ready. Use modern best practices.

Language Rules:
- You MUST respond ONLY in Persian.
- English is allowed ONLY inside code, syntax, file names, commands and technical identifiers.

Output Rules:
When the user requests code, ALWAYS return exactly this format:

[CODE]
# تمام کد اینجا
[/CODE]

[EXPLANATION]
توضیحات کامل به فارسی
[/EXPLANATION]

- Never use markdown code blocks (```).
- For HTML projects, start directly with <!DOCTYPE html>
- For Python, start directly with imports or code.
- Never add extra labels like "HTML:" or "Python:".
- Code must be complete and ready to run.
"""

def call_model(user_id: int, user_message: str) -> str:
    if user_id not in memory:
        memory[user_id] = []

    # ساخت پیام‌ها
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(memory[user_id])
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=4096
        )

        result = response.choices[0].message.content.strip()

        # ذخیره در حافظه
        memory[user_id].append({"role": "user", "content": user_message})
        memory[user_id].append({"role": "assistant", "content": result})
        
        # محدود کردن حافظه
        if len(memory[user_id]) > MAX_MEMORY:
            memory[user_id] = memory[user_id][-MAX_MEMORY:]

        return result

    except Exception as e:
        return f"خطای API: {str(e)}"


def extract_code_and_explanation(text: str):
    """استخراج بخش کد و توضیحات با روش مقاوم‌تر"""
    import re

    # پیدا کردن بخش کد
    code_match = re.search(r'\[CODE\](.*?)\[/CODE\]', text, re.DOTALL)
    # پیدا کردن بخش توضیحات
    expl_match = re.search(r'\[EXPLANATION\](.*?)$', text, re.DOTALL)

    if code_match:
        code = code_match.group(1).strip()
        explanation = expl_match.group(1).strip() if expl_match else ""
        return code, explanation
    
    # اگر فرمت دقیق پیدا نشد، تلاش برای تشخیص ساده
    if "[CODE]" in text and "[EXPLANATION]" in text:
        try:
            parts = text.split("[CODE]", 1)[1].split("[EXPLANATION]", 1)
            code = parts[0].strip()
            explanation = parts[1].strip() if len(parts) > 1 else ""
            return code, explanation
        except:
            pass
    
    return None, text


def detect_file_type(code: str) -> str:
    code_lower = code.lower().strip()
    
    if code_lower.startswith('<!doctype html') or '<html' in code_lower:
        return "html"
    if code_lower.startswith('<!doctype') or '<!DOCTYPE' in code:
        return "html"
    if any(kw in code_lower for kw in ['def ', 'import ', 'from ', 'class ', 'if __name__']):
        return "py"
    if any(kw in code_lower for kw in ['const ', 'let ', 'function ', 'export ', 'async ', 'await']):
        return "js"
    if 'body {' in code_lower or 'html {' in code_lower or 'css {' in code_lower or '{' in code_lower and ('color:' in code_lower or 'margin:' in code_lower):
        return "css"
    if code_lower.strip().startswith(('{', '[')) and ('"' in code_lower or "'" in code_lower):
        return "json"
    
    return "txt"

# این بخش را بعد از تعریف تابع call_model و قبل از bot.polling اضافه کن

ALLOWED_CODE_EXTENSIONS = {".py", ".html"}
MAX_UPLOAD_FILE_SIZE = 512 * 1024  # 512KB
MAX_FILE_TEXT_CHARS = 60000
TELEGRAM_MESSAGE_LIMIT = 3900


def split_long_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT):
    """تقسیم متن طولانی برای ارسال در تلگرام"""
    if not text:
        return [""]

    chunks = []
    current = ""

    for line in text.splitlines(keepends=True):
        if len(current) + len(line) <= limit:
            current += line
        else:
            if current:
                chunks.append(current)
                current = ""

            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]

            current = line

    if current:
        chunks.append(current)

    return chunks


def decode_uploaded_code_file(file_bytes: bytes) -> str:
    """تبدیل فایل کدنویسی به متن با چند encoding رایج"""
    encodings = ["utf-8", "utf-8-sig", "cp1256", "windows-1256", "latin-1"]

    for encoding in encodings:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return file_bytes.decode("utf-8", errors="replace")


def build_file_prompt(file_name: str, file_text: str, caption: str | None = None) -> str:
    """ساخت پیام مناسب برای ارسال محتوای فایل به هوش مصنوعی"""
    caption_text = caption.strip() if caption else ""

    truncated = False
    if len(file_text) > MAX_FILE_TEXT_CHARS:
        file_text = file_text[:MAX_FILE_TEXT_CHARS]
        truncated = True

    truncation_note = (
        "\n\nتوجه: محتوای فایل به خاطر طول زیاد کوتاه شده و فقط بخش اول آن ارسال شده است."
        if truncated
        else ""
    )

    user_request = caption_text or "این فایل را بخوان، بررسی کن و اگر مشکلی دارد توضیح بده."

    return f"""درخواست کاربر:
{user_request}

نام فایل:
{file_name}

محتوای فایل:
{file_text}
{truncation_note}
"""


REGIS_SESSION_COMMAND = "/Regis"
REGIS_SESSION_END_TEXT = "پایان ارسال"
REGIS_SESSION_MAX_ITEMS = 10
REGIS_SESSION_TIMEOUT_SECONDS = 15 * 60

ALLOWED_CODE_EXTENSIONS = {".py", ".html"}
MAX_UPLOAD_FILE_SIZE = 512 * 1024
MAX_FILE_TEXT_CHARS = 60000
TELEGRAM_MESSAGE_LIMIT = 3900

regis_sessions = {}


def split_long_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT):
    """تقسیم متن طولانی برای ارسال در تلگرام"""
    if not text:
        return [""]

    chunks = []
    current = ""

    for line in text.splitlines(keepends=True):
        if len(current) + len(line) <= limit:
            current += line
        else:
            if current:
                chunks.append(current)
                current = ""

            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]

            current = line

    if current:
        chunks.append(current)

    return chunks


def decode_uploaded_code_file(file_bytes: bytes) -> str:
    """تبدیل فایل کدنویسی به متن با چند encoding رایج"""
    encodings = ["utf-8", "utf-8-sig", "cp1256", "windows-1256", "latin-1"]

    for encoding in encodings:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return file_bytes.decode("utf-8", errors="replace")


def is_regis_session_active(user_id: int) -> bool:
    """بررسی فعال بودن حالت جمع‌آوری پیام‌های Regis"""
    session = regis_sessions.get(user_id)

    if not session:
        return False

    created_at = session.get("created_at", 0)
    if time.time() - created_at > REGIS_SESSION_TIMEOUT_SECONDS:
        regis_sessions.pop(user_id, None)
        return False

    return True


def start_regis_session(user_id: int):
    """شروع حالت جمع‌آوری تا ۱۰ پیام بعد از /Regis"""
    regis_sessions[user_id] = {
        "created_at": time.time(),
        "items": []
    }


def add_item_to_regis_session(user_id: int, item_type: str, content: str, file_name: str | None = None):
    """اضافه کردن متن یا محتوای فایل به سشن کاربر"""
    if not is_regis_session_active(user_id):
        return False, "سشن فعال نیست."

    session = regis_sessions[user_id]

    if len(session["items"]) >= REGIS_SESSION_MAX_ITEMS:
        return False, "ظرفیت سشن پر شده."

    session["items"].append({
        "type": item_type,
        "file_name": file_name,
        "content": content
    })

    return True, None


def build_regis_combined_prompt(items: list) -> str:
    """ساخت prompt نهایی از پیام‌ها و فایل‌ها به ترتیب ارسال"""
    parts = [
        "کاربر چند پیام و/یا فایل را به ترتیب ارسال کرده است.",
        "همه موارد زیر را به همان ترتیب بررسی کن و پاسخ یکپارچه بده.",
        "اگر کدها مشکل دارند، دقیق توضیح بده و اگر لازم بود نسخه اصلاح‌شده بده.",
        ""
    ]

    for index, item in enumerate(items, start=1):
        item_type = item.get("type")
        file_name = item.get("file_name")
        content = item.get("content", "")

        if item_type == "text":
            parts.append(f"--- پیام شماره {index} ---")
            parts.append(content)
            parts.append("")
        elif item_type == "file":
            parts.append(f"--- فایل شماره {index} ---")
            parts.append(f"نام فایل: {file_name}")
            parts.append("محتوای فایل:")
            parts.append(content)
            parts.append("")

    return "\n".join(parts).strip()


def finish_regis_session(user_id: int):
    """پایان سشن و ساخت prompt نهایی"""
    session = regis_sessions.pop(user_id, None)

    if not session or not session.get("items"):
        return None

    return build_regis_combined_prompt(session["items"])


def read_telegram_document_as_text(message):
    """خواندن فایل .py یا .html از تلگرام و تبدیل به متن"""
    document = message.document
    file_name = document.file_name or ""

    _, extension = os.path.splitext(file_name.lower())

    if extension not in ALLOWED_CODE_EXTENSIONS:
        raise ValueError("فعلاً فقط فایل‌های .py و .html قابل خواندن هستند.")

    if document.file_size and document.file_size > MAX_UPLOAD_FILE_SIZE:
        raise ValueError("حجم فایل زیاده. لطفاً فایل کمتر از 512KB بفرست.")

    file_info = bot.get_file(document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    file_text = decode_uploaded_code_file(downloaded_file)

    if not file_text.strip():
        raise ValueError("فایل خالیه یا متن قابل خوندن داخلش نیست.")

    if len(file_text) > MAX_FILE_TEXT_CHARS:
        file_text = (
            file_text[:MAX_FILE_TEXT_CHARS]
            + "\n\nتوجه: محتوای فایل به خاطر طول زیاد کوتاه شده و فقط بخش اول آن ارسال شده است."
        )

    return file_name, file_text


@bot.message_handler(commands=["regis"])
def handle_regis_command(message):
    """با دستور /Regis حالت جمع‌آوری پیام‌ها فعال می‌شود"""
    user_id = message.from_user.id

    start_regis_session(user_id)

    bot.reply_to(
        message,
        "اوکی، حالت ارسال چندتایی فعال شد 😎\n"
        "از الان تا ۱۰ پیام/فایل بعدی رو جمع می‌کنم.\n"
        "می‌تونی متن، فایل .py یا فایل .html بفرستی.\n"
        "هر وقت کارت تموم شد بنویس:\n"
        "پایان ارسال"
    )


@bot.message_handler(
    func=lambda message: (
        message.content_type == "text"
        and is_regis_session_active(message.from_user.id)
    ),
    content_types=["text"]
)
def handle_regis_session_text(message):
    """جمع‌آوری پیام‌های متنی در حالت /Regis"""
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if text == REGIS_SESSION_END_TEXT:
        waiting_message = bot.reply_to(message, "گرفتم، دارم همه پیام‌ها و فایل‌ها رو باهم می‌دم به هوش مصنوعی...")

        combined_prompt = finish_regis_session(user_id)

        if not combined_prompt:
            bot.edit_message_text(
                "چیزی برای ارسال ذخیره نشده بود.",
                chat_id=waiting_message.chat.id,
                message_id=waiting_message.message_id
            )
            return

        ai_response = call_model(user_id, combined_prompt)

        bot.edit_message_text(
            "پاسخ آماده شد:",
            chat_id=waiting_message.chat.id,
            message_id=waiting_message.message_id
        )

        for chunk in split_long_text(ai_response):
            bot.send_message(message.chat.id, chunk)

        return

    session = regis_sessions.get(user_id)
    if session and len(session["items"]) >= REGIS_SESSION_MAX_ITEMS:
        bot.reply_to(
            message,
            "به سقف ۱۰ پیام/فایل رسیدی. حالا بنویس: پایان ارسال"
        )
        return

    ok, error = add_item_to_regis_session(user_id, "text", text)

    if not ok:
        bot.reply_to(message, error or "نتونستم پیام رو ذخیره کنم.")
        return

    current_count = len(regis_sessions[user_id]["items"])

    if current_count >= REGIS_SESSION_MAX_ITEMS:
        bot.reply_to(
            message,
            "پیام ذخیره شد. به سقف ۱۰ مورد رسیدی، حالا بنویس: پایان ارسال"
        )
    else:
        bot.reply_to(
            message,
            f"پیام ذخیره شد. تعداد ذخیره‌شده: {current_count}/{REGIS_SESSION_MAX_ITEMS}"
        )


@bot.message_handler(
    func=lambda message: (
        message.content_type == "document"
        and is_regis_session_active(message.from_user.id)
    ),
    content_types=["document"]
)
def handle_regis_session_document(message):
    """جمع‌آوری فایل‌های .py و .html در حالت /Regis"""
    user_id = message.from_user.id

    session = regis_sessions.get(user_id)
    if session and len(session["items"]) >= REGIS_SESSION_MAX_ITEMS:
        bot.reply_to(
            message,
            "به سقف ۱۰ پیام/فایل رسیدی. حالا بنویس: پایان ارسال"
        )
        return

    try:
        file_name, file_text = read_telegram_document_as_text(message)

        if message.caption and message.caption.strip():
            file_text = (
                f"توضیح کاربر برای این فایل:\n{message.caption.strip()}\n\n"
                f"محتوای فایل:\n{file_text}"
            )

        ok, error = add_item_to_regis_session(
            user_id=user_id,
            item_type="file",
            file_name=file_name,
            content=file_text
        )

        if not ok:
            bot.reply_to(message, error or "نتونستم فایل رو ذخیره کنم.")
            return

        current_count = len(regis_sessions[user_id]["items"])

        if current_count >= REGIS_SESSION_MAX_ITEMS:
            bot.reply_to(
                message,
                f"فایل {file_name} ذخیره شد. به سقف ۱۰ مورد رسیدی، حالا بنویس: پایان ارسال"
            )
        else:
            bot.reply_to(
                message,
                f"فایل {file_name} خونده و ذخیره شد. تعداد ذخیره‌شده: {current_count}/{REGIS_SESSION_MAX_ITEMS}"
            )

    except Exception as e:
        bot.reply_to(message, f"خطا موقع خواندن فایل: {str(e)}")



@bot.message_handler(content_types=["document"])
def handle_code_file(message):
    """خواندن فایل‌های .py و .html و ارسال متن آن‌ها به هوش مصنوعی"""
    try:
        document = message.document
        file_name = document.file_name or ""

        _, extension = os.path.splitext(file_name.lower())

        if extension not in ALLOWED_CODE_EXTENSIONS:
            bot.reply_to(
                message,
                "فعلاً فقط فایل‌های .py و .html رو می‌تونم بخونم و بفرستم برای هوش مصنوعی."
            )
            return

        if document.file_size and document.file_size > MAX_UPLOAD_FILE_SIZE:
            bot.reply_to(
                message,
                "حجم فایل زیاده. لطفاً فایل کمتر از 512KB بفرست."
            )
            return

        waiting_message = bot.reply_to(message, "فایل رو گرفتم، دارم می‌خونمش و می‌فرستم برای هوش مصنوعی...")

        file_info = bot.get_file(document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        file_text = decode_uploaded_code_file(downloaded_file)

        if not file_text.strip():
            bot.edit_message_text(
                "فایل خالیه یا متن قابل خوندن داخلش نیست.",
                chat_id=waiting_message.chat.id,
                message_id=waiting_message.message_id
            )
            return

        prompt = build_file_prompt(
            file_name=file_name,
            file_text=file_text,
            caption=message.caption
        )

        ai_response = call_model(message.from_user.id, prompt)

        bot.edit_message_text(
            "تحلیل آماده شد:",
            chat_id=waiting_message.chat.id,
            message_id=waiting_message.message_id
        )

        for chunk in split_long_text(ai_response):
            bot.send_message(message.chat.id, chunk)

    except Exception as e:
        bot.reply_to(message, f"خطا موقع خواندن فایل: {str(e)}")



@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text.strip()

    if not text:
        return

    status_msg = None
    try:
        status_msg = bot.send_message(user_id, "💭رجیس در حال فکر کردن...")
        bot.send_chat_action(user_id, "typing")

        start_time = time.time()
        result = call_model(user_id, text)
        processing_time = round(time.time() - start_time, 1)

        # حذف پیام وضعیت
        if status_msg:
            try:
                bot.delete_message(user_id, status_msg.message_id)
            except:
                pass

        code_part, explanation_part = extract_code_and_explanation(result)

        if code_part:
            extension = detect_file_type(code_part)
            timestamp = int(time.time())
            file_name = f"regis_{user_id}_{timestamp}.{extension}"

            # نوشتن فایل
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(code_part)

            # ارسال فایل
            with open(file_name, "rb") as f:
                bot.send_document(
                    user_id, 
                    f,
                    caption=f"✅ فایل آماده شد ({processing_time} ثانیه)\n📁 {file_name}"
                )

            # پاک کردن فایل موقت
            try:
                os.remove(file_name)
            except:
                pass

            # ارسال توضیحات (اگر وجود داشته باشد)
            if explanation_part and explanation_part.strip():
                bot.send_message(user_id, explanation_part)

        else:
            # فقط متن
            bot.send_message(user_id, result)

    except Exception as e:
        if status_msg:
            try:
                bot.delete_message(user_id, status_msg.message_id)
            except:
                pass
        bot.send_message(user_id, f"❌ خطایی رخ داد: {str(e)}")


if __name__ == "__main__":
    print("🚀 رجیس بات شروع به کار کرد...")
    while True:
        try:
            bot.infinity_polling(
                timeout=180,
                long_polling_timeout=180,
                allowed_updates=["message"]
            )
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
