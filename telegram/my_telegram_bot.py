from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import os
import logging
from flask import Flask, request
import asyncio

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Configuration ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_TOKEN = '8013243836:AAE6qwVFWrSt_0uELMaVTy4WENcVwIvXeGU'
MY_CHAT_ID = '8146161867'
PORT = int(os.environ.get('PORT', 10000))
WEBHOOK_URL = 'https://your-render-app-url.onrender.com'  # استبدل هذا برابط تطبيقك على Render

# إعدادات السعر
DOLLAR_TO_IQD = 1530
DOLLAR_TO_ITUNES = 1.7

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إنشاء مجلد لحفظ الصور إذا لم يكن موجوداً
if not os.path.exists('user_photos'):
    os.makedirs('user_photos')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Global Variables ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
user_sessions = {}  # {user_id: chat_id}
temp_photos = {}    # {user_id: photo_file_id}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Helper Functions ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_main_menu_button():
    return [[InlineKeyboardButton("الرئيسية", callback_data='main_menu')]]

def get_user_link(user):
    if user.username:
        return f"@{user.username}"
    else:
        return f"[{user.full_name}](tg://user?id={user.id})"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Bot Handlers ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    user_sessions[user_id] = chat_id
    
    keyboard = [
        [
            InlineKeyboardButton("دفع عبر زين كاش", callback_data='zen_cash'),
            InlineKeyboardButton("دفع عبر فيزا/ماستر كارد", callback_data='credit_card')
        ],
        [
            InlineKeyboardButton("الإبلاغ عن مشكلة", callback_data='report_issue'),
            InlineKeyboardButton("تحويل دولار ← دينار عراقي", callback_data='calculate_value')
        ],
        [
            InlineKeyboardButton("دفع عبر iTunes", callback_data='itunes_payment')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            "مرحباً بك في بوت يوزر العراقية! اختر الخدمة:",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            "مرحباً بك في بوت يوزر العراقية! اختر الخدمة:",
            reply_markup=reply_markup
        )

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'zen_cash':
        message = """
        خطوات الدفع عبر زين كاش:
        1. الرقم: 07733663333
        2. أرسل صورة التحويل مع رقم الهاتف
        """
        await query.edit_message_text(
            message, 
            reply_markup=InlineKeyboardMarkup(get_main_menu_button())
        )
        await forward_to_admin(update, context, f"المستخدم اختار: دفع عبر زين كاش")

    elif query.data == 'credit_card':
        message = """
        خطوات الدفع عبر فيزا/ماستر:
        1. الرقم: 3658969492
        2. اسم المستلم: Mr. Issa
        3. أرسل صورة التحويل
        """
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(get_main_menu_button())
        )
        await forward_to_admin(update, context, f"المستخدم اختار: دفع عبر فيزا/ماستر كارد")

    elif query.data == 'report_issue':
        await query.edit_message_text(
            "يرجى كتابة مشكلتك وسيقوم الفريق بالرد عليك قريباً...",
            reply_markup=InlineKeyboardMarkup(get_main_menu_button())
        )
        await forward_to_admin(update, context, f"المستخدم يريد الإبلاغ عن مشكلة")

    elif query.data == 'calculate_value':
        context.user_data['conversion_type'] = 'iqd'
        await query.edit_message_text(
            "أدخل المبلغ بالدولار لتحويله إلى دينار عراقي:",
            reply_markup=InlineKeyboardMarkup(get_main_menu_button())
        )
        await forward_to_admin(update, context, f"المستخدم يريد تحويل دولار إلى دينار")

    elif query.data == 'itunes_payment':
        context.user_data['conversion_type'] = 'itunes'
        await query.edit_message_text(
            f"سعر الصرف الحالي: 1$ = {DOLLAR_TO_ITUNES}$ iTunes\n\n"
            "أدخل المبلغ بالدولار:",
            reply_markup=InlineKeyboardMarkup(get_main_menu_button())
        )
        await forward_to_admin(update, context, f"المستخدم يريد شراء رصيد iTunes")

    elif query.data == 'main_menu':
        await start(update, context)

async def forward_to_admin(update: Update, context: CallbackContext, additional_text=None):
    try:
        user = update.effective_user
        user_link = get_user_link(user)
        user_info = (
            f"🚀 رسالة جديدة من:\n"
            f"👤 اسم المستخدم: [{user.full_name}](tg://user?id={user.id})\n"
            f"🆔 ID: `{user.id}`\n"
            f"📌 اليوزر: {user_link}\n"
        )
        
        if additional_text:
            user_info += f"\n📄 النص الإضافي: {additional_text}\n"
        
        if update.message and update.message.photo:
            photo = update.message.photo[-1]
            temp_photos[user.id] = photo.file_id
            
            photo_file = await photo.get_file()
            photo_path = f'user_photos/{user.id}_{photo.file_id}.jpg'
            await photo_file.download_to_drive(photo_path)
            
            with open(photo_path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=MY_CHAT_ID,
                    photo=photo_file,
                    caption=user_info,
                    parse_mode='Markdown'
                )
            
            await context.bot.send_message(
                chat_id=user_sessions[user.id],
                text="تم استلام صورتك بنجاح. يرجى كتابة اليوزر المراد شراؤه:",
                reply_markup=InlineKeyboardMarkup(get_main_menu_button())
            )
        
        elif update.message and update.message.text:
            if user.id in temp_photos:
                user_info += f"\n🎯 اليوزر المطلوب: {update.message.text}\n"
                await context.bot.send_photo(
                    chat_id=MY_CHAT_ID,
                    photo=temp_photos[user.id],
                    caption=user_info,
                    parse_mode='Markdown'
                )
                del temp_photos[user.id]
            else:
                await context.bot.send_message(
                    chat_id=MY_CHAT_ID,
                    text=f"{user_info}\n📩 الرسالة النصية:\n{update.message.text}",
                    parse_mode='Markdown'
                )
        elif update.callback_query:
            await context.bot.send_message(
                chat_id=MY_CHAT_ID,
                text=user_info,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in forwarding: {e}")

async def handle_text_input(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    user_id = update.effective_user.id
    
    if user_id in temp_photos:
        await forward_to_admin(update, context, f"اليوزر المطلوب: {user_input}")
        await update.message.reply_text(
            "تم استلام اليوزر بنجاح وسيتم معالجة طلبك والتواصل معك بأقرب وقت ممكن.",
            reply_markup=InlineKeyboardMarkup(get_main_menu_button())
        )
        return
    
    await forward_to_admin(update, context, f"📩 الرسالة النصية: {user_input}")
    
    try:
        amount = float(user_input)
        conversion_type = context.user_data.get('conversion_type')

        if conversion_type == 'iqd':
            result = int(amount * DOLLAR_TO_IQD)
            await update.message.reply_text(
                f"{amount}$ = {result:,} دينار عراقي",
                reply_markup=InlineKeyboardMarkup(get_main_menu_button())
            )
        
        elif conversion_type == 'itunes':
            result = amount * DOLLAR_TO_ITUNES
            await update.message.reply_text(
                f"{amount}$ = {result:,.2f}$ رصيد iTunes",
                reply_markup=InlineKeyboardMarkup(get_main_menu_button())
            )
        
        else:
            await update.message.reply_text(
                "⚠️ اختر خدمة أولاً من القائمة",
                reply_markup=InlineKeyboardMarkup(get_main_menu_button())
            )

    except ValueError:
        await update.message.reply_text(
            "⚠️ أدخل رقمًا صحيحًا",
            reply_markup=InlineKeyboardMarkup(get_main_menu_button())
        )

async def handle_image(update: Update, context: CallbackContext) -> None:
    await forward_to_admin(update, context, "🖼️ أرسل المستخدم صورة")

async def handle_admin_reply(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message and str(update.effective_chat.id) == MY_CHAT_ID:
        replied_msg = update.message.reply_to_message
        original_text = replied_msg.text or replied_msg.caption
        
        if original_text and "ID:" in original_text:
            try:
                lines = original_text.split('\n')
                user_id = None
                for line in lines:
                    if line.startswith("🆔 ID:"):
                        user_id = int(line.split("`")[1].strip())
                        break
                
                if user_id:
                    reply_text = update.message.text
                    
                    if user_id in user_sessions:
                        await context.bot.send_message(
                            chat_id=user_sessions[user_id],
                            text=f"📬 رد من الدعم الفني:\n\n{reply_text}"
                        )
                        await update.message.reply_text("✅ تم إرسال الرد إلى المستخدم")
                    else:
                        await update.message.reply_text("❌ لم يتم العثور على محادثة المستخدم")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ في إرسال الرد: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Flask App for Keep-Alive ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/keep-alive')
def keep_alive():
    return "Bot is alive!"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Main Function ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main() -> None:
    application = Application.builder().token(API_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(int(MY_CHAT_ID)), handle_admin_reply))

    # Run the bot
    if os.environ.get('RENDER'):
        # On Render - use Webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=API_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{API_TOKEN}"
        )
    else:
        # Locally - use Polling
        application.run_polling()

if __name__ == '__main__':
    # Start Flask server in a separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=PORT))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start the bot
    main()