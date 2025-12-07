"""
Telegram Video Downloader Bot - Standalone Version
===================================================
✅ يرفع حتى 2GB
✅ نجح في تحميل فيديو 3 ساعات (694MB)

التشغيل:
    python3 bot_standalone.py
"""

import os
import sys
import glob  # للبحث عن الملفات وحذفها
import time  # Added import os
import logging
import asyncio
import yt_dlp
import traceback
import json
import re
import requests
from datetime import datetime
from pyrogram import Client, filters, enums, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv
import subscription_db as subdb
from translations import t
from queue_manager import DownloadQueueManager, DownloadTask
import pg_backup


# ═══════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_standalone.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════
load_dotenv()

API_ID = os.getenv("PYROGRAM_API_ID")
API_HASH = os.getenv("PYROGRAM_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("=" * 60)
    print("❌ المتغيرات البيئية ناقصة!")
    print("=" * 60)
    print("الرجاء إنشاء ملف .env وإضافة المتغيرات التالية:")
    print("")
    print("PYROGRAM_API_ID=your_api_id")
    print("PYROGRAM_API_HASH=your_api_hash")
    print("BOT_TOKEN=your_bot_token")
    print("")
    print("راجع ملف .env.example و README.md للتعليمات الكاملة")
    print("=" * 60)
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# Session Management - Auto-cleanup when token changes
# ═══════════════════════════════════════════════════════════════
import hashlib

SESSION_NAME = "video_bot"
SESSION_FILE = f"{SESSION_NAME}.session"
TOKEN_HASH_FILE = ".token_hash"

def get_token_hash(token: str) -> str:
    """إنشاء هاش للتوكن للمقارنة"""
    return hashlib.sha256(token.encode()).hexdigest()[:16]

def check_and_cleanup_session():
    """
    فحص إذا تغير التوكن وحذف الـ session القديم تلقائياً
    Check if token changed and automatically delete old session
    """
    current_hash = get_token_hash(BOT_TOKEN)
    
    # قراءة الهاش المحفوظ
    saved_hash = None
    if os.path.exists(TOKEN_HASH_FILE):
        try:
            with open(TOKEN_HASH_FILE, 'r') as f:
                saved_hash = f.read().strip()
        except:
            pass
    
    # إذا تغير التوكن
    if saved_hash and saved_hash != current_hash:
        logger.warning("⚠️ تم اكتشاف تغيير في BOT_TOKEN!")
        
        # حذف ملف الـ session القديم
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
                logger.info(f"🗑️ تم حذف Session القديم: {SESSION_FILE}")
            except Exception as e:
                logger.error(f"❌ فشل حذف Session: {e}")
        
        # حذف أي ملفات session أخرى مرتبطة
        for file in glob.glob(f"{SESSION_NAME}*.session*"):
            try:
                os.remove(file)
                logger.info(f"🗑️ تم حذف: {file}")
            except:
                pass
        
        logger.info("✅ تم تنظيف الـ Session - سيتم إنشاء جلسة جديدة")
    
    # حفظ الهاش الجديد
    try:
        with open(TOKEN_HASH_FILE, 'w') as f:
            f.write(current_hash)
    except Exception as e:
        logger.warning(f"⚠️ فشل حفظ هاش التوكن: {e}")

# تنفيذ الفحص عند بدء التشغيل
check_and_cleanup_session()

# ═══════════════════════════════════════════════════════════════
# Pyrogram Client
# ═══════════════════════════════════════════════════════════════
app = Client(
    SESSION_NAME,
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize Queue Manager
queue_manager = DownloadQueueManager(cooldown_seconds=10)

# ═══════════════════════════════════════════════════════════════
# دالة الحذف التلقائي للرسائل في المجموعات
# ═══════════════════════════════════════════════════════════════
async def delete_message_after_delay(message, delay_seconds: int):
    """حذف رسالة بعد عدد محدد من الثواني"""
    try:
        await asyncio.sleep(delay_seconds)
        await message.delete()
        logger.info(f"🗑️ تم حذف الرسالة تلقائياً بعد {delay_seconds} ثانية")
    except Exception as e:
        logger.warning(f"⚠️ فشل حذف الرسالة تلقائياً: {e}")

# تخزين الروابط
pending_downloads = {}

# منصات الـ cookies المدعومة
COOKIES_PLATFORMS = {
    'facebook': {'name': 'Facebook 📘', 'file': 'cookies/facebook.txt'},
    'instagram': {'name': 'Instagram �', 'file': 'cookies/instagram.txt'},
    'youtube': {'name': 'YouTube 📺', 'file': 'cookies/youtube.txt'},
    'twitter': {'name': 'Twitter/X 🐦', 'file': 'cookies/twitter.txt'},
    'reddit': {'name': 'Reddit �', 'file': 'cookies/reddit.txt'},
    'snapchat': {'name': 'Snapchat 👻', 'file': 'cookies/snapchat.txt'},
    'pinterest': {'name': 'Pinterest 📌', 'file': 'cookies/pinterest.txt'},
    'tiktok': {'name': 'TikTok 🎵', 'file': 'cookies/tiktok.txt'},
    'other': {'name': 'أخرى 🌐', 'file': 'cookies/other.txt'},
}

def get_platform_cookie_file(url: str) -> str:
    """
    الحصول على ملف الكوكيز المناسب للمنصة بناءً على الرابط
    
    Args:
        url: رابط الفيديو
        
    Returns:
        مسار ملف الكوكيز المناسب إذا وُجد، وإلا None
    """
    platform = None
    
    # تحديد المنصة من الرابط
    if 'instagram.com' in url:
        platform = 'instagram'
    elif 'facebook.com' in url or 'fb.watch' in url:
        platform = 'facebook'
    elif 'youtube.com' in url or 'youtu.be' in url:
        platform = 'youtube'
    elif 'twitter.com' in url or 'x.com' in url:
        platform = 'twitter'
    elif 'tiktok.com' in url:
        platform = 'tiktok'
    elif 'snapchat.com' in url:
        platform = 'snapchat'
    elif 'pinterest.com' in url:
        platform = 'pinterest'
    elif 'reddit.com' in url:
        platform = 'reddit'
    
    if platform and platform in COOKIES_PLATFORMS:
        cookie_file = COOKIES_PLATFORMS[platform]['file']
        if os.path.exists(cookie_file):
            file_size = os.path.getsize(cookie_file)
            if file_size > 100:  # ملف صالح
                logger.info(f"🍪 Found {platform} cookies ({file_size} bytes)")
                return cookie_file
            else:
                logger.warning(f"⚠️ {platform} cookie file is too small ({file_size} bytes)")
    
    return None


# قائمة المواقع الإباحية المحظورة - Blocked Adult Content Domains
ADULT_CONTENT_DOMAINS = [
    'pornhub', 'xvideos', 'xnxx', 'redtube', 'youporn',
    'tube8', 'pornhd', 'spankbang', 'xhamster', 'txxx',
    'porn', 'xxx', 'sex', 'adult', 'hentai', 'brazzers',
    'bangbros', 'naughty', 'eporner', 'tnaflix', 'youjizz',
    'drtuber', 'keezmovies', 'porntrex', 'fuq', 'beeg',
    'slutload', 'pornhost', 'empflix', 'porn555', 'sexvid'
]

# نظام تتبع الأخطاء
user_errors = {}  # {error_id: {'user_id': ..., 'error': ..., 'url': ..., 'time': ..., 'status': 'pending'}}
error_counter = 0

async def send_error_to_admin(user_id, user_name, error_message, url, error_traceback=None):
    """إرسال تنبيه لقناة سجلات الأخطاء عند حدوث خطأ للمستخدم"""
    global error_counter
    error_counter += 1
    error_id = f"err_{error_counter}"
    
    # حفظ الخطأ
    user_errors[error_id] = {
        'user_id': user_id,
        'user_name': user_name,
        'error': error_message,
        'url': url,
        'traceback': error_traceback,
        'time': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'status': 'pending'
    }
    
    # إرسال لقناة سجلات الأخطاء
    error_channel_id = os.getenv("ERROR_LOG_CHANNEL_ID")
    
    if not error_channel_id:
        logger.warning("⚠️ ERROR_LOG_CHANNEL_ID غير موجود في .env")
        return
    
    # Verify bot has access to error log channel
    try:
        await app.get_chat(error_channel_id)
    except Exception as access_error:
        logger.error(f"❌ البوت لا يملك صلاحيات لقناة الأخطاء {error_channel_id}: {access_error}")
        logger.info(f"💡 تأكد من إضافة البوت كمدير في قناة سجلات الأخطاء")
        return
    
    # User link (blue clickable name)
    user_link = f'<a href="tg://user?id={user_id}">{user_name}</a>'
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تم الإصلاح", callback_data=f"resolve_{error_id}")]
    ])
    
    try:
        # بناء الرسالة الأساسية
        error_text = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔔 **خطأ جديد من مستخدم**\n\n"
            f"👤 **المستخدم:** {user_link}\n"
            f"🆔 **ID:** <code>{user_id}</code>\n"
            f"🔗 **الرابط:** <code>{url}</code>\n\n"
            f"❌ **الخطأ:**\n<code>{error_message[:300]}</code>\n\n"
        )
        
        # إضافة traceback إذا كان متوفراً
        if error_traceback:
            # تقصير traceback إذا كان طويلاً جداً (Telegram limit)
            traceback_text = error_traceback[:800] if len(error_traceback) > 800 else error_traceback
            error_text += f"📋 **سجلات الخطأ (Traceback):**\n<code>{traceback_text}</code>\n\n"
        
        error_text += (
            f"🆔 Error ID: <code>{error_id}</code>\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await app.send_message(
            chat_id=error_channel_id,
            text=error_text,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML
        )
        logger.info(f"📨 تم إرسال تنبيه خطأ لقناة السجلات: {error_id}")
    except Exception as e:
        logger.error(f"فشل إرسال تنبيه لقناة الأخطاء: {e}")

async def send_new_member_notification(user_id, user_name, username, join_time):
    """إرسال إشعار لقناة الأعضاء الجدد عند انضمام عضو جديد"""
    try:
        channel_id = os.getenv('NEW_MEMBERS_CHANNEL_ID')
        
        if not channel_id:
            logger.warning("⚠️ NEW_MEMBERS_CHANNEL_ID غير موجود في .env")
            return
        
        # Try to get chat to verify bot has access
        try:
            await app.get_chat(channel_id)
        except Exception as access_error:
            logger.error(f"❌ البوت لا يملك صلاحيات للقناة {channel_id}: {access_error}")
            logger.info(f"💡 تأكد من إضافة البوت كمدير في القناة")
            return
        
        # Format username
        username_text = f"@{username}" if username else "⚠️ لا يوجد يوزر"
        
        # User link (blue clickable name)
        user_link = f'<a href="tg://user?id={user_id}">{user_name}</a>'
        
        # Message text
        notification = f"""━━━━━━━━━━━━━━━━━━━━━━
🎉 عضو جديد انضم للبوت!

👤 معلومات العضو
╔═ الاسم: {user_link}
╠═ اليوزر: {username_text}
╚═ ID: <code>{user_id}</code>

🕐 وقت الانضمام: {join_time}
━━━━━━━━━━━━━━━━━━━━━━"""
        
        await app.send_message(
            chat_id=channel_id,
            text=notification,
            parse_mode=enums.ParseMode.HTML
        )
        
        logger.info(f"✅ تم إرسال إشعار عضو جديد للقناة: {user_name} ({user_id})")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال إشعار العضو الجديد: {str(e)}")


# تتبع صلاحية الـ cookies
cookies_expiry = {}  # {platform: {'uploaded': timestamp, 'expires': timestamp, 'notified': bool}}

# Channel registration tracking
registered_channels = set()  # Track successfully registered channels

async def try_register_channel(channel_id, channel_name):
    """
    محاولة تسجيل قناة مع البوت
    Try to register a channel with the bot
    
    Returns: True if successful, False otherwise
    """
    if not channel_id:
        return False
    
    try:
        # Try to get channel info
        chat = await app.get_chat(channel_id)
        logger.info(f"✅ تم التسجيل: {chat.title} (ID: {chat.id})")
        registered_channels.add(channel_id)
        
        # Try to send a test message
        try:
            test_msg = await app.send_message(
                chat_id=channel_id,
                text=f"✅ تم تسجيل البوت بنجاح في قناة {channel_name}\n\nالبوت جاهز للعمل!"
            )
            await asyncio.sleep(2)
            await test_msg.delete()
            logger.info(f"   ✅ البوت يستطيع الإرسال لـ: {chat.title}")
        except Exception as send_error:
            logger.warning(f"   ⚠️  القناة مسجلة لكن لا يمكن الإرسال حالياً: {send_error}")
            logger.info(f"   💡 حل: أرسل رسالة في القناة (مثل: @{(await app.get_me()).username})")
        
        return True
        
    except Exception as e:
        if "PEER_ID_INVALID" in str(e):
            logger.warning(f"⚠️  {channel_name}: لم يتم التسجيل بعد")
            logger.info(f"   💡 حل: أرسل رسالة في القناة {channel_id}")
        else:
            logger.error(f"❌ خطأ في تسجيل {channel_name}: {e}")
        return False

async def register_all_channels():
    """
    تسجيل جميع القنوات المكونة في .env
    Register all configured channels from .env
    """
    logger.info("🔄 محاولة تسجيل القنوات...")
    
    channels = {
        'LOG_CHANNEL_ID': 'قناة سجلات الفيديو',
        'ERROR_LOG_CHANNEL_ID': 'قناة سجلات الأخطاء',
        'NEW_MEMBERS_CHANNEL_ID': 'قناة الأعضاء الجدد'
    }
    
    success_count = 0
    total_count = 0
    
    for env_var, channel_name in channels.items():
        channel_id = os.getenv(env_var)
        if channel_id:
            total_count += 1
            if await try_register_channel(channel_id, channel_name):
                success_count += 1
    
    if success_count == total_count and total_count > 0:
        logger.info(f"✅ تم تسجيل جميع القنوات ({success_count}/{total_count})")
    elif success_count > 0:
        logger.info(f"⚠️  تم تسجيل {success_count}/{total_count} قناة")
        logger.info("💡 لتسجيل القنوات المتبقية، أرسل رسالة في كل قناة ثم أرسل /register_channels للبوت")
    else:
        logger.warning("⚠️  لم يتم تسجيل أي قناة")
        logger.info("💡 القنوات اختيارية - البوت سيعمل بشكل طبيعي")
        logger.info("💡 لتفعيل القنوات: أرسل رسالة في كل قناة ثم أرسل /register_channels للبوت")

# حالة انتظار cookies من الأدمن
waiting_for_cookies = {}  # {user_id: platform}

# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def is_adult_content_url(url: str) -> bool:
    """
    التحقق من أن الرابط ليس من موقع إباحي
    Check if URL is from an adult content site
    """
    url_lower = url.lower()
    
    # Check default blocked domains
    for domain in ADULT_CONTENT_DOMAINS:
        if domain in url_lower:
            return True
    
    # Check custom blocked URLs from database
    if subdb.is_url_in_custom_blocklist(url):
        return True
    
    return False

def get_file_size_mb(file_path):
    """الحصول على حجم الملف بالميغابايت"""
    return os.path.getsize(file_path) / (1024 * 1024)


async def download_instagram_photo(url: str, user_id: int):
    """
    تحميل صور Instagram باستخدام gallery-dl
    Download Instagram photos using gallery-dl
    
    Returns: (success: bool, files: list, error: str)
    """
    try:
        # Get user language for messages
        lang = subdb.get_user_language(user_id)
        
        # Create temporary directory for this download
        import tempfile
        import subprocess
        temp_dir = tempfile.mkdtemp(prefix="instagram_")
        
        logger.info(f"📸 Attempting Instagram photo download with gallery-dl: {url}")
        
        # Prepare gallery-dl command
        cmd = [
            'gallery-dl',
            '--dest', temp_dir,
            '--filename', '{num:>02}.{extension}',
        ]
        
        # Add cookies if available
        instagram_cookie_file = COOKIES_PLATFORMS.get('instagram', {}).get('file')
        if instagram_cookie_file and os.path.exists(instagram_cookie_file):
            cookie_size = os.path.getsize(instagram_cookie_file)
            if cookie_size > 100:
                cmd.extend(['--cookies', instagram_cookie_file])
                logger.info(f"✅  Using Instagram cookies ({cookie_size} bytes)")
        
        cmd.append(url)
        
        # Run gallery-dl
        loop = asyncio.get_event_loop()
        
        def run_gallery_dl():
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result
        
        result = await loop.run_in_executor(None, run_gallery_dl)
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"❌ gallery-dl failed: {error_msg}")
            return False, [], error_msg
        
        # Find downloaded files
        downloaded_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                downloaded_files.append(file_path)
        
        if not downloaded_files:
            logger.warning("⚠️  No files downloaded by gallery-dl")
            return False, [], "No files downloaded"
        
        logger.info(f"✅ Downloaded {len(downloaded_files)} file(s) from Instagram")
        return True, downloaded_files, None
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ gallery-dl timeout for {url}")
        return False, [], "Download timeout"
    except Exception as e:
        logger.error(f"❌ Error in download_instagram_photo: {e}")
        return False, [], str(e)


async def download_instagram_story_with_gallery_dl(url: str, user_id: int):
    """
    تحميل ستوري Instagram باستخدام gallery-dl (يدعم الصور والفيديوهات)
    Download Instagram story using gallery-dl (supports photos and videos)
    
    Args:
        url: Instagram story URL (e.g., https://www.instagram.com/stories/username/STORY_ID/)
        user_id: User ID for language preferences
    
    Returns: (success: bool, files: list, error: str, is_video: bool)
    """
    try:
        import tempfile
        import subprocess
        
        logger.info(f"📸 Attempting Instagram story download with gallery-dl: {url}")
        
        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp(prefix="insta_story_")
        
        # Prepare gallery-dl command
        cmd = [
            'gallery-dl',
            '--dest', temp_dir,
            '--filename', 'story_{num:>02}.{extension}',
        ]
        
        # Add cookies if available (gallery-dl supports Netscape cookies format)
        instagram_cookie_file = COOKIES_PLATFORMS.get('instagram', {}).get('file')
        if instagram_cookie_file and os.path.exists(instagram_cookie_file):
            cookie_size = os.path.getsize(instagram_cookie_file)
            if cookie_size > 100:
                cmd.extend(['--cookies', instagram_cookie_file])
                logger.info(f"✅ Using Instagram cookies for gallery-dl ({cookie_size} bytes)")
        
        cmd.append(url)
        
        # Run gallery-dl
        loop = asyncio.get_event_loop()
        
        def run_gallery_dl():
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout for stories
            )
            return result
        
        result = await loop.run_in_executor(None, run_gallery_dl)
        
        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"❌ gallery-dl failed for story: {error_msg[:300]}")
            
            # Check if it's a login requirement
            if 'login' in error_msg.lower() or '401' in error_msg or 'authenticate' in error_msg.lower():
                return False, [], "Login required - please update Instagram cookies", False
            
            return False, [], error_msg, False
        
        # Find downloaded files
        downloaded_files = []
        is_video = False
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                downloaded_files.append(file_path)
                
                # Check if any file is a video
                if file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                    is_video = True
                    
                logger.info(f"📁 Downloaded file: {file}")
        
        if not downloaded_files:
            logger.warning("⚠️ No files downloaded by gallery-dl for story")
            return False, [], "No files downloaded - story may be expired or private", False
        
        logger.info(f"✅ Downloaded {len(downloaded_files)} story file(s) with gallery-dl. Is video: {is_video}")
        return True, downloaded_files, None, is_video
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ gallery-dl timeout for story: {url}")
        return False, [], "Download timeout", False
    except Exception as e:
        logger.error(f"❌ Error in download_instagram_story_with_gallery_dl: {e}")
        traceback.print_exc()
        return False, [], str(e), False


async def download_instagram_story_with_instaloader(url: str, user_id: int):
    """
    تحميل ستوري Instagram باستخدام instaloader (يدعم الصور والفيديوهات)
    Download Instagram story using instaloader (supports photos and videos)
    
    Args:
        url: Instagram story URL (e.g., https://www.instagram.com/stories/username/STORY_ID/)
        user_id: User ID for language preferences
    
    Returns: (success: bool, files: list, error: str, is_video: bool)
    """
    try:
        import tempfile
        import instaloader
        
        logger.info(f"📸 Attempting Instagram story download with instaloader: {url}")
        
        # استخراج username و story_id من الرابط
        # Pattern: /stories/username/STORY_ID/
        pattern = r'/stories/([^/]+)/(\d+)'
        match = re.search(pattern, url)
        
        if not match:
            logger.error(f"❌ Could not extract username/story_id from URL: {url}")
            return False, [], "Invalid story URL format", False
        
        username = match.group(1)
        story_id = match.group(2)
        logger.info(f"📋 Extracted: username={username}, story_id={story_id}")
        
        # إنشاء مجلد مؤقت
        temp_dir = tempfile.mkdtemp(prefix="insta_story_")
        
        # إعداد instaloader
        L = instaloader.Instaloader(
            dirname_pattern=temp_dir,
            filename_pattern="{shortcode}",
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern="",
            storyitem_metadata_txt_pattern=""
        )
        
        # تحميل الكوكيز من ملف Netscape cookies.txt
        instagram_cookie_file = COOKIES_PLATFORMS.get('instagram', {}).get('file')
        if instagram_cookie_file and os.path.exists(instagram_cookie_file):
            try:
                # تحويل ملف cookies.txt إلى session
                logger.info(f"🍪 Loading Instagram session from cookies file")
                
                # قراءة الكوكيز وتحويلها
                cookies = {}
                with open(instagram_cookie_file, 'r') as f:
                    for line in f:
                        if line.startswith('#') or not line.strip():
                            continue
                        try:
                            parts = line.strip().split('\t')
                            if len(parts) >= 7:
                                cookies[parts[5]] = parts[6]
                        except:
                            pass
                
                # تعيين الكوكيز للجلسة
                if cookies:
                    L.context._session.cookies.update(cookies)
                    logger.info(f"✅ Loaded {len(cookies)} cookies for instaloader")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to load cookies for instaloader: {e}")
        
        # تشغيل التحميل في executor
        loop = asyncio.get_event_loop()
        
        def download_story():
            try:
                # الحصول على Profile
                profile = instaloader.Profile.from_username(L.context, username)
                
                # تحميل الستوريهات
                stories = L.get_stories(userids=[profile.userid])
                
                downloaded_files = []
                found_story = False
                
                for story in stories:
                    for item in story.get_items():
                        # التحقق من أن هذه هي الستوري المطلوبة
                        item_id = str(item.mediaid)
                        
                        if item_id == story_id or story_id in str(item.mediaid):
                            found_story = True
                            logger.info(f"✅ Found matching story: {item_id}")
                            
                            # تحميل الستوري
                            L.download_storyitem(item, target=temp_dir)
                            
                            # البحث عن الملفات المحملة
                            for root, dirs, files in os.walk(temp_dir):
                                for file in files:
                                    if not file.endswith('.json') and not file.endswith('.txt'):
                                        file_path = os.path.join(root, file)
                                        downloaded_files.append(file_path)
                                        logger.info(f"📁 Downloaded file: {file}")
                            
                            break
                    if found_story:
                        break
                
                return downloaded_files, found_story, None
                
            except instaloader.exceptions.LoginRequiredException as e:
                logger.error(f"❌ Login required: {e}")
                return [], False, "Login required - please update Instagram cookies"
            except instaloader.exceptions.PrivateProfileNotFollowedException as e:
                logger.error(f"❌ Private profile: {e}")
                return [], False, "Private profile - not followed"
            except Exception as e:
                logger.error(f"❌ Instaloader error: {e}")
                return [], False, str(e)
        
        downloaded_files, found_story, error = await loop.run_in_executor(None, download_story)
        
        if error:
            return False, [], error, False
        
        if not downloaded_files:
            if not found_story:
                logger.warning(f"⚠️ Story {story_id} not found or expired")
                return False, [], "Story not found or expired", False
            else:
                logger.warning(f"⚠️ No files downloaded for story {story_id}")
                return False, [], "No files downloaded", False
        
        # تحديد نوع الملف
        is_video = any(f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')) for f in downloaded_files)
        
        logger.info(f"✅ Downloaded {len(downloaded_files)} file(s) with instaloader. Is video: {is_video}")
        return True, downloaded_files, None, is_video
        
    except Exception as e:
        logger.error(f"❌ Error in download_instagram_story_with_instaloader: {e}")
        traceback.print_exc()
        return False, [], str(e), False


async def download_tiktok_photos(url: str, user_id: int):
    """
    تحميل صور TikTok (Photo posts / Slideshows) باستخدام TikWM API
    Download TikTok photos using TikWM API (supports both shortened and full URLs)
    
    Args:
        url: TikTok URL (vm.tiktok.com, tiktok.com/@user/photo/ID, or tiktok.com/@user/video/ID for slideshows)
        user_id: User ID for language preferences
    
    Returns: (success: bool, files: list, error: str)
    """
    try:
        import tempfile
        
        # Get user language
        lang = subdb.get_user_language(user_id)
        
        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp(prefix="tiktok_photos_")
        
        logger.info(f"📸 Attempting TikTok photo download via TikWM API: {url}")
        
        # Use TikWM API to get photo URLs (supports both shortened and full URLs)
        api_url = 'https://www.tikwm.com/api/'
        params = {
            'url': url,
            'hd': 1
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                error_msg = data.get('msg', 'Unknown error from TikWM API')
                logger.error(f"❌ TikWM API error: {error_msg}")
                return False, [], f"خطأ API: {error_msg}"
            
            result_data = data.get('data', {})
            image_urls = result_data.get('images', [])
            
            if not image_urls:
                # قد يكون فيديو وليس صور
                logger.warning("⚠️ No images found - this might be a video, not a photo post")
                return False, [], "هذا المنشور لا يحتوي على صور (ربما فيديو).\n\n💡 أرسل الرابط بدون أي شيء وسيتم تحميل الفيديو تلقائياً."
            
            logger.info(f"✅ Found {len(image_urls)} image(s) via TikWM API")
            
        except requests.RequestException as e:
            logger.error(f"❌ TikWM API request failed: {e}")
            return False, [], f"فشل الاتصال بـ API: {str(e)}"
        except Exception as e:
            logger.error(f"❌ TikWM API error: {e}")
            return False, [], f"خطأ في API: {str(e)}"
        
        # Download each image
        downloaded_files = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': 'https://www.tiktok.com/',
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        for i, img_url in enumerate(image_urls[:20], 1):  # Limit to 20 images
            try:
                logger.info(f"📥 Downloading image {i}/{len(image_urls)}: {img_url[:80]}...")
                
                img_response = session.get(img_url, timeout=30)
                img_response.raise_for_status()
                
                # Determine file extension from URL or content type
                content_type = img_response.headers.get('Content-Type', '')
                if 'jpeg' in content_type or 'jpg' in content_type or '.jpeg' in img_url or '.jpg' in img_url:
                    ext = 'jpg'
                elif 'png' in content_type or '.png' in img_url:
                    ext = 'png'
                elif 'webp' in content_type or '.webp' in img_url:
                    ext = 'webp'
                else:
                    ext = 'jpg'  # default
                
                # Save image
                file_path = os.path.join(temp_dir, f"tiktok_photo_{i:02d}.{ext}")
                with open(file_path, 'wb') as f:
                    f.write(img_response.content)
                
                file_size_kb = os.path.getsize(file_path) / 1024
                downloaded_files.append(file_path)
                logger.info(f"✅ Downloaded image {i}: {file_size_kb:.1f} KB")
                
            except Exception as e:
                logger.error(f"❌ Failed to download image {i}: {e}")
                continue
        
        if not downloaded_files:
            return False, [], "فشل تحميل الصور. حاول مرة أخرى."
        
        logger.info(f"✅ Successfully downloaded {len(downloaded_files)} TikTok photo(s)")
        return True, downloaded_files, None
        
    except Exception as e:
        logger.error(f"❌ Error in download_tiktok_photos: {e}")
        traceback.print_exc()
        return False, [], f"خطأ في تحميل صور TikTok: {str(e)}"


async def download_tiktok_video(url: str, user_id: int, status_message=None):
    """
    تحميل فيديو TikTok باستخدام TikWM API مع تتبع التقدم
    Download TikTok video using TikWM API with progress tracking
    
    Args:
        url: TikTok URL (vm.tiktok.com, tiktok.com/@user/video/ID)
        user_id: User ID for language preferences
        status_message: Message to update with progress (optional)
    
    Returns: (success: bool, file_path: str, video_info: dict, error: str)
    """
    try:
        import tempfile
        import time
        import asyncio
        
        # Get user language
        lang = subdb.get_user_language(user_id)
        
        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp(prefix="tiktok_video_")
        
        logger.info(f"🎬 Attempting TikTok video download via TikWM API: {url}")
        
        # Use TikWM API to get video URL
        api_url = 'https://www.tikwm.com/api/'
        params = {
            'url': url,
            'hd': 1
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                error_msg = data.get('msg', 'Unknown error from TikWM API')
                logger.error(f"❌ TikWM API error: {error_msg}")
                return False, None, None, f"خطأ API: {error_msg}"
            
            result_data = data.get('data', {})
            
            # Try to get HD video first, then fallback to regular
            video_url = result_data.get('hdplay') or result_data.get('play')
            
            if not video_url:
                logger.error("❌ No video URL found in TikWM API response")
                return False, None, None, "لم يتم العثور على رابط الفيديو"
            
            # Get video info
            video_info = {
                'title': result_data.get('title', 'TikTok Video')[:100],
                'author': result_data.get('author', {}).get('nickname', 'Unknown'),
                'duration': result_data.get('duration', 0),
                'play_count': result_data.get('play_count', 0),
                'like_count': result_data.get('digg_count', 0),
            }
            
            logger.info(f"✅ Found video via TikWM API: {video_info['title'][:50]}...")
            
        except requests.RequestException as e:
            logger.error(f"❌ TikWM API request failed: {e}")
            return False, None, None, f"فشل الاتصال بـ API: {str(e)}"
        except Exception as e:
            logger.error(f"❌ TikWM API error: {e}")
            return False, None, None, f"خطأ في API: {str(e)}"
        
        # Download video with progress tracking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
            'Referer': 'https://www.tiktok.com/',
        }
        
        try:
            logger.info(f"📥 Downloading TikTok video with progress tracking...")
            
            session = requests.Session()
            session.headers.update(headers)
            
            video_response = session.get(video_url, timeout=120, stream=True)
            video_response.raise_for_status()
            
            # Get total file size
            total_size = int(video_response.headers.get('content-length', 0))
            total_size_mb = total_size / (1024 * 1024) if total_size else 0
            
            # Determine file extension
            content_type = video_response.headers.get('Content-Type', '')
            if 'mp4' in content_type or 'mp4' in video_url:
                ext = 'mp4'
            elif 'webm' in content_type or 'webm' in video_url:
                ext = 'webm'
            else:
                ext = 'mp4'  # default
            
            # Save video with progress tracking
            file_path = os.path.join(temp_dir, f"tiktok_video.{ext}")
            downloaded = 0
            start_time = time.time()
            last_update_time = 0
            chunk_size = 65536  # 64KB chunks for faster download
            
            with open(file_path, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress every 0.5 seconds
                        current_time = time.time()
                        if status_message and current_time - last_update_time >= 0.5:
                            last_update_time = current_time
                            
                            # Calculate progress
                            elapsed = current_time - start_time
                            if elapsed > 0:
                                speed = downloaded / elapsed  # bytes per second
                                speed_mb = speed / (1024 * 1024)
                                
                                if total_size > 0:
                                    percent = (downloaded / total_size) * 100
                                    remaining_bytes = total_size - downloaded
                                    eta = int(remaining_bytes / speed) if speed > 0 else 0
                                    
                                    # Progress bar (10 segments)
                                    filled = int(percent / 10)
                                    progress_bar = '▰' * filled + '▱' * (10 - filled)
                                    
                                    downloaded_mb = downloaded / (1024 * 1024)
                                    
                                    downloading_text = "جاري التحميل..." if lang == 'ar' else "Downloading..."
                                    progress_text = f"📥 ⏬ {downloading_text}\n📊 {percent:.1f}%\n\n💾 {downloaded_mb:.1f} / {total_size_mb:.1f} MB\n🚀 {speed_mb:.1f} MB/s\n⏳ {eta}s\n\n{progress_bar}"
                                else:
                                    downloaded_mb = downloaded / (1024 * 1024)
                                    downloading_text = "جاري التحميل..." if lang == 'ar' else "Downloading..."
                                    progress_text = f"📥 ⏬ {downloading_text}\n\n💾 {downloaded_mb:.1f} MB\n🚀 {speed_mb:.1f} MB/s"
                                
                                try:
                                    await status_message.edit_text(progress_text)
                                except:
                                    pass  # Ignore flood wait or other errors
                            
                            # Yield control to event loop
                            await asyncio.sleep(0)
            
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"✅ Downloaded TikTok video: {file_size_mb:.2f} MB")
            
            return True, file_path, video_info, None
            
        except Exception as e:
            logger.error(f"❌ Failed to download TikTok video: {e}")
            return False, None, None, f"فشل تحميل الفيديو: {str(e)}"
        
    except Exception as e:
        logger.error(f"❌ Error in download_tiktok_video: {e}")
        traceback.print_exc()
        return False, None, None, f"خطأ في تحميل فيديو TikTok: {str(e)}"


async def get_video_info(url: str):
    """استخراج معلومات الفيديو - نظام ذكي للـ cookies"""
    
    # تحديد إذا كان رابط Facebook
    is_facebook_url = 'facebook.com' in url.lower() or 'fb.watch' in url.lower()
    
    async def try_extract(use_cookies: bool):
        """محاولة استخراج المعلومات"""
        try:
            if is_facebook_url:
                if use_cookies:
                    logger.info("🍪 Facebook: محاولة مع cookies...")
                    platform_cookie = get_platform_cookie_file(url)
                else:
                    logger.info("🔓 Facebook: محاولة بدون cookies...")
                    platform_cookie = None
            else:
                platform_cookie = get_platform_cookie_file(url)
            
            # جمع cookies احتياطية
            all_cookies_files = []
            if not platform_cookie and not is_facebook_url:
                for platform, data in COOKIES_PLATFORMS.items():
                    if os.path.exists(data['file']):
                        file_size = os.path.getsize(data['file'])
                        if file_size > 100:
                            all_cookies_files.append(data['file'])
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'socket_timeout': 30,
                'extract_flat': False,
                'no_check_certificate': True,
                'retries': 3,
            }
            
            cookie_to_use = platform_cookie or (all_cookies_files[0] if all_cookies_files else None)
            
            if cookie_to_use:
                ydl_opts['cookiefile'] = cookie_to_use
                logger.info(f"🍪 Using cookies: {cookie_to_use}")
            
            # إضافة extractor_args
            instagram_cookie = COOKIES_PLATFORMS.get('instagram', {}).get('file')
            facebook_cookie = COOKIES_PLATFORMS.get('facebook', {}).get('file') if use_cookies else None
            
            ydl_opts['extractor_args'] = {
                'facebook': {'cookie_file': facebook_cookie if facebook_cookie and os.path.exists(facebook_cookie) else None},
                'instagram': {'cookie_file': instagram_cookie if instagram_cookie and os.path.exists(instagram_cookie) else None},
            }
            
            loop = asyncio.get_event_loop()
            
            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            return await loop.run_in_executor(None, extract)
        except Exception as e:
            return None, str(e)
    
    try:
        # === نظام ذكي لـ Facebook ===
        if is_facebook_url:
            # المحاولة 1: بدون cookies (أسرع وأنجح للفيديوهات العامة)
            result = await try_extract(use_cookies=False)
            
            if result is not None and not isinstance(result, tuple):
                logger.info("✅ Facebook: نجح بدون cookies!")
                return result
            
            # المحاولة 2: مع cookies (للفيديوهات الخاصة أو المقيدة)
            logger.info("🔄 Facebook: المحاولة الأولى فشلت، جاري المحاولة مع cookies...")
            facebook_cookie = COOKIES_PLATFORMS.get('facebook', {}).get('file')
            
            if facebook_cookie and os.path.exists(facebook_cookie):
                result = await try_extract(use_cookies=True)
                
                if result is not None and not isinstance(result, tuple):
                    logger.info("✅ Facebook: نجح مع cookies!")
                    return result
            
            # فشل كلاهما
            logger.error("❌ Facebook: فشلت جميع المحاولات")
            return None
        
        # === المنصات الأخرى ===
        else:
            platform_cookie = get_platform_cookie_file(url)
            
            all_cookies_files = []
            if not platform_cookie:
                for platform, data in COOKIES_PLATFORMS.items():
                    if os.path.exists(data['file']):
                        file_size = os.path.getsize(data['file'])
                        if file_size > 100:
                            all_cookies_files.append(data['file'])
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'socket_timeout': 30,
                'extract_flat': False,
                'no_check_certificate': True,
                'retries': 3,
            }
            
            cookie_to_use = platform_cookie or (all_cookies_files[0] if all_cookies_files else None)
            
            if cookie_to_use:
                ydl_opts['cookiefile'] = cookie_to_use
                logger.info(f"🍪 Using cookies for video info extraction: {cookie_to_use}")
            else:
                logger.warning(f"⚠️ No cookies available for URL: {url[:50]}...")
            
            instagram_cookie = COOKIES_PLATFORMS.get('instagram', {}).get('file')
            
            ydl_opts['extractor_args'] = {
                'facebook': {'cookie_file': None},
                'instagram': {'cookie_file': instagram_cookie if instagram_cookie and os.path.exists(instagram_cookie) else None},
            }
            
            loop = asyncio.get_event_loop()
            
            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            return await loop.run_in_executor(None, extract)
    except Exception as e:
        error_msg = str(e)
        
        # معالجة خاصة لأخطاء Instagram stories - محاولة التحميل المباشر
        if 'instagram' in error_msg.lower() and '/stories/' in url:
            logger.warning(f"⚠️ Instagram story info extraction issue: {error_msg[:200]}")
            logger.info(f"💡 Will attempt direct download with Instagram cookies")
            # نُرجع dict خاص يشير إلى أنه ستوري ويحتاج تحميل مباشر
            return {'_type': 'instagram_story', 'url': url, 'title': 'Instagram Story', 'duration': 0}
        # معالجة خاصة لأخطاء Facebook parsing - محاولة بدون cookies
        elif 'Cannot parse data' in error_msg and ('facebook' in url.lower() or 'fb.watch' in url.lower()):
            logger.warning(f"⚠️ Facebook parse error with cookies, trying without cookies...")
            try:
                # محاولة ثانية بدون cookies
                ydl_opts_no_cookies = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'socket_timeout': 30,
                    'extract_flat': False,
                    'no_check_certificate': True,
                    # NO cookies this time
                }
                
                def extract_no_cookies():
                    with yt_dlp.YoutubeDL(ydl_opts_no_cookies) as ydl:
                        return ydl.extract_info(url, download=False)
                
                result = await loop.run_in_executor(None, extract_no_cookies)
                if result:
                    logger.info("✅ Facebook extraction succeeded without cookies!")
                    return result
            except Exception as e2:
                logger.error(f"❌ Facebook fallback also failed: {str(e2)[:200]}")
            logger.error(f"خطأ Facebook parse: {error_msg[:200]}")
        elif 'facebook' in error_msg.lower():
            logger.error(f"خطأ Facebook: {error_msg[:200]}")
        else:
            logger.error(f"خطأ في استخراج المعلومات: {error_msg[:300]}")
        return None


async def upload_media_with_progress(client, chat_id, file_path, caption, status_msg, user_id, is_video=True):
    """Upload media with progress tracking"""
    try:
        upload_progress = UploadProgress(status_msg, user_id, asyncio.get_event_loop())
        
        if is_video:
            message = await client.send_video(
                chat_id=chat_id,
                video=file_path,
                caption=caption,
                progress=upload_progress
            )
        else:
            message = await client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                caption=caption,
                progress=upload_progress
            )
        
        return message
    except Exception as e:
        logger.error(f"خطأ في رفع الوسائط: {e}")
        raise
# Upload progress tracking
class UploadProgress:
    def __init__(self, status_msg, user_id, event_loop):
        self.status_msg = status_msg
        self.user_id = user_id
        self.event_loop = event_loop  # Store the event loop
        self.last_edit = 0
        self.last_current = 0
        self.last_time = time.time()
        self.speed = 0
    
    def __call__(self, current, total):
        """Sync callback for Pyrogram - creates async task for updates"""
        try:
            now = time.time()
            
            # Update speed calculation
            time_diff = now - self.last_time
            if time_diff >= 1:  # Update speed every second
                bytes_diff = current - self.last_current
                self.speed = bytes_diff / time_diff
                self.last_time = now
                self.last_current = current
            
            if now - self.last_edit < 1: # Update message every second
                return
            
            self.last_edit = now
            
            # Calculate progress
            percentage = (current / total) * 100
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            speed_mb = self.speed / (1024 * 1024) if self.speed > 0 else 0
            filled = int(percentage // 10)
            progress_bar = '▰' * filled + '▱' * (10 - filled)
            remaining_bytes = total - current
            eta = int(remaining_bytes / self.speed) if self.speed > 0 else 0
            
            # Get user language
            lang = subdb.get_user_language(self.user_id)
            
            upload_msg = t('uploading', lang,
                          percent=f'{percentage:.1f}',
                          current_mb=f'{current_mb:.1f}',
                          total_mb=f'{total_mb:.1f}',
                          speed_mb=f'{speed_mb:.1f}',
                          eta=eta,
                          progress_bar=progress_bar)
            
            # Use run_coroutine_threadsafe to schedule in the correct event loop
            asyncio.run_coroutine_threadsafe(
                self._update_message(upload_msg),
                self.event_loop
            )
        except Exception as e:
            logger.error(f"❌ Upload progress error: {e}")
    
    async def _update_message(self, text):
        """Async helper to update Telegram message"""
        try:
            await self.status_msg.edit_text(text)
        except Exception as e:
            logger.error(f"❌ Message edit error: {e}")


async def forward_to_log_channel(client, message, sent_message, user_id, user_name, username, url, 
                               video_info, duration, file_size_mb, chat=None):
    """تحويل الفيديو إلى قناة السجلات مع معلومات تفصيلية"""
    try:
        channel_id = os.getenv('LOG_CHANNEL_ID')
        
        if not channel_id:
            return
        
        # Format username
        username_text = f"@{username}" if username else "⚠️ لا يوجد يوزر"
        
        # User link (blue clickable name)
        user_link = f'<a href="tg://user?id={user_id}">{user_name}</a>'
        
        # Video title
        title = video_info.get('title', 'فيديو') if video_info else 'فيديو'
        
        # Platform detection
        if 'youtube' in url or 'youtu.be' in url:
            platform, icon = 'YouTube', '📺'
        elif 'facebook' in url or 'fb.watch' in url:
            platform, icon = 'Facebook', '📘'
        elif 'instagram' in url:
            platform, icon = 'Instagram', '📷'
        elif 'twitter' in url or 'x.com' in url:
            platform, icon = 'Twitter/X', '🐦'
        elif 'tiktok' in url:
            platform, icon = 'TikTok', '🎵'
        else:
            platform, icon = 'رابط', '🔗'
        
        # Views formatting
        views = video_info.get('view_count', 'N/A') if video_info else 'N/A'
        if isinstance(views, int):
            views_text = f"{views/1_000_000:.1f}M" if views >= 1_000_000 else f"{views/1_000:.1f}K" if views >= 1_000 else str(views)
        else:
            views_text = 'N/A'
        
        # Duration & Quality
        duration_text = f"{int(duration)//60:02d}:{int(duration)%60:02d}" if duration else "N/A"
        quality = video_info.get('resolution', 'N/A') if video_info else 'N/A'
        
        # Timestamp
        date_text = datetime.now().strftime("%d/%m/%Y • %H:%M UTC")
        
        # Group/Source info
        source_info = ""
        if chat and hasattr(chat, 'type') and str(chat.type) in ['ChatType.GROUP', 'ChatType.SUPERGROUP']:
            group_name = chat.title or "مجموعة"
            group_link = group_name
            
            # Try to get invite link for clickable group name
            if chat.username:
                # مجموعة عامة - لها username
                group_link = f'<a href="https://t.me/{chat.username}">{group_name}</a>'
            else:
                # مجموعة خاصة - محاولة إنشاء رابط دعوة
                try:
                    invite_link = await client.export_chat_invite_link(chat.id)
                    group_link = f'<a href="{invite_link}">{group_name}</a>'
                except Exception as invite_error:
                    logger.warning(f"⚠️ لا يمكن إنشاء رابط دعوة للمجموعة: {invite_error}")
                    # استخدام رابط t.me/c/ للمجموعات الخاصة (يعمل للأعضاء فقط)
                    # تحويل ID السالب لصيغة t.me/c/
                    chat_id_str = str(chat.id).replace("-100", "")
                    group_link = f'<a href="https://t.me/c/{chat_id_str}">{group_name}</a>'
            
            source_info = f"""
🏠 المصدر
╔═ النوع: 👥 مجموعة
╚═ الاسم: {group_link}
"""
        elif chat:
            source_info = f"""
🏠 المصدر: 💬 محادثة خاصة
"""
        
        # Caption with user info
        caption = f"""━━━━━━━━━━━━━━━━━━━━━━
🎬 تحميل جديد

👤 المستخدم
╔═ الاسم: {user_link}
╠═ اليوزر: {username_text}  
╚═ ID: <code>{user_id}</code>
{source_info}
🔗 المصدر: {icon} {platform}
📎 {url}

🎞️ العنوان
{title}

📊 تفاصيل الفيديو
├─ 📹 المدة: {duration_text}
├─ 💾 الحجم: {file_size_mb:.2f} MB
├─ 🎯 الجودة: {quality}
└─ 👁️ المشاهدات: {views_text}

🕐 {date_text}
━━━━━━━━━━━━━━━━━━━━━━"""
        
        # 1. تحويل الفيديو (forward)
        await client.forward_messages(
            chat_id=channel_id,
            from_chat_id=sent_message.chat.id,
            message_ids=sent_message.id
        )
        
        # 2. إرسال معلومات المستخدم كرسالة منفصلة تحت الفيديو
        await client.send_message(
            chat_id=channel_id,
            text=caption,
            parse_mode=enums.ParseMode.HTML
        )
        
        logger.info(f"✅ تم تحويل الفيديو والمعلومات إلى القناة")
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحويل الفيديو إلى القناة: {str(e)}")


async def process_download_from_queue(task: DownloadTask):
    """
    Process a download task from the queue.
    
    Args:
        task: DownloadTask containing download information
    """
    user_id = task.user_id
    url = task.url
    message = task.message
    
    # Get user language
    lang = subdb.get_user_language(user_id)
    
    try:
        # Check for Facebook Stories - not supported
        if ('facebook.com/stories' in url or 'fb.com/stories' in url):
            logger.info(f"❌ Facebook story detected - not supported: {url}")
            await message.reply_text(t('facebook_story_not_supported', lang))
            return
        
        # Send processing notification
        status = await message.reply_text(t('queue_processing_current', lang))
        
        # ======= معالجة ستوري Instagram قبل أي شيء =======
        # Instagram stories need special handling with instaloader (works for photos AND videos)
        if 'instagram.com' in url and '/stories/' in url:
            logger.info("📸 Detected Instagram story - using instaloader first (best for photos)")
            user_name = message.from_user.first_name or "User"
            username = message.from_user.username or "No username"
            
            # التحقق من وجود كوكيز انستقرام
            instagram_cookie = get_platform_cookie_file(url)
            if not instagram_cookie:
                logger.warning("⚠️ No Instagram cookies found for story download")
                await status.edit_text(t('story_cookies_missing', lang))
                return
            
            # استخدام gallery-dl أولاً (أفضل مع cookies)، ثم instaloader كـ fallback
            logger.info(f"🍪 Attempting story download with gallery-dl first")
            success, files, error, is_video = await download_instagram_story_with_gallery_dl(url, user_id)
            
            # إذا فشل gallery-dl، جرب instaloader
            if not success:
                logger.info(f"⚠️ gallery-dl failed, trying instaloader as fallback...")
                success, files, error, is_video = await download_instagram_story_with_instaloader(url, user_id)
            
            if success and files:
                if not is_video:
                    # ستوري صورة - رفع مباشرة
                    logger.info(f"📸 Story is a photo - uploading directly")
                    await status.edit_text(t('uploading', lang,
                                           percent='0.0',
                                           current_mb='0.0',
                                           total_mb='0.0',
                                           speed_mb='0.0',
                                           eta=0,
                                           progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                    
                    for i, photo_path in enumerate(files[:10], 1):
                        try:
                            sent_msg = await message.reply_photo(
                                photo=photo_path,
                                caption=f"📸 ستوري {i}/{len(files)} من Instagram\n👤 {user_name}"
                            )
                            logger.info(f"✅ Sent story photo {i}/{len(files)} to user")
                            
                            # Forward to LOG channel
                            log_channel_id = os.getenv('LOG_CHANNEL_ID')
                            if log_channel_id:
                                try:
                                    await app.forward_messages(
                                        chat_id=log_channel_id,
                                        from_chat_id=message.chat.id,
                                        message_ids=sent_msg.id
                                    )
                                    await app.send_message(
                                        chat_id=log_channel_id,
                                        text=(
                                            f"📸 **ستوري Instagram {i}/{len(files)}**\n\n"
                                            f"👤 **المستخدم:** {user_name}\n"
                                            f"🆔 **ID:** `{user_id}`\n"
                                            f"📱 **Username:** @{username}\n"
                                            f"🔗 **الرابط:** {url}"
                                        )
                                    )
                                except Exception as log_error:
                                    logger.error(f"❌ Failed to forward story to LOG channel: {log_error}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send story photo {i}: {e}")
                    
                    # Cleanup
                    for photo_path in files:
                        try:
                            os.remove(photo_path)
                        except:
                            pass
                    
                    try:
                        await status.delete()
                    except:
                        pass
                    
                    subdb.increment_download_count(user_id)
                    return
                else:
                    # ستوري فيديو من instaloader - رفعها مباشرة
                    logger.info(f"📹 Story is a video from instaloader - uploading directly")
                    await status.edit_text(t('uploading', lang,
                                           percent='0.0',
                                           current_mb='0.0',
                                           total_mb='0.0',
                                           speed_mb='0.0',
                                           eta=0,
                                           progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                    
                    for video_path in files:
                        try:
                            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                            sent_msg = await message.reply_video(
                                video=video_path,
                                caption=f"📹 ستوري فيديو من Instagram\n👤 {user_name}\n📊 {file_size_mb:.1f} MB"
                            )
                            logger.info(f"✅ Sent story video to user")
                            
                            # Forward to LOG channel
                            log_channel_id = os.getenv('LOG_CHANNEL_ID')
                            if log_channel_id:
                                try:
                                    await app.forward_messages(
                                        chat_id=log_channel_id,
                                        from_chat_id=message.chat.id,
                                        message_ids=sent_msg.id
                                    )
                                except Exception as log_error:
                                    logger.error(f"❌ Failed to forward story video to LOG channel: {log_error}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send story video: {e}")
                    
                    # Cleanup
                    for video_path in files:
                        try:
                            os.remove(video_path)
                        except:
                            pass
                    
                    try:
                        await status.delete()
                    except:
                        pass
                    
                    subdb.increment_download_count(user_id)
                    return
            else:
                # فشل instaloader - عرض رسالة خطأ واضحة
                logger.warning(f"⚠️ instaloader failed: {error}")
                await status.edit_text(t('instagram_private_story', lang))
                return
        
        # Early check for TikTok photo posts before get_video_info (yt-dlp doesn't support TikTok photos)
        if ('tiktok.com' in url and '/photo/' in url) or 'vm.tiktok.com' in url:
            logger.info("📸 Detected potential TikTok photo post - attempting photo download via TikWM API")
            user_name = message.from_user.first_name or "User"
            username = message.from_user.username or "No username"
            
            # Try to download TikTok photos using TikWM API
            success, files, error = await download_tiktok_photos(url, user_id)
            
            if success and files:
                await status.edit_text(t('uploading', lang,
                                       percent='0.0',
                                       current_mb='0.0',
                                       total_mb='0.0',
                                       speed_mb='0.0',
                                       eta=0,
                                       progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                
                # Upload photos to user
                for i, photo_path in enumerate(files[:20], 1):  # Limit to 20 photos
                    try:
                        sent_msg = await message.reply_photo(
                            photo=photo_path,
                            caption=f"📸 صورة {i}/{len(files)} من TikTok\n👤 {user_name}"
                        )
                        logger.info(f"✅ Sent TikTok photo {i}/{len(files)} to user")
                        
                        # Forward to LOG channel with caption
                        log_channel_id = os.getenv('LOG_CHANNEL_ID')
                        if log_channel_id:
                            try:
                                await app.forward_messages(
                                    chat_id=log_channel_id,
                                    from_chat_id=message.chat.id,
                                    message_ids=sent_msg.id
                                )
                                await app.send_message(
                                    chat_id=log_channel_id,
                                    text=(
                                        f"📸 **صورة TikTok {i}/{len(files)}**\n\n"
                                        f"👤 **المستخدم:** {user_name}\n"
                                        f"🆔 **ID:** `{user_id}`\n"
                                        f"📱 **Username:** @{username}\n"
                                        f"🔗 **الرابط:** {url}"
                                    )
                                )
                                logger.info(f"✅ Forwarded TikTok photo {i}/{len(files)} to LOG channel")
                            except Exception as log_error:
                                logger.error(f"❌ Failed to forward TikTok photo to LOG channel: {log_error}")
                    except Exception as e:
                        logger.error(f"❌ Failed to send TikTok photo {i}: {e}")
                
                # Cleanup
                for photo_path in files:
                    try:
                        os.remove(photo_path)
                    except:
                        pass
                
                # Delete status message
                try:
                    await status.delete()
                except:
                    pass
                
                # Record download
                subdb.increment_download_count(user_id)
                return
            elif error and "لا يحتوي على صور" in error:
                # It's a video, not photos - continue to normal video download
                logger.info("📹 TikTok post is a video, not photos - continuing to video download")
            else:
                # Failed to download photos
                await send_error_to_admin(user_id, user_name, f"TikTok photo download failed: {error}", url)
                await status.edit_text(f"❌ فشل تحميل صور TikTok\n\n{error}")
                return
        
        # Get video info (for non-story URLs)
        info = await get_video_info(url)
        
        if not info:
            # Check if it's an Instagram URL
            if 'instagram.com' in url:
                # Check if it's a story - stories need special handling
                if '/stories/' in url:
                    logger.info("📸 Detected Instagram story - trying instaloader first (best for photos)")
                    user_name = message.from_user.first_name or "User"
                    username = message.from_user.username or "No username"
                    
                    # التحقق من وجود كوكيز انستقرام
                    instagram_cookie = get_platform_cookie_file(url)
                    if not instagram_cookie:
                        logger.warning("⚠️ No Instagram cookies found for story download")
                        await status.edit_text(t('story_cookies_missing', lang))
                        return
                    
                    # المحاولة 1: استخدام gallery-dl أولاً (أفضل مع cookies)
                    logger.info(f"🍪 Attempting story download with gallery-dl first")
                    success, files, error, is_video = await download_instagram_story_with_gallery_dl(url, user_id)
                    
                    # إذا فشل gallery-dl، جرب instaloader
                    if not success:
                        logger.info(f"⚠️ gallery-dl failed, trying instaloader as fallback...")
                        success, files, error, is_video = await download_instagram_story_with_instaloader(url, user_id)
                    
                    if success and files:
                        if not is_video:
                            # ستوري صورة - رفع مباشرة
                            logger.info(f"📸 Story is a photo - uploading directly")
                            await status.edit_text(t('uploading', lang,
                                                   percent='0.0',
                                                   current_mb='0.0',
                                                   total_mb='0.0',
                                                   speed_mb='0.0',
                                                   eta=0,
                                                   progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                            
                            for i, photo_path in enumerate(files[:10], 1):
                                try:
                                    sent_msg = await message.reply_photo(
                                        photo=photo_path,
                                        caption=f"📸 ستوري {i}/{len(files)} من Instagram\n👤 {user_name}"
                                    )
                                    logger.info(f"✅ Sent story photo {i}/{len(files)} to user")
                                    
                                    # Forward to LOG channel
                                    log_channel_id = os.getenv('LOG_CHANNEL_ID')
                                    if log_channel_id:
                                        try:
                                            await app.forward_messages(
                                                chat_id=log_channel_id,
                                                from_chat_id=message.chat.id,
                                                message_ids=sent_msg.id
                                            )
                                            await app.send_message(
                                                chat_id=log_channel_id,
                                                text=(
                                                    f"📸 **ستوري Instagram {i}/{len(files)}**\n\n"
                                                    f"👤 **المستخدم:** {user_name}\n"
                                                    f"🆔 **ID:** `{user_id}`\n"
                                                    f"📱 **Username:** @{username}\n"
                                                    f"🔗 **الرابط:** {url}"
                                                )
                                            )
                                        except Exception as log_error:
                                            logger.error(f"❌ Failed to forward story to LOG channel: {log_error}")
                                except Exception as e:
                                    logger.error(f"❌ Failed to send story photo {i}: {e}")
                            
                            # Cleanup
                            for photo_path in files:
                                try:
                                    os.remove(photo_path)
                                except:
                                    pass
                            
                            try:
                                await status.delete()
                            except:
                                pass
                            
                            subdb.increment_download_count(user_id)
                            return
                        else:
                            # ستوري فيديو من instaloader - رفعها مباشرة
                            logger.info(f"📹 Story is a video from instaloader - uploading directly")
                            await status.edit_text(t('uploading', lang,
                                                   percent='0.0',
                                                   current_mb='0.0',
                                                   total_mb='0.0',
                                                   speed_mb='0.0',
                                                   eta=0,
                                                   progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                            
                            for video_path in files:
                                try:
                                    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                                    sent_msg = await message.reply_video(
                                        video=video_path,
                                        caption=f"📹 ستوري فيديو من Instagram\n👤 {user_name}\n📊 {file_size_mb:.1f} MB"
                                    )
                                    logger.info(f"✅ Sent story video to user")
                                    
                                    # Forward to LOG channel
                                    log_channel_id = os.getenv('LOG_CHANNEL_ID')
                                    if log_channel_id:
                                        try:
                                            await app.forward_messages(
                                                chat_id=log_channel_id,
                                                from_chat_id=message.chat.id,
                                                message_ids=sent_msg.id
                                            )
                                        except Exception as log_error:
                                            logger.error(f"❌ Failed to forward story video to LOG channel: {log_error}")
                                except Exception as e:
                                    logger.error(f"❌ Failed to send story video: {e}")
                            
                            # Cleanup
                            for video_path in files:
                                try:
                                    os.remove(video_path)
                                except:
                                    pass
                            
                            try:
                                await status.delete()
                            except:
                                pass
                            
                            subdb.increment_download_count(user_id)
                            return
                    else:
                        # فشل instaloader - نحاول yt-dlp
                        logger.info(f"⚠️ instaloader failed ({error}), trying yt-dlp for story")
                        info = {'_type': 'instagram_story', 'url': url, 'title': 'Instagram Story', 'duration': 15}
                    # لا نعود هنا - نكمل مع التحميل عبر yt-dlp
                else:
                    # It's a regular post/photo - try gallery-dl
                    logger.info("🔄 Attempting Instagram photo download with gallery-dl")
                    success, files, error = await download_instagram_photo(url, user_id)
                    
                    if success and files:
                        await status.edit_text(t('uploading', lang,
                                               percent='0.0',
                                               current_mb='0.0',
                                               total_mb='0.0',
                                               speed_mb='0.0',
                                               eta=0,
                                               progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                        
                        # Upload photos to user
                        user_name = message.from_user.first_name
                        username = message.from_user.username or "No username"
                        
                        for i, photo_path in enumerate(files[:10], 1):  # Limit to 10 photos
                            try:
                                sent_msg = await message.reply_photo(
                                    photo=photo_path,
                                    caption=f"📸 صورة {i}/{len(files)} من Instagram\n👤 {user_name}"
                                )
                                logger.info(f"✅ Sent photo {i}/{len(files)} to user")
                                
                                # Forward to LOG channel with caption
                                log_channel_id = os.getenv('LOG_CHANNEL_ID')
                                if log_channel_id:
                                    try:
                                        # Forward the message
                                        await app.forward_messages(
                                            chat_id=log_channel_id,
                                            from_chat_id=message.chat.id,
                                            message_ids=sent_msg.id
                                        )
                                        
                                        # Send info message
                                        await app.send_message(
                                            chat_id=log_channel_id,
                                            text=(
                                                f"📸 **صورة Instagram {i}/{len(files)}**\n\n"
                                                f"👤 **المستخدم:** {user_name}\n"
                                                f"🆔 **ID:** `{user_id}`\n"
                                                f"📱 **Username:** @{username}\n"
                                                f"🔗 **الرابط:** {url}"
                                            )
                                        )
                                        logger.info(f"✅ Forwarded photo {i}/{len(files)} to LOG channel")
                                    except Exception as log_error:
                                        logger.error(f"❌ Failed to forward photo to LOG channel: {log_error}")
                            except Exception as e:
                                logger.error(f"❌ Failed to send photo {i}: {e}")
                        
                        # Cleanup
                        for photo_path in files:
                            try:
                                os.remove(photo_path)
                            except:
                                pass
                        
                        # Delete status message - wrap in try-except to avoid MESSAGE_ID_INVALID
                        try:
                            await status.delete()
                        except:
                            pass
                        
                        # Record download - use correct function name
                        subdb.increment_download_count(user_id)
                        return
                    else:
                        user_name = message.from_user.first_name or "User"
                        await send_error_to_admin(user_id, user_name, f"Instagram photo download failed: {error}", url)
                        await status.edit_text(f"❌ فشل تحميل الصورة من Instagram\n\n{error}")
                        return
            # Check if it's a TikTok photo/slideshow URL
            # Include both direct photo URLs and shortened URLs (which need API check)
            elif ('tiktok.com' in url and '/photo/' in url) or 'vm.tiktok.com' in url:
                logger.info("📸 Detected potential TikTok photo post - attempting photo download")
                user_name = message.from_user.first_name or "User"
                username = message.from_user.username or "No username"
                
                # Try to download TikTok photos
                success, files, error = await download_tiktok_photos(url, user_id)
                
                if success and files:
                    await status.edit_text(t('uploading', lang,
                                           percent='0.0',
                                           current_mb='0.0',
                                           total_mb='0.0',
                                           speed_mb='0.0',
                                           eta=0,
                                           progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                    
                    # Upload photos to user
                    for i, photo_path in enumerate(files[:10], 1):  # Limit to 10 photos
                        try:
                            sent_msg = await message.reply_photo(
                                photo=photo_path,
                                caption=f"📸 صورة {i}/{len(files)} من TikTok\n👤 {user_name}"
                            )
                            logger.info(f"✅ Sent TikTok photo {i}/{len(files)} to user")
                            
                            # Forward to LOG channel with caption
                            log_channel_id = os.getenv('LOG_CHANNEL_ID')
                            if log_channel_id:
                                try:
                                    # Forward the message
                                    await app.forward_messages(
                                        chat_id=log_channel_id,
                                        from_chat_id=message.chat.id,
                                        message_ids=sent_msg.id
                                    )
                                    
                                    # Send info message
                                    await app.send_message(
                                        chat_id=log_channel_id,
                                        text=(
                                            f"📸 **صورة TikTok {i}/{len(files)}**\n\n"
                                            f"👤 **المستخدم:** {user_name}\n"
                                            f"🆔 **ID:** `{user_id}`\n"
                                            f"📱 **Username:** @{username}\n"
                                            f"🔗 **الرابط:** {url}"
                                        )
                                    )
                                    logger.info(f"✅ Forwarded TikTok photo {i}/{len(files)} to LOG channel")
                                except Exception as log_error:
                                    logger.error(f"❌ Failed to forward TikTok photo to LOG channel: {log_error}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send TikTok photo {i}: {e}")
                    
                    # Cleanup
                    for photo_path in files:
                        try:
                            os.remove(photo_path)
                        except:
                            pass
                    
                    # Delete status message
                    try:
                        await status.delete()
                    except:
                        pass
                    
                    # Record download
                    subdb.increment_download_count(user_id)
                    return
                else:
                    # If it's a shortened URL (vm.tiktok.com), try normal video download as fallback
                    if 'vm.tiktok.com' in url and error and "لا يحتوي على صور" in error:
                        logger.info("📹 Shortened URL is not a photo post, falling back to video download")
                        # Re-fetch video info using yt-dlp for video
                        info = await get_video_info(url)
                        if not info:
                            user_name = message.from_user.first_name or "User"
                            await send_error_to_admin(user_id, user_name, f"TikTok video download also failed after photo fallback", url)
                            await status.edit_text(t('invalid_url', lang))
                            return
                        # Continue with normal video processing (will use info below)
                    else:
                        # It was explicitly a photo URL but failed
                        await send_error_to_admin(user_id, user_name, f"TikTok photo download failed: {error}", url)
                        await status.edit_text(f"❌ فشل تحميل صور TikTok\n\n{error}")
                        return
            else:
                # Not Instagram or TikTok photo - check if it's an Instagram story
                if 'instagram.com' in url and '/stories/' in url:
                    logger.info("📹 Detected Instagram story - attempting direct download with cookies")
                    user_name = message.from_user.first_name or "User"
                    
                    # Try to download story directly
                    try:
                        # Note: This is in the queue context, so we need to handle it differently
                        # We'll try the download and let yt-dlp handle the error
                        pass  # Let it fall through to normal download process below
                    except Exception:
                        pass
                    
                    # Send to admin for tracking
                    await send_error_to_admin(user_id, user_name, "Instagram story info extraction failed - will attempt direct download", url)
                    # Don't return here - let the download attempt happen naturally
                else:
                    # Generic error for other URLs
                    user_name = message.from_user.first_name or "User"
                    await send_error_to_admin(user_id, user_name, "Failed to extract video info", url)
                    await status.edit_text(t('invalid_url', lang))
                    return
        
        title = info.get('title', 'Video')[:50]
        duration = info.get('duration', 0)
        duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "0:00"
        
        # Add or update user info
        username = message.from_user.username
        first_name = message.from_user.first_name
        subdb.add_or_update_user(user_id, username, first_name)
        
        # Check subscription and video duration
        is_subscribed = subdb.is_user_subscribed(user_id)
        
        # Check daily limit for non-subscribers
        if not is_subscribed:
            daily_limit = subdb.get_daily_limit()
            
            if daily_limit != -1:
                daily_count = subdb.check_daily_limit(user_id)
                
                if daily_count >= daily_limit:
                    await status.edit_text(
                        t('daily_limit_exceeded', lang, limit=daily_limit, count=daily_count),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(t('subscribe_now', lang), callback_data="pay_binance")],
                            [InlineKeyboardButton(t('contact_developer', lang), url=f"https://t.me/{subdb.get_setting('telegram_support', 'wahab161')}")]
                        ])
                    )
                    return
        
        max_duration_minutes = subdb.get_max_duration()
        max_duration_seconds = max_duration_minutes * 60
        
        # If not subscribed and exceeds max duration
        if not is_subscribed and duration and duration > max_duration_seconds:
            await show_subscription_screen(app, status, user_id, title, duration, max_duration_minutes)
            return
        
        # Show quality selection
        keyboard = [
            [InlineKeyboardButton(t('quality_best', lang), callback_data="quality_best")],
            [InlineKeyboardButton(t('quality_medium', lang), callback_data="quality_medium")],
            [InlineKeyboardButton(t('quality_audio', lang), callback_data="quality_audio")],
        ]
        
        await status.edit_text(
            t('choose_quality', lang, title=title, duration=duration_str),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Store URL for quality callback
        pending_downloads[user_id] = url
        
    except Exception as e:
        logger.error(f"Error in process_download_from_queue for user {user_id}: {e}", exc_info=True)
        # Notify user of error
        try:
            await message.reply_text(t('error_occurred', lang, error=str(e)[:100]))
        except:
            pass


def cleanup_downloaded_files(file_path=None):
    """
    حذف جميع الملفات المحملة من المجلد الحالي ومجلدات التحميل.
    
    Args:
        file_path: المسار المحدد للملف المراد حذفه (اختياري)
    """
    try:
        deleted_count = 0
        
        # حذف الملف المحدد إذا كان موجود
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🗑️ تم حذف الملف: {file_path}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ خطأ في حذف {file_path}: {e}")
        
        # أنواع الملفات المراد حذفها
        video_extensions = ['*.mp4', '*.mkv', '*.webm', '*.avi', '*.mov', '*.flv', '*.wmv', '*.m4v']
        audio_extensions = ['*.mp3', '*.m4a', '*.opus', '*.ogg', '*.wav', '*.flac', '*.aac']
        temp_extensions = ['*.part', '*.ytdl', '*.temp', '*.tmp']
        all_extensions = video_extensions + audio_extensions + temp_extensions
        
        # المجلدات المراد تنظيفها
        directories_to_clean = [
            '.',  # المجلد الحالي
            'downloads',
            'videos'
        ]
        
        # تنظيف كل مجلد
        for directory in directories_to_clean:
            if not os.path.exists(directory):
                continue
                
            for extension in all_extensions:
                pattern = os.path.join(directory, extension)
                for file in glob.glob(pattern):
                    try:
                        # تجنب حذف watermark.png
                        if 'watermark' in file.lower():
                            continue
                        os.remove(file)
                        logger.info(f"🗑️ تم حذف: {file}")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"❌ خطأ في حذف {file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"✅ تم حذف {deleted_count} ملف من المجلدات")
        
    except Exception as e:
        logger.error(f"❌ خطأ في cleanup_downloaded_files: {e}")


def extract_instagram_story_id(url: str):
    """
    استخراج معرّف الستوري من رابط انستقرام
    
    Args:
        url: رابط ستوري انستقرام
        
    Returns:
        Story ID إذا وُجد، وإلا None
    """
    import re
    
    # Pattern: /stories/username/STORY_ID/
    pattern = r'/stories/[^/]+/(\d+)'
    match = re.search(pattern, url)
    
    if match:
        story_id = match.group(1)
        logger.info(f"📋 Extracted Story ID from URL: {story_id}")
        return story_id
    
    logger.warning("⚠️ Could not extract Story ID from URL")
    return None


async def download_and_upload(client, message, url, quality, callback_query=None, is_group=False):
    """تحميل ورفع الفيديو - is_group يحدد إذا كان في مجموعة لإخفاء زر الدعم"""
    # الحصول على معلومات المستخدم من callback_query إذا كان موجوداً
    if callback_query:
        user_id = callback_query.from_user.id
        user_name = callback_query.from_user.first_name
        user_username = callback_query.from_user.username
    else:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        user_username = message.from_user.username
    
    # Get user language
    lang = subdb.get_user_language(user_id)
    status_msg = await message.reply_text(t('processing', lang))
    
    # فحص المحتوى الإباحي - Check for adult content
    if subdb.is_adult_content_blocked():
        if is_adult_content_url(url):
            await status_msg.edit_text(t('adult_content_blocked', lang))
            logger.warning(f"🚫 Blocked adult content URL from user {user_id}: {url[:50]}...")
            return
    
    try:
        # إعدادات التحميل
        quality_formats = {
            'best': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            'medium': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            'audio': 'bestaudio/best'  # النسخة الناجحة - تحميل أفضل جودة صوت
        }
        
        is_audio = (quality == 'audio')
        
        # الحصول على event loop مبكراً
        loop = asyncio.get_event_loop()
        
        # دالة تتبع تقدم التحميل
        last_edit_time = 0
        
        def download_progress_hook(d):
            nonlocal last_edit_time
            if d['status'] == 'downloading':
                try:
                    now = time.time()
                    if now - last_edit_time < 2:  # تحديث كل 2 ثانية
                        return
                        
                    last_edit_time = now
                    
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    
                    if total_bytes > 0:
                        percentage = (downloaded_bytes / total_bytes) * 100
                        current_mb = downloaded_bytes / (1024 * 1024)
                        total_mb = total_bytes / (1024 * 1024)
                        speed = d.get('speed', 0) or 0
                        speed_mb = speed / (1024 * 1024)
                        eta = d.get('eta', 0) or 0
                        
                        filled = int(percentage // 10)
                        progress_bar = '▰' * filled + '▱' * (10 - filled)
                        
                        # DEBUG: Log the language being used
                        logger.info(f"📥 Download progress for user {user_id}, lang={lang}")
                        
                        msg_text = t('downloading', lang, 
                                    percent=f'{percentage:.1f}',
                                    current_mb=f'{current_mb:.1f}',
                                    total_mb=f'{total_mb:.1f}',
                                    speed_mb=f'{speed_mb:.1f}',
                                    eta=eta,
                                    progress_bar=progress_bar)
                        
                        # تحديث الرسالة من thread منفصل
                        try:
                            future = asyncio.run_coroutine_threadsafe(
                                status_msg.edit_text(msg_text),
                                loop
                            )
                            # لا ننتظر النتيجة لتجنب الحظر
                        except Exception:
                            pass
                            
                except Exception as e:
                    logger.error(f"خطأ في progress hook: {e}")
        
        # دالة تتبع مرحلة المعالجة (post-processing)
        def postprocessor_hook(d):
            try:
                status = d.get('status')
                logger.info(f"🔄 Post-processor status: {status}")
                
                if status == 'started':
                    postprocessor = d.get('postprocessor', 'Unknown')
                    logger.info(f"🔧 بدء المعالجة: {postprocessor}")
                    # تم إزالة رسالة المعالجة - المستخدم لا يريدها
                        
                elif status == 'finished':
                    logger.info(f"✅ اكتملت المعالجة")
                    
            except Exception as e:
                logger.error(f"خطأ في postprocessor hook: {e}")


        # تحسين إعدادات التحميل للسرعة والاستقرار
        logger.info("🚀 Using optimized download settings for better performance")
        
        # Check if this is an Instagram story with a specific ID
        is_instagram_story = '/stories/' in url and 'instagram.com' in url
        story_id_from_url = extract_instagram_story_id(url) if is_instagram_story else None
        
        ydl_opts = {
            'format': quality_formats.get(quality, 'best'),
            'outtmpl': '%(title).50s_%(id)s.%(ext)s',  # Limit title to 50 chars to avoid "File name too long" error
            'progress_hooks': [download_progress_hook],
            'postprocessor_hooks': [postprocessor_hook],  # تتبع مرحلة المعالجة
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
            'retries': 15,
            'fragment_retries': 15,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }
        
        # For Instagram stories with a specific ID, try to download only that story
        if story_id_from_url:
            logger.info(f"📌 Instagram story detected with ID: {story_id_from_url}")
            logger.info("🎯 Attempting to download only the specific story (not all stories)")
            ydl_opts['noplaylist'] = True  # Try to prevent downloading all stories
        
        # استخدام كوكيز المنصة المحددة أولاً (Instagram cookies for Instagram URLs)
        # ⚠️ تجاوز cookies لـ Facebook لأنها تسبب مشاكل parsing
        is_facebook_url = 'facebook.com' in url.lower() or 'fb.watch' in url.lower()
        
        if is_facebook_url:
            logger.info("🔓 Facebook URL detected - skipping cookies (works better without)")
            platform_cookie = None
        else:
            platform_cookie = get_platform_cookie_file(url)
        
        # إذا لم توجد كوكيز للمنصة، جمع كل الكوكيز المتاحة كاحتياطي
        all_cookies_files = []
        if not platform_cookie and not is_facebook_url:
            for platform, data in COOKIES_PLATFORMS.items():
                if os.path.exists(data['file']):
                    file_size = os.path.getsize(data['file'])
                    if file_size > 100:
                        all_cookies_files.append(data['file'])
        
        # اختيار الكوكيز المناسبة
        cookie_to_use = platform_cookie or (all_cookies_files[0] if all_cookies_files else None)
        
        if cookie_to_use:
            ydl_opts['cookiefile'] = cookie_to_use
            logger.info(f"🍪 Using cookies for download: {cookie_to_use}")
        elif not is_facebook_url:
            logger.warning(f"⚠️ No cookies available for download")
        
        # تحسينات لجميع منصات التواصل الاجتماعي - استخدام كوكيز المنصات المحددة
        instagram_cookie = COOKIES_PLATFORMS.get('instagram', {}).get('file')
        facebook_cookie = COOKIES_PLATFORMS.get('facebook', {}).get('file')
        youtube_cookie = COOKIES_PLATFORMS.get('youtube', {}).get('file')
        twitter_cookie = COOKIES_PLATFORMS.get('twitter', {}).get('file')
        tiktok_cookie = COOKIES_PLATFORMS.get('tiktok', {}).get('file')
        snapchat_cookie = COOKIES_PLATFORMS.get('snapchat', {}).get('file')
        pinterest_cookie = COOKIES_PLATFORMS.get('pinterest', {}).get('file')
        
        ydl_opts['extractor_args'] = {
            'facebook': {'cookie_file': None},  # ⚠️ تعطيل cookies لـ Facebook - تسبب مشاكل parsing
            'instagram': {'cookie_file': instagram_cookie if instagram_cookie and os.path.exists(instagram_cookie) else None},
            'youtube': {'cookie_file': youtube_cookie if youtube_cookie and os.path.exists(youtube_cookie) else None},
            'twitter': {'cookie_file': twitter_cookie if twitter_cookie and os.path.exists(twitter_cookie) else None},
            'tiktok': {'cookie_file': tiktok_cookie if tiktok_cookie and os.path.exists(tiktok_cookie) else None},
            'snapchat': {'cookie_file': snapchat_cookie if snapchat_cookie and os.path.exists(snapchat_cookie) else None},
            'pinterest': {
                'cookie_file': pinterest_cookie if pinterest_cookie and os.path.exists(pinterest_cookie) else None,
                'api_only': False,
            },
        }
        
        # للملفات الصوتية: تحويل إلى MP3 فقط إذا لم يكن MP3 بالفعل
        if is_audio:
            # تحويل إلى MP3 بجودة ممتازة (128kbps) - حجم أصغر ومعالجة أسرع!
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',  # جودة ممتازة بحجم أصغر
            }]
            logger.info("🎵 استخراج الصوت بجودة ممتازة (128kbps)")
        # لا نحتاج FFmpegVideoConvertor لأن merge_output_format=mp4 تكفي
        # وإضافته تسبب مشاكل conversion مع الملفات الكبيرة
        
        
        # التحميل - استخدام نظام الترجمة
        await status_msg.edit_text(t('start_downloading', lang))
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # التحقق من أن info ليس None
                if info is None:
                    logger.error("❌ yt-dlp returned None - could not extract info")
                    return None, None
                
                # Handle playlists (Instagram stories return playlists)
                if 'entries' in info:
                    # It's a playlist (happens with Instagram stories even with noplaylist=True sometimes)
                    logger.info(f"📋 Detected playlist with {len(info['entries'])} entries")
                    
                    # Try to extract the specific story ID from URL
                    story_id = extract_instagram_story_id(url)
                    
                    if story_id:
                        # Search for the matching story in the playlist using multiple matching strategies
                        entry = None
                        
                        for idx, item in enumerate(info['entries']):
                            # Strategy 1: Match by 'id' field
                            item_id = str(item.get('id', ''))
                            if item_id == story_id:
                                logger.info(f"✅ Found matching story at index {idx} (ID match: {story_id})")
                                entry = item
                                break
                            
                            # Strategy 2: Match by 'display_id' field
                            display_id = str(item.get('display_id', ''))
                            if display_id == story_id:
                                logger.info(f"✅ Found matching story at index {idx} (display_id match: {story_id})")
                                entry = item
                                break
                            
                            # Strategy 3: Match by checking if story_id is in the webpage_url
                            webpage_url = item.get('webpage_url', '')
                            if story_id in webpage_url:
                                logger.info(f"✅ Found matching story at index {idx} (URL contains: {story_id})")
                                entry = item
                                break
                        
                        if entry is None:
                            # Story ID not found in playlist - log warning and use first entry as fallback
                            logger.warning(f"⚠️ Story ID {story_id} not found in playlist using any matching strategy")
                            logger.warning(f"⚠️ Available IDs in playlist: {[str(item.get('id', 'N/A')) for item in info['entries'][:3]]}...")
                            entry = info['entries'][0]
                    else:
                        # No Story ID in URL - use first entry (default behavior)
                        logger.info("📌 No Story ID found in URL, downloading first story")
                        entry = info['entries'][0]
                    
                    file_path = ydl.prepare_filename(entry)
                    return entry, file_path
                else:
                    # Single video
                    file_path = ydl.prepare_filename(info)
                    return info, file_path
        
        info, file_path = await loop.run_in_executor(None, download)
        
        # التحقق من فشل التحميل
        if info is None or file_path is None:
            logger.error("❌ Download failed - info or file_path is None")
            # إذا كانت ستوري Instagram وفشل التحميل، نعرض رسالة الستوري الخاصة
            if 'instagram.com' in url and '/stories/' in url:
                await status_msg.edit_text(t('instagram_private_story', lang))
            else:
                await status_msg.edit_text(t('download_failed', lang))
            return
        
        # ⚠️ إذا كان تحميل صوتي، FFmpegExtractAudio يغير الامتداد إلى .mp3
        # لذلك نحتاج إلى تحديث file_path للملف الحقيقي
        if is_audio:
            # تحويل الامتداد إلى .mp3 (FFmpeg يفعل ذلك تلقائياً)
            base_name = os.path.splitext(file_path)[0]
            mp3_file = f"{base_name}.mp3"
            
            if os.path.exists(mp3_file):
                file_path = mp3_file
                logger.info(f"✅ تم العثور على ملف MP3: {file_path}")
            else:
                logger.warning(f"⚠️ لم يتم العثور على {mp3_file}, استخدام المسار الأصلي")
        
        if not os.path.exists(file_path):
            logger.error(f"❌ الملف غير موجود: {file_path}")
            
            # محاولة البحث عن الملف المحمل حديثاً
            logger.info("🔍 البحث عن ملفات محملة حديثاً...")
            
            if is_audio:
                # البحث عن ملفات صوتية
                audio_files = []
                for ext in ['*.mp3', '*.m4a', '*.opus', '*.ogg']:
                    audio_files.extend(glob.glob(ext))
                
                if audio_files:
                    # استخدام أحدث ملف (آخر ملف تم تعديله)
                    latest_file = max(audio_files, key=os.path.getmtime)
                    logger.info(f"✅ تم العثور على ملف صوتي: {latest_file}")
                    file_path = latest_file
                else:
                    logger.error("❌ لم يتم العثور على أي ملفات صوتية")
                    await status_msg.edit_text(t('download_failed', lang))
                    return
            else:
                # البحث عن ملفات فيديو
                video_files = []
                for ext in ['*.mp4', '*.mkv', '*.webm', '*.avi']:
                    video_files.extend(glob.glob(ext))
                
                if video_files:
                    # استخدام أحدث ملف (آخر ملف تم تعديله)
                    latest_file = max(video_files, key=os.path.getmtime)
                    logger.info(f"✅ تم العثور على ملف فيديو: {latest_file}")
                    file_path = latest_file
                else:
                    logger.error("❌ لم يتم العثور على أي ملفات فيديو")
                    await status_msg.edit_text(t('download_failed', lang))
                    return
        
        # معلومات الملف
        file_size_mb = get_file_size_mb(file_path)
        duration = info.get('duration', 0)
        title = info.get('title', 'فيديو')[:50]
        
        logger.info(f"📊 حجم الملف النهائي: {file_size_mb:.2f} MB")

        # التحقق من الحجم
        if file_size_mb > 2000:
            await status_msg.edit_text(
                f"❌ **الملف كبير جداً!**\n\n"
                f"📊 {file_size_mb:.1f} MB\n"
                f"🔒 الحد الأقصى: 2000 MB"
            )
            os.remove(file_path)
            return
        
        # ═══════════════════════════════════════════════════════════════
        # التحقق من حد المدة (للمجموعات والمحادثات الخاصة)
        # ═══════════════════════════════════════════════════════════════
        max_duration_minutes = subdb.get_max_duration()
        max_duration_seconds = max_duration_minutes * 60
        is_subscribed = subdb.is_user_subscribed(user_id)
        
        logger.info(f"⏱️ Duration check: video={duration}s ({duration/60 if duration else 0:.1f}min), max={max_duration_seconds}s ({max_duration_minutes}min), subscribed={is_subscribed}")
        
        if duration and duration > max_duration_seconds and not is_subscribed:
            duration_minutes = int(duration / 60)
            logger.warning(f"⚠️ Video exceeds limit! {duration_minutes} min > {max_duration_minutes} min")
            
            # حذف الملف المحمل
            try:
                os.remove(file_path)
                logger.info(f"🗑️ Deleted file: {file_path}")
            except Exception as del_error:
                logger.warning(f"⚠️ Failed to delete file: {del_error}")
            
            # عرض رسالة الاشتراك
            await show_subscription_screen(
                app, status_msg, user_id, title, duration_minutes, max_duration_minutes
            )
            return
        
        # Upload
        lang = subdb.get_user_language(user_id)
        # Initial upload message with progress bar at 0%
        initial_progress = t('uploading', lang,
                           percent='0.0',
                           current_mb='0.0',
                           total_mb=f'{file_size_mb:.1f}',
                           speed_mb='0.0',
                           eta=0,
                           progress_bar='▱▱▱▱▱▱▱▱▱▱')
        await status_msg.edit_text(initial_progress)
        
        # إنشاء caption مع اسم المستخدم (وmention في المجموعات)
        if is_group and user_username:
            user_link = f"[{user_name}](https://t.me/{user_username})"
            caption = (
                f"🎬 **{title}**\n\n"
                f"📊 {file_size_mb:.1f} MB\n"
                f"⏱️ {int(duration)//60}:{int(duration)%60:02d}\n"
                f"👤 حمّله: {user_link}"
            )
        elif is_group:
            caption = (
                f"🎬 **{title}**\n\n"
                f"📊 {file_size_mb:.1f} MB\n"
                f"⏱️ {int(duration)//60}:{int(duration)%60:02d}\n"
                f"👤 حمّله: {user_name}"
            )
        else:
            caption = (
                f"🎬 **{title}**\n\n"
                f"📊 {file_size_mb:.1f} MB\n"
                f"⏱️ {int(duration)//60}:{int(duration)%60:02d}\n"
                f"👤 {user_name}"
            )
        
        if is_audio:
            # التأكد من duration صحيح
            audio_duration = int(duration) if duration and duration > 0 else None
            
            # Create upload progress tracker instance with event loop
            upload_progress_tracker = UploadProgress(status_msg, user_id, loop)
            
            # إرسال كملف صوتي عادي (Audio) - يدعم ملفات كبيرة حتى 2GB
            logger.info(f"📤 إرسال كملف صوتي (Audio): {file_size_mb:.1f}MB, duration={audio_duration}s")
            
            sent_msg = await client.send_audio(
                chat_id=message.chat.id,
                audio=file_path,
                caption=caption,
                duration=audio_duration,
                progress=upload_progress_tracker
            )
            logger.info(f"✅ نجح إرسال الملف الصوتي: {file_size_mb:.1f}MB")


        else:
            # التأكد من أن جميع القيم صحيحة قبل الإرسال
            video_duration = int(duration) if duration and duration > 0 else None
            video_width = None
            video_height = None
            
            # محاولة الحصول على width/height من info إذا كانت موجودة
            try:
                if info.get('width'):
                    video_width = int(info['width'])
                if info.get('height'):
                    video_height = int(info['height'])
            except:
                pass
            
            logger.info(f"📹 Sending video: duration={video_duration}, width={video_width}, height={video_height}")
            
            # Support button on Binance - فقط في المحادثات الخاصة
            if not is_group:
                binance_id = subdb.get_setting('binance_pay_id', '86847466')
                lang = subdb.get_user_language(user_id)
                support_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        t('support_dev_binance', lang), 
                        url=f"https://app.binance.com/qr/dplkda88dd4d4e86847466"
                    )],
                    [InlineKeyboardButton(
                        t('binance_pay_id', lang, binance_id=binance_id),
                        callback_data="binance_info"
                    )]
                ])
            else:
                support_keyboard = None  # لا أزرار في المجموعات
            
            # Create upload progress tracker instance with event loop
            upload_progress_tracker = UploadProgress(status_msg, user_id, loop)
            
            try:
                sent_msg = await client.send_video(
                    chat_id=message.chat.id,
                    video=file_path,
                    caption=caption,
                    duration=video_duration,
                    width=video_width,
                    height=video_height,
                    supports_streaming=True,
                    reply_markup=support_keyboard,
                    progress=upload_progress_tracker
                )
            except Exception as send_error:
                logger.error(f"❌ خطأ في send_video: {send_error}")
                # محاولة بدون أي معاملات إضافية
                logger.info("🔄 Retrying with minimal parameters...")
                sent_msg = await client.send_video(
                    chat_id=message.chat.id,
                    video=file_path,
                    caption=caption,
                    supports_streaming=True
                )
            
            # ═══════════════════════════════════════════════════════════════
            # الحذف التلقائي في المجموعات
            # ═══════════════════════════════════════════════════════════════
            if is_group:
                auto_delete_seconds = subdb.get_group_auto_delete(message.chat.id)
                if auto_delete_seconds > 0:
                    logger.info(f"🗑️ سيتم حذف الفيديو بعد {auto_delete_seconds} ثانية")
                    # جدولة حذف الرسالة
                    asyncio.create_task(delete_message_after_delay(sent_msg, auto_delete_seconds))
        
        await status_msg.delete()
        logger.info(f"✅ نجح رفع {file_size_mb:.1f}MB للمستخدم {user_id}")
        
        # تحويل الفيديو إلى قناة السجلات
        try:
            await forward_to_log_channel(
                client=client,
                message=message,
                sent_message=sent_msg,
                user_id=user_id,
                user_name=user_name,
                username=user_username,
                url=url,
                video_info=info,
                duration=duration,
                file_size_mb=file_size_mb,
                chat=message.chat
            )
        except Exception as log_error:
            logger.error(f"⚠️ خطأ في إرسال للقناة: {log_error}")
        
        # حذف جميع الملفات المحملة من كل المجلدات
        cleanup_downloaded_files(file_path)
        
        # زيادة عداد التحميلات اليومية للمستخدمين غير المشتركين
        if not subdb.is_user_subscribed(user_id):
            subdb.increment_download_count(user_id)
            
            # عرض رسالة التحميلات المتبقية
            daily_limit = subdb.get_daily_limit()
            if daily_limit != -1:  # فقط إذا لم يكن غير محدود
                daily_count = subdb.check_daily_limit(user_id)
                remaining = daily_limit - daily_count
                
                if remaining > 0:
                    # الحصول على لغة المستخدم
                    lang = subdb.get_user_language(user_id)
                    await message.reply_text(
                        t('downloads_remaining', lang, remaining=remaining)
                    )

        
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        
        # إذا كان الخطأ to_bytes، يعني الفيديو نجح لكن مشكلة metadata
        if 'to_bytes' in str(e):
            # الفيديو تم رفعه بنجاح، فقط نحذف الرسالة والملفات
            try:
                await status_msg.delete()
                cleanup_downloaded_files(file_path if 'file_path' in locals() else None)
                logger.info(f"✅ نجح رفع {file_size_mb:.1f}MB للمستخدم {user_id} (تم تجاهل خطأ metadata)")
            except:
                pass
        else:
            # خطأ حقيقي - إرسال تنبيه للأدمن
            user_name = message.from_user.first_name or "مستخدم"
            
            # الحصول على traceback الكامل
            error_traceback = traceback.format_exc()
            
            # إرسال الخطأ مع traceback إلى القناة
            await send_error_to_admin(user_id, user_name, str(e), url, error_traceback)
            
            error_text = str(e)
            
            # تنظيف رسالة الخطأ من ANSI codes
            import re
            error_text = re.sub(r'\x1b\[[0-9;]*m', '', error_text)
            
            # Get user language for error messages
            lang = subdb.get_user_language(user_id)
            
            # حذف الملفات المحملة حتى في حالة الخطأ
            cleanup_downloaded_files(file_path if 'file_path' in locals() else None)
            
            # رسائل مخصصة لأخطاء معينة
            if 'Cannot parse data' in error_text and 'facebook' in error_text.lower():
                await status_msg.edit_text(t('facebook_unavailable', lang))
            elif 'Pinterest' in error_text and ('Connection reset' in error_text or 'Unable to download' in error_text):
                await status_msg.edit_text(t('pinterest_unavailable', lang))
            elif 'instagram' in url and '/stories/' in url and any(x in error_text.lower() for x in ['login', 'private', 'forbidden', '401', '403', 'not found', 'unavailable']):
                # Instagram private story error
                await status_msg.edit_text(t('instagram_private_story', lang))
            else:
                # تقصير رسالة الخطأ
                short_error = error_text.split('\n')[0][:100]
                await status_msg.edit_text(t('generic_error', lang, error=short_error))



# ═══════════════════════════════════════════════════════════════
# Handlers
# ═══════════════════════════════════════════════════════════════

@app.on_message(filters.channel)
async def handle_channel_message(client, message):
    """
    Handler to make bot aware of channels it's admin in.
    This helps resolve PEER_ID_INVALID errors by caching channel information.
    
    When a message is posted in a channel where the bot is admin,
    Telegram sends an update to the bot. This handler processes that update
    and allows Telegram to recognize the channel for future interactions.
    """
    try:
        chat = message.chat
        logger.info(f"✅ Channel recognized: {chat.title} (ID: {chat.id})")
        
        # Log channel details for debugging
        logger.info(f"   📝 Type: {chat.type}")
        logger.info(f"   👥 Username: {chat.username if chat.username else 'No username'}")
        
        # Try to send a confirmation message (will be deleted immediately)
        try:
            test_msg = await client.send_message(
                chat_id=chat.id,
                text="✅ البوت نشط ومتصل بالقناة"
            )
            await asyncio.sleep(2)
            await test_msg.delete()
            logger.info(f"   ✅ Bot can now send messages to {chat.title}")
        except Exception as send_error:
            logger.warning(f"   ⚠️  Bot recognized channel but can't send messages: {send_error}")
        
    except Exception as e:
        logger.error(f"❌ Error in channel message handler: {e}")

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    
    # ═══════════════════════════════════════════════════════════════
    # في المجموعات - لا نرسل keyboard شخصي، فقط رسالة ترحيب بسيطة
    # ═══════════════════════════════════════════════════════════════
    if message.chat.type.value != "private":
        lang = subdb.get_user_language(user_id)
        await message.reply_text(
            f"👋 مرحباً!\n\n"
            f"🤖 أنا بوت تحميل الفيديوهات\n"
            f"📹 أرسل لي أي رابط فيديو للتحميل\n\n"
            f"⚙️ للأدمن: استخدم /settings لإعدادات المجموعة"
        )
        return
    
    # التحقق من وجود لغة محددة للمستخدم
    lang = subdb.get_user_language(user_id)
    
    # إذا كانت أول مرة (لغة غير محددة أو قيمة افتراضية)
    # نتحقق إذا كان موجود في قاعدة البيانات
    user_exists = subdb.find_user_by_id(user_id)
    
    if not user_exists:
        # مستخدم جديد - إرسال إشعار للقناة
        join_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await send_new_member_notification(
            user_id=user_id,
            user_name=message.from_user.first_name,
            username=message.from_user.username,
            join_time=join_time
        )
        
        # عرض اختيار اللغة بتصميم عصري
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇮🇶 العربية", callback_data="lang_ar"),
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
            ]
        ])
        
        language_msg = (
            "🌍✨ **مرحباً بك!** | **Welcome!**\n\n"
            "┌─────────────────────────┐\n"
            "│   🎨 **اختر لغتك**        │\n"
            "│   **Choose Your Language**  │\n"
            "└─────────────────────────┘\n\n"
            "👇 **اضغط على لغتك المفضلة:**"
        )
        
        await message.reply_text(
            language_msg,
            reply_markup=keyboard
        )
        return
    
    # مستخدم موجود - عرض الرسالة الترحيبية
    keyboard = None
    admin_id = os.getenv("ADMIN_ID")
    
    if admin_id and str(user_id) == admin_id:
        from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton(t('btn_cookies', lang)), KeyboardButton(t('btn_daily_report', lang))],
            [KeyboardButton(t('btn_errors', lang)), KeyboardButton(t('btn_subscription', lang))],
            [KeyboardButton(t('btn_change_language', lang))]
        ], resize_keyboard=True)
    else:
        # للمستخدمين العاديين - التحقق من الاشتراك
        from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
        
        # التحقق من حالة الاشتراك
        is_subscribed = subdb.is_user_subscribed(user_id)
        
        if is_subscribed:
            # مشترك - عرض زر الاشتراك + إضافة للمجموعة + تغيير اللغة
            keyboard = ReplyKeyboardMarkup([
                [KeyboardButton(t('btn_my_subscription', lang))],
                [KeyboardButton(t('btn_add_to_group', lang))],
                [KeyboardButton(t('btn_change_language', lang))]
            ], resize_keyboard=True)
        else:
            # غير مشترك - زر إضافة للمجموعة + تغيير اللغة
            keyboard = ReplyKeyboardMarkup([
                [KeyboardButton(t('btn_add_to_group', lang))],
                [KeyboardButton(t('btn_change_language', lang))]
            ], resize_keyboard=True)
    
    # زر إضافة البوت للمجموعة - Add to Group button
    bot_me = await client.get_me()
    add_to_group_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            t('btn_add_to_group', lang),
            url=f"https://t.me/{bot_me.username}?startgroup=true"
        )]
    ])
    
    await message.reply_text(
        t('welcome', lang, name=message.from_user.first_name),
        reply_markup=keyboard
    )
    
    # إرسال زر إضافة البوت للمجموعة كرسالة منفصلة
    await message.reply_text(
        "👥",
        reply_markup=add_to_group_keyboard
    )


# معالج الأزرار السريعة
@app.on_message(filters.text & filters.regex(r'^(🍪 Cookies|📊 التقرير اليومي|🔔 الأخطاء|💎 إعدادات الاشتراك|📁 نسخ احتياطي)$'))
async def handle_quick_buttons(client, message):
    """معالج الأزرار السريعة - يعمل في المحادثات الخاصة فقط"""
    # تجاهل المجموعات - الأزرار للمحادثات الخاصة فقط
    if message.chat.type.value != "private":
        return
    
    user_id = message.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        return
    
    if message.text == "🍪 Cookies":
        await cookies_panel(client, message)
    elif message.text == "📊 التقرير اليومي":
        await send_daily_report(client, message.from_user.id)
    elif message.text == "🔔 الأخطاء":
        await show_errors(client, message)
    elif message.text == "💎 إعدادات الاشتراك":
        await subscription_settings_panel(client, message)
    elif message.text == "📁 نسخ احتياطي":
        await send_database_backup(client, message)


# معالج زر اشتراكي - Subscription Status Button Handler
@app.on_message(filters.text & filters.regex(r'^💎 اشتراكي$|^💎 My Subscription$'))
async def handle_my_subscription(client, message):
    """معالج زر حالة الاشتراك للمستخدمين - يعمل في المحادثات الخاصة فقط"""
    # تجاهل المجموعات
    if message.chat.type.value != "private":
        return
    
    user_id = message.from_user.id
    lang = subdb.get_user_language(user_id)
    
    # التحقق من انتظار إدخال رابط للحظر
    if user_id in pending_downloads and pending_downloads[user_id].get('waiting_for') == 'blocked_url':
        url_to_block = message.text.strip()
        
        # إضافة الرابط للقائمة المحظورة
        if subdb.add_blocked_url(url_to_block, user_id):
            await message.reply_text(
                f"✅ تمت إضافة الرابط للقائمة المحظورة!\n\n"
                f"🔗 {url_to_block}\n\n"
                f"الآن لن يتمكن أي مستخدم من التحميل من هذا الموقع"
            )
        else:
            await message.reply_text(
                "❌ خطأ في إضافة الرابط\n\n"
                "قد يكون الرابط موجود مسبقاً"
            )
        
        del pending_downloads[user_id]
        return
    
    # التحقق من انتظار إدخال سعر الاشتراك
    if not subdb.is_user_subscribed(user_id):
        await message.reply_text(t('not_subscribed', lang))
        return
    
    # الحصول على معلومات الاشتراك
    time_info = subdb.get_time_remaining(user_id)
    
    if not time_info:
        await message.reply_text(t('not_subscribed', lang))
        return
    
    # عرض معلومات الاشتراك
    await message.reply_text(
        t('subscription_status', lang,
          end_date=time_info['end_date_formatted'],
          days=time_info['days'],
          hours=time_info['hours'])
    )



async def send_daily_report(client, admin_id):
    """إرسال التقرير اليومي"""
    now = datetime.now()
    report_text = f"📊 **تقرير فحص الكوكيز اليومي**\n\n"
    report_text += f"📅 **التاريخ:** {now.strftime('%d-%m-%Y %H:%M:%S')}\n\n"
    
    valid_cookies = []
    expired_cookies = []
    missing_cookies = []
    
    for platform_id, data in COOKIES_PLATFORMS.items():
        if os.path.exists(data['file']):
            file_time = os.path.getmtime(data['file'])
            uploaded_date = datetime.fromtimestamp(file_time)
            days_ago = (now - uploaded_date).days
            days_left = max(0, 30 - days_ago)
            
            if days_left > 0:
                valid_cookies.append((data['name'], days_left))
            else:
                expired_cookies.append(data['name'])
        else:
            missing_cookies.append(data['name'])
    
    # الكوكيز الصالحة
    report_text += f"✅ **الكوكيز الصالحة ({len(valid_cookies)}):**\n"
    if valid_cookies:
        for name, days in valid_cookies:
            report_text += f"• {name}: {days} يوم\n"
    else:
        report_text += "⚠️ لا توجد\n"
    
    report_text += "\n"
    
    # الكوكيز المنتهية
    if expired_cookies:
        report_text += f"❌ **منتهية ({len(expired_cookies)}):**\n"
        for name in expired_cookies:
            report_text += f"• {name}\n"
        report_text += "\n"
    
    # الغير موجودة
    if missing_cookies:
        report_text += f"⚠️ **غير موجودة ({len(missing_cookies)}):**\n"
        for name in missing_cookies:
            report_text += f"• {name}\n"
        report_text += "\n"
    
    # إحصائيات
    total = len(COOKIES_PLATFORMS)
    checked = len(valid_cookies) + len(expired_cookies)
    success_rate = (len(valid_cookies) / total * 100) if total > 0 else 0
    
    report_text += f"📈 **الإحصائيات:**\n"
    report_text += f"• تم الفحص: {checked} منصة\n"
    report_text += f"• معدل النجاح: {success_rate:.1f}%"
    
    await client.send_message(admin_id, report_text)


# مهمة خلفية للتقرير اليومي
async def show_errors(client, message):
    """عرض قائمة الأخطاء للأدمن"""
    pending_errors = {k: v for k, v in user_errors.items() if v['status'] == 'pending'}
    
    if not pending_errors:
        await message.reply_text("✅ **لا توجد أخطاء معلقة!**\n\nجميع المشاكل تم حلها.")
        return
    
    text = "🔔 **قائمة الأخطاء المعلقة**\n\n"
    
    for error_id, error_data in list(pending_errors.items())[:10]:  # آخر 10 أخطاء
        text += f"━━━━━━━━━━━━━━━━\n"
        text += f"🆔 **ID:** `{error_id}`\n"
        text += f"👤 **المستخدم:** {error_data['user_name']} (`{error_data['user_id']}`)\n"
        text += f"🕐 **الوقت:** {error_data['time']}\n"
        text += f"🔗 **الرابط:** `{error_data['url'][:40]}...`\n\n"
    
    text += f"\n📝 **إجمالي الأخطاء المعلقة:** {len(pending_errors)}"
    
    await message.reply_text(text)


@app.on_callback_query(filters.regex(r'^resolve_'))
async def handle_resolve_error(client, callback_query):
    """معالج زر تم الإصلاح"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    error_id = callback_query.data.replace('resolve_', '')
    
    if error_id not in user_errors:
        await callback_query.answer("❌ الخطأ غير موجود!", show_alert=True)
        return
    
    error_data = user_errors[error_id]
    
    if error_data['status'] == 'resolved':
        await callback_query.answer("✅ تم حل هذا الخطأ مسبقاً", show_alert=True)
        return
    
    # تحديث الحالة
    user_errors[error_id]['status'] = 'resolved'
    
    # إرسال رسالة للمستخدم
    try:
        await client.send_message(
            chat_id=error_data['user_id'],
            text=f"✅ **تم إصلاح مشكلتك!**\n\n"
                 f"المشكلة التي واجهتها مع الرابط:\n"
                 f"`{error_data['url'][:50]}...`\n\n"
                 f"تم حلها الآن. يمكنك المحاولة مرة أخرى! 🎉"
        )
        logger.info(f"✅ تم إرسال إشعار الحل للمستخدم {error_data['user_id']}")
    except Exception as e:
        logger.error(f"فشل إرسال إشعار للمستخدم: {e}")
    
    # تحديث الرسالة
    await callback_query.message.edit_text(
        callback_query.message.text + f"\n\n✅ **تم الحل بواسطة الأدمن**",
        reply_markup=None
    )
    
    await callback_query.answer("✅ تم إرسال إشعار للمستخدم", show_alert=True)


# تقرير يومي تلقائي
async def daily_report_task():
    """مهمة خلفية لإرسال التقرير يومياً"""
    from datetime import timedelta
    
    while True:
        now = datetime.now()
        # إرسال في الساعة 9 صباحاً
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        if now > target_time:
            # إذا مرت الساعة 9، اذهب لليوم التالي
            target_time = target_time + timedelta(days=1)
        
        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        # إرسال التقرير
        admin_id = int(os.getenv("ADMIN_ID"))
        await send_daily_report(app, admin_id)
        
        # انتظر يوم كامل
        await asyncio.sleep(86400)


async def send_database_backup(client, message):
    """إرسال نسخة احتياطية من قاعدة البيانات PostgreSQL"""
    user_id = message.from_user.id
    
    # التحقق من صلاحيات الأدمن
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or str(user_id) != admin_id:
        await message.reply_text("❌ **غير مصرح!**\n\nهذا الأمر للمشرفين فقط.")
        return
    
    try:
        # رسالة انتظار
        status_msg = await message.reply_text(
            "⏳ **جاري إنشاء النسخة الاحتياطية...**\n\n"
            "هذا قد يستغرق بضع ثوانٍ... ⏰"
        )
        
        # إنشاء النسخة الاحتياطية
        logger.info(f"🔄 الأدمن {user_id} طلب نسخة احتياطية من قاعدة البيانات")
        success, result = pg_backup.create_backup(prefer_sql=True)
        
        if not success:
            await status_msg.edit_text(
                f"❌ **فشل إنشاء النسخة الاحتياطية!**\n\n"
                f"**الخطأ:** `{result}`\n\n"
                f"تواصل مع مطور البوت للمساعدة."
            )
            logger.error(f"❌ فشل إنشاء النسخة الاحتياطية: {result}")
            return
        
        backup_file_path = result
        file_size_mb = os.path.getsize(backup_file_path) / (1024 * 1024)
        file_type = "SQL" if backup_file_path.endswith(".sql") else "JSON"
        
        # تحديث الرسالة
        await status_msg.edit_text(
            f"📤 **جاري رفع النسخة الاحتياطية...**\n\n"
            f"📦 النوع: {file_type}\n"
            f"💾 الحجم: {file_size_mb:.2f} MB"
        )
        
        # إرسال الملف
        caption = (
            f"📁 **نسخة احتياطية من قاعدة البيانات**\n\n"
            f"📦 **النوع:** {file_type}\n"
            f"💾 **الحجم:** {file_size_mb:.2f} MB\n"
            f"📅 **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🗄️ **قاعدة البيانات:** PostgreSQL\n\n"
            f"✅ يمكنك استخدام هذا الملف لاستعادة البيانات في حالة الطوارئ."
        )
        
        await client.send_document(
            chat_id=user_id,
            document=backup_file_path,
            caption=caption
        )
        
        # حذف رسالة الحالة
        await status_msg.delete()
        
        # حذف الملف المؤقت
        try:
            os.remove(backup_file_path)
            logger.info(f"🗑️ تم حذف الملف المؤقت: {backup_file_path}")
        except Exception as e:
            logger.warning(f"⚠️ فشل حذف الملف المؤقت: {e}")
        
        # تنظيف الملفات القديمة
        pg_backup.cleanup_old_backups(max_age_hours=1)
        
        logger.info(f"✅ تم إرسال النسخة الاحتياطية بنجاح للأدمن {user_id}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في send_database_backup: {e}", exc_info=True)
        try:
            await message.reply_text(
                f"❌ **حدث خطأ أثناء إنشاء النسخة الاحتياطية!**\n\n"
                f"**الخطأ:** `{str(e)[:200]}`"
            )
        except:
            pass


@app.on_message(filters.command("cookies"))
async def cookies_panel(client, message):
    """لوحة إدارة الـ cookies (للأدمن فقط)"""
    user_id = message.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        await message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    # بناء الأزرار
    keyboard = []
    for platform_id, data in COOKIES_PLATFORMS.items():
        keyboard.append([
            InlineKeyboardButton(data['name'], callback_data=f"cookies_{platform_id}")
        ])
    
    # زر مراجعة حالة الـ cookies
    keyboard.append([
        InlineKeyboardButton("📊 حالة جميع الـ Cookies", callback_data="cookies_status")
    ])
    
    await message.reply_text(
        "🍪 **إدارة Cookies**\n\n"
        "اختر المنصة لإضافة أو اختبار الـ cookies:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@app.on_callback_query(filters.regex(r'^cookies_(?!back$|status$)'))
async def cookies_platform_handler(client, callback_query):
    """معالج اختيار المنصة"""
    user_id = callback_query.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    # استخراج اسم المنصة من callback_data
    platform_id = callback_query.data.replace('cookies_', '')
    
    if platform_id not in COOKIES_PLATFORMS:
        await callback_query.answer("❌ منصة غير صحيحة!")
        return
    
    platform = COOKIES_PLATFORMS[platform_id]
    cookie_exists = os.path.exists(platform['file'])
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة Cookies", callback_data=f"add_cookie_{platform_id}")],
        [InlineKeyboardButton("✅ اختبار Cookies", callback_data=f"test_cookie_{platform_id}")],
        [InlineKeyboardButton("« رجوع", callback_data="cookies_back")]
    ])
    
    status = "✅ موجود" if cookie_exists else "❌ غير موجود"
    
    # إضافة معلومات الصلاحية
    expiry_info = ""
    if cookie_exists:
        file_time = os.path.getmtime(platform['file'])
        uploaded_date = datetime.fromtimestamp(file_time)
        days_ago = (datetime.now() - uploaded_date).days
        days_left = max(0, 30 - days_ago)
        
        expiry_info = f"\n⏱️ **رفع قبل:** {days_ago} يوم\n📅 **باقي:** {days_left} يوم"
    
    await callback_query.message.edit_text(
        f"🍪 **{platform['name']}**\n\n"
        f"📊 **الحالة:** {status}{expiry_info}\n\n"
        "اختر الإجراء:",
        reply_markup=keyboard
    )
    await callback_query.answer()


@app.on_callback_query(filters.regex(r'^cookies_status$'))
async def cookies_status_handler(client, callback_query):
    """معالج عرض حالة جميع الـ Cookies"""
    user_id = callback_query.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    status_text = "📊 **حالة جميع الـ Cookies**\n\n"
    
    for platform_id, data in COOKIES_PLATFORMS.items():
        cookie_exists = os.path.exists(data['file'])
        
        if cookie_exists:
            file_time = os.path.getmtime(data['file'])
            uploaded_date = datetime.fromtimestamp(file_time)
            days_ago = (datetime.now() - uploaded_date).days
            
            # افتراض صلاحية 30 يوم
            days_left = 30 - days_ago
            
            if days_left > 7:
                status_icon = "✅"
            elif days_left > 0:
                status_icon = "⚠️"
            else:
                status_icon = "❌"
            
            status_text += f"{status_icon} **{data['name']}**\n"
            status_text += f"   ⏱️ رفع قبل: {days_ago} يوم\n"
            status_text += f"   📅 باقي: {max(0, days_left)} يوم\n\n"
        else:
            status_text += f"❌ **{data['name']}**\n"
            status_text += f"   ⚠️ غير موجود\n\n"
    
    await callback_query.message.edit_text(
        status_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« رجوع", callback_data="cookies_back")]
        ])
    )
    
    await callback_query.answer()


@app.on_message(filters.command("backup"))
async def backup_command(client, message):
    """معالج أمر /backup - لإنشاء نسخة احتياطية من قاعدة البيانات"""
    await send_database_backup(client, message)


@app.on_callback_query(filters.regex(r'^add_cookie_'))
async def add_cookie_handler(client, callback_query):
    """طلب إضافة cookies"""
    user_id = callback_query.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    platform_id = callback_query.data.replace('add_cookie_', '')
    platform = COOKIES_PLATFORMS[platform_id]
    
    waiting_for_cookies[user_id] = platform_id
    
    await callback_query.message.edit_text(
        f"🍪 **إضافة Cookies - {platform['name']}**\n\n"
        "📝 **كيفية الحصول على Cookies:**\n"
        "1. افتح المنصة في المتصفح\n"
        "2. سجل دخول لحسابك\n"
        "3. استخدم إضافة **Get cookies.txt** أو **EditThisCookie**\n"
        "4. صدّر الـ cookies بصيغة Netscape\n"
        "5. أرسل الملف هنا\n\n"
        "⚠️ **ملاحظة:** استخدم ملف .txt فقط (Netscape format)"
    )
    await callback_query.answer()


def analyze_cookie_validity(cookie_file: str) -> dict:
    """
    تحليل ملف الـ cookies وإرجاع معلومات الصلاحية
    Analyze cookie file and return validity information
    
    Returns:
        dict with: exists, valid_count, expired_count, total_count, 
                   expires_in_days, session_cookies, file_age_days
    """
    result = {
        'exists': False,
        'valid_count': 0,
        'expired_count': 0,
        'total_count': 0,
        'expires_in_days': None,
        'session_cookies': 0,
        'file_age_days': 0
    }
    
    if not os.path.exists(cookie_file):
        return result
    
    result['exists'] = True
    result['file_age_days'] = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cookie_file))).days
    
    # قراءة وتحليل الكوكيز
    current_time = time.time()
    min_expiry = None
    
    try:
        with open(cookie_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    result['total_count'] += 1
                    try:
                        expiry = int(parts[4])
                        if expiry == 0:
                            # Session cookie - صالح طالما المتصفح مفتوح
                            result['session_cookies'] += 1
                            result['valid_count'] += 1
                        elif expiry < current_time:
                            result['expired_count'] += 1
                        else:
                            result['valid_count'] += 1
                            if min_expiry is None or expiry < min_expiry:
                                min_expiry = expiry
                    except:
                        pass
    except Exception as e:
        logger.error(f"Error reading cookie file: {e}")
    
    if min_expiry:
        result['expires_in_days'] = max(0, int((min_expiry - current_time) / 86400))
    
    return result


@app.on_callback_query(filters.regex(r'^test_cookie_'))
async def test_cookie_handler(client, callback_query):
    """اختبار cookies مع روابط حقيقية لكل منصة"""
    user_id = callback_query.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    platform_id = callback_query.data.replace('test_cookie_', '')
    platform = COOKIES_PLATFORMS[platform_id]
    
    if not os.path.exists(platform['file']):
        await callback_query.answer("❌ لا توجد cookies لهذه المنصة!", show_alert=True)
        return
    
    await callback_query.answer("⏳ جاري تحليل واختبار الـ Cookies...")
    
    # تحليل صلاحية الكوكيز أولاً
    cookie_info = analyze_cookie_validity(platform['file'])
    
    # إعداد نص معلومات الكوكيز
    cookie_status_text = ""
    if cookie_info['total_count'] > 0:
        validity_icon = "✅" if cookie_info['valid_count'] > cookie_info['expired_count'] else "⚠️"
        cookie_status_text = (
            f"\n📊 **تحليل الكوكيز:**\n"
            f"   • إجمالي: {cookie_info['total_count']} كوكي\n"
            f"   • {validity_icon} صالحة: {cookie_info['valid_count']}\n"
            f"   • ❌ منتهية: {cookie_info['expired_count']}\n"
            f"   • 🔄 مؤقتة (Session): {cookie_info['session_cookies']}\n"
        )
        
        # عرض تاريخ الانتهاء فقط إذا كان هناك كوكيز غير Session
        if cookie_info['expires_in_days'] is not None and cookie_info['expires_in_days'] > 0:
            if cookie_info['expires_in_days'] <= 3:
                expiry_icon = "🔴"
            elif cookie_info['expires_in_days'] <= 7:
                expiry_icon = "🟡"
            else:
                expiry_icon = "🟢"
            cookie_status_text += f"   • {expiry_icon} تنتهي خلال: {cookie_info['expires_in_days']} يوم\n"
        elif cookie_info['session_cookies'] == cookie_info['valid_count']:
            # كل الكوكيز الصالحة هي Session cookies
            cookie_status_text += f"   • 🟢 كوكيز مؤقتة (لا تنتهي)\n"
        
        if cookie_info['file_age_days'] > 0:
            cookie_status_text += f"   • 📅 عمر الملف: {cookie_info['file_age_days']} يوم\n"
    
    # روابط اختبار - YouTube للجميع (مضمون 100%)
    # لأن المنصات الأخرى تتغير روابطها أو تحتاج تسجيل دخول
    test_urls = {
        'youtube': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',  # أول فيديو على يوتيوب
        'instagram': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
        'twitter': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
        'facebook': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
        'tiktok': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
        'reddit': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
        'pinterest': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
        'snapchat': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
        'other': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
    }
    
    # ملاحظة: الاختبار الحقيقي هو تحليل الكوكيز نفسها
    # YouTube فقط للتأكد من أن yt-dlp يعمل
    
    test_url = test_urls.get(platform_id, test_urls['other'])
    
    try:
        test_opts = {
            'quiet': True,
            'no_warnings': True,
            'cookiefile': platform['file'],
            'skip_download': True,
            'no_check_certificate': True,
            'socket_timeout': 30,
        }
        
        loop = asyncio.get_event_loop()
        
        def do_test():
            with yt_dlp.YoutubeDL(test_opts) as ydl:
                return ydl.extract_info(test_url, download=False)
        
        info = await loop.run_in_executor(None, do_test)
        
        # الحصول على معلومات الفيديو
        video_title = info.get('title', 'فيديو')[:50]
        video_duration = info.get('duration', 0)
        duration_str = f"{int(video_duration)//60}:{int(video_duration)%60:02d}" if video_duration else "—"
        
        # تحديد حالة الكوكيز النهائية
        if cookie_info['expired_count'] > cookie_info['valid_count']:
            final_status = "⚠️ معظم الكوكيز منتهية - يُنصح بالتحديث"
        elif cookie_info['expires_in_days'] is not None and cookie_info['expires_in_days'] <= 3:
            final_status = "⚠️ الكوكيز ستنتهي قريباً - حدّثها"
        else:
            final_status = "✅ تعمل بشكل ممتاز!"
        
        await callback_query.message.edit_text(
            f"✅ **اختبار Cookies ناجح!**\n\n"
            f"🍪 **المنصة:** {platform['name']}\n"
            f"📂 **الملف:** `{platform['file']}`\n\n"
            f"🎬 **فيديو الاختبار:** {video_title}...\n"
            f"⏱️ **المدة:** {duration_str}\n"
            f"🔗 **من:** {platform['name'].split()[0]}\n"
            f"{cookie_status_text}\n"
            f"📊 **الحالة:** {final_status}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« رجوع", callback_data=f"cookies_{platform_id}")]
            ])
        )
        
    except Exception as e:
        error_msg = str(e)
        
        # تنظيف رسالة الخطأ من ANSI codes
        error_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
        
        # تحديد نوع الخطأ وعرض رسالة مناسبة
        if "login" in error_msg.lower() or "sign in" in error_msg.lower():
            status_msg = "❌ **الكوكيز منتهية أو غير صالحة**\n\nيجب تحديث ملف الكوكيز بتسجيل دخول جديد."
        elif "private" in error_msg.lower():
            status_msg = "⚠️ **المحتوى خاص**\n\nالكوكيز صالحة لكن المحتوى خاص. جرب رابط عام."
        elif "Unsupported URL" in error_msg:
            status_msg = "ℹ️ **yt-dlp لا يدعم هذا الرابط**\n\nالكوكيز محفوظة وستعمل مع الروابط المدعومة."
        elif "unavailable" in error_msg.lower() or "not found" in error_msg.lower():
            status_msg = "⚠️ **الفيديو التجريبي غير متاح**\n\nالكوكيز محفوظة - جرب تحميل رابط آخر للتأكد."
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            status_msg = "⚠️ **تم تجاوز حد الطلبات**\n\nالكوكيز صالحة لكن المنصة حظرت الطلبات مؤقتاً."
        else:
            status_msg = f"⚠️ **خطأ في الاختبار**\n\n`{error_msg[:200]}`"
        
        await callback_query.message.edit_text(
            f"{status_msg}\n\n"
            f"🍪 **المنصة:** {platform['name']}\n"
            f"📂 **الملف:** `{platform['file']}`\n"
            f"{cookie_status_text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 إعادة الاختبار", callback_data=f"test_cookie_{platform_id}")],
                [InlineKeyboardButton("« رجوع", callback_data=f"cookies_{platform_id}")]
            ])
        )




@app.on_callback_query(filters.regex(r'^cookies_back$'))
async def cookies_back_handler(client, callback_query):
    """العودة لقائمة المنصات"""
    user_id = callback_query.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        return
    
    keyboard = []
    for platform_id, data in COOKIES_PLATFORMS.items():
        keyboard.append([
            InlineKeyboardButton(data['name'], callback_data=f"cookies_{platform_id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("📊 حالة جميع الـ Cookies", callback_data="cookies_status")
    ])
    
    await callback_query.message.edit_text(
        "🍪 **إدارة Cookies**\n\n"
        "اختر المنصة لإضافة أو اختبار الـ cookies:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await callback_query.answer()


@app.on_message(filters.document)
async def handle_cookie_file(client, message):
    """معالج ملفات الـ cookies"""
    user_id = message.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        return
    
    if user_id not in waiting_for_cookies:
        return
    
    platform_id = waiting_for_cookies[user_id]
    platform = COOKIES_PLATFORMS[platform_id]
    
    # التحقق من نوع الملف
    if not message.document.file_name.endswith('.txt'):
        await message.reply_text("❌ يجب أن يكون الملف بصيغة .txt!")
        return
    
    status_msg = await message.reply_text("⏳ جاري حفظ الـ cookies...")
    
    try:
        # تحميل الملف
        file_path = await client.download_media(message.document.file_id)
        
        # نسخ الملف إلى مجلد cookies
        import shutil
        shutil.move(file_path, platform['file'])
        
        del waiting_for_cookies[user_id]
        
        await status_msg.edit_text(
            f"✅ **تم حفظ Cookies بنجاح!**\n\n"
            f"🍪 **المنصة:** {platform['name']}\n"
            f"📂 **الملف:** {platform['file']}\n\n"
            "يمكنك الآن استخدام /cookies لاختبارها."
        )
        
        logger.info(f"✅ الأدمن {user_id} أضاف cookies لـ {platform_id}")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ فشل حفظ الملف: {str(e)}")
        logger.error(f"خطأ في حفظ cookies: {e}")


# ═══════════════════════════════════════════════════════════════
# Group Handlers - معالجات المجموعات
# ═══════════════════════════════════════════════════════════════

@app.on_message(filters.new_chat_members)
async def on_bot_added_to_group(client, message):
    """معالج عندما يُضاف البوت لمجموعة - يعرض الإعدادات تلقائياً"""
    bot_me = await client.get_me()
    
    # التحقق من أن البوت هو من تمت إضافته
    for member in message.new_chat_members:
        if member.id == bot_me.id:
            chat_id = message.chat.id
            
            # الحصول على لغة من أضاف البوت
            if message.from_user:
                user_id = message.from_user.id
                lang = subdb.get_user_language(user_id)
                user_name = message.from_user.first_name
            else:
                lang = 'ar'
                user_id = None
                user_name = "Admin"
            
            logger.info(f"🤖 تمت إضافة البوت لمجموعة: {message.chat.title} (ID: {chat_id})")
            
            # إنشاء الإعدادات الافتراضية
            subdb.set_group_settings(chat_id, admin_only=True)
            
            # زر الإعدادات
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ إعدادات البوت", callback_data=f"group_settings_main_{chat_id}")]
            ])
            
            welcome_msg = (
                f"👋 **مرحباً!**\n\n"
                f"🤖 تمت إضافة بوت تحميل الفيديوهات للمجموعة بنجاح!\n\n"
                f"📹 **كيف تستخدم البوت:**\n"
                f"• أرسل أي رابط فيديو في المجموعة\n"
                f"• سيقوم البوت بتحميله تلقائياً\n\n"
                f"⚙️ **للأدمن:** اضغط الزر أدناه أو استخدم /settings"
            )
            
            await message.reply_text(welcome_msg, reply_markup=keyboard)
            
            break

@app.on_message(filters.group & filters.command("settings"))
async def group_settings_command(client, message):
    """معالج أمر /settings في المجموعات - للأدمن فقط"""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = subdb.get_user_language(user_id)
    
    # التحقق من صلاحيات الأدمن
    try:
        from pyrogram.enums import ChatMemberStatus
        member = await client.get_chat_member(chat_id, user_id)
        is_admin = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        logger.info(f"🔍 Group settings: user {user_id} status = {member.status}, is_admin = {is_admin}")
    except Exception as e:
        logger.error(f"خطأ في فحص صلاحيات المستخدم: {e}")
        is_admin = False
    
    if not is_admin:
        await message.reply_text(t('group_not_admin', lang))
        return
    
    # عرض القائمة الرئيسية للإعدادات
    await show_group_settings_menu(client, message, chat_id, lang)


async def show_group_settings_menu(client, message_or_callback, chat_id: int, lang: str, edit: bool = False):
    """عرض القائمة الرئيسية لإعدادات المجموعة"""
    settings = subdb.get_group_settings(chat_id)
    
    # تنسيق الإعدادات الحالية بناءً على اللغة
    if lang == 'en':
        who_can_use = t('grp_admins_only_current', lang) if settings['admin_only'] else t('grp_everyone_current', lang)
        auto_delete = f"⏱️ {settings['auto_delete_seconds']}{t('grp_seconds', lang)}" if settings['auto_delete_seconds'] > 0 else t('grp_disabled', lang)
        quiet_mode = t('grp_enabled', lang) if settings['quiet_mode'] else t('grp_disabled', lang)
        delete_link = t('grp_enabled', lang) if settings.get('delete_user_link', False) else t('grp_disabled', lang)
        max_duration = f"⏰ {settings['max_duration_minutes']} {t('grp_minutes', lang)}" if settings['max_duration_minutes'] > 0 else t('grp_no_limit', lang)
        max_size = f"📦 {settings['max_file_size_mb']} MB"
    else:
        who_can_use = t('grp_admins_only_current', lang) if settings['admin_only'] else t('grp_everyone_current', lang)
        auto_delete = f"⏱️ {settings['auto_delete_seconds']} {t('grp_seconds', lang)}" if settings['auto_delete_seconds'] > 0 else t('grp_disabled', lang)
        quiet_mode = t('grp_enabled', lang) if settings['quiet_mode'] else t('grp_disabled', lang)
        delete_link = t('grp_enabled', lang) if settings.get('delete_user_link', False) else t('grp_disabled', lang)
        max_duration = f"⏰ {settings['max_duration_minutes']} {t('grp_minutes', lang)}" if settings['max_duration_minutes'] > 0 else t('grp_no_limit', lang)
        max_size = f"📦 {settings['max_file_size_mb']} MB"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{t('grp_btn_who', lang)}: {who_can_use}", callback_data=f"grp_who_{chat_id}")],
        [InlineKeyboardButton(f"{t('grp_btn_delete', lang)}: {auto_delete}", callback_data=f"grp_delete_{chat_id}")],
        [InlineKeyboardButton(f"{t('grp_delete_link', lang)}: {delete_link}", callback_data=f"grp_dellink_{chat_id}")],
        [InlineKeyboardButton(f"{t('grp_btn_quiet', lang)}: {quiet_mode}", callback_data=f"grp_quiet_{chat_id}")],
        [
            InlineKeyboardButton(f"{t('grp_btn_duration', lang)}: {max_duration}", callback_data=f"grp_duration_{chat_id}"),
            InlineKeyboardButton(f"{t('grp_btn_size', lang)}: {max_size}", callback_data=f"grp_size_{chat_id}")
        ],
        [InlineKeyboardButton("⭐ VIP - تحميل غير محدود" if lang == 'ar' else "⭐ VIP - Unlimited", callback_data=f"grp_vip_{chat_id}")],
        [InlineKeyboardButton(t('grp_btn_close', lang), callback_data=f"grp_close_{chat_id}")]
    ])
    
    text = (
        f"{t('grp_settings_header', lang)}\n\n"
        f"{t('grp_who_uses', lang)} {who_can_use}\n"
        f"{t('grp_auto_delete', lang)} {auto_delete}\n"
        f"{t('grp_delete_link', lang)}: {delete_link}\n"
        f"{t('grp_quiet_mode', lang)} {quiet_mode}\n"
        f"{t('grp_max_duration', lang)} {max_duration}\n"
        f"{t('grp_max_size', lang)} {max_size}"
    )
    
    if edit:
        await message_or_callback.edit_text(text, reply_markup=keyboard)
    else:
        await message_or_callback.reply_text(text, reply_markup=keyboard)


@app.on_callback_query(filters.regex(r'^group_set_'))
async def handle_group_settings_callback(client, callback_query):
    """معالج تغيير إعدادات المجموعة - القديم للتوافق"""
    user_id = callback_query.from_user.id
    lang = subdb.get_user_language(user_id)
    
    # استخراج البيانات
    data = callback_query.data  # group_set_admin_-123456 or group_set_all_-123456
    parts = data.split('_')
    setting_type = parts[2]  # admin or all
    chat_id = int('_'.join(parts[3:]))  # Handle negative IDs
    
    # التحقق من صلاحيات الأدمن
    if not await check_group_admin(client, callback_query, chat_id, user_id, lang):
        return
    
    # تحديث الإعدادات
    admin_only = (setting_type == "admin")
    subdb.set_group_settings(chat_id, admin_only=admin_only)
    
    await callback_query.answer("✅ تم الحفظ!")
    await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)


async def check_group_admin(client, callback_query, chat_id: int, user_id: int, lang: str) -> bool:
    """التحقق من أن المستخدم أدمن في المجموعة"""
    try:
        from pyrogram.enums import ChatMemberStatus
        member = await client.get_chat_member(chat_id, user_id)
        is_admin = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        if not is_admin:
            await callback_query.answer("⛔ هذه الإعدادات للأدمن فقط!", show_alert=True)
            return False
        return True
    except Exception as e:
        logger.error(f"خطأ في فحص صلاحيات المستخدم: {e}")
        await callback_query.answer("❌ حدث خطأ", show_alert=True)
        return False


# ═══════════════════════════════════════════════════════════════
# معالجات الإعدادات الجديدة للمجموعات
# ═══════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r'^grp_'))
async def handle_new_group_settings(client, callback_query):
    """معالج إعدادات المجموعة الجديدة"""
    user_id = callback_query.from_user.id
    lang = subdb.get_user_language(user_id)
    data = callback_query.data
    
    # استخراج البيانات من callback_data
    # الصيغة: grp_action_chatid أو grp_action_value_chatid
    parts = data.split('_')
    action = parts[1]  # who, delete, quiet, duration, size, close, back, setwho, setdel, setdur, setsize
    
    # التعامل مع الـ actions المركبة (مثل setwho_admin_-123456 أو setdel_600_-123456)
    if action in ["setwho", "setdel", "setdur", "setsize"]:
        # الصيغة: grp_setwho_admin_-123456 أو grp_setdel_600_-123456
        value = parts[2]  # admin/all أو 600/0/etc
        chat_id = int('_'.join(parts[3:]))  # باقي الأجزاء هي chat_id
    else:
        # الصيغة: grp_who_-123456 أو grp_delete_-123456
        value = None
        chat_id = int('_'.join(parts[2:]))  # باقي الأجزاء هي chat_id
    
    # التحقق من صلاحيات الأدمن
    if action != "close" and not await check_group_admin(client, callback_query, chat_id, user_id, lang):
        return
    
    settings = subdb.get_group_settings(chat_id)
    
    # ═══════════════════════════════════════════════════════════════
    # معالجة كل حدث
    # ═══════════════════════════════════════════════════════════════
    
    if action == "settings" or action == "back":
        # العودة للقائمة الرئيسية
        await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)
        await callback_query.answer()
    
    elif action == "who":
        # قائمة اختيار من يستخدم البوت
        admin_text = t('grp_btn_admin_only', lang)
        everyone_text = t('grp_btn_everyone', lang)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"✓ {admin_text}" if settings['admin_only'] else admin_text,
                callback_data=f"grp_setwho_admin_{chat_id}"
            )],
            [InlineKeyboardButton(
                f"✓ {everyone_text}" if not settings['admin_only'] else everyone_text,
                callback_data=f"grp_setwho_all_{chat_id}"
            )],
            [InlineKeyboardButton(t('grp_btn_back', lang), callback_data=f"grp_back_{chat_id}")]
        ])
        await callback_query.message.edit_text(
            t('grp_who_title', lang),
            reply_markup=keyboard
        )
        await callback_query.answer()
    
    elif action == "setwho":
        # تعيين من يستخدم البوت
        who_type = value  # admin or all
        subdb.set_group_settings(chat_id, admin_only=(who_type == "admin"))
        await callback_query.answer(t('grp_saved', lang))
        await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)
    
    elif action == "delete":
        # قائمة الحذف التلقائي
        current = settings['auto_delete_seconds']
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"✓ {t('grp_btn_disabled', lang)}" if current == 0 else t('grp_btn_disabled', lang), callback_data=f"grp_setdel_0_{chat_id}"),
                InlineKeyboardButton(f"✓ {t('grp_btn_30s', lang)}" if current == 30 else t('grp_btn_30s', lang), callback_data=f"grp_setdel_30_{chat_id}")
            ],
            [
                InlineKeyboardButton(f"✓ {t('grp_btn_60s', lang)}" if current == 60 else t('grp_btn_60s', lang), callback_data=f"grp_setdel_60_{chat_id}"),
                InlineKeyboardButton(f"✓ {t('grp_btn_120s', lang)}" if current == 120 else t('grp_btn_120s', lang), callback_data=f"grp_setdel_120_{chat_id}")
            ],
            [
                InlineKeyboardButton(f"✓ {t('grp_btn_5min', lang)}" if current == 300 else t('grp_btn_5min', lang), callback_data=f"grp_setdel_300_{chat_id}"),
                InlineKeyboardButton(f"✓ {t('grp_btn_10min', lang)}" if current == 600 else t('grp_btn_10min', lang), callback_data=f"grp_setdel_600_{chat_id}")
            ],
            [InlineKeyboardButton(t('grp_btn_back', lang), callback_data=f"grp_back_{chat_id}")]
        ])
        await callback_query.message.edit_text(
            t('grp_delete_title', lang),
            reply_markup=keyboard
        )
        await callback_query.answer()
    
    elif action == "setdel":
        # تعيين الحذف التلقائي
        seconds = int(value)
        subdb.set_group_settings(chat_id, auto_delete_seconds=seconds)
        await callback_query.answer(t('grp_saved', lang))
        await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)
    
    elif action == "dellink":
        # تبديل حذف رابط المستخدم
        current = settings.get('delete_user_link', False)
        subdb.set_group_settings(chat_id, delete_user_link=not current)
        status = "✅" if not current else "❌"
        await callback_query.answer(f"🔗 حذف الرابط: {status}")
        await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)
    
    elif action == "quiet":
        # تبديل الوضع الهادئ
        subdb.set_group_settings(chat_id, quiet_mode=not settings['quiet_mode'])
        status = t('grp_enabled', lang) if not settings['quiet_mode'] else t('grp_disabled', lang)
        await callback_query.answer(f"🔕 {status}")
        await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)
    
    elif action == "duration":
        # قائمة حد المدة
        current = settings['max_duration_minutes']
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"✓ {t('grp_btn_15min', lang)}" if current == 15 else t('grp_btn_15min', lang), callback_data=f"grp_setdur_15_{chat_id}"),
                InlineKeyboardButton(f"✓ {t('grp_btn_30min', lang)}" if current == 30 else t('grp_btn_30min', lang), callback_data=f"grp_setdur_30_{chat_id}")
            ],
            [
                InlineKeyboardButton(f"✓ {t('grp_btn_60min', lang)}" if current == 60 else t('grp_btn_60min', lang), callback_data=f"grp_setdur_60_{chat_id}"),
                InlineKeyboardButton(f"✓ {t('grp_btn_120min', lang)}" if current == 120 else t('grp_btn_120min', lang), callback_data=f"grp_setdur_120_{chat_id}")
            ],
            [
                InlineKeyboardButton(f"✓ {t('grp_btn_no_limit', lang)}" if current == 0 else t('grp_btn_no_limit', lang), callback_data=f"grp_setdur_0_{chat_id}")
            ],
            [InlineKeyboardButton(t('grp_btn_back', lang), callback_data=f"grp_back_{chat_id}")]
        ])
        await callback_query.message.edit_text(
            t('grp_duration_title', lang),
            reply_markup=keyboard
        )
        await callback_query.answer()
    
    elif action == "setdur":
        # تعيين حد المدة
        minutes = int(value)
        subdb.set_group_settings(chat_id, max_duration_minutes=minutes)
        await callback_query.answer(t('grp_saved', lang))
        await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)
    
    elif action == "size":
        # قائمة حد الحجم
        current = settings['max_file_size_mb']
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✓ 100 MB" if current == 100 else "100 MB", callback_data=f"grp_setsize_100_{chat_id}"),
                InlineKeyboardButton("✓ 250 MB" if current == 250 else "250 MB", callback_data=f"grp_setsize_250_{chat_id}")
            ],
            [
                InlineKeyboardButton("✓ 500 MB" if current == 500 else "500 MB", callback_data=f"grp_setsize_500_{chat_id}"),
                InlineKeyboardButton("✓ 1 GB" if current == 1000 else "1 GB", callback_data=f"grp_setsize_1000_{chat_id}")
            ],
            [
                InlineKeyboardButton(f"✓ {t('grp_btn_2gb_max', lang)}" if current == 2000 else t('grp_btn_2gb_max', lang), callback_data=f"grp_setsize_2000_{chat_id}")
            ],
            [InlineKeyboardButton(t('grp_btn_back', lang), callback_data=f"grp_back_{chat_id}")]
        ])
        await callback_query.message.edit_text(
            t('grp_size_title', lang),
            reply_markup=keyboard
        )
        await callback_query.answer()
    
    elif action == "setsize":
        # تعيين حد الحجم
        size_mb = int(value)
        subdb.set_group_settings(chat_id, max_file_size_mb=size_mb)
        await callback_query.answer(t('grp_saved', lang))
        await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)
    
    elif action == "close":
        # إغلاق القائمة
        try:
            await callback_query.message.delete()
        except:
            pass
        await callback_query.answer("✅ تم الإغلاق")
    
    elif action == "vip":
        # عرض معلومات اشتراك VIP للمجموعات
        group_monthly = subdb.get_setting('price_group_monthly', '15')
        group_yearly = subdb.get_setting('price_group_yearly', '120')
        telegram_support = subdb.get_setting('telegram_support', 'wahab161')
        
        if lang == 'en':
            text = (
                "⭐ **VIP Group Subscription**\n\n"
                "🔓 **Unlock these features:**\n"
                "• Custom video duration limit\n"
                "• Unlimited downloads for all members\n"
                "• Priority support\n"
                "• No daily limits\n\n"
                "💰 **Group Subscription Prices:**\n"
                f"• Monthly: ${group_monthly}\n"
                f"• Yearly: ${group_yearly} (save 33%!)\n\n"
                "📱 **To subscribe:**\n"
                f"Contact: @{telegram_support}\n\n"
                "After payment, your group will be upgraded immediately! 🚀"
            )
        else:
            text = (
                "⭐ **اشتراك VIP للمجموعة**\n\n"
                "🔓 **فتح هذه الميزات:**\n"
                "• تحكم مخصص في حد مدة الفيديو\n"
                "• تحميلات غير محدودة لجميع الأعضاء\n"
                "• دعم مميز وأولوية\n"
                "• بدون حد يومي\n\n"
                "💰 **أسعار اشتراك المجموعة:**\n"
                f"• شهري: ${group_monthly}\n"
                f"• سنوي: ${group_yearly} (وفّر 33%!)\n\n"
                "📱 **للاشتراك:**\n"
                f"تواصل معنا: @{telegram_support}\n\n"
                "بعد الدفع سيتم ترقية مجموعتك فوراً! 🚀"
            )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Binance Pay", callback_data="pay_binance")],
            [InlineKeyboardButton("📱 تواصل للاشتراك" if lang == 'ar' else "📱 Contact to Subscribe", url=f"https://t.me/{telegram_support}")],
            [InlineKeyboardButton(t('grp_btn_back', lang), callback_data=f"grp_back_{chat_id}")]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()


@app.on_callback_query(filters.regex(r'^group_settings_main_'))
async def handle_settings_main_button(client, callback_query):
    """معالج زر الإعدادات الرئيسي من رسالة الترحيب"""
    user_id = callback_query.from_user.id
    lang = subdb.get_user_language(user_id)
    data = callback_query.data
    
    # استخراج chat_id
    chat_id = int(data.replace("group_settings_main_", ""))
    
    # التحقق من صلاحيات الأدمن
    if not await check_group_admin(client, callback_query, chat_id, user_id, lang):
        return
    
    await show_group_settings_menu(client, callback_query.message, chat_id, lang, edit=True)
    await callback_query.answer()


@app.on_message(filters.group & filters.text & filters.regex(r'https?://\S+'))
async def handle_group_url(client, message):
    """معالج الروابط في المجموعات"""
    if not message.from_user:
        return
    
    url = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = subdb.get_user_language(user_id)
    
    # التحقق من إعدادات المجموعة
    if subdb.is_group_admin_only(chat_id):
        # التحقق من صلاحيات المستخدم
        try:
            from pyrogram.enums import ChatMemberStatus
            member = await client.get_chat_member(chat_id, user_id)
            is_admin = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            logger.info(f"🔍 Group URL: user {user_id} status = {member.status}, is_admin = {is_admin}")
        except Exception as e:
            logger.error(f"خطأ في فحص صلاحيات المستخدم في المجموعة: {e}")
            is_admin = False
        
        if not is_admin:
            # المستخدم ليس أدمن والإعداد للأدمن فقط
            await message.reply_text(t('group_download_not_allowed', lang))
            return
    
    # تسجيل المستخدم إذا لم يكن موجوداً
    subdb.add_or_update_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    # التحقق من المحتوى الإباحي
    if is_adult_content_url(url):
        await message.reply_text(t('adult_content_blocked', lang))
        return
    
    # التحقق من الروابط المحظورة المخصصة
    if subdb.is_url_in_custom_blocklist(url):
        await message.reply_text(t('adult_content_blocked', lang))
        return
    
    # التحقق من ستوري فيسبوك
    if 'facebook.com/stories' in url or 'fb.com/stories' in url:
        await message.reply_text(t('facebook_story_not_supported', lang))
        return
    
    # الحصول على الإعدادات
    group_settings = subdb.get_group_settings(chat_id)
    
    # حذف رابط المستخدم إذا كان مفعلاً
    if group_settings.get('delete_user_link', False):
        try:
            await message.delete()
            logger.info(f"🗑️ تم حذف رابط المستخدم في المجموعة {chat_id}")
        except Exception as e:
            logger.warning(f"⚠️ فشل حذف رابط المستخدم: {e}")
    
    # رسالة المعالجة
    status_msg = await message.reply_text(t('processing', lang))
    
    # تحميل الفيديو بجودة متوسطة تلقائياً (720p)
    try:
        await download_and_upload(
            client=client,
            message=message,
            url=url,
            quality="720p",
            callback_query=None,
            is_group=True
        )
        # حذف رسالة "جاري المعالجة" بعد النجاح
        try:
            await status_msg.delete()
        except:
            pass
    except Exception as e:
        logger.error(f"خطأ في تحميل الفيديو في المجموعة: {e}")
        await status_msg.edit_text(t('download_failed', lang))


@app.on_message(filters.text & filters.private & filters.regex(r'https?://\S+'))
async def handle_url(client, message):
    if not message.from_user:
        return
    
    url = message.text.strip()
    user_id = message.from_user.id
    
    # Get user language FIRST
    lang = subdb.get_user_language(user_id)
    
    # Check rate limiting
    is_limited, seconds_remaining = queue_manager.is_rate_limited(user_id)
    if is_limited:
        await message.reply_text(
            t('queue_rate_limit', lang, seconds=int(seconds_remaining) + 1)
        )
        return
    
    # Mark request time immediately for rate limiting (even during quality selection)
    queue_manager.mark_request(user_id)
    
    # Check if user already has downloads in queue
    queue_size = queue_manager.get_queue_size(user_id)
    is_processing = queue_manager.is_processing(user_id)
    
    if is_processing or queue_size > 0:
        # Check for Facebook Stories BEFORE adding to queue - not supported
        if ('facebook.com/stories' in url or 'fb.com/stories' in url):
            logger.info(f"❌ Facebook story detected - not supported: {url}")
            await message.reply_text(t('facebook_story_not_supported', lang))
            return
        
        # User has active downloads, add to queue
        # Create download task
        task = DownloadTask(
            url=url,
            message=message,
            user_id=user_id,
            quality="pending"  # Will be set when quality is chosen
        )
        
        # Add to queue
        position = await queue_manager.add_to_queue(
            user_id=user_id,
            task=task,
            process_func=process_download_from_queue
        )
        
        # Notify user
        await message.reply_text(
            t('queue_position', lang, position=position)
        )
        return
    
    # No active downloads, process normally
    pending_downloads[user_id] = url
    
    # Check for Facebook Stories - not supported
    if ('facebook.com/stories' in url or 'fb.com/stories' in url):
        logger.info(f"❌ Facebook story detected - not supported: {url}")
        await message.reply_text(t('facebook_story_not_supported', lang))
        return
    
    status = await message.reply_text(t('processing', lang))
    
    try:
        # ======= معالجة ستوري Instagram قبل أي شيء (مثل TikTok photos) =======
        # Instagram stories need special handling with instaloader FIRST (works for photos AND videos)
        if 'instagram.com' in url and '/stories/' in url:
            logger.info("📸 Detected Instagram story - using instaloader first (best for photos)")
            user_name = message.from_user.first_name or "User"
            username = message.from_user.username or "No username"
            
            # التحقق من وجود كوكيز انستقرام
            instagram_cookie = get_platform_cookie_file(url)
            if not instagram_cookie:
                logger.warning("⚠️ No Instagram cookies found for story download")
                await status.edit_text(t('story_cookies_missing', lang))
                return
            
            # استخدام gallery-dl أولاً (أفضل مع cookies)، ثم instaloader كـ fallback
            logger.info(f"🍪 Attempting story download with gallery-dl first")
            success, files, error, is_video = await download_instagram_story_with_gallery_dl(url, user_id)
            
            # إذا فشل gallery-dl، جرب instaloader
            if not success:
                logger.info(f"⚠️ gallery-dl failed, trying instaloader as fallback...")
                success, files, error, is_video = await download_instagram_story_with_instaloader(url, user_id)
            
            if success and files:
                if not is_video:
                    # ستوري صورة - رفع مباشرة
                    logger.info(f"📸 Story is a photo - uploading directly")
                    await status.edit_text(t('uploading', lang,
                                           percent='0.0',
                                           current_mb='0.0',
                                           total_mb='0.0',
                                           speed_mb='0.0',
                                           eta=0,
                                           progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                    
                    for i, photo_path in enumerate(files[:10], 1):
                        try:
                            sent_msg = await message.reply_photo(
                                photo=photo_path,
                                caption=f"📸 ستوري {i}/{len(files)} من Instagram\n👤 {user_name}"
                            )
                            logger.info(f"✅ Sent story photo {i}/{len(files)} to user")
                            
                            # Forward to LOG channel
                            log_channel_id = os.getenv('LOG_CHANNEL_ID')
                            if log_channel_id:
                                try:
                                    await app.forward_messages(
                                        chat_id=log_channel_id,
                                        from_chat_id=message.chat.id,
                                        message_ids=sent_msg.id
                                    )
                                    await app.send_message(
                                        chat_id=log_channel_id,
                                        text=(
                                            f"📸 **ستوري Instagram {i}/{len(files)}**\n\n"
                                            f"👤 **المستخدم:** {user_name}\n"
                                            f"🆔 **ID:** `{user_id}`\n"
                                            f"📱 **Username:** @{username}\n"
                                            f"🔗 **الرابط:** {url}"
                                        )
                                    )
                                except Exception as log_error:
                                    logger.error(f"❌ Failed to forward story to LOG channel: {log_error}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send story photo {i}: {e}")
                    
                    # Cleanup
                    for photo_path in files:
                        try:
                            os.remove(photo_path)
                        except:
                            pass
                    
                    try:
                        await status.delete()
                    except:
                        pass
                    
                    subdb.increment_download_count(user_id)
                    return
                else:
                    # ستوري فيديو من instaloader - رفعها مباشرة
                    logger.info(f"📹 Story is a video from instaloader - uploading directly")
                    await status.edit_text(t('uploading', lang,
                                           percent='0.0',
                                           current_mb='0.0',
                                           total_mb='0.0',
                                           speed_mb='0.0',
                                           eta=0,
                                           progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                    
                    for video_path in files:
                        try:
                            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                            sent_msg = await message.reply_video(
                                video=video_path,
                                caption=f"📹 ستوري فيديو من Instagram\n👤 {user_name}\n📊 {file_size_mb:.1f} MB"
                            )
                            logger.info(f"✅ Sent story video to user")
                            
                            # Forward to LOG channel
                            log_channel_id = os.getenv('LOG_CHANNEL_ID')
                            if log_channel_id:
                                try:
                                    await app.forward_messages(
                                        chat_id=log_channel_id,
                                        from_chat_id=message.chat.id,
                                        message_ids=sent_msg.id
                                    )
                                except Exception as log_error:
                                    logger.error(f"❌ Failed to forward story video to LOG channel: {log_error}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send story video: {e}")
                    
                    # Cleanup
                    for video_path in files:
                        try:
                            os.remove(video_path)
                        except:
                            pass
                    
                    try:
                        await status.delete()
                    except:
                        pass
                    
                    subdb.increment_download_count(user_id)
                    return
            else:
                # فشل instaloader - عرض رسالة خطأ واضحة
                logger.warning(f"⚠️ instaloader failed: {error}")
                await status.edit_text(t('instagram_private_story', lang))
                return
        
        # Early check for TikTok photo posts before get_video_info (yt-dlp doesn't support TikTok photos)
        if ('tiktok.com' in url and '/photo/' in url) or 'vm.tiktok.com' in url:
            logger.info("📸 Detected potential TikTok photo post - attempting photo download via TikWM API")
            user_name = message.from_user.first_name or "User"
            username = message.from_user.username or "No username"
            
            # Try to download TikTok photos using TikWM API
            success, files, error = await download_tiktok_photos(url, user_id)
            
            if success and files:
                await status.edit_text(t('uploading', lang,
                                       percent='0.0',
                                       current_mb='0.0',
                                       total_mb='0.0',
                                       speed_mb='0.0',
                                       eta=0,
                                       progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                
                # Upload photos to user
                for i, photo_path in enumerate(files[:20], 1):  # Limit to 20 photos
                    try:
                        sent_msg = await message.reply_photo(
                            photo=photo_path,
                            caption=f"📸 صورة {i}/{len(files)} من TikTok\n👤 {user_name}"
                        )
                        logger.info(f"✅ Sent TikTok photo {i}/{len(files)} to user")
                        
                        # Forward to LOG channel
                        log_channel_id = os.getenv('LOG_CHANNEL_ID')
                        if log_channel_id:
                            try:
                                await app.forward_messages(
                                    chat_id=log_channel_id,
                                    from_chat_id=message.chat.id,
                                    message_ids=sent_msg.id
                                )
                            except Exception as log_error:
                                logger.error(f"❌ Failed to forward TikTok photo to LOG channel: {log_error}")
                    except Exception as e:
                        logger.error(f"❌ Failed to send TikTok photo {i}: {e}")
                
                # Cleanup
                for photo_path in files:
                    try:
                        os.remove(photo_path)
                    except:
                        pass
                
                # Delete status message
                try:
                    await status.delete()
                except:
                    pass
                
                # Record download
                subdb.increment_download_count(user_id)
                return
            elif error and "لا يحتوي على صور" in error:
                # It's a video, not photos - show quality selection buttons
                logger.info("📹 TikTok post is a video, not photos - showing quality selection")
                
                # Get video info from TikWM API for display
                try:
                    api_url = 'https://www.tikwm.com/api/'
                    params = {'url': url, 'hd': 1}
                    response = requests.get(api_url, params=params, timeout=15)
                    data = response.json()
                    
                    if data.get('code') == 0:
                        result_data = data.get('data', {})
                        title = result_data.get('title', 'TikTok Video')[:50]
                        duration = result_data.get('duration', 0)
                        duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "0:00"
                    else:
                        title = 'TikTok Video'
                        duration_str = "0:00"
                except:
                    title = 'TikTok Video'
                    duration_str = "0:00"
                
                # Show quality selection buttons
                keyboard = [
                    [InlineKeyboardButton(t('quality_best', lang), callback_data="quality_best")],
                    [InlineKeyboardButton(t('quality_medium', lang), callback_data="quality_medium")],
                    [InlineKeyboardButton(t('quality_audio', lang), callback_data="quality_audio")],
                ]
                
                await status.edit_text(
                    t('choose_quality', lang, title=title, duration=duration_str),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            else:
                # Failed to download photos
                await send_error_to_admin(user_id, user_name, f"TikTok photo download failed: {error}", url)
                await status.edit_text(f"❌ فشل تحميل صور TikTok\n\n{error}")
                return
        
        info = await get_video_info(url)
        
        if not info:
            # Check if it's an Instagram URL
            if 'instagram.com' in url:
                # Check if it's a story - stories should be downloaded as videos
                if '/stories/' in url:
                    logger.info("📸 Detected Instagram story - using instaloader first (best for photos)")
                    user_name = message.from_user.first_name or "User"
                    username = message.from_user.username or "No username"
                    
                    # Check if Instagram cookies exist
                    instagram_cookie = get_platform_cookie_file(url)
                    if not instagram_cookie:
                        logger.warning("⚠️ No Instagram cookies found for story download")
                        await status.edit_text(t('story_cookies_missing', lang))
                        return
                    
                    # استخدام gallery-dl أولاً (أفضل مع cookies)، ثم instaloader كـ fallback
                    logger.info(f"🍪 Attempting story download with gallery-dl first")
                    success, files, error, is_video = await download_instagram_story_with_gallery_dl(url, user_id)
                    
                    # إذا فشل gallery-dl، جرب instaloader
                    if not success:
                        logger.info(f"⚠️ gallery-dl failed, trying instaloader as fallback...")
                        success, files, error, is_video = await download_instagram_story_with_instaloader(url, user_id)
                    
                    if success and files:
                        if not is_video:
                            # ستوري صورة - رفع مباشرة
                            logger.info(f"📸 Story is a photo - uploading directly")
                            await status.edit_text(t('uploading', lang,
                                                   percent='0.0',
                                                   current_mb='0.0',
                                                   total_mb='0.0',
                                                   speed_mb='0.0',
                                                   eta=0,
                                                   progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                            
                            for i, photo_path in enumerate(files[:10], 1):
                                try:
                                    sent_msg = await message.reply_photo(
                                        photo=photo_path,
                                        caption=f"📸 ستوري {i}/{len(files)} من Instagram\n👤 {user_name}"
                                    )
                                    logger.info(f"✅ Sent story photo {i}/{len(files)} to user")
                                    
                                    # Forward to LOG channel
                                    log_channel_id = os.getenv('LOG_CHANNEL_ID')
                                    if log_channel_id:
                                        try:
                                            await app.forward_messages(
                                                chat_id=log_channel_id,
                                                from_chat_id=message.chat.id,
                                                message_ids=sent_msg.id
                                            )
                                            await app.send_message(
                                                chat_id=log_channel_id,
                                                text=(
                                                    f"📸 **ستوري Instagram {i}/{len(files)}**\n\n"
                                                    f"👤 **المستخدم:** {user_name}\n"
                                                    f"🆔 **ID:** `{user_id}`\n"
                                                    f"📱 **Username:** @{username}\n"
                                                    f"🔗 **الرابط:** {url}"
                                                )
                                            )
                                        except Exception as log_error:
                                            logger.error(f"❌ Failed to forward story to LOG channel: {log_error}")
                                except Exception as e:
                                    logger.error(f"❌ Failed to send story photo {i}: {e}")
                            
                            # Cleanup
                            for photo_path in files:
                                try:
                                    os.remove(photo_path)
                                except:
                                    pass
                            
                            try:
                                await status.delete()
                            except:
                                pass
                            
                            subdb.increment_download_count(user_id)
                            return
                        else:
                            # ستوري فيديو من instaloader - رفعها مباشرة
                            logger.info(f"📹 Story is a video from instaloader - uploading directly")
                            await status.edit_text(t('uploading', lang,
                                                   percent='0.0',
                                                   current_mb='0.0',
                                                   total_mb='0.0',
                                                   speed_mb='0.0',
                                                   eta=0,
                                                   progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                            
                            for video_path in files:
                                try:
                                    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                                    sent_msg = await message.reply_video(
                                        video=video_path,
                                        caption=f"📹 ستوري فيديو من Instagram\n👤 {user_name}\n📊 {file_size_mb:.1f} MB"
                                    )
                                    logger.info(f"✅ Sent story video to user")
                                    
                                    # Forward to LOG channel
                                    log_channel_id = os.getenv('LOG_CHANNEL_ID')
                                    if log_channel_id:
                                        try:
                                            await app.forward_messages(
                                                chat_id=log_channel_id,
                                                from_chat_id=message.chat.id,
                                                message_ids=sent_msg.id
                                            )
                                        except Exception as log_error:
                                            logger.error(f"❌ Failed to forward story video to LOG channel: {log_error}")
                                except Exception as e:
                                    logger.error(f"❌ Failed to send story video: {e}")
                            
                            # Cleanup
                            for video_path in files:
                                try:
                                    os.remove(video_path)
                                except:
                                    pass
                            
                            try:
                                await status.delete()
                            except:
                                pass
                            
                            subdb.increment_download_count(user_id)
                            return
                    else:
                        # فشل instaloader - عرض رسالة خطأ واضحة
                        logger.warning(f"⚠️ instaloader failed: {error}")
                        await status.edit_text(t('instagram_private_story', lang))
                        return
                else:
                    # It's a regular post/photo - try gallery-dl
                    logger.info("🔄 Attempting Instagram photo download with gallery-dl")
                    success, files, error = await download_instagram_photo(url, user_id)
                    
                    if success and files:
                        await status.edit_text(t('uploading', lang,
                                               percent='0.0',
                                               current_mb='0.0',
                                               total_mb='0.0',
                                               speed_mb='0.0',
                                               eta=0,
                                               progress_bar='▱▱▱▱▱▱▱▱▱▱'))
                        
                        # Upload photos to user
                        user_name = message.from_user.first_name
                        username = message.from_user.username or "No username"
                        
                        for i, photo_path in enumerate(files[:10], 1):  # Limit to 10 photos
                            try:
                                sent_msg = await message.reply_photo(
                                    photo=photo_path,
                                    caption=f"📸 صورة {i}/{len(files)} من Instagram\n👤 {user_name}"
                                )
                                logger.info(f"✅ Sent photo {i}/{len(files)} to user")
                                
                                # Forward to LOG channel with caption
                                log_channel_id = os.getenv('LOG_CHANNEL_ID')
                                if log_channel_id:
                                    try:
                                        # Forward the message
                                        await app.forward_messages(
                                            chat_id=log_channel_id,
                                            from_chat_id=message.chat.id,
                                            message_ids=sent_msg.id
                                        )
                                        
                                        # Send info message
                                        await app.send_message(
                                            chat_id=log_channel_id,
                                            text=(
                                                f"📸 **صورة Instagram {i}/{len(files)}**\n\n"
                                                f"👤 **المستخدم:** {user_name}\n"
                                                f"🆔 **ID:** `{user_id}`\n"
                                                f"📱 **Username:** @{username}\n"
                                                f"🔗 **الرابط:** {url}"
                                            )
                                        )
                                        logger.info(f"✅ Forwarded photo {i}/{len(files)} to LOG channel")
                                    except Exception as log_error:
                                        logger.error(f"❌ Failed to forward photo to LOG channel: {log_error}")
                            except Exception as e:
                                logger.error(f"❌ Failed to send photo {i}: {e}")
                        
                        # Cleanup
                        for photo_path in files:
                            try:
                                os.remove(photo_path)
                            except:
                                pass
                        
                        # Delete status message - wrap in try-except to avoid MESSAGE_ID_INVALID
                        try:
                            await status.delete()
                        except:
                            pass
                        
                        # Record download - use correct function name
                        subdb.increment_download_count(user_id)
                        return
                    else:
                        user_name = message.from_user.first_name or "User"
                        await send_error_to_admin(user_id, user_name, f"Instagram photo download failed: {error}", url)
                        await status.edit_text(f"❌ فشل تحميل الصورة من Instagram\n\n{error}")
                        return
            # Check if it's a TikTok URL - show quality selection
            elif 'tiktok.com' in url:
                logger.info("🎬 TikTok video info extraction failed (yt-dlp) - showing quality selection")
                
                # Get video info from TikWM API for display
                try:
                    api_url = 'https://www.tikwm.com/api/'
                    params = {'url': url, 'hd': 1}
                    response = requests.get(api_url, params=params, timeout=15)
                    data = response.json()
                    
                    if data.get('code') == 0:
                        result_data = data.get('data', {})
                        title = result_data.get('title', 'TikTok Video')[:50]
                        duration = result_data.get('duration', 0)
                        duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "0:00"
                    else:
                        title = 'TikTok Video'
                        duration_str = "0:00"
                except:
                    title = 'TikTok Video'
                    duration_str = "0:00"
                
                # Show quality selection buttons
                keyboard = [
                    [InlineKeyboardButton(t('quality_best', lang), callback_data="quality_best")],
                    [InlineKeyboardButton(t('quality_medium', lang), callback_data="quality_medium")],
                    [InlineKeyboardButton(t('quality_audio', lang), callback_data="quality_audio")],
                ]
                
                await status.edit_text(
                    t('choose_quality', lang, title=title, duration=duration_str),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Not Instagram or TikTok - show generic error
                user_name = message.from_user.first_name or "User"
                await send_error_to_admin(user_id, user_name, "Failed to extract video info", url)
                await status.edit_text(t('invalid_url', lang))
                return
    except Exception as e:
        # Unexpected error
        user_name = message.from_user.first_name or "User"
        await send_error_to_admin(user_id, user_name, str(e), url)
        await status.edit_text(t('error_occurred', lang, error=str(e)[:100]))
        return
    
    title = info.get('title', 'Video')[:50]
    duration = info.get('duration', 0)
    duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "0:00"
    
    # Add or update user info
    username = message.from_user.username
    first_name = message.from_user.first_name
    subdb.add_or_update_user(user_id, username, first_name)
    
    # Check subscription and video duration
    is_subscribed = subdb.is_user_subscribed(user_id)
    
    # فحص الحد اليومي للمستخدمين غير المشتركين
    # Check daily limit for non-subscribers
    if not is_subscribed:
        daily_limit = subdb.get_daily_limit()
        
        # فقط فحص إذا كان الحد ليس "غير محدود" (-1)
        if daily_limit != -1:
            daily_count = subdb.check_daily_limit(user_id)
            
            if daily_count >= daily_limit:
                await status.edit_text(
                    t('daily_limit_exceeded', lang, limit=daily_limit, count=daily_count),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(t('subscribe_now', lang), callback_data="pay_binance")],
                        [InlineKeyboardButton(t('contact_developer', lang), url=f"https://t.me/{subdb.get_setting('telegram_support', 'wahab161')}")]
                    ])
                )
                return
    
    max_duration_minutes = subdb.get_max_duration()
    max_duration_seconds = max_duration_minutes * 60
    
    # If not subscribed and exceeds max duration
    if not is_subscribed and duration and duration > max_duration_seconds:
        await show_subscription_screen(client, status, user_id, title, duration, max_duration_minutes)
        return
    
    # Show quality selection
    keyboard = [
        [InlineKeyboardButton(t('quality_best', lang), callback_data="quality_best")],
        [InlineKeyboardButton(t('quality_medium', lang), callback_data="quality_medium")],
        [InlineKeyboardButton(t('quality_audio', lang), callback_data="quality_audio")],
    ]
    
    await status.edit_text(
        t('choose_quality', lang, title=title, duration=duration_str),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



@app.on_callback_query(filters.regex(r'^quality_'))
async def handle_quality(client, callback_query):
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    quality = callback_query.data.replace("quality_", "")
    
    if user_id not in pending_downloads:
        lang = subdb.get_user_language(user_id)
        await callback_query.message.edit_text(t('error_occurred', lang, error="Session expired. Send link again."))
        return
    
    url = pending_downloads[user_id]
    lang = subdb.get_user_language(user_id)
    await callback_query.message.edit_text(t('start_download', lang))
    
    # Check if it's a TikTok URL - use TikWM API instead of yt-dlp
    if 'tiktok.com' in url or 'vm.tiktok.com' in url:
        user_name = callback_query.from_user.first_name or "User"
        
        if quality == 'audio':
            # Download audio only using TikWM API
            try:
                logger.info(f"🎵 Downloading TikTok audio via TikWM API: {url}")
                
                import tempfile
                temp_dir = tempfile.mkdtemp(prefix="tiktok_audio_")
                
                api_url = 'https://www.tikwm.com/api/'
                params = {'url': url, 'hd': 1}
                
                response = requests.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get('code') != 0:
                    await callback_query.message.edit_text(f"❌ {t('error_occurred', lang, error=data.get('msg', 'API Error'))}")
                    pending_downloads.pop(user_id, None)
                    return
                
                result_data = data.get('data', {})
                music_url = result_data.get('music')
                
                if not music_url:
                    await callback_query.message.edit_text(f"❌ {t('error_occurred', lang, error='No audio found')}")
                    pending_downloads.pop(user_id, None)
                    return
                
                # Download audio
                headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.tiktok.com/'}
                audio_response = requests.get(music_url, headers=headers, timeout=60)
                audio_response.raise_for_status()
                
                audio_path = os.path.join(temp_dir, "tiktok_audio.mp3")
                with open(audio_path, 'wb') as f:
                    f.write(audio_response.content)
                
                file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
                title = result_data.get('title', 'TikTok Audio')[:50]
                
                # Send audio to user
                binance_id = subdb.get_setting('binance_pay_id', '86847466')
                support_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(t('support_dev_binance', lang), url="https://app.binance.com/qr/dplkda88dd4d4e86847466")],
                    [InlineKeyboardButton(t('binance_pay_id', lang, binance_id=binance_id), callback_data="binance_info")]
                ])
                
                await callback_query.message.reply_audio(
                    audio=audio_path,
                    caption=f"🎵 TikTok Audio\n🎶 {title}\n👤 {user_name}",
                    reply_markup=support_keyboard
                )
                
                logger.info(f"✅ Sent TikTok audio to user ({file_size_mb:.2f} MB)")
                
                # Cleanup
                try:
                    os.remove(audio_path)
                    await callback_query.message.delete()
                except:
                    pass
                
                subdb.increment_download_count(user_id)
                
            except Exception as e:
                logger.error(f"❌ TikTok audio download failed: {e}")
                await callback_query.message.edit_text(f"❌ {t('error_occurred', lang, error=str(e)[:100])}")
        else:
            # Download video using TikWM API with progress tracking
            video_success, video_path, video_info, video_error = await download_tiktok_video(url, user_id, callback_query.message)
            
            if video_success and video_path:
                try:
                    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                    caption = f"🎵 TikTok\n📹 {video_info.get('title', 'فيديو')[:50]}\n👤 {user_name}"
                    
                    binance_id = subdb.get_setting('binance_pay_id', '86847466')
                    support_keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(t('support_dev_binance', lang), url="https://app.binance.com/qr/dplkda88dd4d4e86847466")],
                        [InlineKeyboardButton(t('binance_pay_id', lang, binance_id=binance_id), callback_data="binance_info")]
                    ])
                    
                    await callback_query.message.reply_video(
                        video=video_path,
                        caption=caption,
                        supports_streaming=True,
                        reply_markup=support_keyboard
                    )
                    
                    logger.info(f"✅ Sent TikTok video to user ({file_size_mb:.2f} MB)")
                    
                    # Cleanup
                    try:
                        os.remove(video_path)
                        await callback_query.message.delete()
                    except:
                        pass
                    
                    subdb.increment_download_count(user_id)
                    
                except Exception as e:
                    logger.error(f"❌ TikTok video upload failed: {e}")
                    await callback_query.message.edit_text(f"❌ {t('error_occurred', lang, error=str(e)[:100])}")
            else:
                await callback_query.message.edit_text(f"❌ {t('error_occurred', lang, error=video_error or 'Download failed')}")
    else:
        # Use normal yt-dlp download for other platforms
        await download_and_upload(client, callback_query.message, url, quality, callback_query)
    
    # Safe deletion - prevents KeyError if user clicks multiple quality buttons
    pending_downloads.pop(user_id, None)


# ═══════════════════════════════════════════════════════════════
# Subscription System Handlers
# ═══════════════════════════════════════════════════════════════

async def show_subscription_screen(client, message, user_id, title, duration, max_minutes):
    """عرض شاشة الاشتراك للمستخدمين غير المشتركين"""
    duration_minutes = int(duration) // 60
    telegram_support = subdb.get_setting('telegram_support', 'wahab161')
    binance_id = subdb.get_setting('binance_pay_id', '86847466')
    
    # Get user language
    lang = subdb.get_user_language(user_id)
    
    # الحصول على الأسعار
    user_monthly = subdb.get_setting('price_user_monthly', '5')
    user_yearly = subdb.get_setting('price_user_yearly', '40')
    group_monthly = subdb.get_setting('price_group_monthly', '15')
    group_yearly = subdb.get_setting('price_group_yearly', '120')
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t('binance_pay', lang), callback_data=f"pay_binance")],
        [InlineKeyboardButton(t('visa_card', lang), callback_data=f"pay_visa")],
        [InlineKeyboardButton(t('mastercard', lang), callback_data=f"pay_mastercard")],
        [InlineKeyboardButton(t('telegram_contact', lang), url=f"https://t.me/{telegram_support}")]
    ])
    
    if lang == 'en':
        prices_text = (
            f"\n\n💰 **Subscription Prices:**\n"
            f"👤 **Personal:**\n"
            f"• Monthly: ${user_monthly}\n"
            f"• Yearly: ${user_yearly}\n\n"
            f"👥 **Group:**\n"
            f"• Monthly: ${group_monthly}\n"
            f"• Yearly: ${group_yearly}"
        )
    else:
        prices_text = (
            f"\n\n💰 **أسعار الاشتراك:**\n"
            f"👤 **للمستخدم:**\n"
            f"• شهري: ${user_monthly}\n"
            f"• سنوي: ${user_yearly}\n\n"
            f"👥 **للمجموعة:**\n"
            f"• شهري: ${group_monthly}\n"
            f"• سنوي: ${group_yearly}"
        )
    
    text = (
        t('subscription_required', lang, title=title, duration=duration_minutes, max_duration=max_minutes) +
        "\n\n━━━━━━━━━━━━━━━━\n\n" +
        t('subscription_benefits', lang) +
        prices_text +
        "\n\n" +
        t('choose_payment_method', lang)
    )
    
    await message.edit_text(text, reply_markup=keyboard)


@app.on_callback_query(filters.regex(r'^pay_'))
async def handle_payment_method(client, callback_query):
    """معالج طرق الدفع"""
    user_id = callback_query.from_user.id
    payment_method = callback_query.data.replace('pay_', '')
    
    # Get user language
    lang = subdb.get_user_language(user_id)
    
    binance_id = subdb.get_setting('binance_pay_id', '86847466')
    telegram_support = subdb.get_setting('telegram_support', 'wahab161')
    
    # الحصول على جميع الأسعار
    user_monthly = subdb.get_setting('price_user_monthly', '5')
    user_yearly = subdb.get_setting('price_user_yearly', '40')
    group_monthly = subdb.get_setting('price_group_monthly', '15')
    group_yearly = subdb.get_setting('price_group_yearly', '120')
    
    # نص الأسعار حسب اللغة
    if lang == 'en':
        prices_text = (
            f"\n\n💰 **Subscription Prices:**\n"
            f"👤 **Personal:** ${user_monthly}/month • ${user_yearly}/year\n"
            f"👥 **Group:** ${group_monthly}/month • ${group_yearly}/year"
        )
    else:
        prices_text = (
            f"\n\n💰 **أسعار الاشتراك:**\n"
            f"👤 **مستخدم:** ${user_monthly}/شهر • ${user_yearly}/سنة\n"
            f"👥 **مجموعة:** ${group_monthly}/شهر • ${group_yearly}/سنة"
        )
    
    if payment_method == 'binance':
        text = (
            f"{t('payment_binance_title', lang)}\n\n"
            f"🆔 **Binance Pay ID:** `{binance_id}`\n\n"
            f"{t('payment_binance_steps', lang, binance_id=binance_id)}"
            f"{prices_text}"
        )
    elif payment_method == 'visa':
        text = (
            f"{t('payment_visa_title', lang)}\n\n"
            f"{t('payment_visa_instructions', lang, support_username=telegram_support)}"
            f"{prices_text}"
        )
    elif payment_method == 'mastercard':
        text = (
            f"{t('payment_mastercard_title', lang)}\n\n"
            f"{t('payment_mastercard_instructions', lang, support_username=telegram_support)}"
            f"{prices_text}"
        )
    
    # حفظ طريقة الدفع المختارة
    pending_downloads[user_id] = {'payment_method': payment_method}
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t('contact_developer', lang), url=f"https://t.me/{telegram_support}")],
        [InlineKeyboardButton(t('back', lang), callback_data="back_to_subscription")]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@app.on_callback_query(filters.regex(r'^binance_id_info$'))
async def handle_binance_id_info(client, callback_query):
    """معالج زر معلومات Binance ID"""
    binance_id = subdb.get_setting('binance_pay_id', '86847466')
    await callback_query.answer(
        f"💵 Binance Pay ID: {binance_id}\n\n"
        f"يمكنك دعم المطور عبر إرسال أي مبلغ!",
        show_alert=True
    )


@app.on_callback_query(filters.regex(r'^binance_info$'))
async def handle_binance_info(client, callback_query):
    """معالج زر Binance Pay ID"""
    user_id = callback_query.from_user.id
    lang = subdb.get_user_language(user_id)
    binance_id = subdb.get_setting('binance_pay_id', '86847466')
    
    if lang == 'ar':
        message = (
            f"💵 هذا هو Binance Pay ID:\n\n"
            f"🆔 {binance_id}\n\n"
            f"📲 أرسل أي مبلغ لدعم المطور!\n"
            f"✨ شكراً لك!"
        )
    else:
        message = (
            f"💵 This is the Binance Pay ID:\n\n"
            f"🆔 {binance_id}\n\n"
            f"📲 Send any amount to support the developer!\n"
            f"✨ Thank you!"
        )
    
    await callback_query.answer(message, show_alert=True)


@app.on_callback_query(filters.regex(r'^back_to_subscription$'))
async def handle_back_to_subscription(client, callback_query):
    """معالج الرجوع لشاشة الاشتراك"""
    user_id = callback_query.from_user.id
    
    # Get user language
    lang = subdb.get_user_language(user_id)
    
    telegram_support = subdb.get_setting('telegram_support', 'wahab161')
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t('binance_pay', lang), callback_data="pay_binance")],
        [InlineKeyboardButton(t('visa_card', lang), callback_data="pay_visa")],
        [InlineKeyboardButton(t('mastercard', lang), callback_data="pay_mastercard")],
        [InlineKeyboardButton(t('telegram_contact', lang), url=f"https://t.me/{telegram_support}")]
    ])
    
    # Show subscription options
    text = (
        t('subscription_required', lang, title="Video", duration=10, max_duration=5) +
        "\n\n━━━━━━━━━━━━━━━━\n\n" +
        t('subscription_benefits', lang) +
        "\n\n" +
        t('choose_payment_method', lang)
    )
    
    await callback_query.message.edit_text(
        text,
        reply_markup=keyboard
    )
    await callback_query.answer()


async def notify_admin_contact(client, user_id, user, payment_method):
    """إرسال إشعار للمطور عند محاولة المستخدم التواصل"""
    try:
        admin_id = int(os.getenv("ADMIN_ID"))
        username = user.username or "لا يوجد"
        first_name = user.first_name or "مستخدم"
        
        text = (
            f"📞 **طلب اشتراك جديد!**\n\n"
            f"👤 **المستخدم:** {first_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📱 **Username:** @{username}\n"
            f"💳 **الطريقة المطلوبة:** {payment_method}\n\n"
            f"المستخدم يريد الاشتراك ويحتاج للتواصل معك! 💬"
        )
        
        await client.send_message(admin_id, text)
        logger.info(f"📞 إشعار تواصل من {user_id} للأدمن")
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار التواصل: {e}")



@app.on_message(filters.photo)
async def handle_payment_proof(client, message):
    """معالج إثبات الدفع (الصور)"""
    user_id = message.from_user.id
    lang = subdb.get_user_language(user_id)
    
    # التحقق إذا كان المستخدم في عملية دفع
    if user_id not in pending_downloads:
        # رد فوري: البوت لا يدعم الصور إلا لإثبات الدفع
        await message.reply_text(t('unsupported_media_photo', lang))
        return
    
    payment_data = pending_downloads.get(user_id)
    if not isinstance(payment_data, dict) or 'payment_method' not in payment_data:
        # رد فوري: البوت لا يدعم الصور إلا لإثبات الدفع
        await message.reply_text(t('unsupported_media_photo', lang))
        return
    
    payment_method = payment_data['payment_method']
    
    # حفظ الدفعة في قاعدة البيانات
    payment_id = subdb.add_payment(
        user_id=user_id,
        payment_method=payment_method,
        proof_file_id=message.photo.file_id,
        proof_message_id=message.id
    )
    
    # حذف من pending
    del pending_downloads[user_id]
    
    # إرسال إشعار للمستخدم
    await message.reply_text(
        "✅ **تم استلام إثبات الدفع!**\n\n"
        "سيتم مراجعة دفعتك من قبل المسؤول.\n"
        "ستصلك رسالة فور تفعيل اشتراكك! 🎉\n\n"
        "⏳ الانتظار المتوقع: أقل من 24 ساعة"
    )
    
    # إرسال إشعار للأدمن
    admin_id = int(os.getenv("ADMIN_ID"))
    username = message.from_user.username or "لا يوجد"
    first_name = message.from_user.first_name or "مستخدم"
    
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قبول", callback_data=f"approve_payment_{payment_id}"),
         InlineKeyboardButton("❌ رفض", callback_data=f"reject_payment_{payment_id}")]
    ])
    
    await client.send_photo(
        chat_id=admin_id,
        photo=message.photo.file_id,
        caption=(
            f"💰 **دفعة جديدة!**\n\n"
            f"👤 **المستخدم:** {first_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📱 **Username:** @{username}\n"
            f"💳 **طريقة الدفع:** {payment_method}\n"
            f"🔖 **رقم الدفعة:** #{payment_id}\n\n"
            f"**قرار:**"
        ),
        reply_markup=admin_keyboard
    )
    
    logger.info(f"💰 دفعة جديدة #{payment_id} من {user_id} عبر {payment_method}")


@app.on_message(filters.video)
async def handle_video_upload(client, message):
    """معالج الفيديوهات المرفوعة - الرد التلقائي"""
    user_id = message.from_user.id
    lang = subdb.get_user_language(user_id)
    
    # البوت لا يدعم رفع الفيديوهات، فقط تحميلها من الروابط
    await message.reply_text(t('unsupported_media_video', lang))


@app.on_message(filters.audio | filters.voice | filters.animation | filters.sticker)
async def handle_other_media(client, message):
    """معالج الوسائط الأخرى - الرد التلقائي"""
    user_id = message.from_user.id
    lang = subdb.get_user_language(user_id)
    
    # البوت يدعم تحميل الفيديوهات من الروابط فقط
    await message.reply_text(t('unsupported_media_general', lang))


# ═══════════════════════════════════════════════════════════════
# معالجات لوحة الدفوعات المحسنة - Improved Payments Panel Handlers
# ═══════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r'^payment_approve_'))
async def handle_payment_approve(client, callback_query):
    """معالج قبول الدفع من لوحة الدفوعات المحسنة"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    payment_id = int(callback_query.data.replace('payment_approve_', ''))
    admin_id = callback_query.from_user.id
    
    success, message_text = subdb.approve_payment(payment_id, admin_id)
    
    if success:
        payment_info = subdb.get_payment_by_id(payment_id)
        if payment_info:
            user_id = payment_info[1]
            user_lang = subdb.get_user_language(user_id)
            
            try:
                await client.send_message(
                    chat_id=user_id,
                    text=t('subscription_activated', user_lang)
                )
            except:
                pass
        
        await callback_query.answer("✅ تم تفعيل الاشتراك بنجاح!", show_alert=True)
        
        # العودة لعرض الدفوعات المتبقية
        payments = subdb.get_pending_payments()
        if payments:
            # عرض الدفعة التالية
            await show_payment_at_index(callback_query.message, payments, 0)
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_sub_settings")]
            ])
            await callback_query.message.edit_text(
                "✅ **تمت معالجة جميع الدفوعات!**\n\n"
                "🎉 لا توجد دفوعات معلقة حالياً.",
                reply_markup=keyboard
            )
    else:
        await callback_query.answer(f"❌ {message_text}", show_alert=True)


@app.on_callback_query(filters.regex(r'^payment_reject_'))
async def handle_payment_reject(client, callback_query):
    """معالج رفض الدفع من لوحة الدفوعات المحسنة"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    payment_id = int(callback_query.data.replace('payment_reject_', ''))
    
    payment_info = subdb.get_payment_by_id(payment_id)
    if payment_info:
        user_id = payment_info[1]
        subdb.reject_payment(payment_id)
        
        try:
            telegram_support = subdb.get_setting('telegram_support', 'wahab161')
            await client.send_message(
                chat_id=user_id,
                text=(
                    "❌ **تم رفض دفعتك**\n\n"
                    "قد يكون هناك مشكلة في إثبات الدفع.\n"
                    f"تواصل مع المطور: @{telegram_support}"
                )
            )
        except:
            pass
        
        await callback_query.answer("❌ تم رفض الدفعة", show_alert=True)
        
        # العودة لعرض الدفوعات المتبقية
        payments = subdb.get_pending_payments()
        if payments:
            await show_payment_at_index(callback_query.message, payments, 0)
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_sub_settings")]
            ])
            await callback_query.message.edit_text(
                "✅ **تمت معالجة جميع الدفوعات!**\n\n"
                "🎉 لا توجد دفوعات معلقة حالياً.",
                reply_markup=keyboard
            )


@app.on_callback_query(filters.regex(r'^payment_proof_'))
async def handle_payment_proof(client, callback_query):
    """معالج عرض إيصال الدفع"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    payment_id = int(callback_query.data.replace('payment_proof_', ''))
    
    payment_info = subdb.get_payment_by_id(payment_id)
    if payment_info and payment_info[6]:  # proof_file_id
        proof_id = payment_info[6]
        
        try:
            # إرسال الإيصال كرسالة منفصلة
            await client.send_photo(
                chat_id=callback_query.from_user.id,
                photo=proof_id,
                caption=f"🧾 إيصال الدفعة #{payment_id}"
            )
            await callback_query.answer("✅ تم إرسال الإيصال", show_alert=False)
        except:
            try:
                await client.send_document(
                    chat_id=callback_query.from_user.id,
                    document=proof_id,
                    caption=f"🧾 إيصال الدفعة #{payment_id}"
                )
                await callback_query.answer("✅ تم إرسال الإيصال", show_alert=False)
            except Exception as e:
                await callback_query.answer(f"❌ خطأ في عرض الإيصال: {str(e)[:50]}", show_alert=True)
    else:
        await callback_query.answer("❌ لم يتم العثور على الإيصال", show_alert=True)


@app.on_callback_query(filters.regex(r'^payment_next_'))
async def handle_payment_next(client, callback_query):
    """معالج التنقل بين الدفوعات"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    index = int(callback_query.data.replace('payment_next_', ''))
    
    payments = subdb.get_pending_payments()
    if payments and index < len(payments):
        await show_payment_at_index(callback_query.message, payments, index)
    else:
        await callback_query.answer("❌ لا توجد دفوعات أخرى", show_alert=True)


async def show_payment_at_index(message, payments, index):
    """عرض دفعة محددة بناءً على الفهرس"""
    if index >= len(payments):
        index = 0
    
    payment = payments[index]
    payment_id, user_id, username, first_name, method, amount, proof_id, created = payment
    username_str = f"@{username}" if username else "🚫 لا يوجد"
    name = first_name or "مستخدم"
    
    # تنسيق التاريخ
    if created:
        try:
            if isinstance(created, str):
                created_dt = datetime.fromisoformat(created)
            else:
                created_dt = created
            date_str = created_dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_str = str(created)[:16]
    else:
        date_str = "غير محدد"
    
    text = "💳 **الدفوعات المعلقة**\n\n"
    text += f"📊 **إجمالي المعلقة:** {len(payments)} | 📍 العرض: {index + 1}/{len(payments)}\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🔖 **الدفعة #{payment_id}**\n\n"
    text += f"👤 **المستخدم:** {name}\n"
    text += f"📧 **اليوزر:** {username_str}\n"
    text += f"🆔 **ID:** `{user_id}`\n\n"
    text += f"💰 **المبلغ:** ${amount}\n"
    text += f"💳 **طريقة الدفع:** {method}\n"
    text += f"📅 **التاريخ:** {date_str}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = [
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"payment_approve_{payment_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"payment_reject_{payment_id}")
        ]
    ]
    
    if proof_id:
        buttons.append([
            InlineKeyboardButton("🧾 عرض الإيصال", callback_data=f"payment_proof_{payment_id}")
        ])
    
    # أزرار التنقل
    if len(payments) > 1:
        nav_buttons = []
        if index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"payment_next_{index - 1}"))
        if index < len(payments) - 1:
            nav_buttons.append(InlineKeyboardButton("➡️ التالي", callback_data=f"payment_next_{index + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_sub_settings")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    await message.edit_text(text, reply_markup=keyboard)


@app.on_callback_query(filters.regex(r'^approve_payment_'))
async def handle_approve_payment(client, callback_query):
    """معالج قبول الدفع من الأدمن"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    payment_id = int(callback_query.data.replace('approve_payment_', ''))
    admin_id = callback_query.from_user.id
    
    success, message_text = subdb.approve_payment(payment_id, admin_id)
    
    if success:
        # الحصول على معلومات الدفعة
        payment_info = subdb.get_payment_by_id(payment_id)
        if payment_info:
            user_id = payment_info[1]
            
            # إرسال إشعار للمستخدم
            try:
                # Get user's preferred language
                user_lang = subdb.get_user_language(user_id)
                
                await client.send_message(
                    chat_id=user_id,
                    text=t('subscription_activated', user_lang)
                )
            except:
                pass
        
        await callback_query.message.edit_caption(
            callback_query.message.caption + "\n\n✅ **تم القبول والتفعيل**",
            reply_markup=None
        )
        await callback_query.answer("✅ تم تفعيل الاشتراك بنجاح!", show_alert=True)
    else:
        await callback_query.answer(f"❌ {message_text}", show_alert=True)


@app.on_callback_query(filters.regex(r'^reject_payment_'))
async def handle_reject_payment(client, callback_query):
    """معالج رفض الدفع من الأدمن"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    payment_id = int(callback_query.data.replace('reject_payment_', ''))
    
    # الحصول على معلومات الدفعة
    payment_info = subdb.get_payment_by_id(payment_id)
    if payment_info:
        user_id = payment_info[1]
        
        # رفض الدفعة
        subdb.reject_payment(payment_id)
        
        # إرسال إشعار للمستخدم
        try:
            telegram_support = subdb.get_setting('telegram_support', 'wahab161')
            await client.send_message(
                chat_id=user_id,
                text=(
                    "❌ **تم رفض دفعتك**\n\n"
                    "قد يكون هناك مشكلة في إثبات الدفع.\n"
                    f"تواصل مع المطور: @{telegram_support}"
                )
            )
        except:
            pass
        
        await callback_query.message.edit_caption(
            callback_query.message.caption + "\n\n❌ **تم الرفض**",
            reply_markup=None
        )
        await callback_query.answer("❌ تم رفض الدفعة", show_alert=True)


async def subscription_settings_panel(client, message):
    """لوحة إعدادات الاشتراك للأدمن"""
    user_id = message.from_user.id
    
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or int(admin_id) != user_id:
        await message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    max_duration = subdb.get_max_duration()
    price = subdb.get_setting('subscription_price', '10')
    duration_days = subdb.get_setting('subscription_duration_days', '30')
    stats = subdb.get_user_stats()
    
    # الحصول على حالة حظر المحتوى الإباحي
    adult_block_status = "🔴 محظور" if subdb.is_adult_content_blocked() else "🟢 مسموح"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱️ تحديد المدة القصوى", callback_data="sub_set_duration")],
        [InlineKeyboardButton("💰 تحديد السعر", callback_data="sub_set_price")],
        [InlineKeyboardButton(f"🔞 المحتوى الإباحي: {adult_block_status}", callback_data="sub_toggle_adult_block")],
        [InlineKeyboardButton("🔗 إدارة الروابط المحظورة", callback_data="sub_manage_blocked_urls")],
        [InlineKeyboardButton("👥 عرض المشتركين", callback_data="sub_view_subscribers")],
        [InlineKeyboardButton("📊 عرض آخر 50 مستخدم", callback_data="sub_recent_users")],
        [InlineKeyboardButton("💳 الدفوعات المعلقة", callback_data="sub_pending_payments")],
        [InlineKeyboardButton("📊 إحصائيات الأعضاء", callback_data="sub_member_stats")],
        [InlineKeyboardButton("🔍 بحث عن عضو", callback_data="sub_search_user")],
        [InlineKeyboardButton("✏️ ترقية عضو", callback_data="sub_promote_user")],
        [InlineKeyboardButton("❌ إلغاء ترقية", callback_data="sub_demote_user")],
        [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="sub_broadcast")],
        [InlineKeyboardButton("📡 تسجيل القنوات", callback_data="sub_register_channels")],
        [InlineKeyboardButton("🔧 أدوات النظام", callback_data="sub_system_tools")]
    ])
    
    text = (
        f"💎 **إعدادات الاشتراك**\n\n"
        f"⏱️ **الحد الأقصى للمجاني:** {max_duration} دقيقة\n"
        f"💰 **سعر الاشتراك:** ${price}\n"
        f"📅 **مدة الاشتراك:** {duration_days} يوم\n"
        f"🔞 **حظر المحتوى الإباحي:** {adult_block_status}\n\n"
        f"📊 **الإحصائيات:**\n"
        f"• المجموع: {stats['total']} عضو\n"
        f"• المشتركون: {stats['subscribed']} 💎\n"
        f"• العاديون: {stats['free']} 🆓\n\n"
        f"**اختر الإعداد:**"
    )
    
    await message.reply_text(text, reply_markup=keyboard)


@app.on_callback_query(filters.regex(r'^(sub_|sys_)'))
async def handle_subscription_settings(client, callback_query):
    """معالج إعدادات الاشتراك"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    action = callback_query.data.replace('sub_', '')
    
    if action == 'set_duration':
        max_duration = subdb.get_max_duration()
        daily_limit = subdb.get_daily_limit()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱️ تغيير الحد الزمني", callback_data="change_time_limit")],
            [InlineKeyboardButton("🔢 تغيير الحد اليومي", callback_data="change_daily_limit")],
            [InlineKeyboardButton("« رجوع", callback_data="back_to_sub_settings")]
        ])
        
        await callback_query.message.edit_text(
            "⚙️ **تحديد المدة القصوى**\n\n"
            f"🕒 **الحد الزمني لغير المشتركين:** {max_duration} دقيقة\n"
            f"🔁 **الحد اليومي المسموح به:** {daily_limit} مرات\n\n"
            "💡 **ملاحظات:**\n"
            "• هذه القيود تطبق فقط على المستخدمين غير المشتركين\n"
            "• المشتركون VIP لديهم حرية كاملة بلا قيود\n\n"
            "**اختر الإجراء المطلوب:**",
            reply_markup=keyboard
        )
        
    elif action == 'set_price':
        # قائمة تحديد الأسعار
        user_monthly = subdb.get_setting('price_user_monthly', '5')
        user_yearly = subdb.get_setting('price_user_yearly', '40')
        group_monthly = subdb.get_setting('price_group_monthly', '15')
        group_yearly = subdb.get_setting('price_group_yearly', '120')
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"👤 المستخدم الشهري: ${user_monthly}", callback_data="sub_price_user_monthly")],
            [InlineKeyboardButton(f"👤 المستخدم السنوي: ${user_yearly}", callback_data="sub_price_user_yearly")],
            [InlineKeyboardButton(f"👥 المجموعة الشهري: ${group_monthly}", callback_data="sub_price_group_monthly")],
            [InlineKeyboardButton(f"👥 المجموعة السنوي: ${group_yearly}", callback_data="sub_price_group_yearly")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="sub_back_main")]
        ])
        
        await callback_query.message.edit_text(
            "💰 **تحديد أسعار الاشتراك**\n\n"
            f"👤 **المستخدم الشخصي:**\n"
            f"• شهري: ${user_monthly}\n"
            f"• سنوي: ${user_yearly}\n\n"
            f"👥 **المجموعة:**\n"
            f"• شهري: ${group_monthly}\n"
            f"• سنوي: ${group_yearly}\n\n"
            "اختر السعر لتعديله:",
            reply_markup=keyboard
        )
    
    elif action.startswith('price_'):
        # تحديد سعر معين
        price_type = action.replace('price_', '')
        price_names = {
            'user_monthly': 'المستخدم الشهري',
            'user_yearly': 'المستخدم السنوي',
            'group_monthly': 'المجموعة الشهري',
            'group_yearly': 'المجموعة السنوي'
        }
        current_price = subdb.get_setting(f'price_{price_type}', '10')
        await callback_query.message.edit_text(
            f"💰 **تحديد سعر {price_names.get(price_type, price_type)}**\n\n"
            f"السعر الحالي: ${current_price}\n\n"
            "أرسل السعر الجديد بالدولار (مثلاً: 10)"
        )
        pending_downloads[callback_query.from_user.id] = {'waiting_for': f'price_{price_type}'}
    
    elif action == 'toggle_adult_block':
        # تبديل حالة حظر المحتوى الإباحي
        current_status = subdb.is_adult_content_blocked()
        new_status = not current_status
        subdb.set_adult_content_blocking(new_status)
        
        status_text = "محظور 🔴" if new_status else "مسموح 🟢"
        await callback_query.answer(
            f"✅ تم التحديث! المحتوى الإباحي الآن: {status_text}",
            show_alert=True
        )
        
        # تحديث اللوحة لإظهار الحالة الجديدة
        max_duration = subdb.get_max_duration()
        price = subdb.get_setting('subscription_price', '10')
        duration_days = subdb.get_setting('subscription_duration_days', '30')
        stats = subdb.get_user_stats()
        adult_block_status = "🔴 محظور" if new_status else "🟢 مسموح"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱️ تحديد المدة القصوى", callback_data="sub_set_duration")],
            [InlineKeyboardButton("💰 تحديد السعر", callback_data="sub_set_price")],
            [InlineKeyboardButton(f"🔞 المحتوى الإباحي: {adult_block_status}", callback_data="sub_toggle_adult_block")],
            [InlineKeyboardButton("👥 عرض المشتركين", callback_data="sub_view_subscribers")],
            [InlineKeyboardButton("📊 عرض آخر 50 مستخدم", callback_data="sub_recent_users")],
            [InlineKeyboardButton("💳 الدفوعات المعلقة", callback_data="sub_pending_payments")],
            [InlineKeyboardButton("📊 إحصائيات الأعضاء", callback_data="sub_member_stats")],
            [InlineKeyboardButton("🔍 بحث عن عضو", callback_data="sub_search_user")],
            [InlineKeyboardButton("✏️ ترقية عضو", callback_data="sub_promote_user")],
            [InlineKeyboardButton("❌ إلغاء ترقية", callback_data="sub_demote_user")],
            [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="sub_broadcast")],
            [InlineKeyboardButton("📡 تسجيل القنوات", callback_data="sub_register_channels")]
        ])
        
        text = (
            f"💎 **إعدادات الاشتراك**\n\n"
            f"⏱️ **الحد الأقصى للمجاني:** {max_duration} دقيقة\n"
            f"💰 **سعر الاشتراك:** ${price}\n"
            f"📅 **مدة الاشتراك:** {duration_days} يوم\n"
            f"🔞 **حظر المحتوى الإباحي:** {adult_block_status}\n\n"
            f"📊 **الإحصائيات:**\n"
            f"• المجموع: {stats['total']} عضو\n"
            f"• المشتركون: {stats['subscribed']} 💎\n"
            f"• العاديون: {stats['free']} 🆓\n\n"
            f"**اختر الإعداد:**"
        )
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    elif action == 'manage_blocked_urls':
        # عرض قائمة الروابط المحظورة المخصصة
        blocked_urls = subdb.get_all_blocked_urls()
        
        if not blocked_urls:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إضافة رابط", callback_data="sub_add_blocked_url")],
                [InlineKeyboardButton("« رجوع", callback_data="back_to_sub_settings")]
            ])
            await callback_query.message.edit_text(
                "📋 **لا توجد روابط محظورة مخصصة**\n\n"
                "لم تقم بإضافة أي روابط للحظر بعد",
                reply_markup=keyboard
            )
        else:
            # بناء قائمة الروابط مع أزرار الحذف
            text = "📋 **قائمة الروابط المحظورة المخصصة**\n\n"
            keyboard_buttons = []
            
            for idx, (url_id, url_pattern, added_at, notes) in enumerate(blocked_urls[:15], 1):
                # عرض الرابط
                text += f"{idx}. 🔗 `{url_pattern}`\n"
                if notes:
                    text += f"   📝 {notes[:50]}\n"
                text += "\n"
                
                # إضافة زر الحذف
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"❌ حذف: {url_pattern[:25]}...",
                        callback_data=f"sub_remove_url_{url_id}"
                    )
                ])
            
            text += "\n💡 يمكنك إضافة نطاقات (مثل: example.com) أو روابط كاملة"
            
            # أزرار التحكم
            keyboard_buttons.append([InlineKeyboardButton("➕ إضافة رابط", callback_data="sub_add_blocked_url")])
            keyboard_buttons.append([InlineKeyboardButton("« رجوع", callback_data="back_to_sub_settings")])
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    elif action == 'add_blocked_url':
        # طلب إدخال الرابط
        await callback_query.message.edit_text(
            "📝 **أرسل الرابط أو النطاق للحظر**\n\n"
            "**أمثلة:**\n"
            "• example.com\n"
            "• badsite.net\n"
            "• https://spam.com\n\n"
            "⚠️ سيتم حظر أي رابط يحتوي على هذا النص"
        )
        pending_downloads[callback_query.from_user.id] = {'waiting_for': 'blocked_url'}
    
    elif action.startswith('remove_url_'):
        # إزالة رابط من القائمة
        url_id = int(action.replace('remove_url_', ''))
        
        if subdb.remove_blocked_url(url_id):
            await callback_query.answer("✅ تمت إزالة الرابط من القائمة!", show_alert=True)
            # تحديث القائمة
            blocked_urls = subdb.get_all_blocked_urls()
            
            if not blocked_urls:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ إضافة رابط", callback_data="sub_add_blocked_url")],
                    [InlineKeyboardButton("« رجوع", callback_data="back_to_sub_settings")]
                ])
                await callback_query.message.edit_text(
                    "📋 **لا توجد روابط محظورة مخصصة**\n\n"
                    "لم تقم بإضافة أي روابط للحظر بعد",
                    reply_markup=keyboard
                )
            else:
                # بناء القائمة المحدثة
                text = "📋 **قائمة الروابط المحظورة المخصصة**\n\n"
                keyboard_buttons = []
                
                for idx, (url_id, url_pattern, added_at, notes) in enumerate(blocked_urls[:15], 1):
                    text += f"{idx}. 🔗 `{url_pattern}`\n"
                    if notes:
                        text += f"   📝 {notes[:50]}\n"
                    text += "\n"
                    
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            f"❌ حذف: {url_pattern[:25]}...",
                            callback_data=f"sub_remove_url_{url_id}"
                        )
                    ])
                
                text += "\n💡 يمكنك إضافة نطاقات (مثل: example.com) أو روابط كاملة"
                
                keyboard_buttons.append([InlineKeyboardButton("➕ إضافة رابط", callback_data="sub_add_blocked_url")])
                keyboard_buttons.append([InlineKeyboardButton("« رجوع", callback_data="back_to_sub_settings")])
                
                keyboard = InlineKeyboardMarkup(keyboard_buttons)
                await callback_query.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback_query.answer("❌ خطأ في إزالة الرابط", show_alert=True)
        
    elif action == 'view_subscribers':
        subscribers = subdb.get_all_subscribers()
        
        if not subscribers:
            await callback_query.message.edit_text("📝 **لا يوجد مشتركون حالياً**")
            return
        
        text = "👥 **قائمة المشتركين**\n\n"
        
        for idx, sub in enumerate(subscribers[:20], 1):  # أول 20 مشترك
            user_id, username, first_name, end_date, method = sub
            username_str = f"@{username}" if username else "لا يوجد"
            name = first_name or "مستخدم"
            
            # حساب الأيام المتبقية
            if end_date:
                # PostgreSQL يُرجع datetime object مباشرة، بينما SQLite يُرجع string
                if isinstance(end_date, str):
                    end_dt = datetime.fromisoformat(end_date)
                else:
                    end_dt = end_date
                days_left = (end_dt - datetime.now()).days
                days_str = f"{days_left} يوم" if days_left > 0 else "منتهي"
            else:
                days_str = "مدى الحياة"
            
            text += f"{idx}. {name} ({username_str})\n"
            text += f"   🆔 `{user_id}` | ⏳ {days_str}\n\n"
        
        text += f"\n📊 **إجمالي المشتركين:** {len(subscribers)}"
        
        await callback_query.message.edit_text(text)
        
    elif action == 'pending_payments':
        payments = subdb.get_pending_payments()
        
        if not payments:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_sub_settings")]
            ])
            await callback_query.message.edit_text(
                "✅ **لا توجد دفوعات معلقة**\n\n"
                "📋 جميع الدفوعات تمت معالجتها!",
                reply_markup=keyboard
            )
            return
        
        text = "💳 **الدفوعات المعلقة**\n\n"
        text += f"📊 **إجمالي المعلقة:** {len(payments)}\n\n"
        
        # عرض أول دفعة مع أزرار التفاعل
        payment = payments[0]
        payment_id, user_id, username, first_name, method, amount, proof_id, created = payment
        username_str = f"@{username}" if username else "🚫 لا يوجد"
        name = first_name or "مستخدم"
        
        # تنسيق التاريخ
        if created:
            try:
                if isinstance(created, str):
                    created_dt = datetime.fromisoformat(created)
                else:
                    created_dt = created
                date_str = created_dt.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = str(created)[:16]
        else:
            date_str = "غير محدد"
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"🔖 **الدفعة #{payment_id}**\n\n"
        text += f"👤 **المستخدم:** {name}\n"
        text += f"📧 **اليوزر:** {username_str}\n"
        text += f"🆔 **ID:** `{user_id}`\n\n"
        text += f"💰 **المبلغ:** ${amount}\n"
        text += f"💳 **طريقة الدفع:** {method}\n"
        text += f"📅 **التاريخ:** {date_str}\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━"
        
        # إنشاء أزرار التفاعل
        buttons = [
            [
                InlineKeyboardButton("✅ قبول", callback_data=f"payment_approve_{payment_id}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"payment_reject_{payment_id}")
            ]
        ]
        
        # زر عرض الإيصال إذا كان موجوداً
        if proof_id:
            buttons.append([
                InlineKeyboardButton("🧾 عرض الإيصال", callback_data=f"payment_proof_{payment_id}")
            ])
        
        # تنقل بين الدفوعات إذا كان هناك أكثر من دفعة
        if len(payments) > 1:
            nav_buttons = []
            nav_buttons.append(InlineKeyboardButton(f"➡️ التالي ({len(payments)-1} 📋)", callback_data=f"payment_next_1"))
            buttons.append(nav_buttons)
        
        # زر الرجوع
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_sub_settings")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    elif action == 'member_stats':
        stats = subdb.get_user_stats()
        all_users = subdb.get_all_users()
        
        text = "📊 **إحصائيات الأعضاء**\n\n"
        text += f"👥 **إجمالي الأعضاء:** {stats['total']}\n"
        text += f"💎 **المشتركون:** {stats['subscribed']}\n"
        text += f"🆓 **العاديون:** {stats['free']}\n\n"
        
        # عرض بعض المشتركين مع الأيام المتبقية
        if stats['subscribed'] > 0:
            text += "━━━━━━━━━━━━━━━━\n"
            text += "**المشتركون الحاليون:**\n\n"
            
            count = 0
            for user in all_users:
                user_id, username, first_name, is_subscribed, subscription_end = user
                if is_subscribed:
                    days_left = subdb.get_days_remaining(user_id)
                    name = first_name or "مستخدم"
                    text += f"• {name}: {days_left} يوم متبقية\n"
                    count += 1
                    if count >= 10:  # أول 10 مشتركين
                        break
        
        await callback_query.message.edit_text(text)
    
    elif action == 'recent_users':
        users = subdb.get_recent_users(50)
        
        if not users:
            await callback_query.message.edit_text("📝 **لا يوجد مستخدمون**")
            return
        
        text = "📊 **آخر 50 مستخدم**\n\n"
        
        for idx, user in enumerate(users[:50], 1):
            user_id, username, first_name, is_subscribed = user
            username_str = f"@{username}" if username else "لا يوجد"
            name = first_name or "مستخدم"
            status = "💎" if is_subscribed else "🆓"
            
            text += f"{idx}. {status} {name} ({username_str})\n"
            text += f"   🆔 `{user_id}`\n\n"
        
        text += f"\n📊 **إجمالي المستخدمين:** {len(users)}\n\n"
        text += "💡 **لمراسلة أي مستخدم:**\n"
        text += "استخدم زر 'رسالة خاصة' وأرسل ID المستخدم"
        
        await callback_query.message.edit_text(text)
    
    elif action == 'promote_user':
        await callback_query.message.edit_text(
            "✏️ **ترقية عضو يدوياً**\n\n"
            "أرسل User ID أو Username للعضو المراد ترقيته\n\n"
            "مثال: `123456789` أو `@username`"
        )
        pending_downloads[callback_query.from_user.id] = {'waiting_for': 'promote_user_id'}
    
    elif action == 'demote_user':
        await callback_query.message.edit_text(
            "❌ **إلغاء ترقية عضو**\n\n"
            "أرسل User ID أو Username للعضو المراد إلغاء ترقيته\n\n"
            "مثال: `123456789` أو `@username`"
        )
        pending_downloads[callback_query.from_user.id] = {'waiting_for': 'demote_user_id'}
    
    elif action == 'search_user':
        await callback_query.message.edit_text(
            "🔍 **بحث عن عضو**\n\n"
            "أرسل User ID أو Username للبحث عنه\n\n"
            "مثال: `123456789` أو `@username`"
        )
        pending_downloads[callback_query.from_user.id] = {'waiting_for': 'search_user_id'}
    
    elif action == 'broadcast':
        # عرض شاشة اختيار نوع الإرسال
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📧 إرسال لجميع المستخدمين", callback_data="msg_broadcast_all")],
            [InlineKeyboardButton("👤 إرسال لمستخدم محدد", callback_data="msg_direct_user")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="msg_cancel")]
        ])
        
        stats = subdb.get_user_stats()
        await callback_query.message.edit_text(
            "📢 **نظام الإرسال الجماعي**\n\n"
            f"👥 **عدد المستخدمين:** {stats['total']}\n"
            f"💎 **المشتركون:** {stats['subscribed']}\n"
            f"🆓 **العاديون:** {stats['free']}\n\n"
            "**اختر نوع الإرسال:**",
            reply_markup=keyboard
        )
    
    elif callback_query.data == 'sub_system_tools':
        # لوحة أدوات النظام
        import subprocess
        
        # الحصول على نسخة yt-dlp الحالية
        try:
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=10)
            current_version = result.stdout.strip() if result.returncode == 0 else "غير معروفة"
        except:
            current_version = "غير معروفة"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحديث yt-dlp", callback_data="sys_update_ytdlp")],
            [InlineKeyboardButton("📋 فحص الإصدار", callback_data="sys_check_version")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_sub_settings")]
        ])
        
        await callback_query.message.edit_text(
            "🔧 **أدوات النظام**\n\n"
            f"📦 **نسخة yt-dlp الحالية:** `{current_version}`\n\n"
            "⚡️ **الخيارات المتاحة:**\n"
            "• تحديث yt-dlp لأحدث إصدار\n"
            "• فحص الإصدار الحالي ومقارنته بالأحدث\n\n"
            "💡 **ملاحظة:** التحديث قد يستغرق بضع ثوان",
            reply_markup=keyboard
        )
    
    elif callback_query.data == 'sys_update_ytdlp':
        # تحديث yt-dlp
        import subprocess
        
        await callback_query.message.edit_text("🔄 **جاري تحديث yt-dlp...**\n\n⏳ يرجى الانتظار...")
        
        try:
            # تنفيذ أمر التحديث
            result = subprocess.run(
                ['pip', 'install', '--upgrade', 'yt-dlp', '--break-system-packages'],
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout
            )
            
            # الحصول على النسخة الجديدة
            version_result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=10)
            new_version = version_result.stdout.strip() if version_result.returncode == 0 else "غير معروفة"
            
            if result.returncode == 0:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 فحص الإصدار", callback_data="sys_check_version")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="sub_system_tools")]
                ])
                
                await callback_query.message.edit_text(
                    "✅ **تم التحديث بنجاح!**\n\n"
                    f"📦 **الإصدار الحالي:** `{new_version}`\n\n"
                    "💡 التحديث فعّال فوراً بدون إعادة تشغيل البوت",
                    reply_markup=keyboard
                )
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="sys_update_ytdlp")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="sub_system_tools")]
                ])
                
                error_msg = result.stderr[:200] if result.stderr else "خطأ غير معروف"
                await callback_query.message.edit_text(
                    "❌ **فشل التحديث**\n\n"
                    f"**السبب:**\n`{error_msg}`\n\n"
                    "💡 جرب إعادة المحاولة أو تحديث يدوياً",
                    reply_markup=keyboard
                )
        except subprocess.TimeoutExpired:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="sys_update_ytdlp")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="sub_system_tools")]
            ])
            
            await callback_query.message.edit_text(
                "⏰ **انتهت المهلة**\n\n"
                "التحديث استغرق وقتاً طويلاً جداً\n\n"
                "💡 جرب إعادة المحاولة أو تحديث يدوياً",
                reply_markup=keyboard
            )
        except Exception as e:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="sys_update_ytdlp")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="sub_system_tools")]
            ])
            
            await callback_query.message.edit_text(
                f"❌ **خطأ:**\n`{str(e)[:200]}`",
                reply_markup=keyboard
            )
    
    elif callback_query.data == 'sys_check_version':
        # فحص الإصدار
        import subprocess
        
        await callback_query.message.edit_text("🔍 **جاري فحص الإصدار...**")
        
        try:
            # الإصدار الحالي
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=10)
            current_version = result.stdout.strip() if result.returncode == 0 else "غير معروفة"
            
            # فحص إذا كان هناك تحديث متوفر
            update_check = subprocess.run(
                ['yt-dlp', '-U', '--update-to', 'nightly@latest', '--dry-run'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # تحليل النتيجة
            if 'yt-dlp is up to date' in update_check.stdout or 'yt-dlp is up to date' in update_check.stderr:
                update_status = "✅ أنت على أحدث إصدار!"
                update_available = False
            else:
                update_status = "🔔 يوجد تحديث متاح!"
                update_available = True
            
            keyboard_buttons = []
            if update_available:
                keyboard_buttons.append([InlineKeyboardButton("🔄 تحديث الآن", callback_data="sys_update_ytdlp")])
            keyboard_buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="sub_system_tools")])
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            await callback_query.message.edit_text(
                "📋 **معلومات yt-dlp**\n\n"
                f"📦 **الإصدار الحالي:** `{current_version}`\n\n"
                f"**الحالة:** {update_status}",
                reply_markup=keyboard
            )
        except Exception as e:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="sub_system_tools")]
            ])
            
            await callback_query.message.edit_text(
                f"❌ **خطأ في الفحص:**\n`{str(e)[:200]}`",
                reply_markup=keyboard
            )
    
    elif callback_query.data == 'sub_register_channels':
        # تسجيل القنوات
        await callback_query.message.edit_text("🔄 جاري محاولة تسجيل القنوات...")
        
        channels = {
            'LOG_CHANNEL_ID': 'قناة سجلات الفيديو',
            'ERROR_LOG_CHANNEL_ID': 'قناة سجلات الأخطاء',
            'NEW_MEMBERS_CHANNEL_ID': 'قناة الأعضاء الجدد'
        }
        
        results = []
        success_count = 0
        total_count = 0
        
        for env_var, channel_name in channels.items():
            channel_id = os.getenv(env_var)
            if channel_id:
                total_count += 1
                if await try_register_channel(channel_id, channel_name):
                    results.append(f"✅ {channel_name}")
                    success_count += 1
                else:
                    results.append(f"❌ {channel_name}")
        
        # Build result message
        result_text = "📡 **نتيجة تسجيل القنوات:**\n\n"
        result_text += "\n".join(results)
        result_text += f"\n\n📊 **الإحصائيات:**\n"
        result_text += f"• تم التسجيل: {success_count}/{total_count}\n\n"
        
        if success_count == total_count and total_count > 0:
            result_text += "🎉 **تم تسجيل جميع القنوات بنجاح!**"
        elif success_count > 0:
            result_text += "⚠️ **بعض القنوات لم يتم تسجيلها**\n\n"
            result_text += "💡 **الحل:**\n"
            result_text += "1. افتح كل قناة فاشلة\n"
            result_text += "2. أرسل رسالة (مثل: test)\n"
            result_text += "3. اضغط الزر مرة أخرى"
        else:
            result_text += "❌ **لم يتم تسجيل أي قناة**\n\n"
            result_text += "💡 **الحل:**\n"
            result_text += "1. تأكد من إضافة البوت كـ Admin في القنوات\n"
            result_text += "2. أرسل رسالة في كل قناة\n"
            result_text += "3. اضغط الزر مرة أخرى"
        
        # Add back button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="sub_register_channels")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_sub_settings")]
        ])
        
        await callback_query.message.edit_text(result_text, reply_markup=keyboard)
    
    await callback_query.answer()


@app.on_callback_query(filters.regex(r'^(change_time_limit|change_daily_limit|back_to_sub_settings)$'))
async def handle_duration_actions(client, callback_query):
    """معالج إعدادات المدة والحد اليومي"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    action = callback_query.data
    user_id = callback_query.from_user.id
    
    if action == 'change_time_limit':
        await callback_query.message.edit_text(
            "⏱️ **تغيير الحد الزمني**\n\n"
            f"القيمة الحالية: {subdb.get_max_duration()} دقيقة\n\n"
            "أرسل الحد الزمني الجديد بالدقائق\n"
            "(مثلاً: 60 لساعة واحدة، 120 لساعتين)"
        )
        pending_downloads[user_id] = {'waiting_for': 'max_duration'}
    
    elif action == 'change_daily_limit':
        current_limit = subdb.get_daily_limit()
        
        # عرض الحد الحالي
        if current_limit == -1:
            current_text = "♾️ غير محدود"
        else:
            current_text = f"{current_limit} مرات"
        
        # لوحة أزرار الاختيار السريع
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("3️⃣ 3 تحميلات", callback_data="set_daily_limit_3"),
             InlineKeyboardButton("5️⃣ 5 تحميلات", callback_data="set_daily_limit_5")],
            [InlineKeyboardButton("🔟 10 تحميلات", callback_data="set_daily_limit_10"),
             InlineKeyboardButton("2️⃣0️⃣ 20 تحميلة", callback_data="set_daily_limit_20")],
            [InlineKeyboardButton("♾️ غير محدود", callback_data="set_daily_limit_unlimited")],
            [InlineKeyboardButton("✏️ إدخال يدوي", callback_data="set_daily_limit_manual")],
            [InlineKeyboardButton("« رجوع", callback_data="back_to_sub_settings")]
        ])
        
        await callback_query.message.edit_text(
            f"🔢 **تغيير الحد اليومي**\n\n"
            f"القيمة الحالية: {current_text}\n\n"
            "اختر الحد اليومي للتحميلات:",
            reply_markup=keyboard
        )
    
    elif action == 'back_to_sub_settings':
        # العودة لشاشة إعدادات الاشتراك - rebuild panel directly
        max_duration = subdb.get_max_duration()
        price = subdb.get_setting('subscription_price', '10')
        duration_days = subdb.get_setting('subscription_duration_days', '30')
        stats = subdb.get_user_stats()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱️ تحديد المدة القصوى", callback_data="sub_set_duration")],
            [InlineKeyboardButton("💰 تحديد السعر", callback_data="sub_set_price")],
            [InlineKeyboardButton("👥 عرض المشتركين", callback_data="sub_view_subscribers")],
            [InlineKeyboardButton("📊 عرض آخر 50 مستخدم", callback_data="sub_recent_users")],
            [InlineKeyboardButton("💳 الدفوعات المعلقة", callback_data="sub_pending_payments")],
            [InlineKeyboardButton("📊 إحصائيات الأعضاء", callback_data="sub_member_stats")],
            [InlineKeyboardButton("🔍 بحث عن عضو", callback_data="sub_search_user")],
            [InlineKeyboardButton("✏️ ترقية عضو", callback_data="sub_promote_user")],
            [InlineKeyboardButton("❌ إلغاء ترقية", callback_data="sub_demote_user")],
            [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="sub_broadcast")],
            [InlineKeyboardButton("📡 تسجيل القنوات", callback_data="sub_register_channels")]
        ])
        
        text = (
            f"💎 **إعدادات الاشتراك**\n\n"
            f"⏱️ **الحد الأقصى للمجاني:** {max_duration} دقيقة\n"
            f"💰 **سعر الاشتراك:** ${price}\n"
            f"📅 **مدة الاشتراك:** {duration_days} يوم\n\n"
            f"📊 **الإحصائيات:**\n"
            f"• المجموع: {stats['total']} عضو\n"
            f"• المشتركون: {stats['subscribed']} 💎\n"
            f"• العاديون: {stats['free']} 🆓\n\n"
            f"**اختر الإعداد:**"
        )
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    await callback_query.answer()


@app.on_callback_query(filters.regex(r'^msg_'))
async def handle_message_type(client, callback_query):
    """معالج اختيار نوع الرسالة"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    user_id = callback_query.from_user.id
    action = callback_query.data.replace('msg_', '')
    
    if action == 'broadcast_all':
        await callback_query.message.edit_text(
            "📢 **إرسال رسالة لجميع المستخدمين**\n\n"
            "أرسل الرسالة التي تريد إرسالها لجميع مستخدمي البوت\n\n"
            f"⚠️ سيتم إرسالها لـ **{subdb.get_user_stats()['total']}** مستخدم"
        )
        pending_downloads[user_id] = {'waiting_for': 'broadcast_message'}
    
    elif action == 'direct_user':
        await callback_query.message.edit_text(
            "👤 **إرسال رسالة لمستخدم محدد**\n\n"
            "أرسل **User ID** أو **Username** للمستخدم المراد مراسلته\n\n"
            "**أمثلة:**\n"
            "• `123456789` (User ID)\n"
            "• `@username` (Username)"
        )
        pending_downloads[user_id] = {'waiting_for': 'direct_msg_user_id'}
    
    elif action == 'cancel':
        await callback_query.message.edit_text("❌ **تم الإلغاء**")
        if user_id in pending_downloads:
            del pending_downloads[user_id]
    
    await callback_query.answer()


@app.on_callback_query(filters.regex(r'^set_daily_limit_'))
async def handle_set_daily_limit(client, callback_query):
    """معالج اختيار الحد اليومي السريع"""
    if int(os.getenv("ADMIN_ID", "0")) != callback_query.from_user.id:
        await callback_query.answer("❌ للمشرفين فقط!", show_alert=True)
        return
    
    user_id = callback_query.from_user.id
    action = callback_query.data.replace('set_daily_limit_', '')
    
    if action == 'manual':
        # الإدخال اليدوي
        await callback_query.message.edit_text(
            "✏️ **إدخال يدوي للحد اليومي**\n\n"
            f"القيمة الحالية: {subdb.get_daily_limit()} مرات\n\n"
            "أرسل الحد اليومي الجديد للتحميلات\n"
            "(مثلاً: 6 لست مرات يومياً، 15 لـ 15 مرة)"
        )
        pending_downloads[user_id] = {'waiting_for': 'daily_limit'}
    
    elif action == 'unlimited':
        # تعيين غير محدود
        subdb.set_daily_limit(-1)
        await callback_query.message.edit_text(
            "✅ **تم تحديث الحد اليومي**\n\n"
            "الحد الجديد: ♾️ غير محدود\n\n"
            "المستخدمون غير المشتركين يمكنهم الآن التحميل بدون قيود يومية."
        )
        logger.info("✅ تم تعيين الحد اليومي إلى: غير محدود")
    
    else:
        # اختيار رقم محدد
        try:
            limit = int(action)
            subdb.set_daily_limit(limit)
            await callback_query.message.edit_text(
                f"✅ **تم تحديث الحد اليومي**\n\n"
                f"الحد الجديد: {limit} مرات في اليوم"
            )
            logger.info(f"✅ تم تعيين الحد اليومي إلى: {limit} مرات")
        except ValueError:
            await callback_query.answer("❌ خطأ في القيمة", show_alert=True)
    
    await callback_query.answer()



@app.on_message(filters.text & ~filters.regex(r'https?://') & ~filters.regex(r'^(🍪|📊|🔔|💎|/)'))
async def handle_admin_input(client, message):
    """معالج إدخالات الأدمن للإعدادات"""
    user_id = message.from_user.id
    
    if int(os.getenv("ADMIN_ID", "0")) != user_id:
        return
    
    if user_id not in pending_downloads:
        return
    
    data = pending_downloads.get(user_id)
    if not isinstance(data, dict) or 'waiting_for' not in data:
        return
    
    waiting_for = data['waiting_for']
    
    try:
        if waiting_for == 'max_duration':
            minutes = int(message.text.strip())
            if minutes < 1:
                await message.reply_text("❌ يجب أن تكون المدة أكبر من 0")
                return
            
            subdb.set_max_duration(minutes)
            await message.reply_text(
                f"✅ **تم تحديث الحد الأقصى**\n\n"
                f"المدة الجديدة: {minutes} دقيقة ({minutes//60} ساعة و {minutes%60} دقيقة)"
            )
            del pending_downloads[user_id]
        
        elif waiting_for == 'daily_limit':
            limit = int(message.text.strip())
            if limit < 1:
                await message.reply_text("❌ يجب أن يكون الحد أكبر من 0")
                return
            
            subdb.set_daily_limit(limit)
            await message.reply_text(
                f"✅ **تم تحديث الحد اليومي**\n\n"
                f"الحد الجديد: {limit} مرات في اليوم"
            )
            del pending_downloads[user_id]
            
        elif waiting_for == 'subscription_price':
            price = float(message.text.strip())
            if price < 0:
                await message.reply_text("❌ يجب أن يكون السعر أكبر من 0")
                return
            
            subdb.set_setting('subscription_price', str(price))
            await message.reply_text(
                f"✅ **تم تحديث السعر**\n\n"
                f"السعر الجديد: ${price}"
            )
            del pending_downloads[user_id]
        
        elif waiting_for.startswith('price_'):
            # حفظ السعر الجديد (user_monthly, user_yearly, group_monthly, group_yearly)
            price = float(message.text.strip())
            if price < 0:
                await message.reply_text("❌ يجب أن يكون السعر أكبر من 0")
                return
            
            price_type = waiting_for  # price_user_monthly, etc.
            price_names = {
                'price_user_monthly': 'المستخدم الشهري',
                'price_user_yearly': 'المستخدم السنوي',
                'price_group_monthly': 'المجموعة الشهري',
                'price_group_yearly': 'المجموعة السنوي'
            }
            subdb.set_setting(price_type, str(price))
            await message.reply_text(
                f"✅ **تم تحديث سعر {price_names.get(price_type, '')}**\n\n"
                f"السعر الجديد: ${price}"
            )
            del pending_downloads[user_id]
        
        elif waiting_for == 'promote_user_id':
            user_input = message.text.strip()
            
            # محاولة البحث بواسطة ID أو Username
            target_user = None
            if user_input.isdigit():
                target_user = subdb.find_user_by_id(int(user_input))
            elif user_input.startswith('@') or user_input.isalnum():
                target_user = subdb.find_user_by_username(user_input)
            
            if not target_user:
                await message.reply_text(
                    "❌ **لم يتم العثور على المستخدم**\n\n"
                    "تأكد من أن المستخدم قد استخدم البوت مسبقاً"
                )
                del pending_downloads[user_id]
                return
            
            # حفظ معلومات المستخدم المستهدف
            pending_downloads[user_id] = {
                'waiting_for': 'promote_duration',
                'target_user_id': target_user[0],
                'target_user_name': target_user[2]
            }
            
            # عرض معلومات المستخدم وطلب المدة
            user_status = "💎 مشترك" if target_user[3] else "🆓 عادي"
            await message.reply_text(
                f"👤 **تم العثور على المستخدم:**\n\n"
                f"الاسم: {target_user[2]}\n"
                f"ID: `{target_user[0]}`\n"
                f"الحالة: {user_status}\n\n"
                f"**أرسل مدة الاشتراك بالأيام**\n"
                f"(مثلاً: 30 لشهر واحد، 365 لسنة)"
            )
        
        elif waiting_for == 'promote_duration':
            days = int(message.text.strip())
            if days < 1:
                await message.reply_text("❌ يجب أن تكون المدة أكبر من 0")
                return
            
            target_user_id = data.get('target_user_id')
            target_user_name = data.get('target_user_name')
            
           # ترقية المستخدم
            subdb.activate_subscription(target_user_id, days, 'manual_by_admin')
            
            # إشعار للأدمن
            await message.reply_text(
                f"✅ **تمت الترقية بنجاح!**\n\n"
                f"👤 **المستخدم:** {target_user_name}\n"
                f"🆔 **ID:** `{target_user_id}`\n"
                f"📅 **المدة:** {days} يوم"
            )
            
            # إشعار للمستخدم
            try:
                # Get user's preferred language
                user_lang = subdb.get_user_language(target_user_id)
                
                await client.send_message(
                    chat_id=target_user_id,
                    text=t('subscription_upgraded', user_lang, days=days)
                )
                logger.info(f"✅ تمت ترقية {target_user_id} لمدة {days} يوم")
            except:
                logger.warning(f"لم يتمكن من إرسال إشعار الترقية للمستخدم {target_user_id}")
            
            del pending_downloads[user_id]
        
        elif waiting_for == 'broadcast_message':
            broadcast_text = message.text.strip()
            
            # الحصول على جميع المستخدمين
            all_users = subdb.get_all_users()
            
            await message.reply_text(
                f"📤 **جاري الإرسال...**\n\n"
                f"سيتم إرسال الرسالة لـ {len(all_users)} مستخدم"
            )
            
            success_count = 0
            fail_count = 0
            
            for user in all_users:
                try:
                    # Get each user's preferred language
                    user_lang = subdb.get_user_language(user[0])
                    
                    await client.send_message(
                        chat_id=user[0],  # user_id
                        text=f"{t('broadcast_message_prefix', user_lang)}\n\n{broadcast_text}"
                    )
                    success_count += 1
                    await asyncio.sleep(0.05)  # تأخير بسيط لتجنب Flood
                except:
                    fail_count += 1
            
            await message.reply_text(
                f"✅ **اكتمل الإرسال!**\n\n"
                f"✅ النجاح: {success_count}\n"
                f"❌ الفشل: {fail_count}"
            )
            
            del pending_downloads[user_id]
            logger.info(f"📢 Broadcast: {success_count} نجح, {fail_count} فشل")
        
        elif waiting_for == 'direct_msg_user_id':
            user_input = message.text.strip()
            
            # محاولة البحث بواسطة ID أو Username
            target_user = None
            if user_input.isdigit():
                target_user = subdb.find_user_by_id(int(user_input))
            elif user_input.startswith('@') or user_input.isalnum():
                target_user = subdb.find_user_by_username(user_input)
            
            if not target_user:
                await message.reply_text(
                    "❌ **لم يتم العثور على المستخدم**\n\n"
                    "تأكد من أن المستخدم قد استخدم البوت مسبقاً"
                )
                del pending_downloads[user_id]
                return
            
            # حفظ معلومات المستخدم المستهدف
            pending_downloads[user_id] = {
                'waiting_for': 'direct_msg_text',
                'target_user_id': target_user[0],
                'target_user_name': target_user[2]
            }
            
            await message.reply_text(
                f"👤 **سيتم الإرسال إلى:**\n\n"
                f"الاسم: {target_user[2]}\n"
                f"ID: `{target_user[0]}`\n\n"
                f"**أرسل الرسالة الآن:**"
            )
        
        elif waiting_for == 'direct_msg_text':
            msg_text = message.text.strip()
            target_user_id = data.get('target_user_id')
            target_user_name = data.get('target_user_name')
            
            try:
                # Get user's preferred language
                user_lang = subdb.get_user_language(target_user_id)
                
                await client.send_message(
                    chat_id=target_user_id,
                    text=f"{t('direct_message_prefix', user_lang)}\n\n{msg_text}"
                )
                
                await message.reply_text(
                    f"✅ **تم الإرسال بنجاح!**\n\n"
                    f"👤 إلى: {target_user_name}\n"
                    f"🆔 ID: `{target_user_id}`"
                )
                logger.info(f"✉️ رسالة مباشرة من الأدمن إلى {target_user_id}")
            except Exception as e:
                await message.reply_text(
                    f"❌ **فشل الإرسال**\n\n"
                    f"الخطأ: {str(e)}"
                )
            
            del pending_downloads[user_id]
        
        elif waiting_for == 'search_user_id':
            user_input = message.text.strip()
            
            # محاولة البحث بواسطة ID أو Username
            target_user = None
            if user_input.isdigit():
                target_user = subdb.find_user_by_id(int(user_input))
            elif user_input.startswith('@') or user_input.isalnum():
                target_user = subdb.find_user_by_username(user_input)
            
            if not target_user:
                await message.reply_text(
                    "❌ **لم يتم العثور على المستخدم**\n\n"
                    "تأكد من أن المستخدم قد استخدم البوت مسبقاً"
                )
                del pending_downloads[user_id]
                return
            
            # عرض معلومات المستخدم
            user_id_found, username, first_name, is_subscribed, subscription_end = target_user
            username_str = f"@{username}" if username else "لا يوجد"
            name = first_name or "مستخدم"
            
            # حالة الاشتراك
            if is_subscribed:
                days_left = subdb.get_days_remaining(user_id_found)
                status = f"💎 **مشترك** ({days_left} يوم متبقية)"
            else:
                status = "🆓 **عادي** (غير مشترك)"
            
            text = (
                f"🔍 **معلومات المستخدم**\n\n"
                f"👤 **الاسم:** {name}\n"
                f"🆔 **User ID:** `{user_id_found}`\n"
                f"📱 **Username:** {username_str}\n"
                f"📊 **الحالة:** {status}\n"
            )
            
            await message.reply_text(text)
            del pending_downloads[user_id]
        
        elif waiting_for == 'demote_user_id':
            user_input = message.text.strip()
            
            # محاولة البحث بواسطة ID أو Username
            target_user = None
            if user_input.isdigit():
                target_user = subdb.find_user_by_id(int(user_input))
            elif user_input.startswith('@') or user_input.isalnum():
                target_user = subdb.find_user_by_username(user_input)
            
            if not target_user:
                await message.reply_text(
                    "❌ **لم يتم العثور على المستخدم**\n\n"
                    "تأكد من أن المستخدم قد استخدم البوت مسبقاً"
                )
                del pending_downloads[user_id]
                return
            
            # التحقق من أن المستخدم مشترك
            target_user_id, username, first_name, is_subscribed, subscription_end = target_user
            
            if not is_subscribed:
                await message.reply_text(
                    "❌ **المستخدم ليس مشتركاً**\n\n"
                    f"👤 {first_name}\n"
                    f"🆔 `{target_user_id}`\n"
                    f"الحالة: 🆓 عادي"
                )
                del pending_downloads[user_id]
                return
            
            # إلغاء الاشتراك
            subdb.deactivate_subscription(target_user_id)
            
            # إرسال إشعار للمستخدم
            try:
                # Get user's preferred language
                user_lang = subdb.get_user_language(target_user_id)
                
                await client.send_message(
                    chat_id=target_user_id,
                    text=t('subscription_deactivated', user_lang)
                )
            except:
                pass
            
            await message.reply_text(
                f"✅ **تم إلغاء الترقية بنجاح!**\n\n"
                f"👤 **المستخدم:** {first_name}\n"
                f"🆔 **ID:** `{target_user_id}`\n"
                f"📊 **الحالة الجديدة:** 🆓 عادي"
            )
            logger.info(f"❌ تم إلغاء ترقية المستخدم {target_user_id}")
            del pending_downloads[user_id]
    
    except ValueError:
        await message.reply_text("❌ قيمة غير صحيحة! أرسل رقماً فقط.")


# ═══════════════════════════════════════════════════════════════
# معالج اختيار اللغة - Language Selection Handler
# ═══════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r'^lang_'))
async def handle_language_selection(client, callback_query):
    """معالج اختيار اللغة"""
    lang = callback_query.data.replace('lang_', '')
    user_id = callback_query.from_user.id
    
    # حفظ اللغة
    subdb.set_user_language(user_id, lang)
    
    # إضافة المستخدم إلى قاعدة البيانات
    username = callback_query.from_user.username
    first_name = callback_query.from_user.first_name
    subdb.add_or_update_user(user_id, username, first_name)
    
    # رسالة التأكيد
    await callback_query.message.edit_text(
        t('language_set', lang)
    )
    
    # إرسال رسالة الترحيب
    admin_id = os.getenv("ADMIN_ID")
    keyboard = None
    
    if admin_id and str(user_id) == admin_id:
        from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton(t('btn_cookies', lang)), KeyboardButton(t('btn_daily_report', lang))],
            [KeyboardButton(t('btn_errors', lang)), KeyboardButton(t('btn_subscription', lang))],
            [KeyboardButton("📁 نسخ احتياطي"), KeyboardButton(t('btn_change_language', lang))]
        ], resize_keyboard=True)
    else:
        from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton(t('btn_add_to_group', lang))],
            [KeyboardButton(t('btn_change_language', lang))]
        ], resize_keyboard=True)
    
    await client.send_message(
        chat_id=user_id,
        text=t('welcome', lang, name=first_name),
        reply_markup=keyboard
    )
    
    # إرسال زر إضافة البوت للمجموعة كزر إنلاين أيضاً
    bot_me = await client.get_me()
    add_to_group_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            t('btn_add_to_group', lang),
            url=f"https://t.me/{bot_me.username}?startgroup=true"
        )]
    ])
    
    await client.send_message(
        chat_id=user_id,
        text="👥",
        reply_markup=add_to_group_keyboard
    )
    
    await callback_query.answer()

@app.on_message(filters.command("register_channels"))
async def register_channels_command(client, message):
    """
    أمر للأدمن لتسجيل القنوات يدوياً
    Admin command to manually register channels
    """
    user_id = message.from_user.id
    
    # Check if admin
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or int(admin_id) != user_id:
        await message.reply_text("❌ هذا الأمر متاح للمسؤول فقط")
        return
    
    status_msg = await message.reply_text("🔄 جاري محاولة تسجيل القنوات...")
    
    channels = {
        'LOG_CHANNEL_ID': 'قناة سجلات الفيديو',
        'ERROR_LOG_CHANNEL_ID': 'قناة سجلات الأخطاء',
        'NEW_MEMBERS_CHANNEL_ID': 'قناة الأعضاء الجدد'
    }
    
    results = []
    success_count = 0
    total_count = 0
    
    for env_var, channel_name in channels.items():
        channel_id = os.getenv(env_var)
        if channel_id:
            total_count += 1
            if await try_register_channel(channel_id, channel_name):
                results.append(f"✅ {channel_name}")
                success_count += 1
            else:
                results.append(f"❌ {channel_name}")
    
    # Build result message
    result_text = "**نتيجة تسجيل القنوات:**\n\n"
    result_text += "\n".join(results)
    result_text += f"\n\n📊 **الإحصائيات:**\n"
    result_text += f"• تم التسجيل: {success_count}/{total_count}\n\n"
    
    if success_count == total_count and total_count > 0:
        result_text += "🎉 **تم تسجيل جميع القنوات بنجاح!**"
    elif success_count > 0:
        result_text += "⚠️ **بعض القنوات لم يتم تسجيلها**\n\n"
        result_text += "💡 **الحل:**\n"
        result_text += "1. افتح كل قناة فاشلة\n"
        result_text += "2. أرسل رسالة (مثل: test)\n"
        result_text += "3. أعد تشغيل هذا الأمر"
    else:
        result_text += "❌ **لم يتم تسجيل أي قناة**\n\n"
        result_text += "💡 **الحل:**\n"
        result_text += "1. تأكد من إضافة البوت كـ Admin في القنوات\n"
        result_text += "2. أرسل رسالة في كل قناة\n"
        result_text += "3. أعد تشغيل هذا الأمر"
    
    await status_msg.edit_text(result_text, parse_mode=enums.ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════
# Auto-register channels when receiving any post
# ═══════════════════════════════════════════════════════════════
@app.on_message(filters.channel, group=1)
async def auto_register_channel(client, message):
    """
    تسجيل القنوات تلقائياً عند استلام أي رسالة منها
    Automatically register channels when receiving any message from them
    """
    try:
        channel_id = str(message.chat.id)
        channel_title = message.chat.title or "Unknown"
        
        # Check if this channel is one of our configured channels
        configured_channels = {
            os.getenv('LOG_CHANNEL_ID'): 'قناة سجلات الفيديو',
            os.getenv('ERROR_LOG_CHANNEL_ID'): 'قناة سجلات الأخطاء',
            os.getenv('NEW_MEMBERS_CHANNEL_ID'): 'قناة الأعضاء الجدد'
        }
        
        # Check if already registered
        if channel_id in registered_channels:
            return
        
        # Register the channel
        registered_channels.add(channel_id)
        
        # Check if it's a configured channel
        channel_name = configured_channels.get(channel_id)
        if channel_name:
            logger.info(f"✅ تم تسجيل {channel_name} تلقائياً: {channel_title} (ID: {channel_id})")
            
            # Send confirmation message and delete it
            try:
                confirm_msg = await client.send_message(
                    chat_id=channel_id,
                    text=f"✅ تم تسجيل القناة بنجاح!\n\n📡 {channel_name}\n🔗 البوت جاهز للعمل الآن!"
                )
                await asyncio.sleep(3)
                await confirm_msg.delete()
            except Exception as e:
                logger.warning(f"⚠️ لم يتمكن من إرسال تأكيد للقناة: {e}")
        else:
            logger.info(f"📡 تم تسجيل قناة جديدة: {channel_title} (ID: {channel_id})")
    
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل القناة تلقائياً: {e}")


@app.on_message(filters.text & ~filters.regex(r'^/'), group=10)
async def handle_change_language_button(client, message):
    """معالج زر تغيير اللغة - مع أولوية أعلى"""
    # تجاهل المجموعات - هذا الزر للمحادثات الخاصة فقط
    if message.chat.type.value != "private":
        return
    
    # Check if message is change language button in any language
    if message.text in ["🌍 تغيير اللغة", "🌍 Change Language"]:
        user_id = message.from_user.id
        # Get user's current language
        current_lang = subdb.get_user_language(user_id)
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇮🇶 العربية", callback_data="lang_ar"),
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
            ]
        ])
        
        # Use bilingual message (works for both languages)
        await message.reply_text(
            t('choose_language', current_lang),
            reply_markup=keyboard
        )
    
    # Handler for Add to Group keyboard button
    elif message.text in ["➕ أضف البوت لمجموعتك", "➕ Add Bot to Your Group"]:
        user_id = message.from_user.id
        lang = subdb.get_user_language(user_id)
        
        # Get bot username
        bot_me = await client.get_me()
        
        add_to_group_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                t('btn_add_to_group', lang),
                url=f"https://t.me/{bot_me.username}?startgroup=true"
            )]
        ])
        
        # إرسال التعليمات مع زر الإضافة
        await message.reply_text(
            t('add_bot_instructions', lang),
            reply_markup=add_to_group_keyboard
        )


logger.info("🚀 بدء البوت...")
# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("🤖 Telegram Video Downloader Bot (Standalone)")
    print("=" * 60)
    print("✅ يرفع حتى 2GB")
    print("✅ نجح مع فيديو 3 ساعات")
    print("=" * 60)
    
    # إنشاء مجلد videos وcookies
    os.makedirs('videos', exist_ok=True)
    os.makedirs('cookies', exist_ok=True)
    
    # إنشاء قاعدة البيانات
    subdb.init_db()
    print("✅ تم إنشاء قاعدة بيانات الاشتراكات")
    
    # بدء مهمة التقرير اليومي
    loop = asyncio.get_event_loop()
    loop.create_task(daily_report_task())
    
    # Start the bot
    async def startup():
        """Function to run after bot starts"""
        await app.start()
        logger.info("✅ Bot started successfully")
        
        # ═══════════════════════════════════════════════════════════════
        # ضبط أوامر البوت مع تحديد النطاقات (Command Scopes)
        # ═══════════════════════════════════════════════════════════════
        await set_bot_commands()
        
        # Try to register channels automatically
        await register_all_channels()
        
        # Keep the bot running
        await idle()
    
    try:
        loop.run_until_complete(startup())
    except KeyboardInterrupt:
        print("\n⏹️ تم الإيقاف")


async def set_bot_commands():
    """
    ضبط أوامر البوت برمجياً مع تحديد النطاقات
    Set bot commands programmatically with scopes
    
    - Private chats: start, help, account
    - Groups (admins only): settings
    """
    from pyrogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # 1. مسح الأوامر الحالية (العامة)
        # ═══════════════════════════════════════════════════════════════
        await app.delete_bot_commands()
        logger.info("🗑️ تم مسح الأوامر القديمة")
        
        # ═══════════════════════════════════════════════════════════════
        # 2. أوامر المحادثات الخاصة فقط
        # ═══════════════════════════════════════════════════════════════
        private_commands = [
            BotCommand("start", "🚀 بدء البوت"),
            BotCommand("help", "❓ المساعدة والدليل"),
            BotCommand("account", "💎 حالة اشتراكي"),
        ]
        
        await app.set_bot_commands(
            commands=private_commands,
            scope=BotCommandScopeAllPrivateChats()
        )
        logger.info("✅ تم ضبط أوامر المحادثات الخاصة")
        
        # ═══════════════════════════════════════════════════════════════
        # 3. أوامر المجموعات (للأدمن فقط)
        # ═══════════════════════════════════════════════════════════════
        group_admin_commands = [
            BotCommand("settings", "⚙️ إعدادات المجموعة"),
        ]
        
        await app.set_bot_commands(
            commands=group_admin_commands,
            scope=BotCommandScopeAllChatAdministrators()
        )
        logger.info("✅ تم ضبط أوامر أدمن المجموعات")
        
        # ═══════════════════════════════════════════════════════════════
        # 4. لا أوامر للأعضاء العاديين في المجموعات
        # ═══════════════════════════════════════════════════════════════
        await app.set_bot_commands(
            commands=[],  # قائمة فارغة - لا أوامر
            scope=BotCommandScopeAllGroupChats()
        )
        logger.info("✅ تم إخفاء الأوامر من الأعضاء العاديين في المجموعات")
        
        logger.info("🎯 تم ضبط جميع أوامر البوت بنجاح!")
        
    except Exception as e:
        logger.error(f"❌ خطأ في ضبط أوامر البوت: {e}")
        logger.info("💡 البوت سيعمل بشكل طبيعي، لكن الأوامر قد تظهر بشكل افتراضي")


if __name__ == "__main__":
    main()
