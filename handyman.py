import os
import io
import numpy as np
from PIL import Image
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

#cfg
TOKEN = '' #token
ASCII_CHARS = '@%#*+=-:. '[::-1]  # Dark to light
MAX_MESSAGE_LENGTH = 4096
MAX_WIDTH_FOR_MESSAGE = 100
DEFAULT_WIDTH = 120
SMALL_PREVIEW_WIDTH = 45 #60previnst

#I/O examples
EXAMPLE_INPUT_URL = "https://postimg.cc/G4mj54hD"  # Example input: Cat chonk chart
EXAMPLE_OUTPUT_URL = "https://postimg.cc/gxzMbM4k"  # Example output: ASCII art image


#def small_size_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #smolsizewidth =


#convertingtoasci
def image_to_ascii(image_path, width=DEFAULT_WIDTH):
    try:
        image = Image.open(image_path).convert('L')
        aspect_ratio = image.height / image.width
        height = int(aspect_ratio * width * 0.55)
        image = image.resize((width, height))
        pixels = np.array(image)
        normalized = pixels / 255.0
        indices = np.floor(normalized * (len(ASCII_CHARS) - 1)).astype(int)
        ascii_art = '\n'.join(''.join(ASCII_CHARS[idx] for idx in row) for row in indices)
        return ascii_art
    except Exception as e:
        raise RuntimeError(f"Failed to convert image: {e}")

#kbdbuttons(wip)
def get_main_menu():
    menu = [
        [KeyboardButton("Send Image")],
        [KeyboardButton("Help"), KeyboardButton("Settings")]
    ]
    return ReplyKeyboardMarkup(menu, resize_keyboard=True, one_time_keyboard=False)

def get_back_button():
    keyboard = [[InlineKeyboardButton("Back to Menu", callback_data='back_to_menu')]]
    return InlineKeyboardMarkup(keyboard)

#handling
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "*Welcome to ASCII Art Bot🫩*\n\n"
        "Send me any photo and I'll convert it to ASCII art.\n\n"
        "\n\n*Examples of how it works are shown below:*\n\n"
        "*(╯°□°)╯︵ ┻━┻ ︵ ╯(°□° ╯)*"


    )
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )

    # Example Input Image
    try:
        await update.message.reply_photo(
            photo=EXAMPLE_INPUT_URL,
            caption="*Send smth like this to me ;)*",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text("Example input image unavailable. Try sending your own!")
        print(f"Error sending input example: {e}")  # Log for debugging

    # Example Output (as image preview of ASCII art)
    try:
        await update.message.reply_photo(
            photo=EXAMPLE_OUTPUT_URL,
            caption="*And you will recieve a beautiful art like dat one!*",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text("Example output image unavailable. Try sending your own!")
        print(f"Error sending output example: {e}")  # Log for debugging

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*How to Use:*\n\n"
        "1. Tap *Send Image* or send a photo\n"
        "2. Wait for processing.\n"
        "3. Choose output:\n"
        "   • *Message* – in chat (if small)\n"
        "   • *Small Preview* – quick view\n"
        "   • *.txt File* – full quality\n\n"
        "Use /start to reset."
    )
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=get_back_button()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "Send Image":
        await update.message.reply_text(
            "Please send me an image now!",
            reply_markup=get_back_button()
        )
    elif text == "Help":
        await help_cmd(update, context)
    elif text == "Settings":
        await update.message.reply_text(
            "Settings: Custom width & characters (coming soon!)",
            reply_markup=get_back_button()
        )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"temp_{user.id}.jpg"
    await update.message.reply_chat_action("typing")
    try:
        await photo_file.download_to_drive(photo_path)
        status_msg = await update.message.reply_text("Converting to ASCII... Please wait.")

        # Generate versions
        ascii_full = image_to_ascii(photo_path, width=DEFAULT_WIDTH)
        ascii_msg = ascii_full if DEFAULT_WIDTH <= MAX_WIDTH_FOR_MESSAGE else image_to_ascii(photo_path, width=MAX_WIDTH_FOR_MESSAGE)
        ascii_small = image_to_ascii(photo_path, width=SMALL_PREVIEW_WIDTH)

        context.user_data.update({
            'ascii_full': ascii_full,
            'ascii_msg': ascii_msg,
            'ascii_small': ascii_small,
            'photo_path': photo_path
        })

        await status_msg.edit_text("Ready! Choose your output:")

        keyboard = [
            [
                InlineKeyboardButton("As Message", callback_data='send_msg'),
                InlineKeyboardButton("Small Preview" "(recommended for phones)\n", callback_data='send_small')
            ],
            [
                InlineKeyboardButton("Full .txt File", callback_data='send_txt'),
                InlineKeyboardButton("Back", callback_data='back_to_menu')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Size: ~{len(ascii_full.splitlines())} lines\n"
            "Choose format below:",
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}", reply_markup=get_back_button())
    finally:
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except:
                pass

async def send_output(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = context.user_data
    ascii_full = data.get('ascii_full')
    ascii_msg = data.get('ascii_msg')
    ascii_small = data.get('ascii_small')
    if not ascii_full:
        await query.edit_message_text("No image processed. Send one first.", reply_markup=get_back_button())
        return

    if query.data == 'send_txt':
        txt_buffer = io.BytesIO(ascii_full.encode('utf-8'))
        txt_buffer.name = "ascii_art.txt"
        await query.message.reply_chat_action("upload_document")
        await query.message.reply_document(
            document=txt_buffer,
            filename="ascii_art.txt",
            caption="Your full-resolution ASCII art!"
        )
        await query.edit_message_text("Sent as .txt file!", reply_markup=get_back_button())

    elif query.data == 'send_small':
        await query.message.reply_chat_action("typing")
        await query.message.reply_text(
            f"<pre><code class=\"language-txt\">{ascii_small}</code></pre>",
            parse_mode='HTML'
        )
        await query.edit_message_text("Small preview sent.", reply_markup=get_back_button())

    elif query.data == 'send_msg':
        if len(ascii_msg) < MAX_MESSAGE_LENGTH - 100:
            await query.message.reply_chat_action("typing")
            await query.message.reply_text(
                f"<pre><code class=\"language-txt\">{ascii_msg}</code></pre>",
                parse_mode='HTML'
            )
            await query.edit_message_text("Sent as message!", reply_markup=get_back_button())
        else:
            await query.edit_message_text("Too large for message! Sending as file...", reply_markup=get_back_button())
            txt_buffer = io.BytesIO(ascii_full.encode('utf-8'))
            txt_buffer.name = "ascii_art.txt"
            await query.message.reply_document(
                document=txt_buffer,
                caption="Too big for chat – sent as file"
            )
            await query.edit_message_text("Sent as .txt file!", reply_markup=get_back_button())

    elif query.data == 'back_to_menu':
        await query.edit_message_text("Returned to main menu.")
        await query.message.reply_text(
            "What would you like to do?",
            reply_markup=get_main_menu()
        )

#main
def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # Text buttons
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Image
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # Callbacks
    app.add_handler(CallbackQueryHandler(send_output, pattern='^(send_txt|send_msg|send_small|back_to_menu)$'))

    print("ASCII Art Bot is up & runnin")
    app.run_polling()

if __name__ == '__main__':
    main()
