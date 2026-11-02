"""
Lê o texto de um cronograma de aulas (PDF da faculdade), encontra provas,
trabalhos e entregas e gera um arquivo .ics que abre em qualquer calendário
(Google Agenda, Apple Calendar, Outlook).
"""

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

# Palavras que indicam uma data importante
PALAVRAS_CHAVE = re.compile(r"\b(prova|trabalho|entrega|exame)\b", re.IGNORECASE)

# Linha do cronograma no formato: "14 17/9 Prova 1 (P1) - ..." (aula, data, conteúdo)
LINHA_AULA = re.compile(r"^(?:\d+|-)\s+(\d{1,2})/(\d{1,2})\s+(.+)$")


@dataclass
class Evento:
    data: date
    titulo: str


DATA_CELULA = re.compile(r"^\d{1,2}/\d{1,2}$")


def _linhas_das_tabelas(pagina) -> list[str]:
    """
    Lê as tabelas da página e devolve cada linha como "aula data conteúdo".
    """
    linhas = []
    for tabela in pagina.extract_tables():
        for linha in tabela:
            celulas = [" ".join((c or "").split()) for c in linha]
            celulas = [c for c in celulas if c]
            for i, celula in enumerate(celulas):
                if DATA_CELULA.match(celula) and i + 1 < len(celulas):
                    aula = celulas[i - 1] if i > 0 else "-"
                    
                    # Pega TODAS as colunas depois da data e junta num texto só
                    conteudo = " ".join(celulas[i + 1:])
                    
                    linhas.append(f"{aula} {celula} {conteudo}")
                    break
    return linhas


def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Extrai o texto do PDF, usando as tabelas para as linhas do cronograma."""
    import pdfplumber

    paginas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            linhas_tabela = _linhas_das_tabelas(pagina)
            if linhas_tabela:
                texto = "\n".join(
                    l for l in texto.splitlines() if not LINHA_AULA.match(l.strip())
                )
                texto += "\n" + "\n".join(linhas_tabela)
            paginas.append(texto)
    return "\n".join(paginas)


def _descobrir_ano(texto: str) -> int:
    achou = re.search(r"SEMESTRE:\s*(\d{4})", texto)
    return int(achou.group(1)) if achou else date.today().year


def _descobrir_disciplina(texto: str) -> str:
    achou = re.search(r"DISCIPLINA:\s*(.+)", texto)
    return achou.group(1).strip().title() if achou else "Disciplina"


def encontrar_eventos(texto: str, apenas_futuros: bool = True) -> list[Evento]:
    ano = _descobrir_ano(texto)
    disciplina = _descobrir_disciplina(texto)
    hoje = date.today()
    eventos: list[Evento] = []

    for linha in texto.splitlines():
        achou = LINHA_AULA.match(linha.strip())
        if not achou:
            continue

        dia, mes, conteudo = int(achou.group(1)), int(achou.group(2)), achou.group(3)
        if not PALAVRAS_CHAVE.search(conteudo):
            continue

        try:
            data_evento = date(ano, mes, dia)
        except ValueError:
            continue

        if apenas_futuros and data_evento < hoje:
            continue

        resumo = conteudo.strip()[:70]
        eventos.append(Evento(data_evento, f"{disciplina}: {resumo}"))

    return eventos


def _escapar(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")


def gerar_ics(eventos: list[Evento], lembrete_dias: int = 1) -> str:
    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bot Cronograma//PT-BR//",
        "CALSCALE:GREGORIAN",
    ]

    for ev in eventos:
        fim = ev.data + timedelta(days=1)
        linhas += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@bot-cronograma",
            f"DTSTAMP:{agora}",
            f"DTSTART;VALUE=DATE:{ev.data:%Y%m%d}",
            f"DTEND;VALUE=DATE:{fim:%Y%m%d}",
            f"SUMMARY:{_escapar(ev.titulo)}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_escapar(ev.titulo)}",
            f"TRIGGER:-P{lembrete_dias}D",
            "END:VALARM",
            "END:VEVENT",
        ]

    linhas.append("END:VCALENDAR")
    return "\r\n".join(linhas) + "\r\n"
