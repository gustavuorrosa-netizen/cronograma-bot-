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

# Linha do cronograma com dia/mês e ano opcional (ex: "16 24/09/2026 ..." ou "14 17/9 ...")
LINHA_AULA = re.compile(r"^(?:\d+|-)\s+(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+(.+)$")


@dataclass
class Evento:
    data: date
    titulo: str


# Reconhece datas no formato DD/MM ou DD/MM/YYYY
DATA_CELULA = re.compile(r"^\d{1,2}/\d{1,2}(?:/\d{2,4})?$")


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
                    # Procura o número da aula nas células anteriores; se houver texto como "QUI", usa "-"
                    aula = next((c for c in celulas[:i] if c.isdigit()), "-")
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
    """Procura 'SEMESTRE: 2026/2'. Se não achar, usa o ano atual."""
    achou = re.search(r"SEMESTRE:\s*(\d{4})", texto)
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

    for linha in texto.splitlines():
        achou = LINHA_AULA.match(linha.strip())
        if not achou:
            continue

        dia = int(achou.group(1))
        mes = int(achou.group(2))
        ano_cap = achou.group(3)
        conteudo = achou.group(4)

        if not PALAVRAS_CHAVE.search(conteudo):
            continue

        ano = int(ano_cap) if ano_cap else ano_padrao

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
