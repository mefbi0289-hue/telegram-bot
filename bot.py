import telebot
from telebot import types
from datetime import datetime, timedelta
import json
import os
import threading
import time

TOKEN = "8503624338:AAGjlZGjPFvLER3GtldjwdbCivKW_JAU9NQ"
bot = telebot.TeleBot(TOKEN)

# ---------- ادمین ----------
ADMINS = [8284529360]
REF_PERCENT = 0.05  # 5% پورسانت

# ---------- دیتابیس فایل ----------
DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # اضافه کردن فیلدهای جدید اگر وجود ندارند
            if "admin_sessions" not in data:
                data["admin_sessions"] = {}
            return data
    return {
        "balance": {},
        "users": [],
        "referrer": {},
        "referrals": {},
        "orders": {},
        "services": {},
        "transactions": [],
        "admin_stats": {
            "total_income": 0,
            "total_users": 0,
            "total_orders": 0,
            "broadcasts_sent": 0
        },
        "settings": {
            "welcome_bonus": 5000,
            "ref_bonus": 2000,  # تغییر به 2000 تومان برای هر دعوت
            "min_withdraw": 50000,
            "max_withdraw": 1000000
        },
        "admin_sessions": {}  # اضافه کردن session برای مدیریت
    }

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(DB, f, ensure_ascii=False, indent=2)

DB = load_db()

# ---------- پلن‌های اصلی ----------
PLANS = {
    "1m": "⚡ یک ماهه | معمولی",
    "3m": "🔥 سه ماهه | ویژه",
    "unl": "🚀 نامحدود | پرسرعت"
}

LISTS = {
    "1m": [
        ("5 𝐆❕20T | یک ماهه", 20000),
        ("10𝐆❕35T | یک ماهه", 35000),
        ("20𝐆❕70T | یک ماهه", 70000),
        ("50𝐆❕105T | یک ماهه", 105000),
        ("80𝐆❕155T | یک ماهه", 155000),
    ],
    "3m": [
        ("5 𝐆❕42T | سه ماهه", 42000),
        ("10𝐆❕50T | سه ماهه", 50000),
        ("20𝐆❕106T | سه ماهه", 106000),
        ("50𝐆❕150T | سه ماهه", 150000),
        ("80𝐆❕200T | سه ماهه", 200000),
    ],
    "unl": [
        ("👤 تک کاربره | 120T", 120000),
        ("👥 دو کاربره | 242T", 242000),
        ("👨‍👩‍👧‍👦 پنج کاربره | 560T", 560000),
    ]
}

# ---------- پلن تانل ----------
TUNNEL_PLANS = [
    ("🫟 10 گیگ (1 ماهه)", 80000),
    ("🫟 20 گیگ (1 ماهه)", 135000),
    ("🫟 50 گیگ (1 ماهه)", 268000),
]

# ---------- مدیریت session برای ادمین ----------
def set_admin_session(admin_id, action, data=None):
    """تنظیم session برای ادمین"""
    DB["admin_sessions"][str(admin_id)] = {"action": action, "data": data}
    save_db()

def get_admin_session(admin_id):
    """دریافت session ادمین"""
    return DB["admin_sessions"].get(str(admin_id))

def clear_admin_session(admin_id):
    """پاک کردن session ادمین"""
    if str(admin_id) in DB["admin_sessions"]:
        DB["admin_sessions"].pop(str(admin_id))
        save_db()

# ---------- تابع اطلاع‌رسانی خودکار ----------
def check_expired_services():
    """بررسی سرویس‌های منقضی شده"""
    while True:
        try:
            current_time = datetime.now().timestamp()
            expired_users = []
            
            for user_id, services in list(DB.get("services", {}).items()):
                user_services = []
                for service in services:
                    if service.get("expiry_date", 0) > current_time:
                        user_services.append(service)
                    else:
                        expired_users.append(user_id)
                
                if user_services:
                    DB["services"][user_id] = user_services
                else:
                    DB["services"].pop(user_id, None)
            
            for user_id in expired_users:
                try:
                    bot.send_message(
                        user_id,
                        "⏰ **اعتبار سرویس شما به پایان رسید**\n\nبرای تمدید سرویس به بخش خرید مراجعه کنید."
                    )
                except:
                    pass
            
            save_db()
            time.sleep(3600)
        except Exception as e:
            print(f"Error in check_expired_services: {e}")
            time.sleep(300)

service_checker = threading.Thread(target=check_expired_services, daemon=True)
service_checker.start()

# ---------- تابع‌های کمکی ----------
def is_admin(user_id):
    return user_id in ADMINS

def add_service(user_id, service_name, days):
    """اضافه کردن سرویس به کاربر"""
    expiry_date = (datetime.now() + timedelta(days=days)).timestamp()
    service_data = {
        "name": service_name,
        "purchase_date": datetime.now().timestamp(),
        "expiry_date": expiry_date,
        "days": days
    }
    
    if str(user_id) not in DB["services"]:
        DB["services"][str(user_id)] = []
    
    DB["services"][str(user_id)].append(service_data)
    save_db()
    
    try:
        config_example = f"🔐 **کانفیگ سرویس شما فعال شد!**\n\n📝 نام سرویس: {service_name}\n⏰ مدت زمان: {days} روز\n📅 تاریخ فعالسازی: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
        bot.send_message(user_id, config_example)
    except:
        pass

def add_tunnel_service(user_id, tunnel_name, gigabytes, days):
    """اضافه کردن سرویس تانل به کاربر"""
    expiry_date = (datetime.now() + timedelta(days=days)).timestamp()
    service_data = {
        "name": tunnel_name,
        "type": "tunnel",
        "gigabytes": gigabytes,
        "purchase_date": datetime.now().timestamp(),
        "expiry_date": expiry_date,
        "days": days
    }
    
    if str(user_id) not in DB["services"]:
        DB["services"][str(user_id)] = []
    
    DB["services"][str(user_id)].append(service_data)
    save_db()
    
    try:
        config_example = f"🫟 **کانفیگ تانل شما فعال شد!**\n\n📝 نام سرویس: {tunnel_name}\n💾 حجم: {gigabytes} گیگ\n⏰ مدت زمان: {days} روز\n📅 تاریخ فعالسازی: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
        bot.send_message(user_id, config_example)
    except:
        pass

def log_transaction(user_id, amount, type_, description=""):
    """ثبت تراکنش"""
    transaction = {
        "user_id": user_id,
        "amount": amount,
        "type": type_,
        "description": description,
        "date": datetime.now().timestamp()
    }
    DB["transactions"].append(transaction)
    save_db()

def get_user_info(user_id):
    """دریافت اطلاعات کامل کاربر"""
    try:
        user_id_str = str(user_id)
        balance = DB["balance"].get(user_id_str, 0)
        services = DB["services"].get(user_id_str, [])
        referrals = len(DB["referrals"].get(user_id_str, []))
        
        # تاریخ عضویت
        join_date = "نامشخص"
        user_transactions = [t for t in DB["transactions"] if t["user_id"] == user_id]
        if user_transactions:
            first_transaction = min(user_transactions, key=lambda x: x["date"])
            join_date = datetime.fromtimestamp(first_transaction["date"]).strftime('%Y/%m/%d %H:%M')
        
        # خریدهای انجام شده
        total_spent = 0
        for trans in user_transactions:
            if trans["amount"] < 0:
                total_spent += abs(trans["amount"])
        
        # سرویس‌های فعال
        active_services = []
        for service in services:
            if service.get("expiry_date", 0) > datetime.now().timestamp():
                days_left = int((service["expiry_date"] - datetime.now().timestamp()) / 86400)
                active_services.append(f"{service.get('name', 'نامشخص')} ({days_left} روز)")
        
        info_text = f"""
👤 **اطلاعات کاربر**

🆔 **شناسه:** `{user_id}`
💰 **موجودی:** {balance:,} تومان
💸 **کل خریدها:** {total_spent:,} تومان
👥 **زیرمجموعه:** {referrals} نفر
📅 **تاریخ عضویت:** {join_date}
🎯 **سرویس‌های فعال:** {len(active_services)} مورد
"""
        
        if active_services:
            info_text += "\n📋 **لیست سرویس‌ها:**\n"
            for i, service in enumerate(active_services, 1):
                info_text += f"{i}. {service}\n"
        
        return info_text
    
    except Exception as e:
        return f"❌ خطا در دریافت اطلاعات: {str(e)}"

def create_main_keyboard(uid):
    """ایجاد کیبورد اصلی"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if is_admin(uid):
        kb.row("👑 پنل مدیریت")
    kb.row("🛍 خرید سرویس", "📊 وضعیت اشتراک‌ها")
    kb.row("💰 کیف پول", "📥 لینک دعوت")
    kb.row("🫟 خرید تانل", "📞 پشتیبانی")
    kb.row("❓ راهنما", "💬 ایدی عددی")
    return kb

def create_admin_keyboard():
    """ایجاد کیبورد مدیریت پیشرفته"""
    kb = types.InlineKeyboardMarkup(row_width=2)
    
    # ردیف اول - آمار و کاربران
    kb.row(
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_full_stats"),
        types.InlineKeyboardButton("👤 جستجوی کاربر", callback_data="admin_search_user")
    )
    
    # ردیف دوم - مدیریت مالی
    kb.row(
        types.InlineKeyboardButton("💰 مدیریت مالی", callback_data="admin_financial_menu"),
        types.InlineKeyboardButton("🎁 هدیه به کاربر", callback_data="admin_gift_user_menu")
    )
    
    # ردیف سوم - پیام همگانی و مدیریت
    kb.row(
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast_menu"),
        types.InlineKeyboardButton("📦 سفارشات در انتظار", callback_data="admin_pending_orders")
    )
    
    # ردیف چهارم - گزارشات و ابزارها
    kb.row(
        types.InlineKeyboardButton("📈 گزارشات مالی", callback_data="admin_financial_reports"),
        types.InlineKeyboardButton("🔧 تنظیمات ربات", callback_data="admin_settings")
    )
    
    # ردیف پنجم - مدیریت سرویس‌ها
    kb.row(
        types.InlineKeyboardButton("🎯 مدیریت سرویس‌ها", callback_data="admin_manage_services"),
        types.InlineKeyboardButton("📋 لاگ سیستم", callback_data="admin_system_logs")
    )
    
    # ردیف ششم - بازگشت
    kb.row(types.InlineKeyboardButton("🏠 برگشت به منوی اصلی", callback_data="admin_back_to_main"))
    
    return kb

# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    
    if uid not in DB["users"]:
        DB["users"].append(uid)
        DB["admin_stats"]["total_users"] += 1
        DB["referrals"][str(uid)] = []
        
        # هدیه عضویت
        welcome_bonus = DB["settings"]["welcome_bonus"]
        DB["balance"][str(uid)] = welcome_bonus
        log_transaction(uid, welcome_bonus, "هدیه عضویت", "عضویت در ربات")
        save_db()
    
    # اگر کاربر قبلاً عضو شده، فقط موجودی رو بروز کن
    if str(uid) not in DB["balance"]:
        DB["balance"][str(uid)] = 0
    
    # بررسی لینک دعوت
    args = m.text.split()
    if len(args) > 1:
        try:
            ref = int(args[1])
            if ref != uid and str(uid) not in DB["referrer"]:
                DB["referrer"][str(uid)] = ref
                DB["referrals"][str(ref)].append(uid)
                
                # هدیه دعوت (2000 تومان برای دعوت کننده)
                ref_bonus = DB["settings"]["ref_bonus"]
                DB["balance"][str(ref)] = DB["balance"].get(str(ref), 0) + ref_bonus
                log_transaction(ref, ref_bonus, "هدیه دعوت", f"از دعوت کاربر {uid}")
                
                save_db()
                
                # اطلاع به دعوت کننده
                try:
                    bot.send_message(
                        ref,
                        f"🎉 **کاربر جدید دعوت کردید!**\n\n👤 کاربر: {uid}\n💰 هدیه: {ref_bonus:,} تومان"
                    )
                except:
                    pass
        except:
            pass

    welcome_text = f"""
🚀 **خوش آمدید {m.from_user.first_name}!**

🎯 به VIP VPN STORE خوش آمدید!
✨ **ویژگی‌های ما:**
✅ سرعت نامحدود
✅ پینگ پایین
✅ پشتیبانی ۲۴ ساعته

💎 **هدیه ویژه:** {DB['settings']['welcome_bonus']:,} تومان اعتبار رایگان!

💰 **موجودی فعلی شما:** {DB['balance'].get(str(uid), 0):,} تومان

🔄 آپدیت: {datetime.now().strftime('%Y/%m/%d')}
    """

    bot.send_message(
        uid,
        welcome_text,
        reply_markup=create_main_keyboard(uid)  # تصحیح: reply_mup -> reply_markup
    )

# ---------- HANDLER برای پیام‌های ادمین ----------
@bot.message_handler(func=lambda m: m.from_user.id in ADMINS and str(m.from_user.id) in DB["admin_sessions"])
def handle_admin_messages(m):
    uid = m.from_user.id
    session = get_admin_session(uid)
    
    if not session:
        return
    
    action = session["action"]
    text = m.text.strip()
    
    try:
        if action == "search_user":
            # جستجوی کاربر
            try:
                user_id = int(text)
                user_info = get_user_info(user_id)
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("💰 افزایش موجودی", callback_data=f"admin_add_balance:{user_id}"),
                    types.InlineKeyboardButton("💸 کاهش موجودی", callback_data=f"admin_deduct_balance:{user_id}")
                )
                kb.add(
                    types.InlineKeyboardButton("🎯 افزودن سرویس", callback_data=f"admin_add_service:{user_id}"),
                    types.InlineKeyboardButton("📊 مشاهده تراکنش‌ها", callback_data=f"admin_view_transactions:{user_id}")
                )
                kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_main"))
                
                bot.send_message(uid, user_info, reply_markup=kb, parse_mode="Markdown")
                clear_admin_session(uid)
                
            except ValueError:
                bot.send_message(uid, "❌ شناسه کاربر باید عددی باشد!")
            except Exception as e:
                bot.send_message(uid, f"❌ خطا: {str(e)}")
                
        elif action == "gift_user":
            # هدیه به کاربر خاص
            lines = text.split('\n')
            if len(lines) < 2:
                bot.send_message(uid, "❌ فرمت اشتباه!\nمثال:\n`123456789\n50000`")
                return
            
            try:
                user_id = int(lines[0].strip())
                amount = int(lines[1].strip())
                
                if amount <= 0:
                    bot.send_message(uid, "❌ مبلغ باید بیشتر از صفر باشد!")
                    return
                
                # افزایش موجودی کاربر
                DB["balance"][str(user_id)] = DB["balance"].get(str(user_id), 0) + amount
                log_transaction(user_id, amount, "هدیه ادمین", f"توسط ادمین {uid}")
                save_db()
                
                # اطلاع به کاربر
                try:
                    bot.send_message(
                        user_id,
                        f"🎁 **هدیه ویژه از ادمین!**\n\n💰 مبلغ: {amount:,} تومان\n📝 پیام: هدیه از مدیریت"
                    )
                except:
                    pass
                
                bot.send_message(
                    uid,
                    f"✅ **هدیه با موفقیت ارسال شد**\n\n👤 کاربر: {user_id}\n💰 مبلغ: {amount:,} تومان\n💵 موجودی جدید: {DB['balance'][str(user_id)]:,} تومان"
                )
                clear_admin_session(uid)
                
            except ValueError:
                bot.send_message(uid, "❌ شناسه کاربر و مبلغ باید عددی باشند!")
            except Exception as e:
                bot.send_message(uid, f"❌ خطا: {str(e)}")
                
        elif action == "broadcast_text":
            # تایید و ارسال پیام همگانی
            message_text = text
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("✅ ارسال به همه", callback_data=f"admin_confirm_broadcast:{message_text}"),
                types.InlineKeyboardButton("❌ انصراف", callback_data="admin_broadcast_menu")
            )
            
            preview_text = f"""
📢 **پیش نمایش پیام همگانی**

📝 متن پیام:
{message_text}

👥 تعداد کاربران: {len(DB['users'])}
⏰ زمان ارسال: {datetime.now().strftime('%H:%M')}

آیا مطمئن هستید؟
            """
            
            bot.send_message(uid, preview_text, reply_markup=kb)
            clear_admin_session(uid)
            
        elif action == "gift_all":
            # هدیه به همه کاربران
            try:
                amount = int(text)
                if amount <= 0:
                    bot.send_message(uid, "❌ مبلغ باید بیشتر از صفر باشد!")
                    return
                
                # تایید عملیات
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("✅ تایید و ارسال", callback_data=f"admin_confirm_gift_all:{amount}"),
                    types.InlineKeyboardButton("❌ انصراف", callback_data="admin_financial_menu")
                )
                
                bot.send_message(
                    uid,
                    f"⚠️ **تایید عملیات هدیه به همه**\n\n💰 مبلغ: {amount:,} تومان\n👥 تعداد کاربران: {len(DB['users'])}\n💵 مجموع: {amount * len(DB['users']):,} تومان\n\nآیا مطمئن هستید؟",
                    reply_markup=kb
                )
                clear_admin_session(uid)
                
            except ValueError:
                bot.send_message(uid, "❌ مبلغ باید عددی باشد!")
            except Exception as e:
                bot.send_message(uid, f"❌ خطا: {str(e)}")
                
        elif action == "change_welcome_bonus":
            # تغییر هدیه عضویت
            try:
                new_amount = int(text)
                if new_amount < 0:
                    bot.send_message(uid, "❌ مبلغ نمی‌تواند منفی باشد!")
                    return
                
                DB["settings"]["welcome_bonus"] = new_amount
                save_db()
                
                bot.send_message(
                    uid,
                    f"✅ **هدیه عضویت تغییر کرد**\n\n💰 مبلغ جدید: {new_amount:,} تومان"
                )
                clear_admin_session(uid)
                
            except ValueError:
                bot.send_message(uid, "❌ مبلغ باید عددی باشد!")
            except Exception as e:
                bot.send_message(uid, f"❌ خطا: {str(e)}")
                
        elif action == "change_ref_bonus":
            # تغییر هدیه دعوت
            try:
                new_amount = int(text)
                if new_amount < 0:
                    bot.send_message(uid, "❌ مبلغ نمی‌تواند منفی باشد!")
                    return
                
                DB["settings"]["ref_bonus"] = new_amount
                save_db()
                
                bot.send_message(
                    uid,
                    f"✅ **هدیه دعوت تغییر کرد**\n\n💰 مبلغ جدید: {new_amount:,} تومان"
                )
                clear_admin_session(uid)
                
            except ValueError:
                bot.send_message(uid, "❌ مبلغ باید عددی باشد!")
            except Exception as e:
                bot.send_message(uid, f"❌ خطا: {str(e)}")
                
        elif action == "add_balance":
            # افزایش موجودی کاربر
            try:
                user_id = session.get("data")
                if not user_id:
                    bot.send_message(uid, "❌ خطا در دریافت اطلاعات کاربر")
                    clear_admin_session(uid)
                    return
                    
                amount = int(text)
                if amount <= 0:
                    bot.send_message(uid, "❌ مبلغ باید بیشتر از صفر باشد!")
                    return
                
                DB["balance"][str(user_id)] = DB["balance"].get(str(user_id), 0) + amount
                log_transaction(user_id, amount, "افزایش موجودی", f"توسط ادمین {uid}")
                save_db()
                
                # اطلاع به کاربر
                try:
                    bot.send_message(
                        user_id,
                        f"💰 **موجودی شما افزایش یافت!**\n\n💵 مبلغ: {amount:,} تومان\n📝 توسط: مدیریت"
                    )
                except:
                    pass
                
                bot.send_message(
                    uid,
                    f"✅ **موجودی کاربر افزایش یافت**\n\n👤 کاربر: {user_id}\n💰 مبلغ: {amount:,} تومان\n💵 موجودی جدید: {DB['balance'][str(user_id)]:,} تومان"
                )
                clear_admin_session(uid)
                
            except ValueError:
                bot.send_message(uid, "❌ مبلغ باید عددی باشد!")
            except Exception as e:
                bot.send_message(uid, f"❌ خطا: {str(e)}")
                clear_admin_session(uid)
    
    except Exception as e:
        bot.send_message(uid, f"❌ خطا در پردازش: {str(e)}")
        clear_admin_session(uid)

# ---------- پیام‌های کاربران ----------
@bot.message_handler(func=lambda m: True)
def msgs(m):
    uid = m.from_user.id
    text = m.text.strip()
    
    # اگر ادمین هست و session دارد، پیام را به handler ادمین بده
    if uid in ADMINS and str(uid) in DB["admin_sessions"]:
        return

    if text == "🛍 خرید سرویس":
        kb = types.InlineKeyboardMarkup(row_width=1)
        for k, v in PLANS.items():
            kb.add(types.InlineKeyboardButton(f"📦 {v}", callback_data=f"plan:{k}"))
        kb.add(types.InlineKeyboardButton("🔙 برگشت به منوی قبل", callback_data="back_to_main"))
        
        bot.send_message(
            uid,
            "🎯 **انتخاب پلن سرویس**\n\n💡 پلن‌های موجود:\n⚡ **یک ماهه** - مناسب تست\n🔥 **سه ماهه** - اقتصادی\n🚀 **نامحدود** - پرسرعت",
            reply_markup=kb
        )

    elif text == "📊 وضعیت اشتراک‌ها":
        services = DB["services"].get(str(uid), [])
        if not services:
            bot.send_message(
                uid,
                "❌ **سرویس فعالی ندارید!**\n\nبرای خرید سرویس به بخش 🛍 خرید سرویس مراجعه کنید."
            )
            return
        
        text_msg = "📋 **سرویس‌های فعال شما:**\n\n"
        for i, service in enumerate(services, 1):
            expiry_date = datetime.fromtimestamp(service["expiry_date"])
            remaining = expiry_date - datetime.now()
            days = remaining.days
            hours = remaining.seconds // 3600
            
            text_msg += f"{i}. **{service['name']}**\n"
            text_msg += f"   ⏰ انقضا: {expiry_date.strftime('%Y/%m/%d %H:%M')}\n"
            text_msg += f"   ⏳ باقی‌مانده: {days} روز و {hours} ساعت\n\n"
        
        bot.send_message(uid, text_msg, parse_mode="Markdown")

    elif text == "💰 کیف پول":
        balance = DB["balance"].get(str(uid), 0)
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("💳 شارژ حساب", callback_data="wallet_charge"),
            types.InlineKeyboardButton("📜 تاریخچه تراکنش‌ها", callback_data="wallet_history")
        )
        
        wallet_text = f"💰 **کیف پول شما**\n\n💵 **موجودی:** `{balance:,} تومان`"
        
        bot.send_message(uid, wallet_text, reply_markup=kb, parse_mode="Markdown")

    elif text == "📥 لینک دعوت":
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={uid}"
        referrals = len(DB["referrals"].get(str(uid), []))
        ref_bonus = DB["settings"]["ref_bonus"]
        total_ref_bonus = referrals * ref_bonus
        
        ref_text = f"""
📥 **سیستم بازاریابی**

🎯 **آمار شما:**
👥 زیرمجموعه: **{referrals} نفر**
💰 سود هر دعوت: **{ref_bonus:,} تومان**
💵 کل درآمد از دعوت: **{total_ref_bonus:,} تومان**
⭐ درصد پورسانت خرید: **{REF_PERCENT*100}%**

📊 **محاسبه سود:**
با دعوت **10 نفر** شما **{10 * ref_bonus:,} تومان** دریافت می‌کنید!
با دعوت **50 نفر** شما **{50 * ref_bonus:,} تومان** دریافت می‌کنید!

🔗 **لینک اختصاصی شما:**
`{link}`
        """
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📋 لیست زیرمجموعه‌ها", callback_data="ref_list"))
        
        bot.send_message(uid, ref_text, reply_markup=kb, parse_mode="Markdown")

    elif text == "📞 پشتیبانی":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🗣 گفتگوی آنلاین", url="tg://resolve?domain=HOUINP"),
            types.InlineKeyboardButton("📧 ایمیل پشتیبانی", callback_data="support_email")
        )
        
        support_text = """
🛠 **پشتیبانی VIP VPN**

⏰ **ساعات پاسخگویی:**
• ۹:۰۰ صبح تا ۱۲:۰۰ شب
• پشتیبانی ۷ روز هفته

📞 **روش‌های ارتباطی:**
1️⃣ **گفتگوی آنلاین** - پاسخ سریع
2️⃣ **ایمیل پشتیبانی** - پاسخ در کمتر از ۲ ساعت
        """
        
        bot.send_message(uid, support_text, reply_markup=kb)

    elif text == "❓ راهنما":
        help_text = """
❗ **آموزش اتصال به سرویس**

🎯 **مراحل اتصال:**
1️⃣ سرویس خریداری شده را کپی کنید
2️⃣ در برنامه مورد نظر ترجیحاً | V2Box, V2rayNG | پیست کنید
3️⃣ وی‌پی‌ان را فعال کنید

♨️ **توجه مهم:**
سرویس‌ها روی تمامی اپراتورها فعال هستند.

📍 **توجه:**
از پشتیبانی سوالاتی در رابطه با اپراتور ها و سیمکارت نپرسید.

⚠️ **نکات فنی:**
• از آخرین نسخه برنامه‌ها استفاده کنید
• در صورت قطعی، پروتکل را تغییر دهید

⏰ **توجه:**
بعد از واریز، سرویس مورد نظر حداقل تا ۳۰ ثانیه الی ۱ دقیقه بعد ارسال می‌گردد.

♦ **نکته مهم:**
از فرستادن هرگونه رسید فیک خود داری کنید و وقت ارزشمند خودتون رو تلف نکنید.
        """
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
        
        bot.send_message(uid, help_text, reply_markup=kb)

    elif text == "💬 ایدی عددی":
        user_info = f"""
👤 **اطلاعات حساب شما**

🆔 **شناسه عددی:**
```{uid}```

📛 **نام:** {m.from_user.first_name}
👤 **یوزرنیم:** @{m.from_user.username or "ندارد"}
💰 **موجودی:** {DB['balance'].get(str(uid), 0):,} تومان
        """
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📋 کپی شناسه", callback_data=f"copy_id:{uid}"))
        
        bot.send_message(uid, user_info, parse_mode="Markdown", reply_markup=kb)

    elif text == "🫟 خرید تانل":
        kb = types.InlineKeyboardMarkup(row_width=1)
        for plan_name, price in TUNNEL_PLANS:
            plan_name_clean = plan_name.replace("🫟 ", "").split(" ")[0]
            kb.add(types.InlineKeyboardButton(
                f"{plan_name} - {price:,} تومان",
                callback_data=f"tunnel_plan:{plan_name_clean}:{price}"
            ))
        kb.add(types.InlineKeyboardButton("🔙 برگشت به منوی قبل", callback_data="back_to_main"))
        
        tunnel_text = """
🫟 **خرید تانل اختصاصی**

🎯 **ویژگی‌های تانل:**
✅ IP اختصاصی
✅ پهنای باند بالا
✅ پینگ بسیار پایین

📊 **پلن‌های موجود:**
🫟 10 گیگ - مناسب تست
🫟 20 گیگ - اقتصادی
🫟 50 گیگ - حرفه‌ای
        """
        
        bot.send_message(uid, tunnel_text, reply_markup=kb)

    elif text == "👑 پنل مدیریت" and is_admin(uid):
        admin_text = """
👑 **پنل مدیریت پیشرفته**

🔧 **دسترسی کامل به تمام امکانات ربات:**
✅ مدیریت کاربران
✅ مدیریت مالی
✅ پیام همگانی
✅ گزارشات کامل
✅ تنظیمات ربات

🎯 **انتخاب گزینه مورد نظر:**
        """
        
        bot.send_message(uid, admin_text, reply_markup=create_admin_keyboard())

# ---------- CALLBACK HANDLER اصلی ----------
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid = c.from_user.id
    data = c.data
    
    try:
        if data == "back_to_main":
            bot.edit_message_text(
                "✅ به منوی اصلی بازگشتید",
                uid, c.message.message_id
            )
            time.sleep(1)
            bot.delete_message(uid, c.message.message_id)
            bot.send_message(
                uid,
                "🎯 منوی اصلی | VPN STORE",
                reply_markup=create_main_keyboard(uid)
            )
            
        elif data == "back_to_plans":
            kb = types.InlineKeyboardMarkup(row_width=1)
            for k, v in PLANS.items():
                kb.add(types.InlineKeyboardButton(f"📦 {v}", callback_data=f"plan:{k}"))
            kb.add(types.InlineKeyboardButton("🔙 برگشت به منوی قبل", callback_data="back_to_main"))
            
            bot.edit_message_text(
                "🎯 **انتخاب پلن سرویس**\n\n💡 پلن‌های موجود:\n⚡ **یک ماهه** - مناسب تست\n🔥 **سه ماهه** - اقتصادی\n🚀 **نامحدود** - پرسرعت",
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data.startswith("plan:"):
            p = data.split(":")[1]
            kb = types.InlineKeyboardMarkup(row_width=1)
            
            for i, (title, price) in enumerate(LISTS[p]):
                price_text = f"{price:,}"
                kb.add(types.InlineKeyboardButton(
                    f"{title} - {price_text} تومان",
                    callback_data=f"buy:{p}:{i}:{price}"
                ))
            
            kb.add(types.InlineKeyboardButton("🔙 برگشت", callback_data="back_to_plans"))
            
            plan_info = {
                "1m": "⚡ **پلن یک ماهه** - مناسب تست\n⏰ مدت: 30 روز",
                "3m": "🔥 **پلن سه ماهه** - اقتصادی\n⏰ مدت: 90 روز",
                "unl": "🚀 **پلن نامحدود** - پرسرعت\n⏰ مدت: 30 روز"
            }
            
            bot.edit_message_text(
                f"{plan_info.get(p, '')}\n\n🎯 **انتخاب سرویس:**",
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data.startswith("buy:"):
            _, p, i, price = data.split(":")
            i = int(i)
            price = int(price)
            title = LISTS[p][i][0]
            days = 30 if p in ["1m", "unl"] else 90
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton(f"💳 پرداخت با موجودی", 
                                         callback_data=f"pay_wallet:{p}:{i}:{price}"),
                types.InlineKeyboardButton("🏦 پرداخت کارت به کارت", 
                                         callback_data=f"pay_card:{p}:{i}:{price}")
            )
            kb.add(
                types.InlineKeyboardButton("🔙 انصراف", callback_data=f"plan:{p}")
            )
            
            bot.edit_message_text(
                f"🛒 **جزئیات خرید**\n\n📦 سرویس: {title}\n💰 مبلغ: **{price:,}** تومان\n⏰ مدت: {days} روز",
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data.startswith("pay_wallet:"):
            _, p, i, price = data.split(":")
            price = int(price)
            
            balance = DB["balance"].get(str(uid), 0)
            if balance >= price:
                DB["balance"][str(uid)] = balance - price
                DB["admin_stats"]["total_income"] += price
                DB["admin_stats"]["total_orders"] += 1
                
                title = LISTS[p][int(i)][0]
                days = 30 if p in ["1m", "unl"] else 90
                add_service(uid, title, days)
                
                log_transaction(uid, -price, "خرید سرویس", title)
                
                if str(uid) in DB["referrer"]:
                    ref = DB["referrer"][str(uid)]
                    bonus = int(price * REF_PERCENT)
                    DB["balance"][str(ref)] = DB["balance"].get(str(ref), 0) + bonus
                    log_transaction(ref, bonus, "پورسانت", f"از خرید کاربر {uid}")
                
                save_db()
                
                bot.edit_message_text(
                    f"✅ **خرید موفق!**\n\n📦 سرویس: {title}\n💰 مبلغ: {price:,} تومان\n⏰ اعتبار: {days} روز\n\nسرویس به حساب شما اضافه شد.",
                    uid, c.message.message_id
                )
            else:
                bot.answer_callback_query(
                    c.id,
                    f"❌ موجودی کافی نیست! موجودی شما: {balance:,} تومان",
                    show_alert=True
                )
                
        elif data.startswith("pay_card:"):
            _, p, i, price = data.split(":")
            price = int(price)
            title = LISTS[p][int(i)][0]
            
            DB["orders"][str(uid)] = {
                "type": "service",
                "plan": p,
                "item_index": int(i),
                "amount": price,
                "title": title,
                "status": "pending",
                "timestamp": datetime.now().timestamp()
            }
            save_db()
            
            payment_text = f"""
💳 **پرداخت کارت به کارت**

📦 **سفارش شما:**
• سرویس: {title}
• مبلغ: **{price:,}** تومان

🏦 **اطلاعات پرداخت:**
💳 شماره کارت:
```6219861423194793```

👤 به نام: صفرپور

📱 **روش پرداخت:**
1️⃣ مبلغ را واریز کنید
2️⃣ عکس رسید را آپلود کنید
3️⃣ منتظر تایید باشید
            """
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📸 ارسال رسید", callback_data="send_receipt"))
            kb.add(types.InlineKeyboardButton("🔙 انصراف", callback_data=f"buy:{p}:{int(i)}:{price}"))
            
            bot.edit_message_text(
                payment_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data.startswith("tunnel_plan:"):
            _, plan_type, price = data.split(":")
            price = int(price)
            
            # پیدا کردن نام کامل پلن
            plan_name = ""
            for pn, p in TUNNEL_PLANS:
                if plan_type in pn:
                    plan_name = pn
                    break
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton(f"💳 پرداخت با موجودی", 
                                         callback_data=f"pay_tunnel_wallet:{plan_type}:{price}:{plan_name}"),
                types.InlineKeyboardButton("🏦 پرداخت کارت به کارت", 
                                         callback_data=f"pay_tunnel_card:{plan_type}:{price}:{plan_name}")
            )
            kb.add(
                types.InlineKeyboardButton("🔙 برگشت", callback_data="back_tunnel")
            )
            
            bot.edit_message_text(
                f"🫟 **جزئیات خرید تانل**\n\n📦 سرویس: {plan_name}\n💰 مبلغ: **{price:,}** تومان\n⏰ مدت: ۳۰ روز\n💾 حجم: {plan_type} گیگ",
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data == "back_tunnel":
            kb = types.InlineKeyboardMarkup(row_width=1)
            for plan_name, price in TUNNEL_PLANS:
                plan_name_clean = plan_name.replace("🫟 ", "").split(" ")[0]
                kb.add(types.InlineKeyboardButton(
                    f"{plan_name} - {price:,} تومان",
                    callback_data=f"tunnel_plan:{plan_name_clean}:{price}"
                ))
            kb.add(types.InlineKeyboardButton("🔙 برگشت به منوی قبل", callback_data="back_to_main"))
            
            tunnel_text = """
🫟 **خرید تانل اختصاصی**

🎯 **ویژگی‌های تانل:**
✅ IP اختصاصی
✅ پهنای باند بالا
✅ پینگ بسیار پایین

📊 **پلن‌های موجود:**
🫟 10 گیگ - مناسب تست
🫟 20 گیگ - اقتصادی
🫟 50 گیگ - حرفه‌ای
            """
            
            bot.edit_message_text(
                tunnel_text,
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data.startswith("pay_tunnel_wallet:"):
            _, plan_type, price, plan_name = data.split(":")
            price = int(price)
            
            balance = DB["balance"].get(str(uid), 0)
            if balance >= price:
                DB["balance"][str(uid)] = balance - price
                DB["admin_stats"]["total_income"] += price
                DB["admin_stats"]["total_orders"] += 1
                
                add_tunnel_service(uid, plan_name, plan_type, 30)
                log_transaction(uid, -price, "خرید تانل", plan_name)
                
                if str(uid) in DB["referrer"]:
                    ref = DB["referrer"][str(uid)]
                    bonus = int(price * REF_PERCENT)
                    DB["balance"][str(ref)] = DB["balance"].get(str(ref), 0) + bonus
                    log_transaction(ref, bonus, "پورسانت", f"از خرید تانل کاربر {uid}")
                
                save_db()
                
                bot.edit_message_text(
                    f"✅ **خرید تانل موفق!**\n\n📦 سرویس: {plan_name}\n💰 مبلغ: {price:,} تومان\n⏰ اعتبار: 30 روز\n💾 حجم: {plan_type} گیگ",
                    uid, c.message.message_id
                )
            else:
                bot.answer_callback_query(
                    c.id,
                    f"❌ موجودی کافی نیست! موجودی شما: {balance:,} تومان",
                    show_alert=True
                )
                
        elif data.startswith("pay_tunnel_card:"):
            _, plan_type, price, plan_name = data.split(":")
            price = int(price)
            
            DB["orders"][str(uid)] = {
                "type": "tunnel",
                "plan_type": plan_type,
                "amount": price,
                "title": plan_name,
                "status": "pending",
                "timestamp": datetime.now().timestamp()
            }
            save_db()
            
            payment_text = f"""
💳 **پرداخت کارت به کارت - تانل**

📦 **سفارش شما:**
• سرویس: {plan_name}
• مبلغ: **{price:,}** تومان

🏦 **اطلاعات پرداخت:**
💳 شماره کارت:
```6219861423194793```

👤 به نام: صفرپور

📱 **روش پرداخت:**
1️⃣ مبلغ را واریز کنید
2️⃣ عکس رسید را آپلود کنید
3️⃣ منتظر تایید باشید
            """
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📸 ارسال رسید", callback_data="send_receipt"))
            kb.add(types.InlineKeyboardButton("🔙 انصراف", callback_data=f"tunnel_plan:{plan_type}:{price}"))
            
            bot.edit_message_text(
                payment_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data == "wallet_charge":
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("💳 ۵۰,۰۰۰ تومان", callback_data="charge_amount:50000"),
                types.InlineKeyboardButton("💳 ۱۰۰,۰۰۰ تومان", callback_data="charge_amount:100000")
            )
            kb.add(
                types.InlineKeyboardButton("💳 ۲۰۰,۰۰۰ تومان", callback_data="charge_amount:200000"),
                types.InlineKeyboardButton("💳 ۵۰۰,۰۰۰ تومان", callback_data="charge_amount:500000")
            )
            kb.add(
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_wallet")
            )
            
            bot.edit_message_text(
                "💰 **شارژ حساب**\n\n💡 مبلغ مورد نظر را انتخاب کنید:",
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data == "wallet_history":
            user_transactions = [t for t in DB["transactions"] if t["user_id"] == uid]
            
            if not user_transactions:
                bot.answer_callback_query(
                    c.id,
                    "📭 هیچ تراکنشی ثبت نشده است!",
                    show_alert=True
                )
                return
            
            # فقط 10 تراکنش آخر را نمایش بده
            recent_transactions = user_transactions[-10:]
            history_text = "📜 **تاریخچه تراکنش‌ها**\n\n"
            
            for i, trans in enumerate(reversed(recent_transactions), 1):
                trans_date = datetime.fromtimestamp(trans["date"]).strftime('%Y/%m/%d %H:%M')
                amount = trans["amount"]
                trans_type = trans["type"]
                description = trans["description"]
                
                # تعیین نوع تراکنش
                if trans["amount"] > 0:
                    amount_text = f"+{amount:,}"
                    emoji = "📥"
                else:
                    amount_text = f"{amount:,}"
                    emoji = "📤"
                
                history_text += f"{i}. {emoji} **{trans_type}**\n"
                history_text += f"   💰 مبلغ: `{amount_text} تومان`\n"
                history_text += f"   📝 توضیح: {description}\n"
                history_text += f"   🕒 تاریخ: {trans_date}\n\n"
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_wallet"))
            
            bot.edit_message_text(
                history_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data == "back_to_wallet":
            balance = DB["balance"].get(str(uid), 0)
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("💳 شارژ حساب", callback_data="wallet_charge"),
                types.InlineKeyboardButton("📜 تاریخچه تراکنش‌ها", callback_data="wallet_history")
            )
            
            wallet_text = f"💰 **کیف پول شما**\n\n💵 **موجودی:** `{balance:,} تومان`"
            
            bot.edit_message_text(
                wallet_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data.startswith("charge_amount:"):
            amount = int(data.split(":")[1])
            
            DB["orders"][str(uid)] = {
                "type": "charge",
                "amount": amount,
                "title": f"شارژ کیف پول ({amount:,} تومان)",
                "status": "pending",
                "timestamp": datetime.now().timestamp()
            }
            save_db()
            
            payment_text = f"""
💳 **شارژ کیف پول**

💰 **مبلغ شارژ:**
**{amount:,}** تومان

🏦 **اطلاعات پرداخت:**
💳 شماره کارت:
```6219861423194793```

👤 به نام: صفرپور

📱 **روش پرداخت:**
1️⃣ مبلغ را واریز کنید
2️⃣ عکس رسید را آپلود کنید
3️⃣ منتظر تایید باشید

⚠️ **توجه:**
بعد از تایید، مبلغ به کیف پول شما اضافه خواهد شد.
            """
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📸 ارسال رسید", callback_data="send_receipt"))
            kb.add(types.InlineKeyboardButton("🔙 انصراف", callback_data="wallet_charge"))
            
            bot.edit_message_text(
                payment_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data == "send_receipt":
            bot.answer_callback_query(c.id, "📸 لطفا عکس رسید را ارسال کنید", show_alert=False)
            bot.send_message(uid, "📸 لطفاً عکس رسید پرداختی را ارسال کنید:")
            
        elif data == "support_email":
            bot.answer_callback_query(c.id, "📧 ایمیل: supbportplusila@gmail.com", show_alert=True)
            
        elif data.startswith("copy_id:"):
            user_id = data.split(":")[1]
            bot.answer_callback_query(c.id, f"✅ شناسه {user_id} کپی شد!", show_alert=True)
            
        elif data == "ref_list":
            subs = DB["referrals"].get(str(uid), [])
            if not subs:
                bot.answer_callback_query(c.id, "📭 هنوز زیرمجموعه‌ای ندارید!", show_alert=True)
            else:
                text = "📋 **لیست زیرمجموعه‌های شما:**\n\n"
                for i, sub_id in enumerate(subs, 1):
                    text += f"{i}. 🆔 `{sub_id}`\n"
                
                bot.answer_callback_query(c.id, "در حال دریافت اطلاعات...", show_alert=False)
                time.sleep(0.5)
                bot.send_message(uid, text, parse_mode="Markdown")
                
        elif data.startswith("ok:"):
            if not is_admin(uid):
                return
                
            user_id = int(data.split(":")[1])
            order = DB["orders"].get(str(user_id))
            
            if order and order["status"] == "pending":
                if order["type"] == "service":
                    title = order["title"]
                    days = 30 if order["plan"] in ["1m", "unl"] else 90
                    add_service(user_id, title, days)
                    order_type_text = "سرویس"
                elif order["type"] == "tunnel":
                    title = order["title"]
                    plan_type = order["plan_type"]
                    add_tunnel_service(user_id, title, plan_type, 30)
                    order_type_text = "تانل"
                elif order["type"] == "charge":
                    DB["balance"][str(user_id)] = DB["balance"].get(str(user_id), 0) + order["amount"]
                    log_transaction(user_id, order["amount"], "شارژ حساب", "توسط ادمین")
                    order_type_text = "شارژ حساب"
                
                if order["type"] in ["service", "tunnel"]:
                    DB["admin_stats"]["total_income"] += order["amount"]
                    DB["admin_stats"]["total_orders"] += 1
                
                if order["type"] in ["service", "tunnel"] and str(user_id) in DB["referrer"]:
                    ref = DB["referrer"][str(user_id)]
                    bonus = int(order["amount"] * REF_PERCENT)
                    DB["balance"][str(ref)] = DB["balance"].get(str(ref), 0) + bonus
                    log_transaction(ref, bonus, "پورسانت", f"از خرید کاربر {user_id}")
                
                DB["orders"].pop(str(user_id), None)
                save_db()
                
                try:
                    bot.send_message(
                        user_id,
                        f"✅ **پرداخت شما تایید شد!**\n\n📦 نوع: {order_type_text}\n💰 مبلغ: {order['amount']:,} تومان"
                    )
                except:
                    pass
                
                bot.answer_callback_query(c.id, "✅ سفارش تایید شد")
                
                # اگر پیام عکس بود
                try:
                    bot.edit_message_caption(
                        caption=f"✅ **تایید شده**\n👤 کاربر: {user_id}\n💰 مبلغ: {order['amount']:,} تومان",
                        chat_id=c.message.chat.id,
                        message_id=c.message.message_id
                    )
                except:
                    bot.edit_message_text(
                        f"✅ **تایید شده**\n👤 کاربر: {user_id}\n💰 مبلغ: {order['amount']:,} تومان",
                        chat_id=c.message.chat.id,
                        message_id=c.message.message_id
                    )
                
        elif data.startswith("no:"):
            if not is_admin(uid):
                return
                
            user_id = int(data.split(":")[1])
            order = DB["orders"].get(str(user_id))
            
            if order:
                DB["orders"].pop(str(user_id), None)
                save_db()
                
                try:
                    bot.send_message(user_id, "❌ **پرداخت شما رد شد!**\n\nمبلغ واریزی طی 24 ساعت به حساب شما بازمی‌گردد.")
                except:
                    pass
                
                bot.answer_callback_query(c.id, "❌ سفارش رد شد")
                
                try:
                    bot.edit_message_caption(
                        caption=f"❌ **رد شده**\n👤 کاربر: {user_id}",
                        chat_id=c.message.chat.id,
                        message_id=c.message.message_id
                    )
                except:
                    bot.edit_message_text(
                        f"❌ **رد شده**\n👤 کاربر: {user_id}",
                        chat_id=c.message.chat.id,
                        message_id=c.message.message_id
                    )
                
        # ========== ADMIN PANEL CALLBACKS ==========
        elif data == "admin_full_stats":
            if not is_admin(uid):
                return
                
            # محاسبه آمار پیشرفته
            active_users = 0
            total_balance = sum(DB["balance"].values())
            
            for user_id in DB["users"]:
                services = DB["services"].get(str(user_id), [])
                for service in services:
                    if service.get("expiry_date", 0) > datetime.now().timestamp():
                        active_users += 1
                        break
            
            today = datetime.now().strftime('%Y-%m-%d')
            today_income = 0
            today_transactions = [t for t in DB["transactions"] 
                                if datetime.fromtimestamp(t["date"]).strftime('%Y-%m-%d') == today 
                                and t["type"] in ["خرید سرویس", "خرید تانل"]]
            
            for trans in today_transactions:
                today_income += abs(trans["amount"])
            
            stats_text = f"""
📊 **آمار کامل ربات**

👥 **کاربران:**
• کل کاربران: {DB['admin_stats']['total_users']:,}
• کاربران فعال: {active_users:,}
• کاربران با سرویس: {len(DB['services']):,}

💰 **مالی:**
• درآمد کل: {DB['admin_stats']['total_income']:,} تومان
• درآمد امروز: {today_income:,} تومان
• مجموع موجودی کاربران: {total_balance:,} تومان
• تعداد سفارشات: {DB['admin_stats']['total_orders']:,}

📦 **سفارشات:**
• در انتظار: {len(DB['orders'])}
• پیام‌های ارسالی: {DB['admin_stats'].get('broadcasts_sent', 0):,}

🔄 **آخرین به‌روزرسانی:** {datetime.now().strftime('%Y/%m/%d %H:%M')}
            """
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔄 بروزرسانی آمار", callback_data="admin_full_stats"))
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_main"))
            
            bot.edit_message_text(
                stats_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data == "admin_search_user":
            if not is_admin(uid):
                return
                
            # تنظیم session برای جستجوی کاربر
            set_admin_session(uid, "search_user")
            bot.answer_callback_query(c.id, "🔍 لطفاً شناسه کاربر را ارسال کنید", show_alert=False)
            bot.send_message(uid, "🔍 **جستجوی کاربر**\n\n🆔 لطفاً شناسه عددی کاربر را ارسال کنید:")
            
        elif data == "admin_financial_menu":
            if not is_admin(uid):
                return
                
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("💰 گزارش مالی", callback_data="admin_financial_report"),
                types.InlineKeyboardButton("📊 آمار تراکنش‌ها", callback_data="admin_transaction_stats")
            )
            kb.add(
                types.InlineKeyboardButton("🎁 هدیه به همه", callback_data="admin_gift_all"),
                types.InlineKeyboardButton("💸 کسر از همه", callback_data="admin_deduct_all")
            )
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_main"))
            
            bot.edit_message_text(
                "💰 **مدیریت مالی پیشرفته**\n\nانتخاب گزینه مورد نظر:",
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data == "admin_gift_user_menu":
            if not is_admin(uid):
                return
                
            # تنظیم session برای هدیه به کاربر
            set_admin_session(uid, "gift_user")
            bot.answer_callback_query(c.id, "🎁 لطفاً اطلاعات را ارسال کنید", show_alert=False)
            bot.send_message(uid, "🎁 **هدیه به کاربر**\n\n🆔 شناسه کاربر:\n💰 مبلغ (تومان):\n\nمثال:\n`123456789\n50000`")
            
        elif data == "admin_broadcast_menu":
            if not is_admin(uid):
                return
                
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("📢 پیام متنی", callback_data="admin_broadcast_text"),
                types.InlineKeyboardButton("📷 پیام با عکس", callback_data="admin_broadcast_photo")
            )
            kb.add(
                types.InlineKeyboardButton("📋 پیام به گروه خاص", callback_data="admin_broadcast_group"),
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_main")
            )
            
            bot.edit_message_text(
                "📢 **پیام همگانی**\n\nانتخاب نوع پیام:",
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data == "admin_broadcast_text":
            if not is_admin(uid):
                return
                
            # تنظیم session برای پیام همگانی
            set_admin_session(uid, "broadcast_text")
            bot.answer_callback_query(c.id, "📝 لطفاً متن پیام را ارسال کنید", show_alert=False)
            bot.send_message(uid, "📝 **پیام همگانی متنی**\n\nمتن پیام خود را ارسال کنید:")
            
        elif data == "admin_gift_all":
            if not is_admin(uid):
                return
                
            # تنظیم session برای هدیه به همه
            set_admin_session(uid, "gift_all")
            bot.answer_callback_query(c.id, "💰 لطفاً مبلغ را ارسال کنید", show_alert=False)
            bot.send_message(uid, "💰 **هدیه به همه کاربران**\n\nمبلغ هدیه (تومان) را ارسال کنید:")
            
        elif data == "admin_change_welcome_bonus":
            if not is_admin(uid):
                return
                
            # تنظیم session برای تغییر هدیه عضویت
            set_admin_session(uid, "change_welcome_bonus")
            bot.answer_callback_query(c.id, "🎁 لطفاً مبلغ جدید را ارسال کنید", show_alert=False)
            bot.send_message(uid, "🎁 **تغییر هدیه عضویت**\n\nمبلغ جدید (تومان) را ارسال کنید:")
            
        elif data == "admin_change_ref_bonus":
            if not is_admin(uid):
                return
                
            # تنظیم session برای تغییر هدیه دعوت
            set_admin_session(uid, "change_ref_bonus")
            bot.answer_callback_query(c.id, "💰 لطفاً مبلغ جدید را ارسال کنید", show_alert=False)
            bot.send_message(uid, "💰 **تغییر هدیه دعوت**\n\nمبلغ جدید (تومان) را ارسال کنید:")
            
        elif data.startswith("admin_add_balance:"):
            if not is_admin(uid):
                return
                
            user_id = int(data.split(":")[1])
            
            # تنظیم session برای افزایش موجودی
            set_admin_session(uid, "add_balance", user_id)
            bot.answer_callback_query(c.id, "💰 لطفاً مبلغ را ارسال کنید", show_alert=False)
            bot.send_message(uid, f"💰 **افزایش موجودی کاربر**\n\n👤 کاربر: {user_id}\n💵 مبلغ (تومان) را ارسال کنید:")
            
        elif data == "admin_pending_orders":
            if not is_admin(uid):
                return
                
            orders = DB["orders"]
            if not orders:
                bot.edit_message_text(
                    "📭 **هیچ سفارشی در انتظار نیست**",
                    uid, c.message.message_id
                )
                return
            
            orders_text = "📦 **سفارشات در انتظار تایید**\n\n"
            for user_id, order in orders.items():
                orders_text += f"👤 کاربر: `{user_id}`\n"
                orders_text += f"📦 نوع: {order['type']}\n"
                orders_text += f"💰 مبلغ: {order['amount']:,} تومان\n"
                orders_text += f"🕒 زمان: {datetime.fromtimestamp(order['timestamp']).strftime('%H:%M')}\n"
                orders_text += "─" * 20 + "\n"
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_pending_orders"))
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_main"))
            
            bot.edit_message_text(
                orders_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data == "admin_financial_reports":
            if not is_admin(uid):
                return
                
            # محاسبه گزارش مالی
            today = datetime.now()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # درآمد امروز
            today_income = sum(abs(t["amount"]) for t in DB["transactions"] 
                             if datetime.fromtimestamp(t["date"]).date() == today.date()
                             and t["type"] in ["خرید سرویس", "خرید تانل"])
            
            # درآمد هفته
            week_income = sum(abs(t["amount"]) for t in DB["transactions"] 
                            if datetime.fromtimestamp(t["date"]) >= week_ago
                            and t["type"] in ["خرید سرویس", "خرید تانل"])
            
            # درآمد ماه
            month_income = sum(abs(t["amount"]) for t in DB["transactions"] 
                             if datetime.fromtimestamp(t["date"]) >= month_ago
                             and t["type"] in ["خرید سرویس", "خرید تانل"])
            
            report_text = f"""
📈 **گزارشات مالی**

📅 **بر اساس زمان:**
💰 درآمد امروز: {today_income:,} تومان
📊 درآمد ۷ روزه: {week_income:,} تومان
📈 درآمد ۳۰ روزه: {month_income:,} تومان

🔄 **آمار کلی:**
💳 کل تراکنش‌ها: {len(DB['transactions']):,}
🎯 میانگین خرید: {DB['admin_stats']['total_income'] / max(DB['admin_stats']['total_orders'], 1):,.0f} تومان
👥 ارزش هر کاربر: {DB['admin_stats']['total_income'] / max(DB['admin_stats']['total_users'], 1):,.0f} تومان

📊 **توزیع خرید:**
🛒 خرید سرویس: {sum(1 for t in DB['transactions'] if t['type'] == 'خرید سرویس'):,}
🫟 خرید تانل: {sum(1 for t in DB['transactions'] if t['type'] == 'خرید تانل'):,}
💳 شارژ حساب: {sum(1 for t in DB['transactions'] if t['type'] == 'شارژ حساب'):,}
            """
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_financial_menu"))
            
            bot.edit_message_text(
                report_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data == "admin_settings":
            if not is_admin(uid):
                return
                
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("🎁 تغییر هدیه عضویت", callback_data="admin_change_welcome_bonus"),
                types.InlineKeyboardButton("💰 تغییر هدیه دعوت", callback_data="admin_change_ref_bonus")
            )
            kb.add(
                types.InlineKeyboardButton("🔧 تنظیمات پورسانت", callback_data="admin_change_ref_percent"),
                types.InlineKeyboardButton("📊 تنظیمات حداقل/حداکثر", callback_data="admin_change_limits")
            )
            kb.add(
                types.InlineKeyboardButton("🔄 بازنشانی آمار", callback_data="admin_reset_stats"),
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_main")
            )
            
            settings_text = f"""
🔧 **تنظیمات ربات**

🎯 **مقادیر فعلی:**
🎁 هدیه عضویت: {DB['settings']['welcome_bonus']:,} تومان
💰 هدیه دعوت: {DB['settings']['ref_bonus']:,} تومان
⭐ درصد پورسانت: {REF_PERCENT*100}%
📊 حداقل برداشت: {DB['settings']['min_withdraw']:,} تومان
📈 حداکثر برداشت: {DB['settings']['max_withdraw']:,} تومان
            """
            
            bot.edit_message_text(
                settings_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data == "admin_manage_services":
            if not is_admin(uid):
                return
                
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("📋 لیست سرویس‌ها", callback_data="admin_list_services"),
                types.InlineKeyboardButton("⏰ تمدید سرویس", callback_data="admin_extend_service")
            )
            kb.add(
                types.InlineKeyboardButton("➕ افزودن سرویس دستی", callback_data="admin_add_service_manual"),
                types.InlineKeyboardButton("➖ حذف سرویس", callback_data="admin_remove_service")
            )
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_main"))
            
            bot.edit_message_text(
                "🎯 **مدیریت سرویس‌ها**\n\nانتخاب گزینه مورد نظر:",
                uid, c.message.message_id,
                reply_markup=kb
            )
            
        elif data == "admin_system_logs":
            if not is_admin(uid):
                return
                
            # نمایش 10 لاگ آخر
            recent_transactions = DB["transactions"][-20:]  # 20 تراکنش آخر
            
            if not recent_transactions:
                logs_text = "📭 **لاگی وجود ندارد**"
            else:
                logs_text = "📋 **لاگ سیستم (20 مورد آخر)**\n\n"
                for i, log in enumerate(reversed(recent_transactions), 1):
                    log_date = datetime.fromtimestamp(log["date"]).strftime('%m/%d %H:%M')
                    user_id = log["user_id"]
                    amount = log["amount"]
                    log_type = log["type"]
                    
                    if amount > 0:
                        amount_text = f"+{amount:,}"
                    else:
                        amount_text = f"{amount:,}"
                    
                    logs_text += f"{i}. 🆔 `{user_id}`\n"
                    logs_text += f"   📝 {log_type}\n"
                    logs_text += f"   💰 {amount_text}\n"
                    logs_text += f"   🕒 {log_date}\n\n"
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_system_logs"))
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_main"))
            
            bot.edit_message_text(
                logs_text,
                uid, c.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            
        elif data.startswith("admin_confirm_gift_all:"):
            if not is_admin(uid):
                return
                
            amount = int(data.split(":")[1])
            
            # ارسال هدیه به همه کاربران
            success_count = 0
            failed_count = 0
            
            for user_id in DB["users"]:
                try:
                    DB["balance"][str(user_id)] = DB["balance"].get(str(user_id), 0) + amount
                    log_transaction(user_id, amount, "هدیه همگانی", "توسط ادمین")
                    success_count += 1
                    
                    # اطلاع به کاربر (با تاخیر برای جلوگیری از محدودیت)
                    time.sleep(0.05)
                    try:
                        bot.send_message(
                            user_id,
                            f"🎁 **هدیه ویژه از مدیریت!**\n\n💰 مبلغ: {amount:,} تومان\n🎉 به همه کاربران هدیه داده شد!"
                        )
                    except:
                        failed_count += 1
                        
                except:
                    failed_count += 1
            
            save_db()
            
            bot.edit_message_text(
                f"✅ **هدیه با موفقیت ارسال شد**\n\n💰 مبلغ هر نفر: {amount:,} تومان\n✅ موفق: {success_count} نفر\n❌ ناموفق: {failed_count} نفر\n💵 مجموع: {amount * success_count:,} تومان",
                uid, c.message.message_id
            )
            
        elif data.startswith("admin_confirm_broadcast:"):
            if not is_admin(uid):
                return
                
            # استخراج پیام (ممکن است شامل : باشد)
            parts = data.split(":")
            message_text = ":".join(parts[1:])
            
            # ارسال به همه کاربران
            success_count = 0
            failed_count = 0
            
            for user_id in DB["users"]:
                try:
                    bot.send_message(user_id, message_text)
                    success_count += 1
                    time.sleep(0.05)  # تاخیر برای جلوگیری از محدودیت
                except:
                    failed_count += 1
            
            # ثبت آمار
            DB["admin_stats"]["broadcasts_sent"] = DB["admin_stats"].get("broadcasts_sent", 0) + 1
            save_db()
            
            bot.edit_message_text(
                f"✅ **پیام همگانی ارسال شد**\n\n✅ موفق: {success_count} نفر\n❌ ناموفق: {failed_count} نفر\n📅 زمان: {datetime.now().strftime('%H:%M')}",
                uid, c.message.message_id
            )
            
        elif data == "admin_back_to_main":
            if not is_admin(uid):
                return
                
            admin_text = """
👑 **پنل مدیریت پیشرفته**

🔧 **دسترسی کامل به تمام امکانات ربات:**
✅ مدیریت کاربران
✅ مدیریت مالی
✅ پیام همگانی
✅ گزارشات کامل
✅ تنظیمات ربات

🎯 **انتخاب گزینه مورد نظر:"
            """
            
            bot.edit_message_text(
                admin_text,
                uid, c.message.message_id,
                reply_markup=create_admin_keyboard()
            )
                
    except Exception as e:
        print(f"Error in callback: {e}")
        bot.answer_callback_query(c.id, "⚠️ خطایی رخ داد")

# ---------- دریافت فیش ----------
@bot.message_handler(content_types=["photo"])
def receipt(m):
    uid = m.from_user.id
    
    order = DB["orders"].get(str(uid))
    if not order:
        bot.send_message(uid, "❌ ابتدا باید سفارش خود را ثبت کنید.")
        return
    
    price = order["amount"]
    order_type = order.get("type", "service")
    title = order.get("title", "سرویس")
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"ok:{uid}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"no:{uid}")
    )
    
    if order_type == "charge":
        caption = f"💰 **درخواست شارژ**\n👤 کاربر: {uid}\n💵 مبلغ: {price:,} تومان"
    elif order_type == "tunnel":
        caption = f"🫟 **سفارش تانل جدید**\n👤 کاربر: {uid}\n📦 سرویس: {title}\n💰 مبلغ: {price:,} تومان"
    else:
        caption = f"🛒 **سفارش جدید**\n👤 کاربر: {uid}\n📦 سرویس: {title}\n💰 مبلغ: {price:,} تومان"
    
    for admin in ADMINS:
        try:
            bot.send_photo(admin, m.photo[-1].file_id, caption=caption, reply_markup=kb)
        except:
            pass
    
    bot.send_message(uid, "📨 **رسید شما دریافت شد!**\n⏳ در حال بررسی...")

# ---------- راه‌اندازی ربات ----------
if __name__ == "__main__":
    print("🚀 VPN STORE BOT روی لیارا راه‌اندازی شد...")
    print(f"👑 ادمین: {ADMINS}")
    print(f"👥 کاربران: {len(DB['users'])}")
    print(f"💰 درآمد کل: {DB['admin_stats']['total_income']:,} تومان")
    print(f"🎁 هدیه عضویت: {DB['settings']['welcome_bonus']:,} تومان")
    print(f"💰 هدیه هر دعوت: {DB['settings']['ref_bonus']:,} تومان")
    
    bot_username = bot.get_me().username
    print(f"🔗 آدرس: @{bot_username}")
    print(f"📅 زمان راه‌اندازی: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
    
    # برای لیارا - polling با قابلیت restart خودکار
    import time
    
    while True:
        try:
            print("🔄 شروع دریافت پیام‌ها...")
            bot.polling(
                none_stop=True,      # قطع نشود
                interval=1,          # فاصله بین درخواست‌ها (ثانیه)
                timeout=30,          # timeout برای درخواست
                long_polling_timeout=30  # timeout برای long polling
            )
        except KeyboardInterrupt:
            print("⏹ ربات متوقف شد")
            break
        except Exception as e:
            print(f"⚠️ خطا: {e}")
            print("💤 5 ثانیه صبر...")
            time.sleep(5)
