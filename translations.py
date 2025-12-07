# -*- coding: utf-8 -*-
"""
نظام الترجمات - دعم العربية والإنجليزية
Translation System - Arabic & English Support
"""

TRANSLATIONS = {
    'ar': {
        # الرسائل الأساسية - Basic Messages
        'welcome': '👋 هلا بيك ببوت التحميل الأقوى!\n\n🚀 أحمّل لك كلشي ومن أشهر المنصّات:\n- YouTube (لحد 4 ساعات)\n- Facebook\n- Instagram (الصور + الفيديو + الستوري العامة)\n- TikTok\n- Snapchat (الستوريات)\n- Pinterest\n- X (تويتر سابقًا)\n- Reddit\n\n📌 ملاحظة مهمّة:\nأكدر أحمّل صور وفيديوهات ستوري الإنستا العامة فقط.\n\n🎬 مميزات البوت:\n• تحميل سريع\n• جودة عالية Full HD\n• دعم رفع لحد 2GB\n• تحميل مقاطع يوتيوب حتى 4 ساعات\n• حفظ الفيديو بصيغة MP4 جاهز للمشاهدة\n\n📥 *مجرد دز الرابط… والبوت يتكفّل بكلشي!*',
        'choose_language': '🌍 **اختر لغتك**\nChoose Your Language',
        'language_set': '✅ تم تحديد اللغة: العربية 🇮🇶',
        'language_changed': '✅ تم تغيير اللغة إلى العربية 🇮🇶',
        
        # الأزرار - Buttons
        'btn_cookies': '🍪 Cookies',
        'btn_daily_report': '📊 التقرير اليومي',
        'btn_errors': '🔔 الأخطاء',
        'btn_subscription': '💎 إعدادات الاشتراك',
        'btn_change_language': '🌍 تغيير اللغة',
        'btn_my_subscription': '💎 اشتراكي',
        
        # Download
        'processing': '⏳ **جاري المعالجة...**',
        'start_downloading': '📥 **جاري التحميل...**',
        'upload_started': '⬆️ جاري الرفع...',
        'download_failed': '❌ **فشل التحميل**',
        'downloading': '📥 ⏬ جاري التحميل...\n📊 {percent}%\n\n💾 {current_mb} / {total_mb} MB\n🚀 {speed_mb} MB/s\n⏳ {eta}s\n\n{progress_bar}',
        'uploading': '📤 ⏫ جاري الرفع...\n📊 {percent}%\n\n💾 {current_mb} / {total_mb} MB\n🚀 {speed_mb} MB/s\n⏳ {eta}s\n\n{progress_bar}',
        'choose_quality': '📺 **اختر الجودة:**\n\n🎬 {title}\n⏱️ {duration}',
        'quality_best': '📺 1080p',
        'quality_medium': '📱 720p',
        'quality_audio': '🎵 MP3',
        
        # الاشتراك - Subscription
        'subscription_required': '⚠️ **يتطلب اشتراك مدفوع**\n\n🎬 **الفيديو:** {title}\n⏱️ **المدة:** {duration} دقيقة\n🔒 **الحد الأقصى للمجاني:** {max_duration} دقيقة',
        'subscription_benefits': '💎 **للحصول على اشتراك:**\n• تحميل فيديوهات بدون حد\n• أولوية في التحميل\n• دعم المطور',
        'subscription_status': '💎 **اشتراكك نشط**\n\n📅 **ينتهي في:** {end_date}\n\n⏳ **الوقت المتبقي:**\n• {days} يوم\n• {hours} ساعة',
        'not_subscribed': '❌ **ليس لديك اشتراك نشط**\n\nاشترك الآن للحصول على مزايا غير محدودة!',
        'subscription_upgraded': '🎉 **تمت ترقيتك للاشتراك المميز!**\n\n💎 يمكنك الآن تحميل فيديوهات بدون حد للمدة.\n📅 **مدة الاشتراك:** {days} يوم\n\nاستمتع بالخدمة! ✨',
        'subscription_activated': '🎉 **تم تفعيل اشتراكك!**\n\nيمكنك الآن تحميل فيديوهات بدون حد للمدة.\nاستمتع بالخدمة! 💎',
        'subscription_deactivated': '⚠️ **تم إلغاء اشتراكك**\n\nللمزيد من المعلومات، تواصل مع المطور.',
        'daily_limit_exceeded': '⚠️ **تجاوزت الحد اليومي**\n\n🔁 **الحد المسموح:** {limit} مرات في اليوم\n📊 **تحميلاتك اليوم:** {count} مرات',
        'downloads_remaining': '✅ **تم التحميل بنجاح!**\n\n📊 **باقي لك:** {remaining} تحميلات اليوم',
        'unlimited_downloads': '♾️ غير محدود',
        
        # الأخطاء - Errors
        'error_occurred': '❌ **حدث خطأ**\n\n{error}',
        'invalid_url': '❌ **رابط غير صحيح**\n\nأرسل رابط فيديو صالح',
        'private_story_unavailable': '🔒 **ستوري خاص (Private Story)**\n\n❌ لا يمكن تحميل الستوري لأنه خاص\n\n**الأسباب:**\n• هذا الحساب خاص (Private Account)\n• الستوري مخصص لأشخاص معينين فقط\n• يجب أن تكون متابعاً للحساب لمشاهدته\n\n💡 **الحل:**\n1. تأكد من متابعتك للحساب على Instagram\n2. حدّث ملفات cookies الخاصة بك\n3. جرّب ستوري من حساب عام (Public)',
        'user_not_found': '❌ **لم يتم العثور على المستخدم**\n\nتأكد من أن المستخدم قد استخدم البوت مسبقاً',
        'facebook_unavailable': '⚠️ **Facebook غير متاح حالياً**\n\nFacebook لديه مشاكل في استخراج البيانات.\n\n**السبب:** تغييرات في هيكل موقع Facebook\n\n**الحل:**\n• جرّب رابط آخر\n• انتظر تحديث yt-dlp\n• استخدم منصة أخرى (YouTube, Twitter)\n\nتم إرسال تنبيه للأدمن 🔔',
        'pinterest_unavailable': '⚠️ **Pinterest غير متاح حالياً**\n\nPinterest لديه مشاكل في سيرفراته.\n\nجرّب:\n• رابط آخر من Pinterest\n• منصة أخرى (YouTube, Twitter, TikTok)\n• المحاولة لاحقاً\n\nتم إرسال تنبيه للأدمن 🔔',
        'generic_error': '❌ **حدث خطأ**\n\n**المشكلة:** {error}...\n\nتم إرسال تنبيه للأدمن 🔔',
        
        # الإدارة - Administration
        'admin_only': '❌ هذا الأمر للمشرفين فقط!',
        'success': '✅ تم بنجاح!',
        'cancelled': '❌ تم الإلغاء',
        'broadcast_message_prefix': '📢 **رسالة من المطور:**',
        'direct_message_prefix': '✉️ **رسالة من المطور:**',
        
        # رسائل الاشتراك المفصلة
        'subscribe_now': '💎 اشترك الآن',
        'contact_developer': '📱 تواصل مع المطور',
        'binance_pay': '💰 Binance Pay',
        'visa_card': '💳 Visa',
        'mastercard': '💳 Mastercard',
        'telegram_contact': '📱 تواصل عبر Telegram',
        'back': '« رجوع',
        
        # رسائل التحميل المفصلة
        'start_download': '⏳ بدء التحميل...',
        'downloading_detailed': '📥 جاري التحميل...\n\n📊 {percent}%\n💾 {current} / {total} MB\n🚀 {speed} MB/s\n⏳ {eta}s',
        'uploading_detailed': '📤 جاري الرفع...\n\n📊 {percent}%\n💾 {current} / {total} MB\n🚀 {speed} MB/s\n⏳ {eta}s',
        'video_downloaded': '✅ تم التحميل! جاري الرفع...',
        
        # دعم المطور عبر Binance
        'support_dev_binance': '💰 دعم المطور عبر Binance',
        'binance_pay_id': '💳 Binance Pay ID: {binance_id}',
        
        # Payment screens
        'payment_binance_title': '💳 الدفع عبر Binance Pay',
        'payment_amount': '💰 المبلغ: $10',
        'payment_binance_steps': 'الخطوات:\n1. افتح تطبيق Binance\n2. اذهب إلى Binance Pay\n3. أرسل $10 إلى ID: {binance_id}\n4. التقط صورة للدفعة (screenshot)\n5. أرسل الصورة هنا\n\n✅ بعد إرسال الصورة، سيتم مراجعة دفعتك وتفعيل الاشتراك',
        'payment_visa_title': '💳 الدفع عبر Visa',
        'payment_visa_instructions': 'للدفع عبر Visa، تواصل مع المطور:\n👤 @{support_username}\n\nسيتم إرشادك لإكمال عملية الدفع.',
        'payment_mastercard_title': '💳 الدفع عبر Mastercard',
        'payment_mastercard_instructions': 'للدفع عبر Mastercard، تواصل مع المطور:\n👤 @{support_username}\n\nسيتم إرشادك لإكمال عملية الدفع.',
        'video_label': '🎬 فيديو',
        'audio_label': '🎵 صوت',
        'choose_payment_method': 'اختر طريقة الدفع:',
        
        # Queue System
        'queue_rate_limit': '⏳ **انتظر قليلاً!**\n\nيجب الانتظار {seconds} ثانية قبل إرسال رابط آخر.\n\n💡 يمكنك إرسال رابط آخر بعد {seconds} ثواني.',
        'queue_position': '📋 **تم إضافة الرابط للطابور**\n\n⏱️ **موقعك:** {position} في الطابور\n⚙️ جاري معالجة الفيديو الأول...\n\nانتظر حتى يكتمل التحميل الحالي 🔄',
        'queue_processing_current': '⚙️ **جاري معالجة طلبك...**\n\n📥 يتم الآن تحميل الفيديو الحالي\n⏳ انتظر حتى يكتمل التحميل\n\n💡 سيتم معالجة طلبك التالي تلقائياً',
        'queue_next_download': '🔄 **بدء التحميل التالي...**\n\n📋 يوجد {remaining} فيديو في الطابور',
        
        # Unsupported Media
        'unsupported_media_photo': '📷 البوت لا يدعم تحميل الصور حالياً.\n\nℹ️ إذا كنت تريد الدفع، اضغط /start ثم اختر الاشتراك.',
        'unsupported_media_video': '🎥 البوت لا يدعم رفع الفيديوهات مباشرة.\n\n✅ لتحميل فيديو، أرسل رابط الفيديو من:\n• Facebook\n• Instagram\n• TikTok\n• YouTube\n• وأكثر...',
        'unsupported_media_general': '📎 البوت يعمل مع روابط الفيديوهات فقط.\n\n✅ أرسل رابط فيديو من أي منصة مدعومة.',
        
        # Story Download
        'story_extraction_failed': '⚠️ لا يمكن استخراج معلومات الستوري\n\n🔄 سأحاول التحميل المباشر...',
        'story_expired': '⏰ **الستوري منتهي الصلاحية**\n\nالستوري حُذف أو انتهت صلاحيته (24 ساعة)\n\n💡 جرّب ستوري آخر من نفس الحساب',
        'story_cookies_missing': '🍪 **Cookies مفقودة**\n\nتحميل الستوري يتطلب Instagram cookies\n\nتواصل مع المطور لإضافتها',
        'facebook_story_not_supported': '❌ **ستوري فيسبوك غير مدعوم حالياً**\n\n⚠️ للأسف، تحميل ستوري فيسبوك غير متاح بسبب قيود تقنية من فيسبوك.\n\n💡 **البدائل المتاحة:**\n• يمكنك تحميل فيديوهات فيسبوك العادية\n• Reels فيسبوك\n• منشورات الفيديو\n\n🔮 ربما في المستقبل سيتم دعم هذه الميزة!',
        'instagram_private_story': '🔒 **ستوري خاص - غير متاح**\n\n❌ لا يمكن تحميل ستوري انستقرام الخاص\n\n**يمكنك تحميل:**\n✅ ستوري من الحسابات العامة (Public)\n✅ منشورات انستقرام\n✅ Reels\n\n💡 **ملاحظة:** فقط الستوري من الحسابات العامة يمكن تحميله',
        
        # Adult Content Blocking
        'adult_content_blocked': '🚫 **محتوى محظور**\n\n❌ لا يمكن التحميل من هذا الموقع\n\n**السبب:** هذا الموقع من مواقع المحتوى الإباحي المحظورة\n\n💡 **ملاحظة:** يمكنك استخدام البوت لتحميل المحتوى العادي من المنصات المدعومة:\n• YouTube\n• Facebook\n• Instagram\n• TikTok\n• وغيرها...',
        
        # Custom Blocked URLs Management
        'manage_blocked_urls': '🔗 إدارة الروابط المحظورة',
        'blocked_urls_list': '📋 **قائمة الروابط المحظورة المخصصة**\n\n{list}\n\n💡 يمكنك إضافة نطاقات (مثل: example.com) أو روابط كاملة',
        'no_blocked_urls': '📋 **لا توجد روابط محظورة مخصصة**\n\nلم تقم بإضافة أي روابط للحظر بعد',
        'add_blocked_url': '➕ إضافة رابط للحظر',
        'send_url_to_block': '📝 **أرسل الرابط أو النطاق للحظر**\n\n**أمثلة:**\n• example.com\n• badsite.net\n• https://spam.com\n\n⚠️ سيتم حظر أي رابط يحتوي على هذا النص',
        'url_blocked_success': '✅ تمت إضافة الرابط للقائمة المحظورة!\n\n🔗 {url}\n\nالآن لن يتمكن أي مستخدم من التحميل من هذا الموقع',
        'url_blocked_error': '❌ خطأ في إضافة الرابط\n\nقد يكون الرابط موجود مسبقاً',
        'url_removed_success': '✅ تمت إزالة الرابط من القائمة!',
        'url_removed_error': '❌ خطأ في إزالة الرابط',
        
        # Group Feature - ميزة المجموعات
        'btn_add_to_group': '➕ أضف البوت لمجموعتك',
        'group_settings_title': '⚙️ **إعدادات البوت في المجموعة**',
        'group_who_can_use': '👤 من يستخدم البوت؟',
        'group_admins_only': '👑 الأدمن فقط',
        'group_everyone': '👥 الجميع',
        'group_settings_saved': '✅ تم حفظ الإعدادات!',
        'group_not_admin': '❌ هذا الأمر للأدمن فقط!',
        'group_download_not_allowed': '❌ التحميل متاح للأدمن فقط في هذه المجموعة',
        'group_current_setting': '📌 الإعداد الحالي: {setting}',
        
        # إعدادات المجموعة المتقدمة - Advanced Group Settings
        'grp_settings_header': '⚙️ **إعدادات البوت في المجموعة**\n\nاختر الإعداد الذي تريد تغييره:',
        'grp_who_uses': '👤 **من يستخدم البوت:**',
        'grp_auto_delete': '🗑️ **حذف تلقائي:**',
        'grp_quiet_mode': '🔕 **الوضع الهادئ:**',
        'grp_max_duration': '⏰ **حد المدة:**',
        'grp_max_size': '📦 **حد الحجم:**',
        'grp_btn_who': '👤 من يستخدم البوت',
        'grp_btn_delete': '🗑️ حذف تلقائي',
        'grp_btn_quiet': '🔕 الوضع الهادئ',
        'grp_btn_duration': '⏰ حد المدة',
        'grp_btn_size': '📦 حد الحجم',
        'grp_btn_close': '❌ إغلاق',
        'grp_btn_back': '🔙 رجوع',
        'grp_admins_only_current': '👑 الأدمن فقط',
        'grp_everyone_current': '👥 الجميع',
        'grp_disabled': '❌ معطل',
        'grp_enabled': '✅ مفعل',
        'grp_seconds': 'ث',
        'grp_minutes': 'دقيقة',
        'grp_no_limit': 'بلا حد',
        'grp_who_title': '👤 **من يمكنه استخدام البوت؟**\n\nاختر من يمكنه تحميل الفيديوهات في هذه المجموعة:',
        'grp_delete_title': '🗑️ **حذف رسائل البوت تلقائياً**\n\nسيتم حذف رسائل البوت بعد الوقت المحدد.\nمفيد للحفاظ على نظافة المجموعة:',
        'grp_duration_title': '⏰ **الحد الأقصى لمدة الفيديو**\n\nلن يتم تحميل فيديوهات أطول من المدة المحددة:',
        'grp_size_title': '📦 **الحد الأقصى لحجم الملف**\n\nلن يتم تحميل ملفات أكبر من الحجم المحدد:',
        
        # تعليمات إضافة البوت للمجموعة
        'add_bot_instructions': '''📱 **كيفية إضافة البوت لمجموعتك:**

**الخطوة 1️⃣** اضغط على الزر أدناه
**الخطوة 2️⃣** اختر المجموعة التي تريد إضافة البوت إليها
**الخطوة 3️⃣** اضغط "إضافة" أو "Add"

**بعد الإضافة:**
• البوت سيرسل رسالة ترحيب
• اضغط على زر "⚙️ إعدادات البوت" لضبط الإعدادات
• أو أرسل /settings في المجموعة

**كيف يعمل البوت في المجموعة:**
• أرسل أي رابط فيديو مباشرة
• البوت سيحمّل الفيديو تلقائياً
• بدون أوامر، فقط الرابط!

💡 **ملاحظة:** يجب أن تكون أدمن لتغيير الإعدادات''',
        
        # خيارات حذف الرابط
        'grp_delete_link': '🔗 حذف الرابط',
        'grp_delete_link_enabled': '🔗 حذف الرابط: ✅',
        'grp_delete_link_disabled': '🔗 حذف الرابط: ❌',
        'grp_custom_time': '⏱️ وقت مخصص',
        'grp_enter_custom_time': '⏱️ **أدخل وقت الحذف (بالثواني)**\n\nأرسل رقم من 5 إلى 3600 ثانية\n\nمثال: 45',
        'grp_custom_time_set': '✅ تم ضبط وقت الحذف على {seconds} ثانية',
        'grp_invalid_time': '❌ رقم غير صحيح! أدخل رقم من 5 إلى 3600',
        
        # أزرار القوائم الفرعية
        'grp_btn_admin_only': '👑 الأدمن فقط',
        'grp_btn_everyone': '👥 الجميع',
        'grp_btn_disabled': 'معطل',
        'grp_btn_30s': '30ث',
        'grp_btn_60s': '60ث',
        'grp_btn_120s': '120ث',
        'grp_btn_5min': '5 دقائق',
        'grp_btn_10min': '10 دقائق',
        'grp_btn_15min': '15 دقيقة',
        'grp_btn_30min': '30 دقيقة',
        'grp_btn_60min': '60 دقيقة',
        'grp_btn_120min': '120 دقيقة',
        'grp_btn_no_limit': 'بلا حد',
        'grp_btn_2gb_max': '2 GB (الحد الأقصى)',
        'grp_saved': '✅ تم الحفظ!',
        'grp_closed': '✅ تم الإغلاق',
    },
    
    'en': {
        # Basic Messages
        'welcome': '👋 Welcome to the ultimate download bot!\n\n🚀 I can download from all major platforms:\n- YouTube (up to 4 hours)\n- Facebook\n- Instagram (photos, videos, public stories)\n- TikTok\n- Snapchat (stories)\n- Pinterest\n- X (formerly Twitter)\n- Reddit\n\n📌 Important note:\nI can download Instagram story photos and videos, public only.\n\n🎬 Bot features:\n• Fast downloading\n• High quality Full HD\n• Upload support up to 2GB\n• Download YouTube videos up to 4 hours\n• Save videos as MP4\n\n📥 *Just send the link and the bot handles everything!*',
        'choose_language': '🌍 **اختر لغتك**\nChoose Your Language',
        'language_set': '✅ Language set to: English 🇺🇸',
        'language_changed': '✅ Language changed to English 🇺🇸',
        
        # Buttons
        'btn_cookies': '🍪 Cookies',
        'btn_daily_report': '📊 Daily Report',
        'btn_errors': '🔔 Errors',
        'btn_subscription': '💎 Subscription Settings',
        'btn_change_language': '🌍 Change Language',
        'btn_my_subscription': '💎 My Subscription',
        
        # Download
        'processing': '⏳ **Processing...**',
        'start_downloading': '📥 **Downloading...**',
        'upload_started': '⬆️ Uploading...',
        'download_failed': '❌ **Download Failed**',
        'downloading': '📥 ⏬ Downloading...\n📊 {percent}%\n\n💾 {current_mb} / {total_mb} MB\n🚀 {speed_mb} MB/s\n⏳ {eta}s\n\n{progress_bar}',
        'uploading': '📤 ⏫ Uploading...\n📊 {percent}%\n\n💾 {current_mb} / {total_mb} MB\n🚀 {speed_mb} MB/s\n⏳ {eta}s\n\n{progress_bar}',
        'choose_quality': '📺 **Choose Quality:**\n\n🎬 {title}\n⏱️ {duration}',
        'quality_best': '📺 1080p',
        'quality_medium': '📱 720p',
        'quality_audio': '🎵 MP3',
        
        # Subscription
        'subscription_required': '⚠️ **Subscription Required**\n\n🎬 **Video:** {title}\n⏱️ **Duration:** {duration} minutes\n🔒 **Free Limit:** {max_duration} minutes',
        'subscription_benefits': '💎 **Get Subscription:**\n• Unlimited video downloads\n• Priority downloads\n• Support developer',
        'subscription_status': '💎 **Your Subscription is Active**\n\n📅 **Expires on:** {end_date}\n\n⏳ **Time Remaining:**\n• {days} days\n• {hours} hours',
        'not_subscribed': '❌ **No Active Subscription**\n\nSubscribe now to get unlimited features!',
        'subscription_upgraded': '🎉 **You\'ve been upgraded to Premium!**\n\n💎 You can now download unlimited videos without duration limits.\n📅 **Subscription Duration:** {days} days\n\nEnjoy the service! ✨',
        'subscription_activated': '🎉 **Your subscription has been activated!**\n\nYou can now download unlimited videos without duration limits.\nEnjoy the service! 💎',
        'subscription_deactivated': '⚠️ **Your subscription has been cancelled**\n\nFor more information, contact the developer.',
        'daily_limit_exceeded': '⚠️ **Daily Limit Exceeded**\n\n🔁 **Allowed Limit:** {limit} times per day\n📊 **Your Downloads Today:** {count} times',
        'downloads_remaining': '✅ **Download Successful!**\n\n📊 **You have:** {remaining} downloads remaining today',
        'unlimited_downloads': '♾️ Unlimited',
        
        # Errors
        'error_occurred': '❌ **An Error Occurred**\n\n{error}',
        'invalid_url': '❌ **Invalid URL**\n\nPlease send a valid video link',
        'private_story_unavailable': '🔒 **Private Story**\n\n❌ Cannot download this story because it\'s private\n\n**Reasons:**\n• This is a private account\n• Story is shared with specific people only\n• You must be following the account to view it\n\n💡 **Solution:**\n1. Make sure you follow the account on Instagram\n2. Update your cookies file\n3. Try a story from a public account',
        'user_not_found': '❌ **User Not Found**\n\nMake sure the user has used the bot before',
        'facebook_unavailable': '⚠️ **Facebook Currently Unavailable**\n\nFacebook has issues extracting data.\n\n**Reason:** Changes in Facebook\'s website structure\n\n**Solution:**\n• Try another link\n• Wait for yt-dlp update\n• Use another platform (YouTube, Twitter)\n\nAdmin has been notified 🔔',
        'pinterest_unavailable': '⚠️ **Pinterest Currently Unavailable**\n\nPinterest is experiencing server issues.\n\nTry:\n• Another Pinterest link\n• Another platform (YouTube, Twitter, TikTok)\n• Try again later\n\nAdmin has been notified 🔔',
        'generic_error': '❌ **An Error Occurred**\n\n**Issue:** {error}...\n\nAdmin has been notified 🔔',
        
        # Administration
        'admin_only': '❌ This command is for admins only!',
        'success': '✅ Success!',
        'cancelled': '❌ Cancelled',
        'broadcast_message_prefix': '📢 **Message from Developer:**',
        'direct_message_prefix': '✉️ **Message from Developer:**',
        
        # Detailed subscription messages
        'subscribe_now': '💎 Subscribe Now',
        'contact_developer': '📱 Contact Developer',
        'binance_pay': '💰 Binance Pay',
        'visa_card': '💳 Visa',
        'mastercard': '💳 Mastercard',
        'telegram_contact': '📱 Contact via Telegram',
        'back': '« Back',
        
        # Detailed download messages
        'start_download': '⏳ Starting download...',
        'downloading_detailed': '📥 Downloading...\n\n📊 {percent}%\n💾 {current} / {total} MB\n🚀 {speed} MB/s\n⏳ {eta}s',
        'uploading_detailed': '📤 Uploading...\n\n📊 {percent}%\n💾 {current} / {total} MB\n🚀 {speed} MB/s\n⏳ {eta}s',
        'video_downloaded': '✅ Downloaded! Uploading...',
        
        # Support developer via Binance
        'support_dev_binance': '💰 Support Developer via Binance',
        'binance_pay_id': '💳 Binance Pay ID: {binance_id}',
        
        # Payment screens
        'payment_binance_title': '💳 Pay via Binance Pay',
        'payment_amount': '💰 Amount: $10',
        'payment_binance_steps': 'Steps:\n1. Open Binance app\n2. Go to Binance Pay\n3. Send $10 to ID: {binance_id}\n4. Take a screenshot of the payment\n5. Send the screenshot here\n\n✅ After sending the screenshot, your payment will be reviewed and subscription activated',
        'payment_visa_title': '💳 Pay via Visa',
        'payment_visa_instructions': 'To pay via Visa, contact the developer:\n👤 @{support_username}\n\nYou will be guided to complete the payment.',
        'payment_mastercard_title': '💳 Pay via Mastercard',
        'payment_mastercard_instructions': 'To pay via Mastercard, contact the developer:\n👤 @{support_username}\n\nYou will be guided to complete the payment.',
        'video_label': '🎬 Video',
        'audio_label': '🎵 Audio',
        'choose_payment_method': 'Choose payment method:',
        
        # Queue System
        'queue_rate_limit': '⏳ **Please wait!**\n\nYou must wait {seconds} seconds before sending another link.\n\n💡 You can send another link in {seconds} seconds.',
        'queue_position': '📋 **Link added to queue**\n\n⏱️ **Your position:** {position} in queue\n⚙️ Processing first video...\n\nPlease wait for current download to complete 🔄',
        'queue_processing_current': '⚙️ **Processing your request...**\n\n📥 Currently downloading video\n⏳ Please wait for download to complete\n\n💡 Your next request will be processed automatically',
        'queue_next_download': '🔄 **Starting next download...**\n\n📋 {remaining} video(s) remaining in queue',
        
        # Unsupported Media
        'unsupported_media_photo': '📷 Bot does not support photo uploads currently.\n\nℹ️ If you want to subscribe, press /start then choose subscription.',
        'unsupported_media_video': '🎥 Bot does not support direct video uploads.\n\n✅ To download a video, send a video link from:\n• Facebook\n• Instagram\n• TikTok\n• YouTube\n• and more...',
        'unsupported_media_general': '📎 Bot works with video links only.\n\n✅ Send a video link from any supported platform.',
        
        # Story Download
        'story_extraction_failed': '⚠️ Cannot extract story information\n\n🔄 Will try direct download...',
        'story_expired': '⏰ **Story Expired**\n\nThe story was deleted or expired (24 hours)\n\n💡 Try another story from the same account',
        'story_cookies_missing': '🍪 **Cookies Missing**\n\nStory download requires Instagram cookies\n\nContact developer to add them',
        'facebook_story_not_supported': '❌ **Facebook Stories Not Supported**\n\n⚠️ Unfortunately, Facebook story download is not available due to technical restrictions from Facebook.\n\n💡 **Available Alternatives:**\n• Regular Facebook videos\n• Facebook Reels\n• Video posts\n\n🔮 Maybe this feature will be supported in the future!',
        'instagram_private_story': '🔒 **Private Story - Not Available**\n\n❌ Cannot download private Instagram stories\n\n**You can download:**\n✅ Stories from public accounts\n✅ Instagram posts\n✅ Reels\n\n💡 **Note:** Only stories from public accounts can be downloaded',
        
        # Adult Content Blocking
        'adult_content_blocked': '🚫 **Content Blocked**\n\n❌ Cannot download from this website\n\n**Reason:** This is a blocked adult content website\n\n💡 **Note:** You can use the bot to download regular content from supported platforms:\n• YouTube\n• Facebook\n• Instagram\n• TikTok\n• and more...',
        
        # Custom Blocked URLs Management
        'manage_blocked_urls': '🔗 Manage Blocked URLs',
        'blocked_urls_list': '📋 **Custom Blocked URLs List**\n\n{list}\n\n💡 You can add domains (e.g.: example.com) or full URLs',
        'no_blocked_urls': '📋 **No Custom Blocked URLs**\n\nYou haven\'t added any URLs to block yet',
        'add_blocked_url': '➕ Add URL to Block',
        'send_url_to_block': '📝 **Send URL or domain to block**\n\n**Examples:**\n• example.com\n• badsite.net\n• https://spam.com\n\n⚠️ Any URL containing this text will be blocked',
        'url_blocked_success': '✅ URL added to blocked list!\n\n🔗 {url}\n\nNo user can download from this site now',
        'url_blocked_error': '❌ Error adding URL\n\nURL may already exist',
        'url_removed_success': '✅ URL removed from list!',
        'url_removed_error': '❌ Error removing URL',
        
        # Group Feature
        'btn_add_to_group': '➕ Add Bot to Your Group',
        'group_settings_title': '⚙️ **Bot Settings in Group**',
        'group_who_can_use': '👤 Who can use the bot?',
        'group_admins_only': '👑 Admins Only',
        'group_everyone': '👥 Everyone',
        'group_settings_saved': '✅ Settings Saved!',
        'group_not_admin': '❌ This command is for admins only!',
        'group_download_not_allowed': '❌ Download is available for admins only in this group',
        'group_current_setting': '📌 Current setting: {setting}',
        
        # Advanced Group Settings
        'grp_settings_header': '⚙️ **Bot Settings in Group**\n\nChoose the setting you want to change:',
        'grp_who_uses': '👤 **Who uses the bot:**',
        'grp_auto_delete': '🗑️ **Auto delete:**',
        'grp_quiet_mode': '🔕 **Quiet mode:**',
        'grp_max_duration': '⏰ **Max duration:**',
        'grp_max_size': '📦 **Max size:**',
        'grp_btn_who': '👤 Who uses bot',
        'grp_btn_delete': '🗑️ Auto delete',
        'grp_btn_quiet': '🔕 Quiet mode',
        'grp_btn_duration': '⏰ Max duration',
        'grp_btn_size': '📦 Max size',
        'grp_btn_close': '❌ Close',
        'grp_btn_back': '🔙 Back',
        'grp_admins_only_current': '👑 Admins Only',
        'grp_everyone_current': '👥 Everyone',
        'grp_disabled': '❌ Disabled',
        'grp_enabled': '✅ Enabled',
        'grp_seconds': 's',
        'grp_minutes': 'min',
        'grp_no_limit': 'No limit',
        'grp_who_title': '👤 **Who can use the bot?**\n\nChoose who can download videos in this group:',
        'grp_delete_title': '🗑️ **Auto-delete bot messages**\n\nBot messages will be deleted after the specified time.\nUseful to keep the group clean:',
        'grp_duration_title': '⏰ **Maximum video duration**\n\nVideos longer than the specified duration will not be downloaded:',
        'grp_size_title': '📦 **Maximum file size**\n\nFiles larger than the specified size will not be downloaded:',
        
        # Add bot instructions
        'add_bot_instructions': '''📱 **How to add the bot to your group:**

**Step 1️⃣** Press the button below
**Step 2️⃣** Choose the group you want to add the bot to
**Step 3️⃣** Press "Add"

**After adding:**
• The bot will send a welcome message
• Press "⚙️ Bot Settings" to configure settings
• Or send /settings in the group

**How the bot works in groups:**
• Send any video link directly
• The bot will download the video automatically
• No commands needed, just the link!

💡 **Note:** You must be an admin to change settings''',
        
        # Delete link options
        'grp_delete_link': '🔗 Delete Link',
        'grp_delete_link_enabled': '🔗 Delete Link: ✅',
        'grp_delete_link_disabled': '🔗 Delete Link: ❌',
        'grp_custom_time': '⏱️ Custom Time',
        'grp_enter_custom_time': '⏱️ **Enter delete time (in seconds)**\n\nSend a number from 5 to 3600 seconds\n\nExample: 45',
        'grp_custom_time_set': '✅ Delete time set to {seconds} seconds',
        'grp_invalid_time': '❌ Invalid number! Enter a number from 5 to 3600',
        
        # Submenu buttons
        'grp_btn_admin_only': '👑 Admins Only',
        'grp_btn_everyone': '👥 Everyone',
        'grp_btn_disabled': 'Disabled',
        'grp_btn_30s': '30s',
        'grp_btn_60s': '60s',
        'grp_btn_120s': '120s',
        'grp_btn_5min': '5 min',
        'grp_btn_10min': '10 min',
        'grp_btn_15min': '15 min',
        'grp_btn_30min': '30 min',
        'grp_btn_60min': '60 min',
        'grp_btn_120min': '120 min',
        'grp_btn_no_limit': 'No limit',
        'grp_btn_2gb_max': '2 GB (Max)',
        'grp_saved': '✅ Saved!',
        'grp_closed': '✅ Closed',
    }
}

def t(key, lang='ar', **kwargs):
    """
    Get translated text
    
    Args:
        key: Translation key
        lang: Language code ('ar' or 'en')
        **kwargs: Format parameters
    
    Returns:
        Translated and formatted text
    """
    text = TRANSLATIONS.get(lang, TRANSLATIONS['ar']).get(key, key)
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    
    return text

def get_available_languages():
    """Get list of available language codes"""
    return list(TRANSLATIONS.keys())
