"""Regressões do consolidado contínuo, grupos SEI e resultados dinâmicos."""

from __future__ import annotations

import csv
import io
import unittest
from copy import deepcopy

from icms.regras import MUNICIPAIS, nova_linha_municipal
from icms.relatorios import (
    COLUNAS_GERAIS,
    COLUNAS_PARAMETROS,
    COLUNAS_RESULTADOS,
    consolidado_geral_visual,
    filtrar_resultados_por_processo,
    proteger_csv,
    renderizar_tabela,
    resultado_consolidado,
    resumo_fichas,
)
from icms.repositorio import Repositorio
from tests.test_regras import ficha_valida


class TesteConsolidadoGeral(unittest.TestCase):
    """Valida a tabela Excel-like sem perda de dados municipais."""

    def setUp(self) -> None:
        """Gera duas fichas: uma com três municípios e outra com um."""
        self.repo = Repositorio()
        self.primeira = ficha_valida()
        self.primeira["municipios"][0]["nome"] = "juatuba"
        for nome, pontuacoes in (
            ("contagem", (3, 0, 4, 1)),
            ("betim", (1, 2, 0, 9)),
        ):
            municipio = nova_linha_municipal(nome)
            for codigo, numero in zip(MUNICIPAIS, pontuacoes, strict=True):
                municipio[codigo].update(gestor=numero, validado=numero)
            self.primeira["municipios"].append(municipio)
        self.segunda = deepcopy(self.primeira)
        self.segunda["processo"] = "0000.00.0000002/2026-00"
        self.segunda["unidade"] = "UC da segunda ficha"
        self.segunda["municipios"] = [nova_linha_municipal("sarzedo")]
        for codigo in MUNICIPAIS:
            self.segunda["municipios"][0][codigo].update(
                gestor=0, validado=0
            )
        self.repo.gravar(self.primeira, 0, "Concluída", "teste")
        self.repo.gravar(self.segunda, 0, "Concluída", "teste")

    def quadros(self):
        """Gera o resumo e o resultado analítico oficiais."""
        registros = self.repo.listar()
        return resumo_fichas(registros), resultado_consolidado(registros)

    def test_consolidado_agrupa_sem_repetir_identificacao(self) -> None:
        """Ficha com três municípios ocupa três linhas: só a primeira tem SEI."""
        _, analitico = self.quadros()
        visual = consolidado_geral_visual(analitico)
        self.assertEqual(len(visual), 4)
        self.assertEqual(list(visual.columns), COLUNAS_RESULTADOS)
        self.assertEqual(
            visual["Município"].tolist(),
            ["juatuba", "contagem", "betim", "sarzedo"],
        )
        for coluna in [*COLUNAS_GERAIS, *COLUNAS_PARAMETROS]:
            self.assertEqual(visual.iloc[1][coluna], "")
            self.assertEqual(visual.iloc[2][coluna], "")
            self.assertEqual(visual.iloc[0][coluna], analitico.iloc[0][coluna])
        self.assertEqual(visual.iloc[3]["Nº SEI"], self.segunda["processo"])
        self.assertEqual(visual.iloc[3]["REMETENTE - UCs"], "UC da segunda ficha")

    def test_pontuacoes_e_fq_independentes_por_municipio(self) -> None:
        """Não mescla ou soma as pontuações de municípios diferentes."""
        _, analitico = self.quadros()
        visual = consolidado_geral_visual(analitico)
        self.assertEqual(visual.iloc[1]["PARÂM 10"], 3)
        self.assertEqual(visual.iloc[1]["PARÂM 11.2"], 4)
        self.assertEqual(visual.iloc[2]["PARÂM 11.3"], 9)
        self.assertEqual(visual.iloc[1]["SOMA PARÂMETROS"], 42)
        self.assertAlmostEqual(visual.iloc[1]["FQ"], 42 / 89, places=4)
        self.assertEqual(visual.iloc[0]["SOMA PARÂMETROS"], 34)
        self.assertEqual(visual.iloc[3]["SOMA PARÂMETROS"], 34)

    def test_csv_agrupado_e_analitico_possuem_quatro_linhas(self) -> None:
        """CSV visual sem repetição e CSV analítico com SEI em todas as linhas."""
        _, analitico = self.quadros()
        visual = consolidado_geral_visual(analitico)
        linhas_visuais = list(csv.reader(
            io.StringIO(proteger_csv(visual).decode("utf-8-sig")), delimiter=";"
        ))
        linhas_analiticas = list(csv.reader(
            io.StringIO(proteger_csv(analitico).decode("utf-8-sig")), delimiter=";"
        ))
        self.assertEqual(len(linhas_visuais), 5)
        self.assertEqual(len(linhas_analiticas), 5)
        self.assertTrue(all(len(linha) == 27 for linha in linhas_visuais))
        self.assertEqual(linhas_visuais[2][0], "")
        self.assertEqual(linhas_visuais[3][0], "")
        self.assertEqual(linhas_analiticas[2][0], self.primeira["processo"])
        self.assertEqual(linhas_analiticas[3][0], self.primeira["processo"])
        self.assertEqual(linhas_visuais[2][20], "contagem")
        self.assertEqual(linhas_visuais[2][-1], "0,4719")

    def test_pesquisa_por_municipio_exibe_processo_completo(self) -> None:
        """Filtrar contagem mostra os outros dois municípios do mesmo SEI."""
        resumo, analitico = self.quadros()
        filtrado_resumo, filtrado_municipios = filtrar_resultados_por_processo(
            resumo, analitico, "Contagem"
        )
        self.assertEqual(len(filtrado_resumo), 1)
        self.assertEqual(len(filtrado_municipios), 3)
        self.assertEqual(
            filtrado_municipios["Município"].tolist(),
            ["juatuba", "contagem", "betim"],
        )
        sem_resultado, sem_municipios = filtrar_resultados_por_processo(
            resumo, analitico, "não localizado"
        )
        self.assertTrue(sem_resultado.empty)
        self.assertTrue(sem_municipios.empty)

    def test_html_uma_tabela_com_cabecalhos_agrupados(self) -> None:
        """Visual tem uma tabela e marca as linhas municipais adicionais."""
        _, analitico = self.quadros()
        html = renderizar_tabela(
            consolidado_geral_visual(analitico), agrupar_processos=True
        )
        self.assertIn("IDENTIFICAÇÃO", html)
        self.assertIn("PARÂMETROS GERAIS", html)
        self.assertIn("RESULTADOS POR MUNICÍPIO", html)
        self.assertEqual(html.count('<table class="tabela-planilha">'), 1)
        self.assertEqual(html.count('class="linha-inicio-processo"'), 2)
        self.assertEqual(html.count('class="linha-municipio-adicional"'), 2)
        self.assertIn("0.4719", html)
        self.assertIn("↳", html)

    def test_exclusao_remove_todo_o_grupo(self) -> None:
        """Exclusão de uma ficha remove seus municípios do consolidado."""
        self.repo.excluir(self.primeira["processo"], 1, "teste")
        _, analitico = self.quadros()
        visual = consolidado_geral_visual(analitico)
        self.assertEqual(len(visual), 1)
        self.assertEqual(visual.iloc[0]["Município"], "sarzedo")

    def test_grupo_dinamico_com_mais_de_treze_municipios(self) -> None:
        """A quantidade municipal não determina o número de colunas."""
        ficha = ficha_valida()
        ficha["processo"] = "0000.00.0000003/2026-00"
        ficha["municipios"][0]["nome"] = "município teste 01"
        for indice in range(2, 18):
            municipio = nova_linha_municipal(f"município teste {indice:02d}")
            for codigo in MUNICIPAIS:
                municipio[codigo].update(gestor=0, validado=0)
            ficha["municipios"].append(municipio)
        self.repo.gravar(ficha, 0, "Concluída", "teste")
        _, analitico = self.quadros()
        visual = consolidado_geral_visual(analitico)
        self.assertEqual(len(visual), 21)
        self.assertEqual(len(visual.columns), 27)
        self.assertEqual(visual.iloc[-1]["Município"], "município teste 17")


if __name__ == "__main__":
    unittest.main()
