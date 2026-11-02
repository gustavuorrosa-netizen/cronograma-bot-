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
PALAVRAS_CHAVE = re.compile(
    r"\b(prova|trabalho|entrega|exame|p1|p2|ps|g2|t1|t2|avaliação|avaliativa|substituição)\b",
    re.IGNORECASE,
)

# Reconhece datas no formato DD/MM ou DD/MM/YYYY em qualquer lugar da linha
REGEX_DATA = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")


@dataclass
class Evento:
    data: date
    titulo: str


def _linhas_das_tabelas(pagina) -> list[str]:
    """Lê as tabelas da página e devolve o conteúdo de cada linha como texto simples."""
    linhas = []
    for tabela in pagina.extract_tables():
        for linha in tabela:
            celulas = [" ".join((c or "").split()) for c in linha if c]
            if celulas:
                linhas.append(" ".join(celulas))
    return linhas


def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Extrai o texto do PDF, combinando o texto corrido e as tabelas."""
    import pdfplumber

    paginas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            linhas_tabela = _linhas_das_tabelas(pagina)
            if linhas_tabela:
                texto += "\n" + "\n".join(linhas_tabela)
            paginas.append(texto)
    return "\n".join(paginas)


def _descobrir_ano(texto: str) -> int:
    """Procura 'SEMESTRE: 2026/2' ou ano de 4 dígitos. Se não achar, usa o ano atual."""
    achou = re.search(r"\b(20\d{2})\b", texto)
    return int(achou.group(1)) if achou else date.today().year


def _descobrir_disciplina(texto: str) -> str:
    """Procura 'DISCIPLINA: NOME'. Se não achar, devolve um nome genérico."""
    achou = re.search(r"DISCIPLINA:\s*(.+)", texto)
    return achou.group(1).strip().title() if achou else "Disciplina"


def encontrar_eventos(texto: str, apenas_futuros: bool = True) -> list[Evento]:
    """Devolve a lista de provas/trabalhos/entregas encontrados no texto."""
    ano_padrao = _descobrir_ano(texto)
    disciplina = _descobrir_disciplina(texto)
    hoje = date.today()
    eventos: list[Evento] = []
    vistos = set()

    for linha in texto.splitlines():
        linha_limpa = linha.strip()
        if not linha_limpa:
            continue

        match_data = REGEX_DATA.search(linha_limpa)
        if match_data and PALAVRAS_CHAVE.search(linha_limpa):
            dia = int(match_data.group(1))
            mes = int(match_data.group(2))
            ano_str = match_data.group(3)

            if ano_str:
                ano = int(ano_str) if len(ano_str) == 4 else 2000 + int(ano_str)
            else:
                ano = ano_padrao

            try:
                data_evento = date(ano, mes, dia)
            except ValueError:
                continue

            if apenas_futuros and data_evento < hoje:
                continue

            chave = (data_evento, linha_limpa[:40])
            if chave in vistos:
                continue
            vistos.add(chave)

            # Limpa o resumo retirando horários repetitivos se existirem
            resumo = re.sub(r"\b\d{2}:\d{2}\s*-\s*\d{2}:\d{2}\b", "", linha_limpa).strip()
            resumo = re.sub(r"\s+", " ", resumo)[:80]

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
