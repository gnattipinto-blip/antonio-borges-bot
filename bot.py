import os
import logging
from pyairtable import Api
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN")
BASE_ID = "app1iGVSUpnNzLGYK"

ADMINS_RAW = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_RAW.split(",") if x.strip()]

EMPREENDIMENTOS = {
        "1": {"nome": "Antonio Borges 122", "tabela": "unidades"},
        "2": {"nome": "Macairo", "tabela": "macairo"},
        "3": {"nome": "Versalles", "tabela": "versalles"},
        "4": {"nome": "Josefina", "tabela": "josefina"},
        "5": {"nome": "Paulo", "tabela": "paulo"},
        "6": {"nome": "Manoel Duarte", "tabela": "manoel duarte"},
}

api = Api(AIRTABLE_TOKEN)

def is_admin(user_id):
        return not ADMIN_IDS or user_id in ADMIN_IDS

def get_table(tabela):
        return api.table(BASE_ID, tabela)

def get_all(tabela):
        return get_table(tabela).all()

def get_by_status(tabela, status):
        records = get_table(tabela).all()
        return [r for r in records if r["fields"].get("status", "").strip().upper() == status.upper()]

def find_record(tabela, unidade_nome, bloco=None):
        records = get_table(tabela).all()
        for r in records:
                    f = r["fields"]
                    nome = f.get("unidade", f.get("Name", "")).strip().upper()
                    if nome == unidade_nome.strip().upper():
                                    if bloco is None or f.get("bloco", "").strip().upper() == bloco.strip().upper():
                                                        return r
                                            return None

def menu_teclado():
        teclado = []
        for key, val in EMPREENDIMENTOS.items():
                    teclado.append([InlineKeyboardButton(key + " - " + val["nome"], callback_data="emp_" + key)])
                return InlineKeyboardMarkup(teclado)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = "Ola! Escolha o empreendimento:\n\n"
    for key, val in EMPREENDIMENTOS.items():
                msg += key + " - " + val["nome"] + "\n"
            await update.message.reply_text(msg, reply_markup=menu_teclado())

async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = "Escolha o empreendimento:\n\n"
    for key, val in EMPREENDIMENTOS.items():
                msg += key + " - " + val["nome"] + "\n"
            await update.message.reply_text(msg, reply_markup=menu_teclado())

async def callback_empreendimento(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("emp_"):
                key = data.replace("emp_", "")
                if key not in EMPREENDIMENTOS:
                                await query.edit_message_text("Empreendimento invalido.")
                                return
                            emp = EMPREENDIMENTOS[key]
        ctx.user_data["emp_key"] = key
        ctx.user_data["emp_nome"] = emp["nome"]
        ctx.user_data["emp_tabela"] = emp["tabela"]
        teclado = [
                        [InlineKeyboardButton("Todas as unidades", callback_data="acao_todas")],
                        [InlineKeyboardButton("Disponiveis", callback_data="acao_disponiveis")],
                        [InlineKeyboardButton("Resumo", callback_data="acao_resumo")],
                        [InlineKeyboardButton("Voltar ao menu", callback_data="voltar_menu")],
        ]
        await query.edit_message_text(
                        "Empreendimento: " + emp["nome"] + "\n\nEscolha uma opcao:",
                        reply_markup=InlineKeyboardMarkup(teclado)
        )
elif data == "acao_todas":
        tabela = ctx.user_data.get("emp_tabela", "unidades")
        nome = ctx.user_data.get("emp_nome", "")
        records = get_all(tabela)
        if not records:
                        await query.edit_message_text("Nenhuma unidade encontrada.")
                        return
                    blocos = {}
        for r in records:
                        f = r["fields"]
                        bloco = f.get("bloco", "?")
                        if bloco not in blocos:
                                            blocos[bloco] = []
                                        blocos[bloco].append(r)
        linhas = ["Todas as Unidades - " + nome]
        for bloco in sorted(blocos.keys()):
                        linhas.append("\n-- Bloco " + str(bloco) + " --")
            for r in blocos[bloco]:
                                f = r["fields"]
                                status = f.get("status", "?")
                                unidade = f.get("unidade", f.get("Name", "?"))
                                comprador = f.get("comprador", "")
                                linha = status + " " + unidade
                                if comprador:
                                                        linha += " (" + comprador + ")"
                                                    linhas.append(linha)
        teclado = [[InlineKeyboardButton("Voltar", callback_data="emp_" + ctx.user_data.get("emp_key", "1"))]]
        await query.edit_message_text("\n".join(linhas), reply_markup=InlineKeyboardMarkup(teclado))
elif data == "acao_disponiveis":
        tabela = ctx.user_data.get("emp_tabela", "unidades")
        nome = ctx.user_data.get("emp_nome", "")
        records = get_by_status(tabela, "DISPONIVEL")
        if not records:
                        await query.edit_message_text("Nenhuma unidade disponivel no momento.")
            return
        linhas = ["Unidades Disponiveis - " + nome]
        for r in records:
                        f = r["fields"]
            unidade = f.get("unidade", f.get("Name", "?"))
            tipo = f.get("tipo", f.get("Notes", "?"))
            linhas.append("OK " + unidade + " (" + str(tipo) + ")")
        linhas.append("\nTotal: " + str(len(records)) + " disponivel(is)")
        teclado = [[InlineKeyboardButton("Voltar", callback_data="emp_" + ctx.user_data.get("emp_key", "1"))]]
        await query.edit_message_text("\n".join(linhas), reply_markup=InlineKeyboardMarkup(teclado))
elif data == "acao_resumo":
        tabela = ctx.user_data.get("emp_tabela", "unidades")
        nome = ctx.user_data.get("emp_nome", "")
        records = get_all(tabela)
        total = len(records)
        disp = sum(1 for r in records if r["fields"].get("status", "").upper() == "DISPONIVEL")
        res = sum(1 for r in records if r["fields"].get("status", "").upper() == "RESERVADO")
        vend = sum(1 for r in records if r["fields"].get("status", "").upper() == "VENDIDO")
        pct = int((res + vend) / total * 100) if total else 0
        msg = "Resumo - " + nome + "\n\nTotal: " + str(total) + "\nDisponiveis: " + str(disp) + "\nReservadas: " + str(res) + "\nVendidas: " + str(vend) + "\nOcupado: " + str(pct) + "%"
        teclado = [[InlineKeyboardButton("Voltar", callback_data="emp_" + ctx.user_data.get("emp_key", "1"))]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(teclado))
elif data == "voltar_menu":
        msg = "Escolha o empreendimento:\n\n"
        for key, val in EMPREENDIMENTOS.items():
                        msg += key + " - " + val["nome"] + "\n"
        await query.edit_message_text(msg, reply_markup=menu_teclado())

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
    emp_tabela = ctx.user_data.get("emp_tabela", "unidades")
    r = find_record(emp_tabela, unidade, bloco)
    if not r:
                await update.message.reply_text("Unidade " + unidade + " Bloco " + bloco + " nao encontrada.")
        return
    get_table(emp_tabela).update(r["id"], {"status": "RESERVADO", "comprador": comprador})
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
    emp_tabela = ctx.user_data.get("emp_tabela", "unidades")
    r = find_record(emp_tabela, unidade, bloco)
    if not r:
                await update.message.reply_text("Unidade " + unidade + " Bloco " + bloco + " nao encontrada.")
        return
    get_table(emp_tabela).update(r["id"], {"status": "VENDIDO", "comprador": comprador})
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
    emp_tabela = ctx.user_data.get("emp_tabela", "unidades")
    r = find_record(emp_tabela, unidade, bloco)
    if not r:
                await update.message.reply_text("Unidade " + unidade + " nao encontrada.")
        return
    get_table(emp_tabela).update(r["id"], {"status": "DISPONIVEL", "comprador": ""})
    await update.message.reply_text(unidade + " liberada.")

async def cmd_todas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        tabela = ctx.user_data.get("emp_tabela", "unidades")
    nome = ctx.user_data.get("emp_nome", "Antonio Borges 122")
    records = get_all(tabela)
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
    linhas = ["Todas as Unidades - " + nome]
    for bloco in sorted(blocos.keys()):
                linhas.append("\n-- Bloco " + str(bloco) + " --")
        for r in blocos[bloco]:
                        f = r["fields"]
            status = f.get("status", "?")
            unidade = f.get("unidade", f.get("Name", "?"))
            comprador = f.get("comprador", "")
            linha = status + " " + unidade
            if comprador:
                                linha += " (" + comprador + ")"
            linhas.append(linha)
    await update.message.reply_text("\n".join(linhas))

def main():
        app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("todas", cmd_todas))
    app.add_handler(CommandHandler("reservar", cmd_reservar))
    app.add_handler(CommandHandler("vender", cmd_vender))
    app.add_handler(CommandHandler("liberar", cmd_liberar))
    app.add_handler(CallbackQueryHandler(callback_empreendimento))
    app.run_polling()

if __name__ == "__main__":
        main()
