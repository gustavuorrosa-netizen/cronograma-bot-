"""
Página web (Streamlit): arraste o PDF do plano de ensino e baixe o calendário.

Para rodar:
  pip install -r requirements-web.txt
  streamlit run app_web.py
"""

import os
import tempfile

import streamlit as st

from cronograma import encontrar_eventos, extrair_texto_pdf, gerar_ics

DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

st.set_page_config(page_title="Cronograma → Calendário", page_icon="📅")
st.title("📅 Cronograma → Calendário")
st.write(
    "Envie o PDF do plano de ensino e baixe um arquivo de calendário (.ics) "
    "com as provas, trabalhos e entregas."
)

pdf = st.file_uploader("PDF do plano de ensino", type="pdf")
col1, col2 = st.columns(2)
lembrete = col1.number_input("Avisar quantos dias antes?", min_value=0, max_value=14, value=1)
todas = col2.checkbox("Incluir datas que já passaram")

if pdf is not None:
    # O leitor trabalha com um caminho de arquivo, então salvamos em um arquivo temporário.
    with tempfile.TemporaryDirectory() as pasta:
        caminho = os.path.join(pasta, "plano.pdf")
        with open(caminho, "wb") as f:
            f.write(pdf.getbuffer())
        try:
            texto = extrair_texto_pdf(caminho)
        except Exception as erro:
            st.error(f"Não consegui ler esse PDF: {erro}")
            st.stop()

    eventos = encontrar_eventos(texto, apenas_futuros=not todas)

    if not eventos:
        st.warning("Não encontrei provas ou trabalhos nesse PDF.")
    else:
        st.subheader(f"{len(eventos)} datas encontradas")
        st.table(
            {
                "Data": [f"{e.data:%d/%m/%Y} ({DIAS_SEMANA[e.data.weekday()]})" for e in eventos],
                "O quê": [e.titulo.split(": ", 1)[-1] for e in eventos],
            }
        )
        st.download_button(
            "⬇️ Baixar calendário (.ics)",
            data=gerar_ics(eventos, lembrete_dias=int(lembrete)),
            file_name="provas_e_trabalhos.ics",
            mime="text/calendar",
        )
        st.caption("Abra o arquivo baixado para adicionar tudo ao Google Agenda, Apple Calendar ou Outlook.")
