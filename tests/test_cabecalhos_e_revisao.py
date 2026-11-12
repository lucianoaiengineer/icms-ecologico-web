"""Regressões dos títulos municipais e remoção da revisão duplicada."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from icms.regras import NOMES_MUNICIPAIS
from icms.relatorios import (
    COLUNAS_RESULTADOS,
    apresentar_cabecalhos_municipais,
    consolidado_geral_visual,
    proteger_csv,
    renderizar_tabela,
    resultado_consolidado,
)
from icms.repositorio import Repositorio
from tests.test_regras import ficha_valida


RAIZ = Path(__file__).resolve().parents[1]


def test_cabecalhos_visiveis_sem_alterar_chaves_tecnicas() -> None:
    """As quatro chaves do cálculo ficam iguais, mas os títulos são humanos."""
    repositorio = Repositorio()
    ficha = ficha_valida()
    repositorio.gravar(ficha, 0, "Concluída", "teste")
    analitico = resultado_consolidado(repositorio.listar())
    assert "PARÂM 10" in analitico.columns
    visual = apresentar_cabecalhos_municipais(analitico)
    assert len(visual.columns) == len(COLUNAS_RESULTADOS) == 27
    for codigo, titulo in NOMES_MUNICIPAIS.items():
        assert titulo in visual.columns
        assert f"PARÂM {codigo}" not in visual.columns
        assert visual.loc[0, titulo] == analitico.loc[0, f"PARÂM {codigo}"]
    assert visual.loc[0, "FQ"] == analitico.loc[0, "FQ"]


def test_consolidado_e_consulta_usam_titulos_aprovados() -> None:
    """Cabeçalhos descritivos são exibidos sem perder agrupamento do SEI."""
    repositorio = Repositorio()
    repositorio.gravar(ficha_valida(), 0, "Concluída", "teste")
    analitico = resultado_consolidado(repositorio.listar())
    visual = apresentar_cabecalhos_municipais(consolidado_geral_visual(analitico))
    html = renderizar_tabela(visual, agrupar_processos=True)
    assert "RESULTADOS POR MUNICÍPIO" in html
    assert "IDENTIFICAÇÃO" in html
    assert "PARÂMETROS GERAIS" in html
    for titulo in NOMES_MUNICIPAIS.values():
        assert f"<th scope=\"col\">{titulo}</th>" in html
    assert "PARÂM 11.3" not in html
    consulta = apresentar_cabecalhos_municipais(
        analitico[[
            "Município", "PARÂM 10", "PARÂM 11.1", "PARÂM 11.2",
            "PARÂM 11.3", "SOMA PARÂMETROS", "FQ",
        ]]
    )
    assert list(consulta.columns)[1:5] == list(NOMES_MUNICIPAIS.values())


def test_csv_usa_titulos_municipais() -> None:
    """Ambos os formatos de exportação usam os nomes completos."""
    repositorio = Repositorio()
    repositorio.gravar(ficha_valida(), 0, "Concluída", "teste")
    analitico = resultado_consolidado(repositorio.listar())
    for quadro in (analitico, consolidado_geral_visual(analitico)):
        csv_texto = proteger_csv(apresentar_cabecalhos_municipais(quadro))
        cabecalho = next(csv.reader(
            io.StringIO(csv_texto.decode("utf-8-sig")), delimiter=";"
        ))
        assert cabecalho[21:25] == list(NOMES_MUNICIPAIS.values())


def test_sem_revisao_duplicada_com_validacao_preservada() -> None:
    """Remover a revisão visual não pode suprimir a validação da gravação."""
    app = (RAIZ / "app.py").read_text(encoding="utf-8")
    assert 'st.button("Revisar preenchimento")' not in app
    assert "#### Revisão do preenchimento" not in app
    assert "#### Resumo final da ficha" in app
    assert 'repositorio.gravar(' in app
    ficha = ficha_valida()
    ficha["pontuacao_categoria"] = 0
    with pytest.raises(ValueError):
        Repositorio().gravar(ficha, 0, "Concluída", "teste")
