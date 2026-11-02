def criar_email_interativo(disciplina: str, titulo_evento: str, data_str: str) -> str:
    """Gera o código HTML para um e-mail interativo e bonito no celular."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 24px; shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <div style="background-color: #e74c3c; color: white; padding: 10px 16px; border-radius: 8px; font-weight: bold; display: inline-block; margin-bottom: 16px;">
                ⚠️ Lembrete de Prova / Entrega
            </div>
            
            <h2 style="color: #2c3e50; margin-top: 0;">{disciplina}</h2>
            <p style="font-size: 16px; color: #555;">Você tem um compromisso importante amanhã!</p>
            
            <div style="background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                <strong style="color: #2c3e50; font-size: 18px;">{titulo_evento}</strong><br>
                <span style="color: #7f8c8d; font-size: 14px;">📅 Data: {data_str}</span>
            </div>

            <!-- Botões Interativos -->
            <div style="text-align: center; margin-top: 25px;">
                <a href="https://calendar.google.com" style="background-color: #3498db; color: white; text-decoration: none; padding: 12px 20px; border-radius: 6px; font-weight: bold; display: inline-block; margin: 5px;">
                    📅 Ver na Minha Agenda
                </a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="font-size: 12px; color: #bdc3c7; text-align: center;">Enviado automaticamente pelo seu Bot de Cronograma.</p>
        </div>
        def enviar_email_interativo(assunto: str, html_corpo: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    
    # Define o conteúdo como HTML
    msg.add_alternative(html_corpo, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        servidor.send_message(msg)
    </body>
    </html>
    """
