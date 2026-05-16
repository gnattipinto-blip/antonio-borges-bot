import os
import logging
from pyairtable import Api
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN")
BASE_ID = "app1iGVSUpnNzLGYK"
TABLE_NAME = "unidades"

ADMINS_RAW = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_RAW.split(",") if x.strip()]

api = Api(AIRTABLE_TOKEN)
table = api.table(BASE_ID, TABLE_NAME)

def is_admin(user_id):
    return not ADMIN_IDS or user_id in ADMIN_IDS

def get_all():
    return table.all()

def get_by_status(status):
    records = table.all()
    return [r for r in records if r["fields"].get("status", "").strip().upper() == status.upper()]

def find_record(unidade_nome, bloco=None):
    records = table.all()
    for r in records:
        f = r["fields"]
        nome = f.get("unidade", "").strip().upper()
        if nome == unidade_nome.strip().upper():
            if bloco is None or f.get("bloco", "").strip().upper() == bloco.strip().upper():
                return r
    return None

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = "Bot Antonio Borges 122\n\n/disponiveis - Unidades disponiveis\n/todas - Todas as unidades\n/resumo - Resumo geral\n\nAdmins:\n/reservar AP 101 A Nome\n/vender AP 101 A Nome\n/liberar AP 101 A"
    await update.message.reply_text(msg)

async def cmd_todas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    records = get_all()
    if not records:
        await update.message.reply_text("Nenhuma unidade encontrada.")
        return
    blocos = {}
    for r in records:
        f = r["fields"]
        bloco = f.get("bloco", "?")
        if bloco not in blocos:
            blocos[bloco] = []
        blocos[bloco].append(r)
    linhas = ["Todas as Unidades - Antonio Borges 122"]
    for bloco in sorted(blocos.keys()):
        linhas.append("\n-- Bloco " + bloco + " --")
        for r in blocos[bloco]:
            f = r["fields"]
            status = f.get("status", "?")
            unidade = f.get("unidade", "?")
            comprador = f.get("comprador", "")
            linha = status + " " + unidade
            if comprador:
                linha += " (" + comprador + ")"
            linhas.append(linha)
    await update.message.reply_text("\n".join(linhas))

async def cmd_disponiveis(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    records = get_by_status("DISPONIVEL")
    if not records:
        await update.message.reply_text("Nenhuma unidade disponivel no momento.")
        return
    blocos = {}
    for r in records:
        f = r["fields"]
        bloco = f.get("bloco", "?")
        if bloco not in blocos:
            blocos[bloco] = []
        blocos[bloco].append(r)
    linhas = ["Unidades Disponiveis - Antonio Borges 122"]
    for bloco in sorted(blocos.keys()):
        linhas.append("\n-- Bloco " + bloco + " --")
        for r in blocos[bloco]:
            f = r["fields"]
            unidade = f.get("unidade", "?")
            tipo = f.get("tipo", "?")
            linhas.append("OK " + unidade + " (" + tipo + ")")
    linhas.append("\nTotal: " + String(records.length) + " disponivel(is)")
    await update.message.reply_text("\n".join(linhas))

async def cmd_resumo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    records = get_all()
    total = len(records)
    disp = sum(1 for r in records if r["fields"].get("status", "").upper() == "DISPONIVEL")
    res = sum(1 for r in records if r["fields"].get("status", "").upper() == "RESERVADO")
    vend = sum(1 for r in records if r["fields"].get("status", "").upper() == "VENDIDO")
    pct = int((res + vend) / total * 100) if total else 0
    msg = "Resumo Antonio Borges 122\n\nTotal: " + str(total) + "\nDisponiveis: " + str(disp) + "\nReservadas: " + str(res) + "\nVendidas: " + str(vend) + "\nOcupado: " + str(pct) + "%"
    await update.message.reply_text(msg)

async def cmd_reservar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Apenas admins.")
        return
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text("Uso: /reservar AP 101 A Nome Completo")
        return
    unidade = args[0] + " " + args[1]
    bloco = args[2]
    comprador = " ".join(args[3:])
    r = find_record(unidade, bloco)
    if not r:
        await update.message.reply_text("Unidade " + unidade + " Bloco " + bloco + " nao encontrada.")
        return
    table.update(r["id"], {"status": "RESERVADO", "comprador": comprador})
    await update.message.reply_text(unidade + " Bloco " + bloco + " reservada para " + comprador + ".")

async def cmd_vender(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Apenas admins.")
        return
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text("Uso: /vender AP 101 A Nome Completo")
        return
    unidade = args[0] + " " + args[1]
    bloco = args[2]
    comprador = " ".join(args[3:])
    r = find_record(unidade, bloco)
    if not r:
        await update.message.reply_text("Unidade " + unidade + " Bloco " + bloco + " nao encontrada.")
        return
    table.update(r["id"], {"status": "VENDIDO", "comprador": comprador})
    await update.message.reply_text(unidade + " Bloco " + bloco + " vendida para " + comprador + ".")

async def cmd_liberar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Apenas admins.")
        return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /liberar AP 101 A")
        return
    unidade = args[0] + " " + args[1]
    bloco = args[2] if len(args) > 2 else None
    r = find_record(unidade, bloco)
    if not r:
        await update.message.reply_text("Unidade " + unidade + " nao encontrada.")
        return
    table.update(r["id"], {"status": "DISPONIVEL", "comprador": ""})
    await update.message.reply_text(unidade + " liberada e disponivel novamente.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("todas", cmd_todas))
    app.add_handler(CommandHandler("disponiveis", cmd_disponiveis))
    app.add_handler(CommandHandler("resumo", cmd_resumo))
    app.add_handler(CommandHandler("reservar", cmd_reservar))
    app.add_handler(CommandHandler("vender", cmd_vender))
    app.add_handler(CommandHandler("liberar", cmd_liberar))
    app.run_polling()

if __name__ == "__main__":
    main()
