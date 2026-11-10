"""Regressões para o FQ, o relatório e a exportação da aplicação."""

from __future__ import annotations

import csv
import io
import unittest
from copy import deepcopy

from icms.regras import PARAMETROS
from icms.relatorios import (
    colunas_resultado_alteradas,
    mapa_parametros_resultado,
    proteger_csv,
    quadro_final_ficha,
    renderizar_tabela,
    resultado_consolidado,
)
from icms.repositorio import Repositorio
from tests.test_regras import ficha_valida


class TesteRelatorios(unittest.TestCase):
    """Confere funções puras de relatório sem iniciar o Streamlit."""

    def setUp(self) -> None:
        """Inicializa uma base temporária para cada teste."""
        self.repositorio = Repositorio()
        self.ficha = ficha_valida()

    def test_relatorio_tem_50_colunas_em_ordem_da_planilha(self) -> None:
        """Expõe os 18 parâmetros e as 13 notas, sem pontos do gestor."""
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        tabela = resultado_consolidado(self.repositorio.listar())
        parametros = [f"PARÂM {codigo}" for codigo, _ in PARAMETROS]
        parametros.extend(["PARÂM 10", "PARÂM 11.1", "PARÂM 11.2", "PARÂM 11.3"])
        self.assertEqual(tabela.shape, (1, 50))
        self.assertEqual(list(tabela.columns[6:24]), parametros)
        self.assertEqual(list(tabela.columns[24:28]), ["Município1", "Nota1",
                                                          "Município2", "Nota2"])
        self.assertNotIn("Pontos Gestor", tabela.columns)
        self.assertNotIn("Pontos Validados", tabela.columns)
        self.assertEqual(tabela.iloc[0]["Nota1"], 0.3820)

    def test_parametros_gerais_usam_validados_e_nao_pontos_gestor(self) -> None:
        """Mostra valores reais do exemplo sintético, sem trocar as origens."""
        self.ficha["parametros"]["1.1"]["gestor"] = 9
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        tabela = resultado_consolidado(self.repositorio.listar())
        esperados = [6, 0, 0, 9, 0, 0, 0, 0, 2, 6, 2, 2, 2, 5]
        obtidos = [tabela.iloc[0][f"PARÂM {codigo}"] for codigo, _ in PARAMETROS]
        self.assertEqual(obtidos, esperados)
        self.assertEqual(tabela.iloc[0]["PARÂM 10"], 0)

    def test_parametro_10_soma_todos_os_municipios_da_ficha(self) -> None:
        """O fator 10 agrega a chave 10 de todos os municípios identificados."""
        self.ficha["municipios"][0]["10"] = 4
        self.ficha["municipios"][1].update(
            nome="Outro município",
            **{"10": 6, "11.1": 2, "11.2": 0, "11.3": 0},
        )
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        tabela = resultado_consolidado(self.repositorio.listar())
        self.assertEqual(tabela.iloc[0]["PARÂM 10"], 10)
        self.assertEqual(tabela.iloc[0]["PARÂM 11.1"], 2)
        self.assertEqual(tabela.iloc[0]["PARÂM 11.2"], 2)
        self.assertEqual(tabela.iloc[0]["PARÂM 11.3"], 2)
        self.assertAlmostEqual(tabela.iloc[0]["Nota1"], 38 / 89, places=4)
        self.assertAlmostEqual(tabela.iloc[0]["Nota2"], 42 / 89, places=4)

    def test_rascunho_nao_entra_no_relatorio(self) -> None:
        """Mantém fichas parciais fora dos resultados consolidados."""
        self.repositorio.gravar(self.ficha, 0, "Rascunho", "teste")
        self.assertTrue(resultado_consolidado(self.repositorio.listar()).empty)

    def test_exclusao_atualiza_a_consulta_do_relatorio(self) -> None:
        """A ficha removida deixa de aparecer ao reconstruir os resultados."""
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        outra = deepcopy(self.ficha)
        outra["processo"] = "0000.00.0000002/2026-00"
        self.repositorio.gravar(outra, 0, "Concluída", "teste")
        self.repositorio.excluir(self.ficha["processo"], 1, "teste")
        tabela = resultado_consolidado(self.repositorio.listar())
        self.assertEqual(tabela.shape[0], 1)
        self.assertEqual(tabela.iloc[0]["Nº SEI"], outra["processo"])

    def test_mapa_de_fatores_pode_ser_configurado(self) -> None:
        """Preserva valores-padrão e permite aprovar origens distintas depois."""
        mapa = mapa_parametros_resultado({"11.3": "11.2"})
        self.assertEqual(mapa, {"11.1": "11.1", "11.2": "11.1", "11.3": "11.2"})

    def test_pontos_validados_destacam_parametro_e_notas(self) -> None:
        """Alterações do parâmetro geral realçam a coluna correspondente."""
        colunas = colunas_resultado_alteradas({"parametros.1.1.validado": {}})
        self.assertIn("PARÂM 1.1", colunas)
        self.assertIn("Nota1", colunas)
        self.assertNotIn("PARÂM 1.2", colunas)
        self.assertEqual(
            colunas_resultado_alteradas({"parametros.1.1.gestor": {}}), set()
        )

    def test_parametro_municipal_10_destaca_coluna_e_nota(self) -> None:
        """Alterar o parâmetro 10 destaca o total e a nota atingida."""
        colunas = colunas_resultado_alteradas({"municipios[1].10": {}})
        self.assertIn("PARÂM 10", colunas)
        self.assertIn("Nota1", colunas)
        self.assertNotIn("Nota2", colunas)

    def test_mudanca_municipal_destaca_fator_correspondente(self) -> None:
        """Marca os fatores e a nota relacionados à posição modificada."""
        colunas = colunas_resultado_alteradas({"municipios[1].11.1": {}})
        self.assertIn("Nota1", colunas)
        self.assertIn("PARÂM 11.1", colunas)
        self.assertIn("PARÂM 11.2", colunas)
        self.assertIn("PARÂM 11.3", colunas)

    def test_resumo_preserva_13_posicoes(self) -> None:
        """Apresenta as posições vazias como traço, sem atribuir nota falsa."""
        quadro = quadro_final_ficha(self.ficha)
        self.assertEqual(len(quadro), 13)
        self.assertEqual(quadro.iloc[0]["PONTUAÇÃO FINAL FQ"], "0,3820")
        self.assertEqual(quadro.iloc[1]["PONTUAÇÃO FINAL FQ"], "-")

    def test_exportacao_csv_tem_50_colunas_e_delimitador(self) -> None:
        """Aplica a seleção do relatório à exportação CSV."""
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        arquivo = proteger_csv(resultado_consolidado(self.repositorio.listar()))
        linhas = list(
            csv.reader(io.StringIO(arquivo.decode("utf-8-sig")), delimiter=";")
        )
        self.assertEqual(len(linhas[0]), 50)
        self.assertEqual(len(linhas[1]), 50)
        self.assertIn("PARÂM 1.1", linhas[0])
        self.assertIn("PARÂM 10", linhas[0])
        self.assertNotIn("Indicador", linhas[0])

    def test_html_escapa_texto_do_usuario(self) -> None:
        """O relatório não deve inserir tags fornecidas pelo usuário."""
        self.ficha["unidade"] = "<script>alert(1)</script>"
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        tabela = resultado_consolidado(self.repositorio.listar())
        codigo = renderizar_tabela(tabela)
        self.assertNotIn("<script>", codigo)
        self.assertIn("&lt;script&gt;", codigo)


if __name__ == "__main__":
    unittest.main()
