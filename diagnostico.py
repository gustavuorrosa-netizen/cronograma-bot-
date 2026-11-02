"""
Diagnóstico: mostra o que o computador consegue ler de um PDF.

Uso:  py diagnostico.py "arquivo.pdf"
"""

import re
import sys
from importlib.metadata import version

import pdfplumber

DATA = re.compile(r"\d{1,2}/\d{1,2}")

if len(sys.argv) < 2:
    print('Uso: py diagnostico.py "arquivo.pdf"')
    sys.exit(1)

print("Python:", sys.version.split()[0])
for pacote in ("pdfplumber", "pdfminer.six", "pypdfium2"):
    try:
        print(f"{pacote}:", version(pacote))
    except Exception:
        print(f"{pacote}: (não instalado)")

with pdfplumber.open(sys.argv[1]) as pdf:
    print("\nPáginas:", len(pdf.pages))
    for n, pagina in enumerate(pdf.pages, 1):
        texto = pagina.extract_text() or ""
        linhas = texto.splitlines()
        com_data = [l for l in linhas if DATA.search(l)]
        tabelas = pagina.extract_tables()
        print(f"\n--- Página {n}: {len(texto)} caracteres, {len(linhas)} linhas, "
              f"{len(com_data)} com data, {len(tabelas)} tabelas")
        for l in com_data[:4]:
            print("   texto:", repr(l[:90]))
        for t in tabelas[:2]:
            if t and t[0]:
                print("   tabela, 1a linha:", repr([c for c in t[min(1, len(t) - 1)] if c][:3]))
