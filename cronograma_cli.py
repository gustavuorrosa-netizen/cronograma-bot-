"""
Modo linha de comando: lê o PDF do plano de ensino e gera um arquivo .ics.

Exemplos:
  python cronograma_cli.py plano.pdf
  python cronograma_cli.py plano.pdf -o minhas_provas.ics --lembrete 2
  python cronograma_cli.py plano.pdf --todas      (inclui datas que já passaram)
"""

import argparse
import sys

from cronograma import encontrar_eventos, extrair_texto_pdf, gerar_ics

DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera um calendário (.ics) com as provas e trabalhos de um plano de ensino em PDF."
    )
    parser.add_argument("pdf", help="caminho do PDF do plano de ensino")
    parser.add_argument("-o", "--saida", default="provas_e_trabalhos.ics",
                        help="nome do arquivo .ics (padrão: provas_e_trabalhos.ics)")
    parser.add_argument("--lembrete", type=int, default=1, metavar="DIAS",
                        help="quantos dias antes avisar (padrão: 1)")
    parser.add_argument("--todas", action="store_true",
                        help="incluir também datas que já passaram")
    args = parser.parse_args()

    try:
        texto = extrair_texto_pdf(args.pdf)
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {args.pdf}")
        return 1
    except Exception as erro:
        print(f"Não consegui ler o PDF: {erro}")
        return 1

    eventos = encontrar_eventos(texto, apenas_futuros=not args.todas)
    if not eventos:
        print("Não encontrei provas ou trabalhos nesse PDF.")
        return 1

    for e in eventos:
        titulo = e.titulo.split(": ", 1)[-1]
        print(f"{e.data:%d/%m} ({DIAS_SEMANA[e.data.weekday()]}) - {titulo}")

    with open(args.saida, "w", encoding="utf-8", newline="") as arquivo:
        arquivo.write(gerar_ics(eventos, lembrete_dias=args.lembrete))

    print(f"\n{len(eventos)} eventos salvos em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
