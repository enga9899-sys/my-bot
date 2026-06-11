import telebot
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# التوكن الشغال مالتك
TOKEN = "8879289850:AAHhuOSXgEELB7Ca0QB46J1G88ThFfZqixg"
bot = telebot.TeleBot(TOKEN)

# دالة التأكد من الأدمن
def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
    except:
        return False

# دالة حماية الكروب وقفل الملصقات
@bot.message_handler(content_types=['sticker'])
def control_stickers(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'stickers'")
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == 'closed':
            if not is_admin(message.chat.id, message.from_user.id):
                bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        print(f"Error in stickers: {e}")

# تهيئة وتحديث قاعدة البيانات الشاملة
try:
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, response TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS quizzes (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, options TEXT, correct_index INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()
    print("تم تحديث قاعدة البيانات الشاملة بنجاح!")
except Exception as e:
    print(f"Database error: {e}")

# دالة توليد أزرار الخاص (المواد تظهر تلقائياً بدون الزر الثابت)
def get_private_materials_markup():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT keyword FROM replies")
    rows = cursor.fetchall()
    conn.close()
    
    markup = InlineKeyboardMarkup()
    
    # إضافة باقي المواد الدراسية تلقائياً (إذا قمت بإضافة "الجدول" كـ رد، سيظهر كزر تلقائي هنا)
    if rows:
        for row in rows:
            markup.add(InlineKeyboardButton(text=f"📚 {row[0].upper()}", callback_data=f"pv_mat_{row[0]}"))
    return markup

# --- 1. حل مشكلة الـ Start نهائياً بالخاص ---
@bot.message_handler(commands=['start'])
def handle_start_command(message):
    if message.chat.type == 'private':
        markup = get_private_materials_markup()
        welcome_text = "👋 أهلاً بك في البوت المساعد المباشر للجروب الدراسي!\n\n📂 أدناه تجد الأزرار الخاصة بالمواد والجدول، اضغط على أي زر لتحميل ملفاتك فوراً:"
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# --- 2. ميزة الترحيب التلقائي بالطلاب الجدد بالجروب ---
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            continue
        first_name = member.first_name
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'welcome_msg'")
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            welcome_text = f"👋 أهلاً بك يا [{first_name}](tg://user?id={member.id}) نورتنا!\n\n" + row[0]
        else:
            welcome_text = f"👋 أهلاً بك يا [{first_name}](tg://user?id={member.id}) نورت الجروب الدراسي مالتنا! \n✨ اكتب 'المواد' لتنزيل ملازمك بالخاص."
            
        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

# --- 3. أمر تعديل رسالة الترحيب ---
@bot.message_handler(func=lambda message: message.text and message.text.startswith("اضف ترحيب"))
def set_welcome_message(message):
    try:
        if ":" in message.text:
            _, welcome_content = message.text.split(":", 1)
            welcome_content = welcome_content.strip()
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('welcome_msg', ?)", (welcome_content,))
            conn.commit()
            conn.close()
            bot.reply_to(message, f"✅ تم حفظ رسالة الترحيب الثابتة بنجاح!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# --- 4. أمر قفل وفتح الملصقات ---
@bot.message_handler(func=lambda message: message.text and message.text.strip() in ["قفل الملصقات", "فتح الملصقات"])
def toggle_stickers_command(message):
    if message.chat.type in ['group', 'supergroup'] and not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "⚠️ هذا الأمر خاص بالأدمنية فقط!")
        return
    status = "closed" if message.text.strip() == "قفل الملصقات" else "open"
    msg_reply = "🔒 تم قفل الملصقات بنجاح!" if status == "closed" else "🔓 تم فتح الملصقات طبيعي!"
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('stickers', ?)", (status,))
        conn.commit()
        conn.close()
        bot.reply_to(message, msg_reply)
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# --- 5. سيستم إدارة الكلمات المسيئة ---
@bot.message_handler(func=lambda message: message.text and (message.text.startswith("اضف حظر") or message.text.startswith("الغاء حظر") or message.text.strip() == "تصفير المحظورات"))
def manage_bad_words(message):
    if message.chat.type in ['group', 'supergroup'] and not is_admin(message.chat.id, message.from_user.id):
        return
    text = message.text.strip()
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    try:
        if text == "تصفير المحظورات":
            cursor.execute("DELETE FROM bad_words")
            conn.commit()
            bot.reply_to(message, "🗑️ تم تصفير قائمة الألفاظ المحظورة بالكامل!")
        elif ":" in text:
            command, word = text.split(":", 1)
            word = word.strip().lower()
            if "اضف حظر" in command:
                cursor.execute("INSERT OR IGNORE INTO bad_words (word) VALUES (?)", (word,))
                conn.commit()
                bot.reply_to(message, f"🚫 تم إضافة الكلمة ({word}) إلى قائمة الحظر!")
            elif "الغاء حظر" in command:
                cursor.execute("DELETE FROM bad_words WHERE word = ?", (word,))
                conn.commit()
                bot.reply_to(message, f"✅ تم إلغاء الحظر عن الكلمة ({word})!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")
    finally:
        conn.close()

# --- 6. إدارة المواد الدراسية ---
@bot.message_handler(func=lambda message: message.text and message.text.startswith("اضف رد"))
def add_new_reply(message):
    if message.chat.type in ['group', 'supergroup'] and not is_admin(message.chat.id, message.from_user.id):
        return
    try:
        if ":" in message.text:
            main_part = message.text.replace("اضف رد", "").strip()
            keyword, response = main_part.split(":", 1)
            keyword = keyword.strip().lower()
            response = response.strip()
            
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            if not response:
                cursor.execute("DELETE FROM replies WHERE keyword = ?", (keyword,))
                conn.commit()
                bot.reply_to(message, f"🗑️ تم حذف تصنيف ({keyword}) بنجاح!")
            else:
                cursor.execute("DELETE FROM replies WHERE keyword = ? AND response NOT LIKE 'FILE_TYPE:%'", (keyword,))
                cursor.execute("INSERT INTO replies (keyword, response) VALUES (?, ?)", (keyword, response))
                conn.commit()
                bot.reply_to(message, f"✅ تم إضافة المادة بنجاح! 🔑 الكلمة: {keyword}")
            conn.close()
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# --- 7. دالة حفظ الملازم والملفات ---
@bot.message_handler(content_types=['document', 'photo'])
def save_file_reply(message):
    caption = message.caption
    if caption and caption.startswith("اضف رد") and ":" in caption:
        if message.chat.type in ['group', 'supergroup'] and not is_admin(message.chat.id, message.from_user.id):
            return
        try:
            main_part = caption.replace("اضف رد", "").strip()
            keyword, _ = main_part.split(":", 1)
            keyword = keyword.strip().lower()
            
            file_id = message.document.file_id if message.document else message.photo[-1].file_id
            file_type = "document" if message.document else "photo"
            response_data = f"FILE_TYPE:{file_type}:{file_id}"
            
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO replies (keyword, response) VALUES (?, ?)", (keyword, response_data))
            conn.commit()
            conn.close()
            bot.reply_to(message, f"✅ تم حفظ الملف بنجاح في تصنيف ({keyword})!")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ بالملف: {e}")

# --- 8. ميزة صنع الكويز ---
@bot.message_handler(func=lambda message: message.text and message.text.startswith("صنع كويز"))
def create_quiz(message):
    try:
        if ":" in message.text:
            parts = message.text.replace("صنع كويز", "").strip().split(":")
            if len(parts) == 3:
                question = parts[0].strip()
                options_text = parts[1].strip()
                correct_idx = int(parts[2].strip())
                
                conn = sqlite3.connect('bot_database.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO quizzes (question, options, correct_index) VALUES (?, ?, ?)", (question, options_text, correct_idx))
                conn.commit()
                conn.close()
                bot.reply_to(message, f"✅ تم حفظ السؤال بنجاح!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ بالكويز: {e}")

@bot.message_handler(commands=['quiz'])
def send_quiz(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT question, options, correct_index FROM quizzes ORDER BY RANDOM() LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            question, options_text, correct_index = row
            options = [opt.strip() for opt in options_text.split(",")]
            bot.send_poll(chat_id=message.chat.id, question=question, options=options, type='quiz', correct_option_id=correct_index, is_anonymous=False)
    except Exception as e:
        print(f"Error quiz: {e}")

# --- 9. نظام التحويل للخاص ---
@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ['مواد', 'المواد'])
def redirect_to_private(message):
    if message.chat.type in ['group', 'supergroup']:
        try:
            bot_username = bot.get_me().username
            redirect_url = f"https://t.me/{bot_username}?start=start"
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text=f"📂 فتح الملازم والجدول الدراسي", url=redirect_url))
            
            bot.reply_to(message, f"👋 عيني [{message.from_user.first_name}](tg://user?id={message.from_user.id})، اضغط على الزر جوة وراح يفتح وياك البوت بالخاص ويعرض الك المواد والجدول فوراً وبضغطة وحدة:", reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            print(f"Redirect error: {e}")

# معالجة ضغط الأزرار بالخاص وإرسال الملفات والجدول 🌟
@bot.callback_query_handler(func=lambda call: call.data.startswith("pv_mat_"))
def handle_private_material_buttons(call):
    material_name = call.data.replace("pv_mat_", "")
    student_id = call.message.chat.id
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT response FROM replies WHERE keyword = ?", (material_name,))
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            bot.answer_callback_query(call.id, f"📥 جاري عرض {material_name.upper()}...")
            for row in rows:
                response_data = row[0]
                if response_data.startswith("FILE_TYPE:"):
                    _, file_type, file_id = response_data.split(":")
                    if file_type == "document":
                        bot.send_document(student_id, file_id)
                    elif file_type == "photo":
                        bot.send_photo(student_id, file_id)
                else:
                    bot.send_message(student_id, response_data, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ لم يتم رفع ملفات هذه المادة حالياً.", show_alert=True)
    except Exception as e:
        print(f"Error sending file in PV: {e}")

# --- 10. دالة الفلترة والتحقق من الكلمات المحظورة بالجروب العام ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    clean_text = message.text.strip().lower() if message.text else ""
    if not clean_text:
        return

    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT word FROM bad_words")
        words = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        for word in words:
            if word in clean_text:
                if message.chat.type in ['group', 'supergroup'] and not is_admin(message.chat.id, message.from_user.id):
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id, f"⚠️ عيني [{message.from_user.first_name}](tg://user?id={message.from_user.id})، يرجى الالتزام بالأدب!", parse_mode="Markdown")
                    return
    except Exception as e:
        print(f"Error checking bad words: {e}")

print("🚀 تم تشغيل النسخة المحدثة وحذف زر الجدول الثابت!")
bot.infinity_polling()