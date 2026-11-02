"""
Bot de Telegram que envia e-mails e transforma cronogramas em calendário.

Como funciona:
  1. /lembrete <texto>  -> o bot envia o texto para o seu e-mail.
  2. Você manda o PDF do cronograma da disciplina -> o bot encontra provas,
     trabalhos e entregas, gera um arquivo .ics (abre no Google Agenda,
     Apple Calendar, Outlook) e também envia esse arquivo por e-mail.

Comandos:
  /start            -> mensagem de boas-vindas
  /lembrete <texto> -> envia o texto por e-mail
"""

import asyncio
import os
import smtplib
import tempfile
from email.message import EmailMessage

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from cronograma import encontrar_eventos, extrair_texto_pdf, gerar_ics

# Carrega as variáveis do arquivo .env (token, e-mail, senha)
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")
# Opcional: se preenchido, só esse chat pode usar o bot (evita estranhos usando o seu e-mail)
CHAT_ID_PERMITIDO = os.getenv("CHAT_ID_PERMITIDO")

DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def autorizado(update: Update) -> bool:
    """Confere se quem mandou a mensagem pode usar o bot."""
    if not CHAT_ID_PERMITIDO:
        return True
    return str(update.effective_chat.id) == CHAT_ID_PERMITIDO


def enviar_email(assunto: str, corpo: str, anexo: tuple[str, bytes] | None = None) -> None:
    """Envia um e-mail pelo Gmail. 'anexo' é (nome_do_arquivo, conteúdo_em_bytes)."""
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    msg.set_content(corpo)

    if anexo:
        nome, conteudo = anexo
        msg.add_attachment(conteudo, maintype="text", subtype="calendar", filename=nome)

    # Conecta no Gmail de forma segura (porta 465 = SSL)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        servidor.send_message(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /start."""
    if not autorizado(update):
        return
    await update.message.reply_text(
        "Oi! Eu faço duas coisas:\n"
        "1) /lembrete entregar o T1 na sexta -> mando por e-mail\n"
        "2) Envie o PDF do cronograma da disciplina -> eu marco provas e "
        "trabalhos no seu calendário"
    )


async def lembrete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /lembrete <texto> enviando um e-mail."""
    if not autorizado(update):
        return

    # context.args é a lista de palavras depois do comando
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
    """Recebe o PDF do cronograma, acha as datas importantes e gera o .ics."""
    if not autorizado(update):
        return

    await update.message.reply_text("Lendo o cronograma...")

    with tempfile.TemporaryDirectory() as pasta:
        caminho_pdf = os.path.join(pasta, "cronograma.pdf")
        arquivo = await update.message.document.get_file()
        await arquivo.download_to_drive(caminho_pdf)

        try:
            # Ler PDF demora um pouco: roda em outra thread para não travar o bot
            texto = await asyncio.to_thread(extrair_texto_pdf, caminho_pdf)
        except Exception as erro:
            print(f"Erro ao ler o PDF: {erro}")
            await update.message.reply_text("Não consegui ler esse PDF.")
            return

    eventos = encontrar_eventos(texto)  # só datas que ainda não passaram

    if not eventos:
        await update.message.reply_text(
            "Não encontrei provas ou trabalhos com data futura nesse PDF."
        )
        return

    # Resumo das datas encontradas
    linhas = [
        f"{e.data:%d/%m} ({DIAS_SEMANA[e.data.weekday()]}) - {e.titulo.split(': ', 1)[-1]}"
        for e in eventos
    ]
    await update.message.reply_text("Encontrei estas datas:\n\n" + "\n".join(linhas))

    # Gera o .ics e manda no Telegram (toque no arquivo para adicionar ao calendário)
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
            caption="Abra este arquivo para adicionar tudo ao calendário (com lembrete 1 dia antes).",
        )

    # Também manda o .ics por e-mail
    try:
        enviar_email(
            "Provas e trabalhos do semestre",
            "Segue o arquivo de calendário gerado pelo bot:\n\n" + "\n".join(linhas),
            anexo=(nome_ics, conteudo_ics),
        )
        await update.message.reply_text("Também enviei por e-mail.")
    except Exception as erro:
        print(f"Erro ao enviar e-mail: {erro}")


def main() -> None:
    """Liga o bot e fica esperando mensagens."""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lembrete", lembrete))
    app.add_handler(MessageHandler(filters.Document.PDF, receber_pdf))
    print("Bot rodando... (Ctrl+C para parar)")
    app.run_polling()


if __name__ == "__main__":
    main()
