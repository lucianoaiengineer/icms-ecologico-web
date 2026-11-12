"""Testes de interface Streamlit para os blocos municipais refatorados."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from icms.regras import MUNICIPAIS, NOMES_MUNICIPAIS, calcular
from tests.test_regras import ficha_valida


RAIZ = Path(__file__).resolve().parents[1]


class TesteInterface(unittest.TestCase):
    """Confere formulários e resultados sem serviços externos."""

    def setUp(self) -> None:
        """Executa a aplicação em modo demonstração com sessão isolada."""
        self.modo_anterior = os.environ.get("ICMS_MODO")
        os.environ["ICMS_MODO"] = "demonstracao"
        st.cache_resource.clear()
        self.aplicacao = AppTest.from_file(
            str(RAIZ / "app.py"), default_timeout=30
        ).run()

    def tearDown(self) -> None:
        """Restaura o modo do sistema antes do teste."""
        if self.modo_anterior is None:
            os.environ.pop("ICMS_MODO", None)
        else:
            os.environ["ICMS_MODO"] = self.modo_anterior

    def carregar_ficha(self) -> None:
        """Apresenta uma ficha completa com dados exclusivamente sintéticos."""
        self.aplicacao.session_state.ficha = ficha_valida()
        self.aplicacao.session_state.geracao = 99
        self.aplicacao.run()
        self.assertFalse(self.aplicacao.exception)

    def clicar(self, rotulo: str) -> None:
        """Clica e aguarda o novo ciclo do Streamlit."""
        next(
            botao for botao in self.aplicacao.button if botao.label == rotulo
        ).click().run()
        self.assertFalse(self.aplicacao.exception)

    def test_inicio_exibe_ficha_e_resultados(self) -> None:
        """Apresenta os dois módulos sem conexão SQL na demonstração."""
        self.assertFalse(self.aplicacao.exception)
        self.assertEqual(list(self.aplicacao.radio[0].options), ["Ficha", "Resultados"])
        self.assertTrue(
            any(b.label == "Salvar rascunho" for b in self.aplicacao.button)
        )

    def test_demo_permitida_sem_secrets(self) -> None:
        """Permite iniciar uma demonstração isolada se não houver configuração."""
        os.environ.pop("ICMS_MODO", None)
        try:
            aplicacao = AppTest.from_file(
                str(RAIZ / "app.py"), default_timeout=30
            ).run()
            botao = next(
                b for b in aplicacao.button
                if b.label == "Continuar na demonstração"
            )
            botao.click().run()
            self.assertFalse(aplicacao.exception)
        finally:
            os.environ["ICMS_MODO"] = "demonstracao"

    def test_modo_banco_sem_login_nao_abre_dados(self) -> None:
        """Não expõe fichas sem autenticação institucional configurada."""
        os.environ["ICMS_MODO"] = "banco"
        app = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        botao = next(
            b for b in app.button
            if b.label == "Acesso institucional ainda não configurado"
        )
        self.assertTrue(botao.disabled)

    def test_resumo_sem_revisao_repetida(self) -> None:
        """Mantém o resumo e remove a revisão redundante do formulário."""
        self.carregar_ficha()
        self.assertFalse(any(
            botao.label == "Revisar preenchimento"
            for botao in self.aplicacao.button
        ))
        titulos = " ".join(item.value for item in self.aplicacao.markdown)
        self.assertIn("Resumo final da ficha", titulos)
        self.assertNotIn("Revisão do preenchimento", titulos)

    def test_quatro_blocos_e_titulos_corretos(self) -> None:
        """Não exibe números ou a palavra Parâmetro nos títulos expansíveis."""
        self.carregar_ficha()
        rotulos = [bloco.label for bloco in self.aplicacao.expander]
        for titulo in NOMES_MUNICIPAIS.values():
            self.assertIn(titulo, rotulos)
        self.assertFalse(any(r.startswith("Parâmetro (") for r in rotulos))
        self.assertEqual(
            sum(titulo in rotulos for titulo in NOMES_MUNICIPAIS.values()), 4
        )

    def test_totais_visuais_removidos(self) -> None:
        """Elimina indicadores de totais sem suprimir o cálculo interno."""
        self.carregar_ficha()
        titulos = " ".join(item.value for item in self.aplicacao.markdown)
        self.assertNotIn("TOTAL DOS PARÂMETROS", titulos)
        self.assertFalse(
            any("Total — Pontos" in item.label for item in self.aplicacao.metric)
        )
        calculo = calcular(self.aplicacao.session_state.ficha)
        self.assertEqual(calculo["total_validado"], 34)

    def test_nomes_visiveis_nos_demais_blocos_sem_repetir_digitacao(self) -> None:
        """A identificação do primeiro bloco é reutilizada nos outros três."""
        self.carregar_ficha()
        for codigo in MUNICIPAIS[1:]:
            elemento = next(
                campo for campo in self.aplicacao.text_input
                if campo.key == f"99_somente_nome_{codigo}_1_Município demonstrativo"
            )
            self.assertEqual(elemento.value, "Município demonstrativo")
            self.assertTrue(elemento.disabled)

    def test_pontuacoes_e_justificativa_independentes(self) -> None:
        """Cada bloco possui os três campos próprios do município."""
        self.carregar_ficha()
        for codigo in MUNICIPAIS:
            for campo in ("gestor", "validado"):
                elemento = self.aplicacao.number_input(
                    key=f"99_municipio_1_{codigo}_{campo}"
                )
                self.assertEqual(elemento.value, 0)
                self.assertFalse(elemento.disabled)
            justificativa = self.aplicacao.text_area(
                key=f"99_municipio_1_{codigo}_justificativa"
            )
            self.assertEqual(justificativa.value, "")

    def test_adicionar_e_remover_registro_preserva_pontos(self) -> None:
        """Os controles modificam a quantidade real de municípios."""
        self.carregar_ficha()
        self.clicar("Adicionar registro")
        self.assertEqual(len(self.aplicacao.session_state.ficha["municipios"]), 2)
        geracao = self.aplicacao.session_state.geracao
        self.aplicacao.text_input(key=f"{geracao}_municipio_2").set_value(
            "Município sintético 02"
        ).run()
        self.assertFalse(self.aplicacao.exception)
        self.assertEqual(
            self.aplicacao.session_state.ficha["municipios"][1]["nome"],
            "município sintético 02",
        )
        next(
            botao for botao in self.aplicacao.button
            if botao.key == f"{geracao}_remover_municipio_2"
        ).click().run()
        self.assertFalse(self.aplicacao.exception)
        self.assertEqual(len(self.aplicacao.session_state.ficha["municipios"]), 1)
        self.assertEqual(
            self.aplicacao.session_state.ficha["municipios"][0]["nome"],
            "Município demonstrativo",
        )

    def test_concluir_e_consultar_resultado_municipal(self) -> None:
        """Uma ficha concluída gera um resultado por município real."""
        self.carregar_ficha()
        self.aplicacao.number_input(key="99_municipio_1_10_validado").set_value(
            3
        ).run()
        self.clicar("Cadastrar")
        self.assertTrue(
            any("Concluída salva" in aviso.value for aviso in self.aplicacao.success)
        )
        self.aplicacao.radio[0].set_value("Resultados").run()
        self.assertFalse(self.aplicacao.exception)
        grades = [
            elemento.value for elemento in self.aplicacao.markdown
            if 'class="tabela-planilha"' in elemento.value
        ]
        self.assertGreaterEqual(len(grades), 2)
        self.assertTrue(any("Município demonstrativo" in html for html in grades))
        self.assertTrue(any("Recursos Financeiro" in html for html in grades))
        self.assertTrue(any("0.4157" in html for html in grades))
        self.assertFalse(any("Nota13" in html for html in grades))


if __name__ == "__main__":
    unittest.main()
