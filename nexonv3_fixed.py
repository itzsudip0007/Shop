import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
import time
import qrcode
import io
import threading
import datetime
import random
import traceback

# --- CONFIGURATION ---
BOT_TOKEN = "8833268418:AAHE8Nj6XhNZU3md-XvvnjMngS2VvtuVzb0" 
ADMIN_ID =  7422190601 
OWNER_CONTACT = "@Nexonhere" 
bot = telebot.TeleBot(BOT_TOKEN)

# --- FILES ---
DATA_FILE = "users.json"
CONFIG_FILE = "config.json"
PRODUCTS_FILE = "products.json"
UTR_FILE = "used_utrs.json"
SOLD_FILE = "sold.txt" 

# --- GLOBAL VARS ---
config = {}
products = {}
users = {}
used_utrs = []
user_states = {} 

# --- DATA MANAGER ---

def load_json_safe(filename, default_val):
    if not os.path.exists(filename):
        return default_val
    try:
        with open(filename, 'r') as f:
            data = f.read().strip()
            if not data: return default_val
            return json.loads(data)
    except:
        return default_val

def load_data():
    global config, products, users, used_utrs
    
    # 1. Config
    default_config = {
        "upi": "Nexon@Slc",
        "merchant_name": "SUDIP",
        "banner_url": "https://i.imgur.com/2K7o0vQ.png",
        "support_user": "NexonHere",
        "tnc": "📜 **Terms & Conditions**\n\n1. After Payment Wait Few Minutes.\n2. Verify product before buying.\n3. UTR must be valid.\n4. Delivery is instant."
    }
    config = load_json_safe(CONFIG_FILE, default_config)
    save_json(CONFIG_FILE, config)

    # 2. Products
    default_products = {
        "p1": {"name": "₹Fresh FB", "price": 15, "file": "5.txt"},
        "p2": {"name": "Indonesia [WhatsApp]", "price": 40, "file": "1k.txt"},
        "p3": {"name": "Sierra Leone [Telegram]", "price": 60, "file": "2k.txt"},
}
    products = load_json_safe(PRODUCTS_FILE, default_products)
    save_json(PRODUCTS_FILE, products)
    
    for p in products.values():
        if not os.path.exists(p['file']): open(p['file'], 'w').close()

    # 3. Users
    users = load_json_safe(DATA_FILE, {})
    
    # 4. UTR History
    used_utrs = load_json_safe(UTR_FILE, [])

def save_json(filename, data):
    try:
        with open(filename, 'w') as f: json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def save_all():
    save_json(CONFIG_FILE, config)
    save_json(PRODUCTS_FILE, products)
    save_json(DATA_FILE, users)
    save_json(UTR_FILE, used_utrs)

# --- STOCK LOGIC ---

def get_stock_count(filename):
    if not os.path.exists(filename): return 0
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return len([l for l in f.readlines() if l.strip()])
    except: return 0

def add_stock_lines(filename, text_data):
    lines = [l for l in text_data.split('\n') if l.strip()]
    with open(filename, 'a', encoding='utf-8') as f:
        for line in lines:
            f.write(line.strip() + "\n")

def process_final_sale(pid, quantity):
    filename = products[pid]['file']
    if not os.path.exists(filename): return None

    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f: 
            lines = f.readlines()
        
        clean_lines = [l.strip() for l in lines if l.strip()]
        
        if len(clean_lines) < quantity:
            return None 

        items_to_take = clean_lines[:quantity]
        remaining = clean_lines[quantity:]

        with open(filename, 'w', encoding='utf-8') as f: 
            f.write("\n".join(remaining) + "\n" if remaining else "")
            
        return items_to_take
    except Exception as e:
        print(f"File Error: {e}")
        return None

def log_sold_codes(order_id, username, item_name, amount, codes):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    codes_str = ", ".join(codes)
    line = f"🆔 {order_id} | 🕒 {now} | 👤 {username} | 📦 {item_name} | 💰 ₹{amount} | 🎟 {codes_str}\n"
    
    with open(SOLD_FILE, "a", encoding="utf-8") as f:
        f.write(line)

def add_strike(user_id):
    uid = str(user_id)
    if uid not in users: users[uid] = {"history": [], "strikes": 0}
    if "strikes" not in users[uid]: users[uid]["strikes"] = 0
    
    users[uid]["strikes"] += 1
    save_all()
    
    if users[uid]["strikes"] >= 3:
        try:
            bot.send_message(user_id, f"🚫 **YOU ARE BANNED**\n\nYou failed to complete payment 3 times.\nContact Support: @{config['support_user']}")
        except: pass

# --- UTILS ---

def generate_qr(amount):
    upi_url = f"upi://pay?pa={config['upi']}&pn={config['merchant_name']}&am={amount}&cu=INR"
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    bio = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(bio)
    bio.seek(0)
    return bio

def run_broadcast(text):
    count = 0
    blocked = 0
    for uid in list(users.keys()):
        try:
            bot.send_message(uid, f"📢 **Announcement**\n\n{text}", parse_mode="Markdown")
            count += 1
            time.sleep(0.05) 
        except:
            blocked += 1
    
    try:
        bot.send_message(ADMIN_ID, f"✅ **Broadcast Completed**\nSent: {count}\nBlocked/Failed: {blocked}")
    except: pass

def safe_update_message(cid, mid, text, markup=None):
    try:
        bot.edit_message_text(text, cid, mid, parse_mode="Markdown", reply_markup=markup)
    except:
        try:
            bot.delete_message(cid, mid)
        except: pass
        try:
            bot.send_message(cid, text, parse_mode="Markdown", reply_markup=markup)
        except: pass

# --- MENUS ---

def main_menu():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton("⚡ Buy Vouchers", callback_data="shop"))
    m.add(InlineKeyboardButton("👤 Profile", callback_data="profile"),
          InlineKeyboardButton("🆘 Support", url=f"https://t.me/{config['support_user']}"))
    return m

def shop_menu():
    m = InlineKeyboardMarkup()
    for pid, p in products.items():
        stock = get_stock_count(p['file'])
        txt = f"{p['name']} | ₹{p['price']} | 📦 {stock}"
        m.add(InlineKeyboardButton(txt, callback_data=f"sel_{pid}"))
    m.add(InlineKeyboardButton("🔙 Back to Home", callback_data="home"))
    return m

def quantity_menu(pid, price):
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton(f"2 Qty (₹{price*2})", callback_data=f"buy_{pid}_2"),
        InlineKeyboardButton(f"5 Qty (₹{price*5})", callback_data=f"buy_{pid}_5")
    )
    m.add(
        InlineKeyboardButton(f"10 Qty (₹{price*10})", callback_data=f"buy_{pid}_10"),
        InlineKeyboardButton(f"25 Qty (₹{price*25})", callback_data=f"buy_{pid}_25")
    )
    m.add(InlineKeyboardButton("✏️ Custom Qty", callback_data=f"cust_{pid}"))
    m.add(InlineKeyboardButton("🔙 Back", callback_data="shop"))
    return m

def admin_menu():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton("➕ Add Stock", callback_data="adm_stock"),
          InlineKeyboardButton("👥 View Users", callback_data="adm_users"))
    m.add(InlineKeyboardButton("📢 Broadcast", callback_data="adm_cast"),
          InlineKeyboardButton("📜 Sales History", callback_data="adm_sales"))
    m.add(InlineKeyboardButton("📜 Set T&C", callback_data="adm_tnc"),
          InlineKeyboardButton("🖼 Set Banner", callback_data="adm_banner"))
    m.add(InlineKeyboardButton("🏦 Set UPI", callback_data="adm_upi"),
          InlineKeyboardButton("✏️ Edit Products", callback_data="adm_edit_prod"))
    m.add(InlineKeyboardButton("❌ Close", callback_data="close"))
    return m

# --- BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    cid = str(message.chat.id)
    if cid not in users: users[cid] = {"history": [], "strikes": 0}
    save_all()
    
    if users[cid].get("strikes", 0) >= 3:
        bot.send_message(cid, f"🚫 **BANNED**\nContact @{config['support_user']}")
        return

    try:
        bot.send_photo(cid, config['banner_url'])
    except: pass 

    text_body = (
        f"👋 *Welcome, {message.from_user.first_name}!*\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🚀 *Instant Delivery System*\n"
        "✅ Verified Vouchers\n"
        "⚡ 24/7 Auto-Stock\n"
        "👇 *Tap a button to begin:*"
    )
    bot.send_message(cid, text_body, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🔑 *Admin Panel*", parse_mode="Markdown", reply_markup=admin_menu())

# --- CALLBACKS ---

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    cid = call.message.chat.id
    mid = call.message.message_id
    data = call.data

    try: bot.answer_callback_query(call.id)
    except: pass

    if data == "home":
        user_states.pop(cid, None)
        safe_update_message(cid, mid, "👇 *Main Menu*", main_menu())

    elif data == "shop":
        safe_update_message(cid, mid, "🛒 *Select a Product below:*", shop_menu())

    elif data == "profile":
        u_data = users.get(str(cid), {})
        hist = u_data.get("history", [])
        strikes = u_data.get("strikes", 0)
        
        txt = (
            f"👤 *User Profile*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{cid}`\n"
            f"⚠️ Strikes: {strikes}/3\n"
            f"📦 Total Orders: {len(hist)}\n"
        )
        
        btn = InlineKeyboardMarkup(row_width=2)
        btn.add(InlineKeyboardButton("📜 My Orders", callback_data="my_orders"))
        btn.add(InlineKeyboardButton("🔙 Back", callback_data="home"))
        safe_update_message(cid, mid, txt, btn)

    elif data == "my_orders":
        hist = users.get(str(cid), {}).get("history", [])
        if not hist:
            bot.answer_callback_query(call.id, "❌ No orders found.", show_alert=True)
            return
            
        report = "📜 **MY RECENT ORDERS**\n\n"
        recent_orders = list(reversed(hist))[:5] 
        
        for order in recent_orders:
            codes_list = order.get('codes', [])
            formatted_codes = "\n".join([f"`{c}`" for c in codes_list])
            report += (
                f"🆔 **{order.get('oid', 'N/A')}**\n"
                f"📆 {order['date']} | ₹{order['amt']}\n"
                f"📦 {order['item']}\n"
                f"👇 *Codes:*\n{formatted_codes}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
            )
        btn = InlineKeyboardMarkup()
        btn.add(InlineKeyboardButton("🔙 Back to Profile", callback_data="profile"))
        safe_update_message(cid, mid, report, btn)

    elif data.startswith("sel_"):
        pid = data.split("_")[1]
        prod = products.get(pid)
        if not prod: return
        
        safe_update_message(
            cid, mid,
            f"📦 **Selected:** {prod['name']}\n💰 **Price per unit:** ₹{prod['price']}\n\n👇 **Select Quantity:**",
            quantity_menu(pid, prod['price'])
        )

    elif data.startswith("cust_"):
        pid = data.split("_")[1]
        prod = products[pid]
        max_stock = get_stock_count(prod['file'])
        
        if max_stock == 0:
            bot.answer_callback_query(call.id, "❌ Out of Stock!", show_alert=True)
            return

        bot.send_message(cid, f"🔢 **Enter Quantity**\nMax available: {max_stock}\n👇 Type the number below:")
        user_states[cid] = {"state": "waiting_quantity", "pid": pid}

    elif data.startswith("buy_"):
        parts = data.split("_")
        pid = parts[1]
        qty = int(parts[2])
        initiate_purchase(cid, mid, pid, qty)

    elif data == "cancel_buy":
        user_states.pop(cid, None)
        safe_update_message(cid, mid, "❌ Order Cancelled.", main_menu())

    elif data.startswith("pay_"):
        pid = data.split("_")[1]
        if cid not in user_states:
            bot.send_message(cid, "❌ Session Expired. Start again.")
            return

        state = user_states[cid]
        qty = state['qty']
        price = state['total_price']
        
        qr = generate_qr(price)
        txt = (
            f"💳 *Payment Required*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Item: {products[pid]['name']}\n"
            f"🔢 Quantity: {qty}\n"
            f"💰 **Total to Pay: ₹{price}**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👇 *Send UTR Number OR Screenshot below:*\n\n"
        )
        try: bot.delete_message(cid, mid) 
        except: pass
        
        bot.send_photo(cid, qr, caption=txt, parse_mode="Markdown")
        user_states[cid]['state'] = "waiting_payment"

    # --- ADMIN ACTIONS ---
    elif data.startswith("appr_"):
        try:
            _, buyer_id, pid, qty_str = data.split("_")
            buyer_id = int(buyer_id)
            qty = int(qty_str)
            prod = products[pid]

            codes = process_final_sale(pid, qty)

            if codes:
                order_id = f"ORD-{int(time.time())}-{random.randint(100,999)}"
                formatted_codes = "\n\n".join([f"`{c}`" for c in codes])

                msg = (
                    f"✅ **Order Successful!**\n"
                    f"🆔 Order ID: `{order_id}`\n"
                    f"📦 {prod['name']} (x{qty})\n"
                    f"👇 **Your Codes:**\n"
                    f"{formatted_codes}"
                )
                
                try:
                    bot.send_message(buyer_id, msg, parse_mode="Markdown")
                except:
                    bot.send_message(cid, f"⚠️ User {buyer_id} blocked bot, but codes were removed.")

                buyer_str = str(buyer_id)
                if buyer_str not in users: users[buyer_str] = {"history": [], "strikes": 0}
                
                total_amt = qty * prod['price']
                users[buyer_str]['history'].append({
                    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "item": prod['name'],
                    "amt": total_amt,
                    "oid": order_id,
                    "codes": codes
                })
                users[buyer_str]['strikes'] = 0 
                save_all()
                
                try:
                    username = f"@{bot.get_chat(buyer_id).username}"
                except: username = "Unknown"
                
                log_sold_codes(order_id, username, prod['name'], total_amt, codes)

                safe_update_message(cid, mid, f"✅ **Sold to {buyer_id}**\n🆔 {order_id}")
            else:
                bot.send_message(cid, f"❌ **OUT OF STOCK**\nCould not fulfill order for {buyer_id}.\nRefund the user.")
        
        except Exception as e:
            bot.send_message(cid, f"❌ Error processing approval: {e}")

    elif data.startswith("rej_"):
        buyer_id = data.split("_")[1]
        add_strike(buyer_id)
        try:
            bot.send_message(int(buyer_id), f"❌ **Payment Denied.**\nAdmin marked it invalid.\nStrike added.", parse_mode="Markdown")
        except: pass
        safe_update_message(cid, mid, f"🚫 **Rejected & Striked {buyer_id}**")

    # --- ADMIN MENUS ---
    elif data == "adm_stock":
        m = InlineKeyboardMarkup()
        for pid, p in products.items():
            m.add(InlineKeyboardButton(f"➕ Add to {p['name']}", callback_data=f"addstk_{pid}"))
        m.add(InlineKeyboardButton("🔙 Cancel", callback_data="close"))
        safe_update_message(cid, mid, "Select Product to add stock:", m)
    
    elif data == "adm_sales":
        if os.path.exists(SOLD_FILE):
             try:
                with open(SOLD_FILE, 'rb') as f:
                    bot.send_document(cid, f, caption="✅ **Sold Codes Log**")
             except: bot.send_message(cid, "❌ Error sending file.")
        else:
             bot.send_message(cid, "❌ No sales recorded yet.")

    elif data == "adm_users":
        txt = "USER REPORT\n===========\n"
        for uid, d in users.items():
            txt += f"ID: {uid} | Strikes: {d.get('strikes', 0)}\n"
        bio = io.BytesIO(txt.encode('utf-8'))
        bio.name = "users.txt"
        bot.send_document(cid, bio, caption="✅ User list.")

    elif data == "adm_cast":
        bot.send_message(cid, "📢 Send broadcast message:")
        user_states[cid] = {"state": "broadcasting"}

    elif data == "adm_edit_prod":
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton("➕ Add New Product", callback_data="adm_new_prod"))
        m.add(InlineKeyboardButton("💰 Update Price", callback_data="adm_upd_price"))
        m.add(InlineKeyboardButton("🗑 Delete Product", callback_data="adm_del_prod"))
        m.add(InlineKeyboardButton("🔙 Back", callback_data="close"))
        safe_update_message(cid, mid, "⚙️ Product Manager:", m)

    elif data == "adm_upd_price":
        m = InlineKeyboardMarkup()
        for pid, p in products.items():
            m.add(InlineKeyboardButton(f"{p['name']} (Curr: ₹{p['price']})", callback_data=f"uppr_{pid}"))
        m.add(InlineKeyboardButton("🔙 Back", callback_data="adm_edit_prod"))
        safe_update_message(cid, mid, "Select Product to Update Price:", m)

    elif data.startswith("uppr_"):
        pid = data.split("_")[1]
        user_states[cid] = {"state": "waiting_new_price", "pid": pid}
        bot.send_message(cid, f"📝 Enter new price for **{products[pid]['name']}**:", parse_mode="Markdown")

    elif data == "adm_new_prod":
        bot.send_message(cid, "1️⃣ Send Product Name:")
        user_states[cid] = {"state": "new_prod_name"}

    elif data == "adm_del_prod":
        m = InlineKeyboardMarkup()
        for pid, p in products.items():
            m.add(InlineKeyboardButton(f"🗑 {p['name']}", callback_data=f"delp_{pid}"))
        safe_update_message(cid, mid, "Select to delete:", m)

    elif data.startswith("delp_"):
        pid = data.split("_")[1]
        del products[pid]
        save_all()
        bot.send_message(cid, "✅ Product Deleted.")

    elif data.startswith("addstk_"):
        pid = data.split("_")[1]
        user_states[cid] = {"state": "adding_stock", "pid": pid}
        bot.send_message(cid, f"📝 Send stock for **{products[pid]['name']}**.", parse_mode="Markdown")

    elif data == "adm_upi":
        bot.send_message(cid, "🏦 Send new UPI ID:")
        user_states[cid] = {"state": "set_upi"}
    
    # --- FIXED: SET TNC HANDLER ---
    elif data == "adm_tnc":
        bot.send_message(cid, "📜 Send the new Terms & Conditions text:")
        user_states[cid] = {"state": "set_tnc"}

    # --- FIXED: SET BANNER HANDLER ---
    elif data == "adm_banner":
        bot.send_message(cid, "🖼 Send the new Banner Image (or URL):")
        user_states[cid] = {"state": "set_banner"}

    elif data == "close":
        bot.delete_message(cid, mid)

def initiate_purchase(cid, mid, pid, qty):
    if users.get(str(cid), {}).get("strikes", 0) >= 3:
        bot.send_message(cid, f"🚫 **BANNED.** Contact Support.")
        return

    prod = products[pid]
    stock = get_stock_count(prod['file'])
    
    if stock < qty:
        bot.send_message(cid, f"⚠️ Not enough stock! Available: {stock}")
        return

    total_price = qty * prod['price']
    
    user_states[cid] = {
        "state": "confirm_buy",
        "pid": pid,
        "qty": qty,
        "total_price": total_price
    }
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"✅ Pay ₹{total_price}", callback_data=f"pay_{pid}"))
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel_buy"))
    
    tnc_text = config.get("tnc", "⚠️ No refunds.")
    
    safe_update_message(
        cid, mid,
        f"📜 **Terms & Conditions**\n\n{tnc_text}\n\n🛒 **Qty:** {qty} | **Total:** ₹{total_price}", 
        markup
    )

# --- INPUT HANDLERS ---

@bot.message_handler(content_types=['text', 'photo'])
def handle_input(message):
    cid = message.chat.id
    if cid not in user_states: return

    st = user_states[cid]
    step = st.get('state')
    
    if step == "waiting_quantity":
        try:
            qty = int(message.text)
            pid = st['pid']
            initiate_purchase(cid, None, pid, qty)
        except ValueError:
            bot.reply_to(message, "❌ Please enter a valid number.")

    elif step == "waiting_new_price":
        try:
            new_price = int(message.text)
            pid = st['pid']
            if pid in products:
                products[pid]['price'] = new_price
                save_all()
                bot.send_message(cid, f"✅ Price updated to ₹{new_price}")
            else:
                bot.send_message(cid, "❌ Product not found.")
            user_states.pop(cid, None)
        except ValueError:
            bot.reply_to(message, "❌ Please enter a valid number.")

    elif step == "waiting_payment":
        utr_txt = None
        is_photo = False
        
        if message.content_type == 'text':
            utr = message.text.strip()
            if not utr.isdigit() or len(utr) < 8: 
                bot.reply_to(message, "⚠️ Invalid UTR format.")
                return
            if utr in used_utrs:
                bot.reply_to(message, "⚠️ Duplicate UTR.")
                return
            utr_txt = utr
            used_utrs.append(utr)
            save_all()
        elif message.content_type == 'photo':
            is_photo = True
        else:
            return

        prod = products[st['pid']]
        qty = st['qty']
        amt = st['total_price']
        
        bot.send_message(cid, f"✅ **Payment Submitted!**\n⏳ Waiting for Admin confirmation...\n\n⚠️ If no response in 10 mins, contact {OWNER_CONTACT}")
        
        btns = InlineKeyboardMarkup()
        btns.add(InlineKeyboardButton("✅ Approve", callback_data=f"appr_{cid}_{st['pid']}_{qty}"),
                 InlineKeyboardButton("🚫 Deny", callback_data=f"rej_{cid}"))
        
        txt = f"🚨 **ORDER REQUEST**\nUser: {cid}\nItem: {prod['name']}\nQty: {qty}\nAmt: ₹{amt}"
        if utr_txt: txt += f"\nUTR: `{utr_txt}`"
        
        if is_photo: bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=txt, reply_markup=btns)
        else: bot.send_message(ADMIN_ID, txt, reply_markup=btns)
        
        user_states.pop(cid, None)

    elif step == "broadcasting":
        threading.Thread(target=run_broadcast, args=(message.text,), daemon=True).start()
        bot.send_message(cid, "📢 Broadcast started.")
        user_states.pop(cid, None)

    elif step == "adding_stock":
        add_stock_lines(products[st['pid']]['file'], message.text)
        bot.send_message(cid, "✅ Stock added.")
        user_states.pop(cid, None)

    elif step == "set_upi":
        config['upi'] = message.text
        save_all()
        bot.send_message(cid, "✅ UPI Updated.")
        user_states.pop(cid, None)
    
    # --- FIXED: SAVE TNC ---
    elif step == "set_tnc":
        config['tnc'] = message.text
        save_all()
        bot.send_message(cid, "✅ Terms & Conditions updated.")
        user_states.pop(cid, None)

    # --- FIXED: SAVE BANNER ---
    elif step == "set_banner":
        if message.content_type == 'photo':
            # Get the file_id of the largest photo
            file_id = message.photo[-1].file_id
            config['banner_url'] = file_id
            save_all()
            bot.send_message(cid, "✅ Banner Image updated.")
            user_states.pop(cid, None)
        elif message.content_type == 'text':
            config['banner_url'] = message.text.strip()
            save_all()
            bot.send_message(cid, "✅ Banner URL updated.")
            user_states.pop(cid, None)
        else:
            bot.send_message(cid, "❌ Send a photo or a URL string.")
    
    elif step == "new_prod_name":
        user_states[cid].update({"name": message.text, "state": "new_prod_price"})
        bot.send_message(cid, "2️⃣ Send Price:")
    
    elif step == "new_prod_price":
        try:
            user_states[cid].update({"price": int(message.text), "state": "new_prod_file"})
            bot.send_message(cid, "3️⃣ Send Filename (e.g. `items.txt`):")
        except: bot.send_message(cid, "Number only.")
    
    elif step == "new_prod_file":
        pid = f"p{int(time.time())}"
        d = user_states[cid]
        products[pid] = {"name": d['name'], "price": d['price'], "file": message.text.strip()}
        if not os.path.exists(message.text.strip()): open(message.text.strip(), 'w').close()
        save_all()
        bot.send_message(cid, "✅ Product Added.")
        user_states.pop(cid, None)

# --- STARTUP ---

print("Bot is Live...")
load_data()

# CRASH HANDLER LOOP
while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        error_msg = f"❌ **CRITICAL ERROR**\n{traceback.format_exc()}"
        print(error_msg)
        try:
            bot.send_message(ADMIN_ID, error_msg[:4000]) 
        except: pass
        time.sleep(5) 
