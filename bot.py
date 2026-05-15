import os
import logging
import unicodedata
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TELEGRAM_TOKEN")

ADMINS_RAW = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_RAW.split(",") if x.strip()]

UNIDADES = {}
for bloco in ["A", "B"]:
    for andar in range(1, 4):
        for apto in range(1, 4):
            nome = "Apto " + str(andar) + "0" + str(apto)
            chave = nome + "-" + bloco
            UNIDADES[chave] = {"unidade": nome, "bloco": "Bloco " + bloco, "tipo": "2 Qtos", "status": "DISPONIVEL", "comprador": ""}

def is_admin(user_id):
    return not ADMIN_IDS or user_id in ADMIN_IDS

def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def buscar_unidade(nome):
    nome = nome.strip().upper()
    for chave, u in UNIDADES.items():
        if u["unidade"].upper() == nome:
            return chave, u
    return None, None

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = "Bot Antonio Borges 122\n\n/disponiveis - Unidades disponiveis\n/todas - Todas as unidades\n/resumo - Resumo geral\n\nAdmins:\n/reservar Apto 101 Nome\n/vender Apto 101 Nome\n/liberar Apto 101"
    await update.message.reply_text(msg)

async def cmd_disponiveis(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    disp = [u for u in UNIDADES.values() if u["status"] == "DISPONIVEL"]
    if not disp:
        await update.message.reply_text("Nenhuma unidade disponivel no momento.")
        return
    linhas = ["OK " + u["unidade"] + " - " + u["bloco"] + " (" + u["tipo"] + ")" for u in disp]
    msg = "Unidades Disponiveis - Antonio Borges 122\n\n" + "\n".join(linhas)
    msg += "\n\nTotal: " + str(len(disp)) + " disponivel(is)"
    await update.message.reply_text(msg)

async def cmd_todas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    linhas = []
    bloco_atual = ""
    for u in UNIDADES.values():
        if u["bloco"] != bloco_atual:
            bloco_atual = u["bloco"]
            linhas.append("\n-- " + bloco_atual + " --")
        comp = " -> " + u["comprador"] if u["comprador"] else ""
        linhas.append(u["status"] + " " + u["unidade"] + comp)
    await update.message.reply_text("Todas as Unidades - Antonio Borges 122\n" + "\n".join(linhas))

async def cmd_resumo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    total = len(UNIDADES)
    disp = sum(1 for u in UNIDADES.values() if u["status"] == "DISPONIVEL")
    res = sum(1 for u in UNIDADES.values() if u["status"] == "RESERVADO")
    vend = sum(1 for u in UNIDADES.values() if u["status"] == "VENDIDO")
    pct = ((res + vend) / total * 100) if total else 0
    msg = "Resumo Antonio Borges 122\n\nTotal: " + str(total) + "\nDisponiveis: " + str(disp) + "\nReservadas: " + str(res) + "\nVendidas: " + str(vend) + "\nOcupado: " + str(int(pct)) + "%"
    await update.message.reply_text(msg)

async def cmd_reservar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Apenas admins.")
        return
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text("Uso: /reservar Apto 101 Nome")
        return
    nome = args[0] + " " + args[1]
    comprador = " ".join(args[2:])
    chave, u = buscar_unidade(nome)
    if not u:
        await update.message.reply_text("Unidade " + nome + " nao encontrada.")
        return
    UNIDADES[chave]["status"] = "RESERVADO"
    UNIDADES[chave]["comprador"] = comprador
    await update.message.reply_text(nome + " reservada para " + comprador + ".")

async def cmd_vender(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Apenas admins.")
        return
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text("Uso: /vender Apto 101 Nome")
        return
    nome = args[0] + " " + args[1]
    comprador = " ".join(args[2:])
    chave, u = buscar_unidade(nome)
    if not u:
        await update.message.reply_text("Unidade " + nome + " nao encontrada.")
        return
    UNIDADES[chave]["status"] = "VENDIDO"
    UNIDADES[chave]["comprador"] = comprador
    await update.message.reply_text(nome + " vendida para " + comprador + ".")

async def cmd_liberar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Apenas admins.")
        return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /liberar Apto 101")
        return
    nome = args[0] + " " + args[1]
    chave, u = buscar_unidade(nome)
    if not u:
        await update.message.reply_text("Unidade " + nome + " nao encontrada.")
        return
    UNIDADES[chave]["status"] = "DISPONIVEL"
    UNIDADES[chave]["comprador"] = ""
    await update.message.reply_text(nome + " disponivel novamente.")

async def resposta_livre(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    texto = sem_acento((update.message.text or "").lower())
    palavras_disp = ["disponivel", "disponiveis", "livre", "livres", "quais", "qual", "ta", "tem", "sobrou"]
    palavras_resumo = ["resumo", "quantas", "total", "quanto", "vendida", "vendidas"]
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
    print("Bot rodando v4")
    app.run_polling()

if __name__ == "__main__":
    main()
