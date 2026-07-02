import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from anthropic import Anthropic

# Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Claude Client
client = Anthropic()

# Conversation history (for context)
conversation_history = {}

# SYSTEM PROMPT – OPTIMIERT FÜR FRANCESCO
SYSTEM_PROMPT = """Du bist Claudian, Francescos persönlicher KI-Assistent.

**ÜBER FRANCESCO:**
- 19 Jahre alt, Brindisi, Italien
- Café + Online Business Entrepreneur
- Leidenschaft: AI, Business, Automation, Growth Hacking
- Personality: Locker, charmant, ehrlich, direkt, sarkastisch
- Priorität: Business > Gym > Friends

**DEIN STYLE (Antworte so):**
- Locker & charmant (keine Corporate Scheißdreck)
- Kurz & prägnant (Respekt vor Zeit)
- Actionable (nicht nur Theorie)
- Direkt & ehrlich (aber taktisch)
- Sarcasm erlaubt (aber nicht verletzend)
- Du (nicht Sie!)

**DEINE SKILLS (NUTZE SIE):**
60+ Skills: Financial Analysis, Business Strategy, Growth Hacking,
Pricing Strategy, Unit Economics, CAC/LTV, Cash Flow, Automation,
Code Analysis, Content Creation, KI Prompting, Leadership,
Negotiation, Sales & Closing, Personal Branding, und viele mehr.

**SEIN KONTEXT:**
- Café: Hohe Margin (60-70%), Focus auf Regulars/Loyalität
- Online: Sehr hohe Margin (80%+), aber Customer Acquisition kritisch
- Cash Flow: König (nicht Profit!)
- Business Rule: Data > Gut feeling. Business > alles
- Constraint: Erwartet komplette Zuverlässigkeit (keine Fehler)

**DEINE AUFGABE:**
1. Verstehe was er fragt (oder befiehlt)
2. Nutze relevante Skills aus deinem Arsenal
3. Antworte kurz, spezifisch, actionable
4. Wenn unklar: Rückfrag kurz
5. Gib konkrete Schritte (nicht generisch)

**NICHT:**
- Zu formal, zu viel Blabla, passive-aggressive
- False Modesty, Manipulativ
- 5-Seiten Antworten (kurz!)

**IMMER:**
- Lebendig wirken, zuverlässig, ehrlich
- Witze nur in seinem Humor-Style
- Data-backed recommendations"""

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""

    user_id = update.effective_user.id

    # Get voice file
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    # Download
    voice_path = f"/tmp/voice_{user_id}.ogg"
    await file.download_to_drive(voice_path)

    # Send "typing" indicator
    await update.effective_chat.send_action("typing")

    # Transcribe using Whisper
    try:
        with open(voice_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        user_message = transcript.text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        await update.message.reply_text("❌ Transkription fehlgeschlagen. Versuch nochmal.")
        return

    # Initialize history for user
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Add user message to history
    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    # Get Claude's response
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation_history[user_id]
        )

        assistant_message = response.content[0].text

        # Add to history
        conversation_history[user_id].append({
            "role": "assistant",
            "content": assistant_message
        })

        # Send response
        await update.message.reply_text(assistant_message)

    except Exception as e:
        logger.error(f"Claude error: {e}")
        await update.message.reply_text(f"❌ Fehler: {str(e)}")

    # Cleanup
    if os.path.exists(voice_path):
        os.remove(voice_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages too"""

    user_id = update.effective_user.id
    user_message = update.message.text

    # Initialize history
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Add message
    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    # Typing indicator
    await update.effective_chat.send_action("typing")

    # Get response
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation_history[user_id]
        )

        assistant_message = response.content[0].text

        conversation_history[user_id].append({
            "role": "assistant",
            "content": assistant_message
        })

        await update.message.reply_text(assistant_message)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    await update.message.reply_text(
        "🎙️ Sprich eine Voice-Message oder schreib Text.\n\n"
        "Ich bin dein AI-Assistent. Ich antworte schnell & prägnant.\n\n"
        "Ready? Go! 🚀"
    )

def main():
    """Start bot"""

    # Create application
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(MessageHandler(filters.COMMAND, start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start
    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
