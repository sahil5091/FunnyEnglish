import os
from flask import Flask, request
from telebot import TeleBot, types, util
from datetime import datetime, timedelta
import yt_dlp
from pymongo import MongoClient

# space details: U17GsXh3_3YdVyAmyGAf9eBnDBbsULi1DSNDUndoK
# Initialize the bot
token = "7139954972:AAHe9jeX3v5qH4b-_aO8KHfd7W3uMOXq69Q"
bot = TeleBot(token, parse_mode='html', threaded=False, disable_web_page_preview=True)
# Database connection
client = MongoClient('mongodb+srv://userlink:link12345@cluster0.fg2iaha.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client[bot.get_me().username]
coll2 = db["Active"]

# Ensure index on createdAt with expiration time
coll2.create_index("createdAt", expireAfterSeconds=600)
botid = bot.get_me().id
botusername = bot.get_me().username
app = Flask(__name__)

def check_user_joined_channel(user_id):
    try:
        chat_member = bot.get_chat_member(-1002204108339, user_id)  # Replace with your channel ID
        print(f"Chat member status: {chat_member.status}")
        if chat_member.status in ['member', 'administrator', 'creator', 'restricted']:
            return True
    except Exception as e:
        print(f"Error checking user joined channel: {e}")
    return False

def send_join_channel_message(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Done', callback_data='joined'))
    mention = util.user_link(message.from_user)
    bot.send_message(message.chat.id, f'Hello {mention}, please complete the following task to be able to use this bot:\n\n1. Join our <a href="https://t.me/twitterfunnyvideos">Partner channel</a>.\n\nThen click the "<b>Done</b>" button below.', reply_to_message_id=message.message_id, reply_markup=keyboard)

@bot.callback_query_handler(lambda call: call.data == "joined")
def joined(call: types.CallbackQuery):
    if check_user_joined_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "Thank you for joining! You can now use the bot.", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.from_user.id, "You can now use the bot. Send the Twitter video link to download.")
    else:
        bot.answer_callback_query(call.id, "Please join the channel before clicking this button!", show_alert=True)

@bot.message_handler(func=lambda message: True)
def handle_message(message: types.Message):
    if message.chat.type == 'private' and not check_user_joined_channel(message.from_user.id):
        send_join_channel_message(message)
        return
    if not coll2.find_one_and_delete({"_id": message.from_user.id}):
        coll2.insert_one({"_id": message.from_user.id, "createdAt": datetime.utcnow()})
        try:
            video_url = message.text
            if video_url.startswith('https://www.facebook.com/') or video_url.startswith('https://twitter.com/') or video_url.startswith('https://x.com/'):
                # Handling Facebook, Twitter, and X links with yt-dlp
                bot.send_chat_action(message.chat.id, 'upload_video')
                ydl_opts = {
                    'format': 'best',
                    'quiet': True,
                    'no_warnings': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(video_url, download=False)
                    video_format = next((f for f in info_dict['formats'] if f.get('acodec') != 'none' and f.get('vcodec') != 'none'), None)

                    if video_format:
                        keyboard = types.InlineKeyboardMarkup()
                        bot_link_button = types.InlineKeyboardButton('Visit @twittermemebot', url='https://t.me/twittermemebot')
                        keyboard.add(bot_link_button)
                        final_video_url = video_format['url']
                        title = info_dict.get('title', 'No title')
                        caption = f"<b>{title}</b>\n"
                        bot.send_video(-1002204108339, final_video_url, caption=caption, parse_mode='HTML')
                        bot.send_message(message.chat.id, "✅ Video successfully forwarded to https://t.me/twitterfunnyvideos.", reply_to_message_id=message.message_id)
                        bot.send_message(-1002204108339, "Send Yours Funny Video",reply_markup=keyboard)
                        coll2.delete_one({"_id": message.from_user.id})
                    else:
                        bot.send_message(message.chat.id, "⚠️ Video unavailable.", reply_to_message_id=message.message_id)
                        coll2.delete_one({"_id": message.from_user.id})
            else:
                bot.send_message(message.chat.id, "Send me a link", reply_to_message_id=message.message_id)
                coll2.delete_one({"_id": message.from_user.id})
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ An error occurred: {str(e)}", reply_to_message_id=message.message_id)
            print(f"Error: {e}")
            coll2.delete_one({"_id": message.from_user.id})      
    else:
        coll2.delete_one({"_id": message.from_user.id})

@app.route('/' + token, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    url = os.getenv('VERCEL_PROJECT_PRODUCTION_URL')
    bot.set_webhook(url= f"{url}/{token}", max_connections=50)
    return "!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))