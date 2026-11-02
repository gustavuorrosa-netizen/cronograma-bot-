"""
Bot de Telegram que envia e-mails, transforma cronogramas em calendário
e avisa automaticamente 1 dia antes da prova/trabalho.
"""

import asyncio
import os
import smtplib
import tempfile
import datetime
from email.message import EmailMessage

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from cronograma import encontrar_eventos, extrair_texto_pdf, gerar_ics
import banco # Importa o arquivo do banco de dados que acabamos de criar

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")
CHAT_ID_PERMITIDO = os.getenv("CHAT_ID_PERMITIDO")

DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def autorizado(update: Update) -> bool:
    if not CHAT_ID_PERMITIDO:
        return True
    return str(update.effective_chat.id) == CHAT_ID_PERMITIDO


def enviar_email(assunto: str, corpo: str, anexo: tuple[str, bytes] | None = None) -> None:
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    msg.set_content(corpo)

    if anexo:
        nome, conteudo = anexo
        msg.add_attachment(conteudo, maintype="text", subtype="calendar", filename=nome)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        servidor.send_message(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not autorizado(update):
        return
    await update.message.reply_text(
        "Oi! Eu faço duas coisas:\n"
        "1) /lembrete entregar o T1 na sexta -> mando por e-mail\n"
        "2) Envie o PDF do cronograma -> eu crio um calendário e te aviso 1 dia antes das provas!"
    )


async def lembrete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not autorizado(update):
        return

    texto = " ".join(context.args)

    if not texto:
        await update.message.reply_text("Escreva algo depois do comando. Ex.: /lembrete estudar SQL")
        return

    try:
        enviar_email("Lembrete do bot", texto)
        await update.message.reply_text("E-mail enviado!")
    except Exception as erro:
        print(f"Erro ao enviar e-mail: {erro}")
        await update.message.reply_text("Não consegui enviar o e-mail. Veja o terminal.")


async def receber_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not autorizado(update):
        return

    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("Lendo o cronograma e salvando as datas no banco...")

    with tempfile.TemporaryDirectory() as pasta:
        caminho_pdf = os.path.join(pasta, "cronograma.pdf")
        arquivo = await update.message.document.get_file()
        await arquivo.download_to_drive(caminho_pdf)

        try:
            texto = await asyncio.to_thread(extrair_texto_pdf, caminho_pdf)
        except Exception as erro:
            print(f"Erro ao ler o PDF: {erro}")
            await update.message.reply_text("Não consegui ler esse PDF.")
            return

    eventos = encontrar_eventos(texto)

    if not eventos:
        await update.message.reply_text("Não encontrei provas ou trabalhos com data futura nesse PDF.")
        return

    linhas = []
    for e in eventos:
        linha = f"{e.data:%d/%m} ({DIAS_SEMANA[e.data.weekday()]}) - {e.titulo.split(': ', 1)[-1]}"
        linhas.append(linha)
        # SALVA NO BANCO DE DADOS
        banco.salvar_evento(chat_id, e.data, e.titulo)

    await update.message.reply_text(
        "Encontrei estas datas e já salvei os alertas automáticos para amanhã!\n\n" + "\n".join(linhas)
    )

    conteudo_ics = gerar_ics(eventos).encode("utf-8")
    nome_ics = "provas_e_trabalhos.ics"
    pasta_ics = tempfile.mkdtemp()
    caminho_ics = os.path.join(pasta_ics, nome_ics)
    with open(caminho_ics, "wb") as f:
        f.write(conteudo_ics)

    with open(caminho_ics, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=nome_ics,
            caption="Arquivo de calendário gerado.",
        )


async def verificar_alertas_diarios(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função que roda todo dia de manhã para mandar avisos."""
    eventos_amanha = banco.buscar_eventos_de_amanha()
    
    for evento_id, chat_id, titulo in eventos_amanha:
        mensagem = f"⚠️ *Lembrete Automático!*\nAmanhã você tem: {titulo}"
        try:
            await context.bot.send_message(chat_id=chat_id, text=mensagem, parse_mode='Markdown')
            banco.marcar_como_avisado(evento_id)
            print(f"Aviso enviado para o chat {chat_id}: {titulo}")
        except Exception as erro:
            print(f"Erro ao mandar mensagem para {chat_id}: {erro}")


def main() -> None:
    # Cria o banco de dados se não existir
    banco.conectar()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lembrete", lembrete))
    app.add_handler(MessageHandler(filters.Document.PDF, receber_pdf))
    
    # CONFIGURA O AGENDADOR DIÁRIO
    # Roda todos os dias às 08:00 da manhã (Ajuste o fuso horário se necessário)
    horario_aviso = datetime.time(hour=8, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=-3))) # Fuso de Brasília
    app.job_queue.run_daily(verificar_alertas_diarios, time=horario_aviso)

    print("Bot rodando com agendador... (Ctrl+C para parar)")
    app.run_polling()


if __name__ == "__main__":
    main()
