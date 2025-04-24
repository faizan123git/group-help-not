import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackContext,
    CallbackQueryHandler, MessageHandler, Filters
)
from dotenv import load_dotenv
from database import init_db, get_db
from handlers import (
    welcome_handlers,
    message_deletion,
    warn_system,
    anti_spam,
    language_filter,
    banned_words,
    bio_protection
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    """Handle /start command with proper group/admin checks"""
    try:
        if update.effective_chat.type == 'private':
            user = update.effective_user
            keyboard = [[InlineKeyboardButton(
                "➕ Add to Group", 
                url=f"https://t.me/{context.bot.username}?startgroup=true"
            )]]
            
            update.message.reply_text(
                f"👋 Hello {user.mention_html()}!\n\n"
                "To manage your Telegram group:\n"
                "1. Add me to your group\n"
                "2. Make me admin\n"
                "3. In the group, type /setup\n\n"
                "I'll help you manage members, content, and security!",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            update.message.reply_text("ℹ️ Please use /start in private chat for setup instructions.")
    except Exception as e:
        logger.error(f"Start command error: {e}")

def setup_group(update: Update, context: CallbackContext):
    """Handle /setup command with proper error handling"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type not in ['group', 'supergroup']:
            update.message.reply_text("❌ This command only works in groups!")
            return

        # Verify bot admin status
        bot_member = chat.get_member(context.bot.id)
        if not bot_member.status == 'administrator':
            update.message.reply_text("⚠️ Please make me admin first!")
            return

        # Verify user admin status
        user_member = chat.get_member(user.id)
        if user_member.status not in ['administrator', 'creator']:
            update.message.reply_text("❌ Only admins can setup the group!")
            return

        # Initialize group in database
        with get_db() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO groups (chat_id, group_name) 
                VALUES (?, ?)
            ''', (chat.id, chat.title))
            conn.commit()

        # Send settings menu to DM
        try:
            context.bot.send_message(
                chat_id=user.id,
                text=f"⚙️ Group Settings for {chat.title}",
                reply_markup=get_settings_menu(chat.id, chat.title)
            )
            update.message.reply_text("✅ Settings menu sent to your DM!")
        except Exception as e:
            logger.error(f"DM send error: {e}")
            update.message.reply_text("❌ Please start a chat with me first!")

    except Exception as e:
        logger.error(f"Setup error: {e}")
        update.message.reply_text("❌ Error processing setup request. Please try again.")

def get_settings_menu(chat_id: int, group_name: str) -> InlineKeyboardMarkup:
    """Generate main settings menu with all buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎉 Welcome/Goodbye", callback_data=f"welcome_{chat_id}")],
        [InlineKeyboardButton("⏰ Message Deletion", callback_data=f"deletion_{chat_id}")],
        [InlineKeyboardButton("⚠️ Warning System", callback_data=f"warnings_{chat_id}")],
        [InlineKeyboardButton("🛡️ Anti-Spam", callback_data=f"antispam_{chat_id}")],
        [InlineKeyboardButton("🌐 Language Filter", callback_data=f"language_{chat_id}")],
        [InlineKeyboardButton("🚫 Banned Words", callback_data=f"banned_{chat_id}")],
        [InlineKeyboardButton("🔗 Bio Protection", callback_data=f"bio_{chat_id}")]
    ])

def error_handler(update: Update, context: CallbackContext):
    """Handle all telegram.ext errors"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

def main():
    """Main application entry point"""
    try:
        # Initialize database with error handling
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return

        if not TOKEN:
            logger.error("❌ Missing Telegram token! Check .env file")
            return

        updater = Updater(TOKEN)
        dp = updater.dispatcher

        # Add error handler
        dp.add_error_handler(error_handler)

        # Core commands
        dp.add_handler(CommandHandler('start', start))
        dp.add_handler(CommandHandler('setup', setup_group))

        # Add menu navigation
        dp.add_handler(CallbackQueryHandler(handle_menu_back, pattern=r"^menu_\d+$"))

        # Add feature handlers
        handlers = [
            welcome_handlers,
            message_deletion,
            warn_system,
            anti_spam,
            language_filter,
            banned_words,
            bio_protection
        ]
        
        for handlers in handlers:
            try:
                handlers.add_handlers(dp)
                logger.info(f"✅ Loaded {handler.__name__} handlers")
            except Exception as e:
                logger.error(f"❌ Error loading {handler.__name__}: {e}")

        logger.info("🤖 Bot started successfully")
        updater.start_polling()
        updater.idle()

    except Exception as e:
        logger.critical(f"❌ Fatal startup error: {e}")
        raise

if __name__ == '__main__':
    main()