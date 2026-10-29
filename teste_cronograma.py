"""Teste rápido do leitor de cronograma, usando um trecho do PDF real."""

from cronograma import encontrar_eventos, gerar_ics

TEXTO = """DISCIPLINA: FUNDAMENTOS DE SISTEMAS DIGITAIS
CÓDIGO: 4646B CRÉDITOS: 04 SEMESTRE: 2026/2
13 15/9 Lista de Exercícios de Circuitos Combinacionais 1h
14 17/9 Prova 1 (P1) - Substituível por PS.
15 22/9 Correção da P1 & Introdução a HDL (SystemVerilog) com modelagem de circuitos combinacionais
- 13/10 Feriado
30 17/11 Prova 2 (P2) - Substituível por PS.
31 19/11 Correção da P2 & Trabalho Final Guiado. Especificação de um sistema digital. 1h
32 24/11 Trabalho Final Guiado 1h
34 1/12 Modelagem e validação do sistema digital proposto - entrega 1h
35 3/12 Prova de Substituição - PS: conteúdos das avaliações 1 e 2
- 8/12 Exame de Grau 2 (G2)
"""

eventos = encontrar_eventos(TEXTO, apenas_futuros=False)
for e in eventos:
    print(e.data.strftime("%d/%m/%Y"), "|", e.titulo)

esperado = ["17/09", "17/11", "19/11", "24/11", "01/12", "03/12", "08/12"]
obtido = [e.data.strftime("%d/%m") for e in eventos]
assert obtido == esperado, f"esperado {esperado}, obtido {obtido}"

ics = gerar_ics(eventos)
assert ics.startswith("BEGIN:VCALENDAR") and ics.count("BEGIN:VEVENT") == 7
print("\nOK: 7 eventos encontrados e .ics gerado.")
