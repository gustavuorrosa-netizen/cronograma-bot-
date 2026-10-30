"""
Lê o texto de um cronograma de aulas (PDF da faculdade), encontra provas,
trabalhos e entregas e gera um arquivo .ics que abre em qualquer calendário
(Google Agenda, Apple Calendar, Outlook).

Formatos de linha aceitos (a coluna da aula é opcional):
  "14 17/9 Prova 1 (P1) - ..."        (aula, data, conteúdo)
  "23/11 2AB Prova 2 – P2 ..."        (data, dia/hora, conteúdo)
"""

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

# Palavras que indicam uma data importante (PS = prova de substituição, G1/G2 = graus)
PALAVRAS_CHAVE = re.compile(r"\b(prova|trabalho|entrega|exame|PS|G1|G2)\b", re.IGNORECASE)

# Linha do cronograma: [número da aula ou "-"] data conteúdo
LINHA_AULA = re.compile(r"^(?:(?:\d+|-)\s+)?(\d{1,2})/(\d{1,2})\s+(.+)$")

# Células que não são o conteúdo: datas ("23/11") e códigos de dia/hora ("2AB", "4AB")
DATA_CELULA = re.compile(r"^\d{1,2}/\d{1,2}$")
CODIGO_HORARIO = re.compile(r"^\d[A-Z]{1,3}$")

# Siglas que aparecem sozinhas na linha e ficam mais claras por extenso
SIGLAS = {
    "PS": "Prova de Substituição (PS)",
    "G1": "Grau 1 (G1)",
    "G2": "Grau 2 (G2)",
}

PALAVRAS_MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "para"}


@dataclass
class Evento:
    data: date
    titulo: str


def _linhas_das_tabelas(pagina) -> list[str]:
    """
    Lê as tabelas da página e devolve cada linha como "aula data conteúdo".

    Isso é necessário porque, no texto corrido, uma célula com várias linhas
    (ex.: aula 31) é quebrada e a data fica separada das palavras-chave.
    """
    linhas = []
    for tabela in pagina.extract_tables():
        for linha in tabela:
            # Células mescladas aparecem como None (ou repetidas); guardamos só as com texto.
            celulas = [" ".join((c or "").split()) for c in linha]
            celulas = [c for c in celulas if c]
            for i, celula in enumerate(celulas):
                if not DATA_CELULA.match(celula):
                    continue
                aula = celulas[i - 1] if i > 0 else "-"
                # O conteúdo é a primeira célula depois da data que não seja
                # outra data (célula mesclada repetida) nem código de horário.
                conteudo = next(
                    (
                        c
                        for c in celulas[i + 1:]
                        if not DATA_CELULA.match(c) and not CODIGO_HORARIO.match(c)
                    ),
                    None,
                )
                if conteudo:
                    linhas.append(f"{aula} {celula} {conteudo}")
                break
    return linhas


def extrair_texto_pdf(caminho_pdf: str) -> str:
    """
    Extrai o texto do PDF. As linhas montadas a partir das tabelas vêm
    primeiro (são mais completas); o texto corrido vem depois como reserva.
    """
    import pdfplumber  # importado aqui para o resto do código funcionar sem ele

    paginas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            linhas_tabela = _linhas_das_tabelas(pagina)
            if linhas_tabela:
                texto = "\n".join(linhas_tabela) + "\n" + texto
            paginas.append(texto)
    return "\n".join(paginas)


def _descobrir_ano(texto: str) -> int:
    """Procura 'SEMESTRE: 2026/2'. Se não achar, usa o ano atual."""
    achou = re.search(r"SEMESTRE:\s*(\d{4})", texto)
    return int(achou.group(1)) if achou else date.today().year


def _capitalizar(nome: str) -> str:
    """'FUNDAMENTOS DE SISTEMAS DIGITAIS' -> 'Fundamentos de Sistemas Digitais'."""
    palavras = nome.lower().split()
    return " ".join(
        p if (i > 0 and p in PALAVRAS_MINUSCULAS) else p.capitalize()
        for i, p in enumerate(palavras)
    )


def _descobrir_disciplina(texto: str) -> str:
    """Procura 'DISCIPLINA: NOME' (sem o 'TURMA: ...' que pode vir na mesma linha)."""
    achou = re.search(r"DISCIPLINA:\s*(.+?)(?:\s+TURMA:.*)?$", texto, re.MULTILINE)
    return _capitalizar(achou.group(1)) if achou else "Disciplina"


def _resumir(conteudo: str, limite: int = 70) -> str:
    """Limpa e encurta o texto sem cortar uma palavra no meio (termina com '…')."""
    conteudo = conteudo.strip()
    # Tira o "tipo de atividade", que não ajuda no título do evento
    conteudo = re.sub(
        r"\s*(Atividade avaliativa|Aula expositiva e dialogada)\.?\s*$", "", conteudo
    ).strip()
    if conteudo.upper() in SIGLAS:
        return SIGLAS[conteudo.upper()]
    if len(conteudo) <= limite:
        return conteudo
    return conteudo[:limite].rsplit(" ", 1)[0].rstrip(" .,;:&-") + "…"


def encontrar_eventos(texto: str, apenas_futuros: bool = True) -> list[Evento]:
    """Devolve a lista de provas/trabalhos/entregas encontrados no texto, em ordem de data."""
    ano = _descobrir_ano(texto)
    disciplina = _descobrir_disciplina(texto)
    hoje = date.today()
    eventos: list[Evento] = []
    datas_vistas: set[date] = set()

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
            continue  # data inválida, ignora a linha

        if apenas_futuros and data_evento < hoje:
            continue

        # A mesma data pode aparecer na tabela e no texto corrido: fica a primeira.
        if data_evento in datas_vistas:
            continue
        datas_vistas.add(data_evento)

        eventos.append(Evento(data_evento, f"{disciplina}: {_resumir(conteudo)}"))

    return sorted(eventos, key=lambda e: e.data)


def _escapar(texto: str) -> str:
    """Escapa caracteres especiais do formato iCalendar."""
    return texto.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")


def gerar_ics(eventos: list[Evento], lembrete_dias=1) -> str:
    """
    Monta o conteúdo de um arquivo .ics com eventos de dia inteiro.

    lembrete_dias: quantos dias antes avisar. Aceita um número (1) ou uma
    lista (por exemplo [7, 1] para avisar 1 semana e 1 dia antes).
    """
    if isinstance(lembrete_dias, int):
        lembrete_dias = [lembrete_dias]
    avisos = sorted({d for d in lembrete_dias if d > 0}, reverse=True)

    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bot Cronograma//PT-BR//",
        "CALSCALE:GREGORIAN",
    ]

    for ev in eventos:
        fim = ev.data + timedelta(days=1)  # evento de dia inteiro termina no dia seguinte
        linhas += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@bot-cronograma",
            f"DTSTAMP:{agora}",
            f"DTSTART;VALUE=DATE:{ev.data:%Y%m%d}",
            f"DTEND;VALUE=DATE:{fim:%Y%m%d}",
            f"SUMMARY:{_escapar(ev.titulo)}",
        ]
        for dias in avisos:  # um alerta (VALARM) para cada antecedência
            linhas += [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{_escapar(ev.titulo)}",
                f"TRIGGER:-P{dias}D",
                "END:VALARM",
            ]
        linhas.append("END:VEVENT")

    linhas.append("END:VCALENDAR")
    return "\r\n".join(linhas) + "\r\n"
