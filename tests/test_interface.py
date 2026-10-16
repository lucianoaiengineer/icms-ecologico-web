"""Testes de fluxos do formulário sem conta externa."""

import unittest
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest
from test_regras import ficha_valida


class TesteInterface(unittest.TestCase):
    """Verifica inicialização e ações essenciais do Streamlit."""

    def setUp(self) -> None:
        """Isola o repositório temporário entre os testes."""
        st.cache_resource.clear()
        caminho = Path(__file__).resolve().parents[1] / "app.py"
        self.app = AppTest.from_file(str(caminho), default_timeout=30).run()

    def preparar_ficha(self) -> None:
        """Carrega somente dados sintéticos na sessão de teste."""
        self.app.session_state.ficha = ficha_valida()
        self.app.session_state.geracao = 99
        self.app.run()

    def acionar(self, rotulo: str) -> None:
        """Aciona o botão por seu texto visível."""
        next(
            botao for botao in self.app.button if botao.label == rotulo
        ).click().run()

    def test_inicio(self) -> None:
        self.assertFalse(self.app.exception)
        self.assertEqual(
            [aba.label for aba in self.app.tabs],
            ["Consulta/Edição", "Cadastro", "Resultados"],
        )

    def test_rascunho(self) -> None:
        self.preparar_ficha()
        self.acionar("Salvar rascunho")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any(
                "salva e verificada" in aviso.value
                for aviso in self.app.success
            )
        )
        self.acionar("Consultar resultados")
        self.assertTrue(
            any(
                "Nenhuma ficha concluída" in aviso.value
                for aviso in self.app.info
            )
        )

    def test_concluir_e_exibir_resultado(self) -> None:
        self.preparar_ficha()
        next(
            campo
            for campo in self.app.checkbox
            if campo.label.startswith("Revisei")
        ).check()
        self.acionar("Concluir e salvar resultado")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("Concluída salva" in aviso.value for aviso in self.app.success)
        )
        self.acionar("Consultar resultados")
        self.assertFalse(self.app.exception)
        quadros = [quadro.value for quadro in self.app.dataframe]
        resultado = next(
            quadro for quadro in quadros if "Nº SEI" in quadro.columns
        )
        self.assertEqual(resultado.iloc[0]["Nota1"], 0.38)

    def test_concluir_exige_confirmacao(self) -> None:
        self.preparar_ficha()
        self.acionar("Concluir e salvar resultado")
        self.assertTrue(
            any(
                "marque a confirmação" in erro.value for erro in self.app.error
            )
        )
        self.assertFalse(self.app.success)


if __name__ == "__main__":
    unittest.main()
