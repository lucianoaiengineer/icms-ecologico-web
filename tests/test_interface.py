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

    def test_blocos_municipais(self) -> None:
        """Confere nomes compartilhados e pontuações independentes ao salvar."""
        self.preparar_ficha()
        blocos = [b for b in self.app.expander if b.label.startswith("Parâmetro (")]
        self.assertEqual(
            [b.label for b in blocos],
            [f"Parâmetro ({c}) por Municípios" for c in ("10", "11", "11.1", "11.2")],
        )
        for bloco in blocos:
            self.assertEqual(len(bloco.text_input), 13)
            self.assertEqual(len(bloco.number_input), 13)
        self.app.text_input(key="99_municipio_1").set_value("Município de teste")
        chaves = ("10", "11.1", "11.2", "11.3")
        for chave, valor in zip(chaves, (1, 2, 3, 4)):
            self.app.number_input(key=f"99_municipio_1_{chave}").set_value(valor)
        self.acionar("Salvar rascunho")
        self.assertFalse(self.app.exception)
        for bloco in [b for b in self.app.expander if b.label.startswith("Parâmetro (")]:
            self.assertEqual(bloco.text_input[0].value, "Município de teste")
        next(c for c in self.app.text_input if c.label == "Número do processo SEI").set_value(
            "0000.00.0000001/2026-00"
        )
        next(c for c in self.app.checkbox if c.label.startswith("Confirmo")).check()
        self.acionar("Consultar processo")
        self.assertFalse(self.app.exception)
        municipio = self.app.session_state.ficha["municipios"][0]
        self.assertEqual(municipio["nome"], "Município de teste")
        self.assertEqual([municipio[c] for c in chaves], [1, 2, 3, 4])

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
