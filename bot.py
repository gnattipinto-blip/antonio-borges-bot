import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from unidades import (
    listar_disponiveis, listar_todas, marcar_reservado,
    marcar_vendido, marcar_disponivel, resumo
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = "8955757103:AAHShN1V8jD7eJbUh5lFo1p0X7uKSLW8fwo"
ADMINS_RAW = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_RAW.split(",") if x.strip()]

def is_admin(user_id):
    return not ADMIN_IDS or user_id in ADMIN_IDS

async def cmd_start(update, ctx):
    msg = (
        "🏗️ *Bot – Antônio Borges 122*\n\n"
        "📋 /disponiveis – Unidades disponíveis\n"
        "📊 /todas – Todas as unidades\n"
        "📈 /resumo – Resumo geral\n\n"
        "_Admins:_\n"
        "🔒 /reservar Apto 101 Nome\n"
        "✅ /vender Apto 101 Nome\n"
        "🔓 /liberar Apto 101"
    )
    await update.message.reply_markdown(msg)

async def cmd_disponiveis(update, ctx):
    unidades = listar_disponiveis()
    if not unidades:
        await update.message.reply_text("😔 Nenhuma unidade disponível.")
        return
    linhas = [f"✅ *{u['unidade']}* – {u['bloco']} ({u['tipo']})" for u in unidades]
    msg = "🏠 *Unidades Disponíveis – Antônio Borges 122*\n\n" + "\n".join(linhas)
    msg += f"\n\n_Total: {len(unidades)} disponível(is)_"
    await update.message.reply_markdown(msg)

async def cmd_todas(update, ctx):
    unidades = listar_todas()
    icones = {"DISPONÍVEL": "✅", "RESERVADO": "🔒", "VENDIDO": "❌"}
    linhas = []
    bloco_atual = ""
    for u in unidades:
        if u["bloco"] != bloco_atual:
            bloco_atual = u["bloco"]
            linhas.append(f"\n*── {bloco_atual} ──*")
        ic = icones.get(u["status"], "❓")
        comp = f" → _{u['comprador']}_" if u["comprador"] else ""
        linhas.append(f"{ic} {u['unidade']}{comp}")
    msg = "📋 *Todas as Unidades*\n" + "\n".join(linhas)
    await update.message.reply_markdown(msg)

async def cmd_resumo(update, ctx):
    r = resumo()
    msg = (
        f"📊 *Resumo – Antônio Borges 122*\n\n"
        f"🏗️ Total: *{r['total']}*\n"
        f"✅ Disponíveis: *{r['disponiveis']}*\n"
        f"🔒 Reservadas: *{r['reservadas']}*\n"
        f"❌ Vendidas: *{r['vendidas']}*\n"
        f"📈 Ocupado: *{r['pct_ocupado']:.0f}%*"
    )
    await update.message.reply_markdown(msg)

async def cmd_reservar(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Apenas admins.")
        return
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text("❌ Uso: /reservar Apto 101 Nome")
        return
    unidade = f"{args[0]} {args[1]}"
    comprador = " ".join(args[2:])
    ok, msg = marcar_reservado(unidade, comprador)
    await update.message.reply_markdown(msg)

async def cmd_vender(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Apenas admins.")
        return
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text("❌ Uso: /vender Apto 101 Nome")
        return
    unidade = f"{args[0]} {args[1]}"
    comprador = " ".join(args[2:])
    ok, msg = marcar_vendido(unidade, comprador)
    await update.message.reply_markdown(msg)

async def cmd_liberar(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Apenas admins.")
        return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("❌ Uso: /liberar Apto 101")
        return
    unidade = f"{args[0]} {args[1]}"
    ok, msg = marcar_disponivel(unidade)
    await update.message.reply_markdown(msg)

async def resposta_livre(update, ctx):
    texto = (update.message.text or "").lower()
    palavras_disp = ["disponível", "disponíveis", "livre", "livres", "quais", "tem"]
    palavras_resumo = ["resumo", "quantas", "total"]
    if any(p in texto for p in palavras_disp):
        await cmd_disponiveis(update, ctx)
    elif any(p in texto for p in palavras_resumo):
        await cmd_resumo(update, ctx)
    else:
        await update.message.reply_text("Use /disponiveis, /todas ou /resumo.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("disponiveis", cmd_disponiveis))
    app.add_handler(CommandHandler("todas", cmd_todas))
    app.add_handler(CommandHandler("resumo", cmd_resumo))
    app.add_handler(CommandHandler("reservar", cmd_reservar))
    app.add_handler(CommandHandler("vender", cmd_vender))
    app.add_handler(CommandHandler("liberar", cmd_liberar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, resposta_livre))
    print("✅ Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
