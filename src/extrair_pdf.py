"""
Reconstrói a base 02_educacao a partir do PDF recebido.

O PDF traz a tabela dividida em duas páginas por bloco: a página ímpar tem
ano, município, código, nome e localização; a página seguinte tem a
dependência administrativa e as três taxas de aprovação, na mesma ordem de
linhas. Alguns textos vêm sobrepostos (ex.: "ESTADUUrbAaLn" = "ESTADUAL" +
"Urbana"), e este script separa as duas informações.

Uso:
    python src/extrair_pdf.py caminho/02_educacao.pdf dados/02_educacao_regressao.csv
Requer: pip install pdfplumber pandas
"""
import re
import sys

import pandas as pd
import pdfplumber

COLUNAS = ["ano", "codigo_municipio", "municipio", "codigo_escola", "escola", "localizacao",
           "dependencia_administrativa", "aprovacao_anos_iniciais_pct",
           "aprovacao_ensino_medio_pct", "aprovacao_anos_finais_pct"]


def separar_nome(texto):
    """Remove a palavra Urbana/Rural que o PDF mistura ao nome da escola."""
    texto = re.sub(r"(Urbana|Rural)\s*$", "", texto.strip())
    i = next((k for k, ch in enumerate(texto) if ch.islower()), None)
    if i is not None:
        maiuscula = "R" if texto[i] == "u" else "U"
        j = texto.rfind(maiuscula, 0, i)
        if j >= 0:
            texto = texto[:j] + texto[j + 1:]
        texto = "".join(ch for ch in texto if not ch.islower())
    return re.sub(r"\s+", " ", texto).strip()


def extrair(caminho_pdf):
    linhas, nomes = [], {}
    with pdfplumber.open(caminho_pdf) as pdf:
        for i in range(0, len(pdf.pages), 2):
            esq = pdf.pages[i].extract_tables()[0]
            dir_ = pdf.pages[i + 1].extract_tables()[0]
            if esq[0][0] == "ano":
                esq = esq[1:]
            if dir_[0][0].startswith("depend"):
                dir_ = dir_[1:]
            assert len(esq) == len(dir_), f"páginas {i + 1}/{i + 2} com tamanhos diferentes"
            for e, d in zip(esq, dir_):
                e = [(c or "").replace("\n", " ") for c in e]
                codigo = "".join(ch for ch in e[3] if ch.isdigit())
                municipio = re.sub(r"\s+", " ", e[2] + "".join(ch for ch in e[3] if not ch.isdigit())).strip()
                rural = "u" in "".join(ch for ch in e[5] if ch.islower())
                dep = re.match(r"(Estadual|Municipal|Privada|Federal)", d[0]).group(1)
                taxas = [(c or "").strip() for c in d[1:4]]
                linhas.append([e[0], e[1], municipio, codigo, e[4] + e[5],
                               "Rural" if rural else "Urbana", dep] + taxas)
            # o texto corrido da página traz o nome da escola mais completo
            for ln in pdf.pages[i].extract_text().split("\n"):
                m = re.match(r"^2025\s+52\d{5}\s*.+?(52\d{6})\s*(.+)$", ln.strip())
                if m:
                    nomes[m.group(1)] = separar_nome(m.group(2))
    df = pd.DataFrame(linhas, columns=COLUNAS)
    df["escola"] = df.codigo_escola.map(nomes).fillna(df.escola.map(separar_nome))
    df["escola"] = df.escola.str.replace("MUNICIPALR URAL", "MUNICIPAL RURAL", regex=False)  # caso isolado
    # grafia do município: a versão com mais espaços e sem palavras grudadas
    df["municipio"] = df.municipio.map(lambda s: re.sub(r"([a-zà-ÿ])([A-ZÀ-Þ])", r"\1 \2", s))
    melhor = df.groupby("codigo_municipio").municipio.agg(lambda s: max(s, key=lambda x: (x.count(" "), len(x))))
    df["municipio"] = df.codigo_municipio.map(melhor)
    for c in COLUNAS[-3:]:
        df[c] = pd.to_numeric(df[c].replace("", None))
    return df


if __name__ == "__main__":
    origem, destino = sys.argv[1], sys.argv[2]
    base = extrair(origem)
    base.to_csv(destino, index=False)
    print(f"{len(base)} escolas salvas em {destino}")
