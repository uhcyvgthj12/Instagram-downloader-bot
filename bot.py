import os
import re
import requests
import instaloader
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from bs4 import BeautifulSoup
from config import TELEGRAM_TOKEN, INSTAGRAM, BOT_SETTINGS
import time
from datetime import datetime, timedelta

# Initialize Instaloader
L = instaloader.Instaloader()
if INSTAGRAM["username"] and INSTAGRAM["password"]:
    try:
        L.login(INSTAGRAM["username"], INSTAGRAM["password"])
    except Exception as e:
        print(f"⚠️ Instagram login failed: {e}")

# User download tracking
user_downloads = {}

def check_rate_limit(user_id):
    """Check if user has exceeded rate limits"""
    now = datetime.now()
    
    # Reset daily counts
    if user_id in user_downloads:
        last_time = user_downloads[user_id]["last_time"]
        if now - last_time > timedelta(days=1):
            user_downloads[user_id]["daily_count"] = 0
    
    # Initialize user tracking
    if user_id not in user_downloads:
        user_downloads[user_id] = {
            "last_time": now,
            "daily_count": 0,
            "last_request": None
        }
    
    # Check daily limit
    if user_downloads[user_id]["daily_count"] >= BOT_SETTINGS["max_downloads_per_user"]:
        return False, "❌ You've reached your daily download limit. Try again tomorrow."
    
    # Check rate limit
    last_request = user_downloads[user_id]["last_request"]
    if last_request and (now - last_request).seconds < BOT_SETTINGS["rate_limit"]:
        wait_time = BOT_SETTINGS["rate_limit"] - (now - last_request).seconds
        return False, f"⏳ Please wait {wait_time} seconds before another request."
    
    # Update tracking
    user_downloads[user_id]["last_time"] = now
    user_downloads[user_id]["daily_count"] += 1
    user_downloads[user_id]["last_request"] = now
    
    return True, ""

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 **Instagram Downloader Bot**\n\n"
        "📌 **Send me an Instagram link to download:**\n"
        "- Posts (Photos & Videos)\n"
        "- Reels\n"
        "- IGTV\n"
        "- Stories (Public only)\n\n"
        "⚠️ **Note:** Private content requires Instagram login in config."
    )

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📖 **How to Use:**\n"
        "1. Send me a public Instagram post/reel/IGTV link\n"
        "2. I'll download and send you the media\n\n"
        "🔒 For private content, ensure the bot has Instagram credentials."
    )

def extract_media(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    message_text = update.message.text
    
    # Check rate limits
    allowed, message = check_rate_limit(user_id)
    if not allowed:
        update.message.reply_text(message)
        return
    
    # Validate Instagram URL
    if not re.match(r'https?://(www\.)?instagram\.com/(p|reel|tv|stories)/[a-zA-Z0-9_-]+/?', message_text):
        update.message.reply_text("❌ Invalid Instagram URL. Send a post/reel/IGTV link.")
        return
    
    try:
        update.message.reply_text("⏳ Downloading... Please wait.")
        
        shortcode = re.search(r'instagram\.com/(p|reel|tv|stories)/([a-zA-Z0-9_-]+)', message_text).group(2)
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        media_group = []
        caption = f"📥 **Downloaded via Instagram Bot**\n\n"
        
        if post.owner_username:
            caption += f"👤 @{post.owner_username}\n"
        if post.caption:
            caption += f"📝 {post.caption[:1000]}\n"
        
        # Single Image Post
        if not post.is_video and post.typename == 'GraphImage':
            filename = f"{post.owner_username}_{post.shortcode}"
            L.download_pic(filename, post.url, post.date_utc)
            update.message.reply_photo(photo=open(f"{filename}.jpg", 'rb'), caption=caption)
            os.remove(f"{filename}.jpg")
        
        # Video Post
        elif post.is_video:
            filename = f"{post.owner_username}_{post.shortcode}"
            L.download_pic(filename, post.url, post.date_utc)
            update.message.reply_video(video=open(f"{filename}.mp4", 'rb'), caption=caption)
            os.remove(f"{filename}.mp4")
        
        # Carousel (Multiple Images/Videos)
        elif post.typename == 'GraphSidecar':
            for i, node in enumerate(post.get_sidecar_nodes()):
                if node.is_video:
                    filename = f"{post.owner_username}_{post.shortcode}_{i}"
                    L.download_pic(filename, node.video_url, post.date_utc)
                    media_group.append(InputMediaVideo(media=open(f"{filename}.mp4", 'rb')))
                    os.remove(f"{filename}.mp4")
                else:
                    filename = f"{post.owner_username}_{post.shortcode}_{i}"
                    L.download_pic(filename, node.display_url, post.date_utc)
                    if i == 0:
                        media_group.append(InputMediaPhoto(media=open(f"{filename}.jpg", 'rb'), caption=caption))
                    else:
                        media_group.append(InputMediaPhoto(media=open(f"{filename}.jpg", 'rb')))
                    os.remove(f"{filename}.jpg")
            
            update.message.reply_media_group(media=media_group)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        update.message.reply_text("❌ Failed to download. The post may be private or invalid.")

def main():
    if not TELEGRAM_TOKEN:
        print("❌ Error: TELEGRAM_TOKEN not found!")
        return
    
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, extract_media))

    print("🤖 Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
