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
    normalizar_municipios,
)

CODIGOS_PARAMETROS_GERAIS = frozenset(codigo for codigo, _ in PARAMETROS)


COLUNAS_GERAIS = [
    "Nº SEI", "DATA RECEBIDA", "REMETENTE - UCs", "Esfera", "URFBio",
    "RESPONSÁVEL",
]
COLUNAS_PARAMETROS = [f"PARÂM {codigo}" for codigo, _ in PARAMETROS]
COLUNAS_MUNICIPAIS = [f"PARÂM {codigo}" for codigo in MUNICIPAIS]
COLUNAS_RESULTADOS = [
    *COLUNAS_GERAIS,
    *COLUNAS_PARAMETROS,
    "Município",
    *COLUNAS_MUNICIPAIS,
    "SOMA PARÂMETROS",
    "FQ",
]
COLUNAS_RESUMO = [
    *COLUNAS_GERAIS,
    "Municípios cadastrados",
    "Versão",
    "Última gravação",
]


def mapa_parametros_resultado(
    configuracao: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Mantém as chaves municipais legadas sem remapeamento visual indevido."""
    mapa = {codigo: codigo for codigo in ("11.1", "11.2", "11.3")}
    if configuracao:
        mapa.update(configuracao)
    return mapa


def _identificacao(ficha: dict[str, Any]) -> dict[str, Any]:
    """Organiza os identificadores da ficha em uma ordem constante."""
    return {
        "Nº SEI": ficha["processo"],
        "DATA RECEBIDA": date.fromisoformat(ficha["recebimento"]),
        "REMETENTE - UCs": ficha["unidade"],
        "Esfera": ficha["esfera"],
        "URFBio": ficha["urfbio"],
        "RESPONSÁVEL": ficha["responsavel"],
    }


def resumo_fichas(registros: list[dict[str, Any]]) -> pd.DataFrame:
    """Cria uma linha por ficha concluída, inclusive com municípios variáveis."""
    linhas = []
    for registro in registros:
        if registro["status"] != "Concluída":
            continue
        ficha = normalizar_municipios(registro["ficha"])
        linha = _identificacao(ficha)
        linha.update({
            "Municípios cadastrados": sum(
                bool(m["nome"].strip() and m["nome"].strip() != "-")
                for m in ficha["municipios"]
            ),
            "Versão": registro["versao"],
            "Última gravação": registro.get("atualizado_em", ""),
        })
        linhas.append(linha)
    return pd.DataFrame(linhas, columns=COLUNAS_RESUMO)


def resultado_consolidado(
    registros: list[dict[str, Any]],
    mapa: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Monta uma linha por município existente, nunca 13 pares fixos."""
    linhas: list[dict[str, Any]] = []
    # A configuração anterior era sobre agregados artificiais do antigo
    # relatório. A nota municipal é sempre formada pelas quatro chaves reais.
    for registro in registros:
        if registro["status"] != "Concluída":
            continue
        ficha = normalizar_municipios(registro["ficha"])
        calculo = calcular(ficha)
        calculados = iter(calculo["municipios"])
        identificacao = _identificacao(ficha)
        gerais = {
            f"PARÂM {codigo}": ficha["parametros"][codigo]["validado"]
            for codigo, _ in PARAMETROS
        }
        for municipio in ficha["municipios"]:
            nome = municipio["nome"].strip()
            if nome in ("", "-"):
                continue
            nota = next(calculados)
            linha = {**identificacao, **gerais, "Município": nome}
            for codigo in MUNICIPAIS:
                linha[f"PARÂM {codigo}"] = municipio[codigo]["validado"]
            linha["SOMA PARÂMETROS"] = nota["Soma"]
            linha["FQ"] = nota["fq_numero"]
            linhas.append(linha)
    return pd.DataFrame(linhas, columns=COLUNAS_RESULTADOS)


def consolidado_geral_visual(quadro_analitico: pd.DataFrame) -> pd.DataFrame:
    """Agrupa linhas por SEI sem repetir os dados gerais nas linhas seguintes.

    A tabela analítica original permanece intacta, com o SEI completo em
    cada registro para exportações destinadas a filtros e cruzamentos.
    A ordem dos municípios em cada ficha é preservada.
    """
    if quadro_analitico.empty:
        return quadro_analitico.copy().reset_index(drop=True)

    colunas_compartilhadas = [*COLUNAS_GERAIS, *COLUNAS_PARAMETROS]
    linhas = []
    for _, grupo in quadro_analitico.groupby("Nº SEI", sort=False):
        for indice, (_, registro) in enumerate(grupo.iterrows()):
            linha = registro.copy()
            if indice:
                for coluna in colunas_compartilhadas:
                    linha[coluna] = ""
            linhas.append(linha)
    return pd.DataFrame(linhas, columns=quadro_analitico.columns).reset_index(drop=True)


def filtrar_resultados_por_processo(
    resumo: pd.DataFrame, detalhado: pd.DataFrame, termo: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pesquisa SEI, identificação ou município mantendo o grupo inteiro.

    Um município encontrado seleciona sua ficha completa: os outros
    municípios vinculados continuam visíveis no mesmo consolidado.
    """
    busca = termo.strip()
    if not busca:
        return resumo.copy(), detalhado.copy()

    colunas_busca = (
        "Nº SEI", "REMETENTE - UCs", "Esfera", "URFBio", "RESPONSÁVEL"
    )
    encontrados = pd.Series(False, index=resumo.index)
    for coluna in colunas_busca:
        encontrados |= resumo[coluna].astype(str).str.contains(
            busca, case=False, regex=False, na=False
        )
    if not detalhado.empty:
        municipio_encontrado = detalhado["Município"].astype(str).str.contains(
            busca, case=False, regex=False, na=False
        )
        encontrados |= resumo["Nº SEI"].isin(
            detalhado.loc[municipio_encontrado, "Nº SEI"]
        )
    filtrado = resumo.loc[encontrados].copy()
    return filtrado, detalhado.loc[
        detalhado["Nº SEI"].isin(filtrado["Nº SEI"])
    ].copy()


def quadro_final_ficha(ficha: dict[str, Any]) -> pd.DataFrame:
    """Exibe somente os municípios identificados da ficha atual."""
    ficha = normalizar_municipios(ficha)
    total_validado = sum(
        ponto.get("validado") or 0 for ponto in ficha["parametros"].values()
    )
    linhas = []
    for posicao, municipio in enumerate(ficha["municipios"], 1):
        nome = municipio["nome"].strip()
        if not nome or nome == "-":
            continue
        soma = total_validado + sum(
            municipio[codigo].get("validado") or 0 for codigo in MUNICIPAIS
        )
        linhas.append({
            "Município": nome,
            "SOMA PARÂMETROS": soma,
            "PONTUAÇÃO FINAL FQ": formatar_fq(soma, ficha["pontuacao_categoria"]),
        })
    return pd.DataFrame(
        linhas, columns=["Município", "SOMA PARÂMETROS", "PONTUAÇÃO FINAL FQ"]
    )


def renderizar_tabela(
    quadro: pd.DataFrame,
    destaques_por_processo: dict[str, set[str]] | None = None,
    *,
    agrupar_processos: bool = False,
) -> str:
    """Renderiza grade HTML rolável, podendo marcar visualmente grupos SEI."""
    colunas = list(quadro.columns)
    cabecalho = "".join(
        f'<th scope="col">{html.escape(str(coluna))}</th>' for coluna in colunas
    )
    linhas = []
    processo_atual = ""
    for _, linha in quadro.iterrows():
        processo = str(linha.get("Nº SEI", ""))
        if agrupar_processos and processo:
            processo_atual = processo
        elif agrupar_processos:
            processo = processo_atual
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
                texto = valor.strftime("%d/%m/%Y")
            elif coluna == "FQ" and isinstance(valor, Real):
                texto = f"{valor:.{CASAS_DECIMAIS_FQ}f}"
            elif isinstance(valor, Real) and not isinstance(valor, bool):
                texto = str(int(valor)) if float(valor).is_integer() else str(valor)
            else:
                texto = str(valor)
            if agrupar_processos and coluna == "Nº SEI" and not texto:
                texto = "↳"
            classe = (
                ' class="celula-alterada"'
                if coluna in colunas_alteradas and not (
                    agrupar_processos and not str(linha.get(coluna, ""))
                )
                else ""
            )
            celulas.append(f"<td{classe}>{html.escape(texto)}</td>")
        if agrupar_processos:
            tipo = (
                "linha-inicio-processo"
                if str(linha.get("Nº SEI", ""))
                else "linha-municipio-adicional"
            )
            linhas.append(f'<tr class="{tipo}">{"".join(celulas)}</tr>')
        else:
            linhas.append(f"<tr>{''.join(celulas)}</tr>")
    classe_tabela = (
        "tabela-planilha-rolagem tabela-consolidado-agrupado"
        if agrupar_processos else "tabela-planilha-rolagem"
    )
    cabecalho_grupos = ""
    if agrupar_processos and colunas == COLUNAS_RESULTADOS:
        cabecalho_grupos = (
            '<tr class="cabecalho-grupos">'
            '<th colspan="6" scope="colgroup">IDENTIFICAÇÃO</th>'
            '<th colspan="14" scope="colgroup">PARÂMETROS GERAIS</th>'
            '<th colspan="7" scope="colgroup">RESULTADOS POR MUNICÍPIO</th>'
            '</tr>'
        )
    return (
        f'<div class="{classe_tabela}" role="region" '
        'aria-label="Tabela de dados; use as barras de rolagem para navegar" '
        'tabindex="0"><table class="tabela-planilha">'
        f"<thead>{cabecalho_grupos}<tr>{cabecalho}</tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody></table></div>"
    )


def colunas_resultado_alteradas(
    alteracoes: dict[str, Any],
    mapa: Mapping[str, str] | None = None,
) -> set[str]:
    """Destaca o campo municipal alterado e o FQ correspondente."""
    colunas: set[str] = set()
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
            colunas.add("FQ")
        elif caminho.startswith("parametros."):
            partes = caminho.removeprefix("parametros.").rsplit(".", 1)
            if len(partes) == 2 and partes[1] == "validado":
                if partes[0] in CODIGOS_PARAMETROS_GERAIS:
                    colunas.update((f"PARÂM {partes[0]}", "FQ", "SOMA PARÂMETROS"))
        elif caminho.startswith("municipios[") and "]." in caminho:
            _, campo = caminho.split("].", 1)
            if campo == "nome":
                colunas.add("Município")
            else:
                for codigo in MUNICIPAIS:
                    if campo in (codigo, f"{codigo}.validado"):
                        colunas.update((f"PARÂM {codigo}", "FQ", "SOMA PARÂMETROS"))
                        break
    return colunas


def proteger_csv(quadro: pd.DataFrame) -> bytes:
    """Exporta CSV sem permitir fórmulas em campos de texto no Excel."""
    quadro = quadro.copy()
    for coluna in quadro.columns:
        if coluna == "DATA RECEBIDA":
            quadro[coluna] = quadro[coluna].map(
                lambda valor_csv: (
                    valor_csv.strftime("%d/%m/%Y")
                    if hasattr(valor_csv, "strftime") else valor_csv
                )
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
