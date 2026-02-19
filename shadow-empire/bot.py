"""
Telegram bot for Shadow Empire — launches the Mini App + handles Telegram Stars payments.
"""

import os
import json
import time
import logging
import aiosqlite
import httpx
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, PreCheckoutQueryHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

from backend.game_config import VIP_PACKAGES, CASH_PACKAGES, CASE_PACKAGES

# ── Config ──
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]
_data_dir = os.getenv("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(_data_dir, "game.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Deep link: /start ref_12345 → pass referral code to WebApp
    ref_param = ""
    if context.args and context.args[0].startswith("ref_"):
        ref_param = context.args[0]  # e.g. "ref_12345"

    url = WEBAPP_URL
    sep = "&" if "?" in url else "?"
    url += f"{sep}_v=32"
    if ref_param:
        url += f"&ref={ref_param}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text="🕴️ Играть в Shadow Empire",
            web_app=WebAppInfo(url=url),
        )],
        [
            InlineKeyboardButton(text="📢 Новости", url="https://t.me/shadowempire_official"),
            InlineKeyboardButton(text="💬 Обратная связь", url="https://t.me/shadowempire_chat"),
        ]
    ])

    await update.message.reply_text(
        "🕴️ *Shadow Empire*\n\n"
        "Построй свою империю от уличного ларька до криминального синдиката.\n\n"
        "🏢 Легальный бизнес — прикрытие\n"
        "🌑 Теневой бизнес — настоящие деньги\n"
        "🔫 Ограбления — быстрый куш\n"
        "🚔 Не попадись полиции!\n\n"
        "Жми кнопку ниже, чтобы начать 👇",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕴️ *Shadow Empire — Помощь*\n\n"
        "Цель игры — построить самую крупную империю.\n\n"
        "💡 *Советы:*\n"
        "• Легальный бизнес снижает подозрение\n"
        "• Теневой бизнес приносит больше денег\n"
        "• Если подозрение > 80% — будет рейд!\n"
        "• Репутация Страха усиливает теневой бизнес\n"
        "• Репутация Уважения снижает подозрение\n"
        "• Ограбления дают быстрые деньги но рискованны\n"
        "• 👑 VIP — двойной доход и бонусы!\n\n"
        "/start — открыть игру",
        parse_mode="Markdown",
    )


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Always approve pre-checkout queries for Stars payments."""
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful Telegram Stars payment — activate the purchase."""
    payment = update.message.successful_payment
    try:
        payload = json.loads(payment.invoice_payload)
    except (json.JSONDecodeError, TypeError):
        logger.error("Invalid payment payload")
        return

    tid = payload.get("telegram_id")
    package_id = payload.get("package_id")
    if not tid or not package_id:
        logger.error(f"Missing tid or package_id in payload: {payload}")
        return

    db = await get_db()
    try:
        now = time.time()

        # Determine package type and activate
        if package_id in VIP_PACKAGES:
            pkg = VIP_PACKAGES[package_id]
            days = pkg["days"]
            # Extend VIP if already active
            cursor = await db.execute("SELECT vip_until FROM players WHERE telegram_id=?", (tid,))
            row = await cursor.fetchone()
            if row:
                current_until = row["vip_until"] or 0
                base = max(current_until, now)
                new_until = base + days * 86400
                await db.execute(
                    "UPDATE players SET is_vip=1, vip_until=? WHERE telegram_id=?",
                    (new_until, tid),
                )
            logger.info(f"VIP activated for {tid}: {package_id}")

        elif package_id in CASH_PACKAGES:
            pkg = CASH_PACKAGES[package_id]
            await db.execute(
                "UPDATE players SET cash=cash+? WHERE telegram_id=?",
                (pkg["cash"], tid),
            )
            logger.info(f"Cash added for {tid}: +{pkg['cash']}")

        elif package_id in CASE_PACKAGES:
            pkg = CASE_PACKAGES[package_id]
            for case_id, count in pkg["cases"]:
                for _ in range(count):
                    await db.execute(
                        "INSERT INTO player_cases (telegram_id, case_id) VALUES (?, ?)",
                        (tid, case_id),
                    )
            logger.info(f"Cases added for {tid}: {package_id}")

        elif package_id == "skin_case":
            await db.execute(
                "INSERT INTO player_cases (telegram_id, case_id) VALUES (?, ?)",
                (tid, "skin_case"),
            )
            logger.info(f"Skin case added for {tid}")

        elif package_id == "season_1_premium":
            now = time.time()
            await db.execute(
                "INSERT INTO player_season_pass (telegram_id, season_id, is_premium, purchased_at) VALUES (?,?,1,?) "
                "ON CONFLICT(telegram_id) DO UPDATE SET is_premium=1, purchased_at=?",
                (tid, "season_1", now, now),
            )
            logger.info(f"Season pass premium activated for {tid}")

        else:
            logger.error(f"Unknown package_id: {package_id}")
            await db.close()
            return

        # Log transaction
        await db.execute(
            "INSERT INTO premium_transactions (telegram_id, package_id, payment_method, amount) VALUES (?,?,?,?)",
            (tid, package_id, "stars", str(payment.total_amount)),
        )
        await db.commit()

    except Exception as e:
        logger.error(f"Payment processing error: {e}")
    finally:
        await db.close()


def main():
    proxy_url = os.getenv("PROXY_URL")  # e.g. socks5://user:pass@host:port
    builder = Application.builder().token(BOT_TOKEN)

    if proxy_url:
        request = HTTPXRequest(
            proxy=proxy_url,
            connect_timeout=15.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=15.0,
        )
        builder = builder.request(request).get_updates_request(
            HTTPXRequest(
                proxy=proxy_url,
                connect_timeout=15.0,
                read_timeout=30.0,
                write_timeout=30.0,
                pool_timeout=15.0,
            )
        )

    app = builder.build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    logger.info("Bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
