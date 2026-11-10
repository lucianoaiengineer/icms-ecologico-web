"""Construção de relatórios, visualização tabular e exportação CSV.

Funções sem dependências da interface Streamlit para permitir testes unitários.
"""

from __future__ import annotations

import html
from datetime import date
from numbers import Real
from typing import Any, Mapping

import pandas as pd

from icms.regras import (
    CASAS_DECIMAIS_FQ,
    MUNICIPAIS,
    PARAMETROS,
    calcular,
    formatar_fq,
)

CODIGOS_PARAMETROS_GERAIS = frozenset(codigo for codigo, _ in PARAMETROS)


def mapa_parametros_resultado(
    configuracao: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Relaciona os três fatores visíveis aos totais usados no cálculo."""
    mapa = {
        "11.1": "11.1",
        "11.2": "11.1",
        "11.3": "11.1",
    }
    if configuracao:
        mapa.update(configuracao)
    return {codigo: mapa[codigo] for codigo in ("11.1", "11.2", "11.3")}


def resultado_consolidado(
    registros: list[dict[str, Any]],
    mapa: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Expõe os 18 parâmetros do FQ e as notas de fichas concluídas."""
    mapa = mapa_parametros_resultado(mapa)
    linhas: list[dict[str, Any]] = []
    for registro in registros:
        if registro["status"] != "Concluída":
            continue
        ficha = registro["ficha"]
        calculo = calcular(ficha)
        linha = {
            "Nº SEI": ficha["processo"],
            "DATA RECEBIDA": date.fromisoformat(ficha["recebimento"]),
            "REMETENTE - UCs": ficha["unidade"],
            "Esfera": ficha["esfera"],
            "URFBio": ficha["urfbio"],
            "RESPONSÁVEL": ficha["responsavel"],
        }
        # Os parâmetros gerais exibem os pontos validados (não os do gestor).
        # A ordem acompanha a planilha de referência: 1.1 até 9, depois 10 a 11.3.
        for codigo, _ in PARAMETROS:
            linha[f"PARÂM {codigo}"] = ficha["parametros"][codigo]["validado"]
        linha["PARÂM 10"] = calculo["totais"]["10"]
        for codigo, origem in mapa.items():
            linha[f"PARÂM {codigo}"] = calculo["totais"].get(origem)
        for posicao in range(13):
            municipio = ficha["municipios"][posicao]
            nome = municipio["nome"].strip()
            linha[f"Município{posicao + 1}"] = nome if nome not in ("", "-") else "-"
            nota = next(
                (
                    municipio_calculado
                    for municipio_calculado in calculo["municipios"]
                    if municipio_calculado["Município"] == nome
                ),
                None,
            )
            linha[f"Nota{posicao + 1}"] = (
                float(nota["FQ"].replace(",", ".")) if nota else None
            )
        linhas.append(linha)
    return pd.DataFrame(linhas)


def quadro_final_ficha(ficha: dict[str, Any]) -> pd.DataFrame:
    """Monta a parte inferior da ficha para os 13 municípios."""
    total_validado = sum(
        ponto.get("validado") or 0 for ponto in ficha["parametros"].values()
    )
    linhas = []
    for posicao, municipio in enumerate(ficha["municipios"], 1):
        nome = municipio["nome"].strip()
        if not nome or nome == "-":
            linhas.append(
                {
                    "Posição": f"Município {posicao}",
                    "Município": "-",
                    "SOMA PARÂMETROS": "-",
                    "PONTUAÇÃO FINAL FQ": "-",
                }
            )
            continue
        soma = total_validado + sum(municipio.get(codigo) or 0 for codigo in MUNICIPAIS)
        linhas.append(
            {
                "Posição": f"Município {posicao}",
                "Município": nome,
                "SOMA PARÂMETROS": str(soma),
                "PONTUAÇÃO FINAL FQ": formatar_fq(soma, ficha["pontuacao_categoria"]),
            }
        )
    return pd.DataFrame(linhas)


def renderizar_tabela(
    quadro: pd.DataFrame,
    destaques_por_processo: dict[str, set[str]] | None = None,
) -> str:
    """Renderiza grade HTML branca e rolável, sem linhas vazias do Streamlit."""
    colunas = list(quadro.columns)
    cabecalho = "".join(
        f'<th scope="col">{html.escape(str(coluna))}</th>' for coluna in colunas
    )
    linhas = []
    for _, linha in quadro.iterrows():
        processo = str(linha.get("Nº SEI", ""))
        colunas_alteradas = (
            destaques_por_processo.get(processo, set())
            if destaques_por_processo
            else set()
        )
        celulas = []
        for coluna in colunas:
            valor = linha[coluna]
            if pd.isna(valor):
                texto = ""
            elif coluna == "DATA RECEBIDA" and hasattr(valor, "strftime"):
                texto = valor.strftime("%m/%d/%Y")
            elif coluna.startswith("Nota") and isinstance(valor, Real):
                texto = f"{valor:.{CASAS_DECIMAIS_FQ}f}"
            elif isinstance(valor, Real) and not isinstance(valor, bool):
                texto = str(int(valor)) if float(valor).is_integer() else str(valor)
            else:
                texto = str(valor)
            classe = ' class="celula-alterada"' if coluna in colunas_alteradas else ""
            celulas.append(f"<td{classe}>{html.escape(texto)}</td>")
        linhas.append(f"<tr>{''.join(celulas)}</tr>")
    return (
        '<div class="tabela-planilha-rolagem" role="region" '
        'aria-label="Tabela de dados; use as barras de rolagem para navegar" '
        'tabindex="0"><table class="tabela-planilha">'
        f"<thead><tr>{cabecalho}</tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody></table></div>"
    )


def colunas_resultado_alteradas(
    alteracoes: dict[str, Any],
    mapa: Mapping[str, str] | None = None,
) -> set[str]:
    """Relaciona campos alterados da ficha às colunas visíveis no resultado."""
    colunas: set[str] = set()
    mapa = mapa_parametros_resultado(mapa)
    campos_diretos = {
        "unidade": "REMETENTE - UCs",
        "recebimento": "DATA RECEBIDA",
        "esfera": "Esfera",
        "urfbio": "URFBio",
        "responsavel": "RESPONSÁVEL",
    }
    for caminho in alteracoes:
        if caminho in campos_diretos:
            colunas.add(campos_diretos[caminho])
        elif caminho == "pontuacao_categoria":
            colunas.update(f"Nota{posicao}" for posicao in range(1, 14))
        elif caminho.startswith("parametros."):
            # Os identificadores 1.1, 1.2, 5.1 etc. contêm ponto; separamos
            # somente o prefixo e o nome do campo, preservando o código inteiro.
            codigo_e_campo = caminho.removeprefix("parametros.").rsplit(".", 1)
            partes = ["parametros", *codigo_e_campo]
            if len(partes) == 3 and partes[2] == "validado":
                # Uma pontuação validada afeta sua coluna e todas as notas FQ.
                codigo = partes[1]
                if codigo in CODIGOS_PARAMETROS_GERAIS:
                    colunas.add(f"PARÂM {codigo}")
                    colunas.update(f"Nota{posicao}" for posicao in range(1, 14))
        elif caminho.startswith("municipios[") and "]." in caminho:
            posicao_texto, campo = caminho[len("municipios[") :].split("].", 1)
            if not posicao_texto.isdigit():
                continue
            posicao = int(posicao_texto)
            if not 1 <= posicao <= 13:
                continue
            if campo == "nome":
                colunas.update((f"Município{posicao}", f"Nota{posicao}"))
            elif campo in MUNICIPAIS:
                colunas.add(f"Nota{posicao}")
                if campo == "10":
                    colunas.add("PARÂM 10")
                # Um mesmo total pode alimentar mais de um fator no relatório.
                colunas.update(
                    f"PARÂM {codigo}"
                    for codigo, origem in mapa.items()
                    if origem == campo
                )
    return colunas


def proteger_csv(quadro: pd.DataFrame) -> bytes:
    """Exporta CSV sem permitir fórmulas em campos de texto no Excel."""
    quadro = quadro.copy()
    for coluna in quadro.columns:
        if coluna == "DATA RECEBIDA":
            quadro[coluna] = quadro[coluna].map(
                lambda valor_csv: valor_csv.strftime("%m/%d/%Y")
            )
        else:
            quadro[coluna] = quadro[coluna].map(
                lambda valor_csv: (
                    "'" + valor_csv
                    if isinstance(valor_csv, str)
                    and valor_csv.lstrip().startswith(("=", "+", "-", "@"))
                    and valor_csv != "-"
                    else valor_csv
                )
            )
    return quadro.to_csv(
        index=False,
        sep=";",
        decimal=",",
        float_format=f"%.{CASAS_DECIMAIS_FQ}f",
    ).encode("utf-8-sig")
