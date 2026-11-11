"""Regressões para resultados municipais dinâmicos, FQ e exportação CSV."""

from __future__ import annotations

import csv
import io
import unittest
from copy import deepcopy

from icms.regras import MUNICIPAIS, PARAMETROS, nova_linha_municipal
from icms.relatorios import (
    colunas_resultado_alteradas,
    proteger_csv,
    quadro_final_ficha,
    renderizar_tabela,
    resultado_consolidado,
    resumo_fichas,
)
from icms.repositorio import Repositorio
from tests.test_regras import ficha_valida


class TesteRelatorios(unittest.TestCase):
    """Confere os relatórios sem executar a interface Streamlit."""

    def setUp(self) -> None:
        """Prepara uma ficha sintética com FQ de quatro casas."""
        self.repositorio = Repositorio()
        self.ficha = ficha_valida()

    def _acrescentar(self, nome: str, valores: tuple[int, ...]) -> None:
        """Inclui um município real com seus quatro pontos independentes."""
        municipio = nova_linha_municipal(nome)
        for codigo, valor in zip(MUNICIPAIS, valores, strict=True):
            municipio[codigo].update(gestor=valor, validado=valor)
        self.ficha["municipios"].append(municipio)

    def test_resultado_tem_uma_linha_por_municipio_e_quatro_parametros(self) -> None:
        """Substitui o antigo relatório de 13 pares de colunas fixos."""
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        tabela = resultado_consolidado(self.repositorio.listar())
        parametros = [f"PARÂM {codigo}" for codigo, _ in PARAMETROS]
        parametros += [f"PARÂM {codigo}" for codigo in MUNICIPAIS]
        self.assertEqual(tabela.shape, (1, 27))
        self.assertEqual(list(tabela.columns[6:20]), parametros[:14])
        self.assertEqual(list(tabela.columns[21:25]), parametros[14:])
        self.assertEqual(tabela.iloc[0]["FQ"], 0.3820)
        self.assertNotIn("Município13", tabela.columns)
        self.assertNotIn("Pontos Gestor", tabela.columns)
        self.assertNotIn("Pontos Validados", tabela.columns)

    def test_municipios_adicionados_geram_linhas_reais(self) -> None:
        """Três municípios geram três resultados, mas apenas uma ficha no resumo."""
        self._acrescentar("Município 02", (4, 2, 0, 0))
        self._acrescentar("Município 03", (0, 9, 2, 1))
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        lista = self.repositorio.listar()
        tabela = resultado_consolidado(lista)
        resumo = resumo_fichas(lista)
        self.assertEqual(tabela.shape[0], 3)
        self.assertEqual(resumo.shape[0], 1)
        self.assertEqual(resumo.iloc[0]["Municípios cadastrados"], 3)
        self.assertEqual(tabela.iloc[1]["PARÂM 10"], 4)
        self.assertEqual(tabela.iloc[2]["PARÂM 11.1"], 9)
        self.assertAlmostEqual(tabela.iloc[1]["FQ"], 40 / 89, places=4)

    def test_quantidade_maior_que_treze_nao_cria_colunas_vazias(self) -> None:
        """Aceita mais de 13 municípios sem multiplicar colunas."""
        for indice in range(2, 16):
            self._acrescentar(f"Município sintético {indice:02}", (0, 0, 0, 0))
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        quadro = resultado_consolidado(self.repositorio.listar())
        self.assertEqual(quadro.shape, (15, 27))

    def test_parametros_gerais_usam_validados(self) -> None:
        """Os pontos do gestor não entram no FQ nem no resultado consolidado."""
        self.ficha["parametros"]["1.1"]["gestor"] = 9
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        tabela = resultado_consolidado(self.repositorio.listar())
        esperados = [6, 0, 0, 9, 0, 0, 0, 0, 2, 6, 2, 2, 2, 5]
        obtidos = [tabela.iloc[0][f"PARÂM {codigo}"] for codigo, _ in PARAMETROS]
        self.assertEqual(obtidos, esperados)
        self.assertEqual(tabela.iloc[0]["PARÂM 10"], 0)

    def test_valores_gestor_e_justificativa_nao_afetam_fq(self) -> None:
        """O FQ muda apenas com os quatro valores validados do município."""
        self.ficha["municipios"][0]["10"].update(
            gestor=9, justificativa="Gestor sugeriu pontuação maior", validado=3
        )
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        tabela = resultado_consolidado(self.repositorio.listar())
        self.assertEqual(tabela.iloc[0]["SOMA PARÂMETROS"], 37)
        self.assertAlmostEqual(tabela.iloc[0]["FQ"], 37 / 89, places=4)

    def test_rascunho_nao_entra_no_relatorio(self) -> None:
        """Rascunhos nunca geram resultados consolidados."""
        self.repositorio.gravar(self.ficha, 0, "Rascunho", "teste")
        self.assertTrue(resultado_consolidado(self.repositorio.listar()).empty)
        self.assertTrue(resumo_fichas(self.repositorio.listar()).empty)

    def test_exclusao_atualiza_ambas_as_consultas(self) -> None:
        """Retira a ficha dos dois relatórios após exclusão confirmada."""
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        outra = deepcopy(self.ficha)
        outra["processo"] = "0000.00.0000002/2026-00"
        self.repositorio.gravar(outra, 0, "Concluída", "teste")
        self.repositorio.excluir(self.ficha["processo"], 1, "teste")
        lista = self.repositorio.listar()
        self.assertEqual(resultado_consolidado(lista).shape[0], 1)
        self.assertEqual(resumo_fichas(lista).shape[0], 1)
        self.assertEqual(resumo_fichas(lista).iloc[0]["Nº SEI"], outra["processo"])

    def test_destaques_acompanham_as_colunas_novas(self) -> None:
        """Mudanças validadas destacam o campo e o FQ, sem colunas Nota fixas."""
        gerais = colunas_resultado_alteradas({"parametros.1.1.validado": {}})
        municipais = colunas_resultado_alteradas(
            {"municipios[1].11.2.validado": {}}
        )
        self.assertEqual(gerais, {"PARÂM 1.1", "FQ", "SOMA PARÂMETROS"})
        self.assertEqual(
            municipais, {"PARÂM 11.2", "FQ", "SOMA PARÂMETROS"}
        )
        self.assertEqual(
            colunas_resultado_alteradas({"municipios[1].11.2.gestor": {}}), set()
        )

    def test_resumo_na_ficha_nao_mostra_posicoes_vazias(self) -> None:
        """Apresenta os municípios existentes em vez de treze espaços fixos."""
        quadro = quadro_final_ficha(self.ficha)
        self.assertEqual(len(quadro), 1)
        self.assertEqual(quadro.iloc[0]["PONTUAÇÃO FINAL FQ"], "0,3820")

    def test_exportacao_csv_reproduz_linhas_dinamicas(self) -> None:
        """O CSV detalhado possui 27 colunas e linha para cada município."""
        self._acrescentar("Município 02", (2, 3, 0, 0))
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        arquivo = proteger_csv(resultado_consolidado(self.repositorio.listar()))
        linhas = list(
            csv.reader(io.StringIO(arquivo.decode("utf-8-sig")), delimiter=";")
        )
        self.assertEqual(len(linhas), 3)
        self.assertTrue(all(len(linha) == 27 for linha in linhas))
        self.assertIn("PARÂM 11.3", linhas[0])
        self.assertIn("Município 02", linhas[2])

    def test_html_escapa_texto_do_usuario(self) -> None:
        """A grade HTML não executa tags fornecidas pelo usuário."""
        self.ficha["unidade"] = "<script>alert(1)</script>"
        self.repositorio.gravar(self.ficha, 0, "Concluída", "teste")
        codigo = renderizar_tabela(resultado_consolidado(self.repositorio.listar()))
        self.assertNotIn("<script>", codigo)
        self.assertIn("&lt;script&gt;", codigo)


if __name__ == "__main__":
    unittest.main()
