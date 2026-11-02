"""
Bot de Telegram que envia e-mails interativos em HTML,
transforma cronogramas em calendário e avisa automaticamente 1 dia antes.
"""

import asyncio
import datetime
import os
import smtplib
import tempfile
from email.message import EmailMessage

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import banco
from cronograma import encontrar_eventos, extrair_texto_pdf, gerar_ics

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


def criar_email_interativo(disciplina: str, titulo_evento: str, data_str: str) -> str:
    """Gera o código HTML para um e-mail interativo e adaptado para celulares."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 24px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <div style="background-color: #e74c3c; color: white; padding: 10px 16px; border-radius: 8px; font-weight: bold; display: inline-block; margin-bottom: 16px;">
                ⚠️ Lembrete de Prova / Entrega
            </div>
            
            <h2 style="color: #2c3e50; margin-top: 0;">{disciplina}</h2>
            <p style="font-size: 16px; color: #555;">Você tem um compromisso importante amanhã!</p>
            
            <div style="background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                <strong style="color: #2c3e50; font-size: 18px;">{titulo_evento}</strong><br>
                <span style="color: #7f8c8d; font-size: 14px;">📅 Data: {data_str}</span>
            </div>

            <!-- Botão Interativo -->
            <div style="text-align: center; margin-top: 25px;">
                <a href="https://calendar.google.com" style="background-color: #3498db; color: white; text-decoration: none; padding: 12px 20px; border-radius: 6px; font-weight: bold; display: inline-block; margin: 5px;">
                    📅 Ver na Minha Agenda
                </a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="font-size: 12px; color: #bdc3c7; text-align: center;">Enviado automaticamente pelo seu Bot de Cronograma.</p>
        </div>
    </body>
    </html>
    """


def enviar_email(assunto: str, corpo_texto: str, html_corpo: str | None = None, anexo: tuple[str, bytes] | None = None) -> None:
    """Envia e-mail (suporta texto puro e/ou HTML) via Gmail."""
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO

    msg.set_content(corpo_texto)
    if html_corpo:
        msg.add_alternative(html_corpo, subtype="html")

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
        "2) Envie o PDF do cronograma -> crio o calendário e te aviso por Telegram e e-mail interativo 1 dia antes das provas!"
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
        banco.salvar_evento(chat_id, e.data, e.titulo)

    await update.message.reply_text(
        "Encontrei estas datas e já salvei os alertas automáticos!\n\n" + "\n".join(linhas)
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
            caption="Arquivo de calendário gerado para adicionar à sua agenda.",
        )

    try:
        enviar_email(
            "Provas e trabalhos do semestre",
            "Segue o arquivo de calendário gerado pelo bot:\n\n" + "\n".join(linhas),
            anexo=(nome_ics, conteudo_ics),
        )
    except Exception as erro:
        print(f"Erro ao enviar e-mail inicial: {erro}")


async def verificar_alertas_diarios(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função que roda todo dia de manhã para mandar avisos no Telegram e por E-mail interativo."""
    eventos_amanha = banco.buscar_eventos_de_amanha()
    
    for evento_id, chat_id, titulo in eventos_amanha:
        partes = titulo.split(": ", 1)
        disciplina = partes[0] if len(partes) > 1 else "Disciplina"
        detalhe = partes[1] if len(partes) > 1 else titulo
        amanha_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d/%m/%Y")

        # 1. Envia mensagem no Telegram
        mensagem = f"⚠️ *Lembrete Automático!*\nAmanhã você tem: {titulo}"
        try:
            await context.bot.send_message(chat_id=chat_id, text=mensagem, parse_mode='Markdown')
        except Exception as erro:
            print(f"Erro ao mandar Telegram para {chat_id}: {erro}")

        # 2. Envia E-mail Interativo em HTML
        if EMAIL_DESTINO:
            try:
                html_conteudo = criar_email_interativo(disciplina, detalhe, amanha_str)
                enviar_email(
                    assunto=f"⚠️ Lembrete: {disciplina} amanhã!",
                    corpo_texto=f"Lembrete: amanhã você tem {titulo}",
                    html_corpo=html_conteudo,
                )
                print(f"E-mail interativo enviado para {EMAIL_DESTINO}")
            except Exception as erro:
                print(f"Erro ao enviar e-mail interativo: {erro}")

        banco.marcar_como_avisado(evento_id)


def main() -> None:
    banco.conectar()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lembrete", lembrete))
    app.add_handler(MessageHandler(filters.Document.PDF, receber_pdf))
    
    # Agendador diário às 08:00 (Horário de Brasília)
    horario_aviso = datetime.time(hour=8, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
    app.job_queue.run_daily(verificar_alertas_diarios, time=horario_aviso)

    print("Bot rodando com alertas e e-mails interativos... (Ctrl+C para parar)")
    app.run_polling()


if __name__ == "__main__":
    main()
