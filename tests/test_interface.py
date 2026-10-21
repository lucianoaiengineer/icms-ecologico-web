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
        rotulos = [campo.label for campo in self.app.text_input]
        self.assertLess(
            rotulos.index("Responsável técnico"), rotulos.index("URFBio")
        )
        self.assertFalse(
            any("Descartar campos não salvos" in c.label for c in self.app.checkbox)
        )

    def test_nova_ficha_tem_confirmacao_clara(self) -> None:
        self.preparar_ficha()
        self.acionar("Iniciar nova ficha")
        self.assertTrue(
            any("dados ainda não salvos" in aviso.value for aviso in self.app.warning)
        )
        self.acionar("Descartar e iniciar nova ficha")
        self.assertEqual(self.app.session_state.ficha["processo"], "")

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
        next(
            c
            for c in self.app.text_input
            if c.label == "Número do processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Consultar processo")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("Rascunho" in aviso.value for aviso in self.app.success)
        )
        self.assertFalse(
            any(
                c.label.startswith("Confirmo que desejo abrir")
                for c in self.app.checkbox
            )
        )
        self.acionar("Abrir ficha no Cadastro")
        self.assertFalse(self.app.exception)
        municipio = self.app.session_state.ficha["municipios"][0]
        self.assertEqual(municipio["nome"], "Município de teste")
        self.assertEqual([municipio[c] for c in chaves], [1, 2, 3, 4])

    def test_quadro_final_da_ficha_apresenta_13_municipios_e_fq(self) -> None:
        self.preparar_ficha()
        quadro = next(
            item.value
            for item in self.app.dataframe
            if "PONTUAÇÃO FINAL FQ" in item.value.columns
        )
        self.assertEqual(len(quadro), 13)
        self.assertEqual(
            quadro.iloc[0]["Município"], "Município demonstrativo"
        )
        esperado = sum(
            ponto["validado"] for ponto in ficha_valida()["parametros"].values()
        ) + sum(ficha_valida()["municipios"][0][codigo] for codigo in ("10", "11.1", "11.2", "11.3"))
        self.assertEqual(quadro.iloc[0]["SOMA PARÂMETROS"], str(esperado))
        self.assertEqual(
            quadro.iloc[0]["PONTUAÇÃO FINAL FQ"],
            f"{esperado / 89:.2f}".replace(".", ","),
        )

    def test_revisar_propaga_nomes_para_todos_os_parametros(self) -> None:
        """Mostra os nomes do parâmetro 10 nos outros blocos após revisar."""
        self.preparar_ficha()
        self.app.text_input(key="99_municipio_1").set_value("Município de teste")
        self.acionar("Revisar preenchimento")
        blocos = [
            bloco
            for bloco in self.app.expander
            if bloco.label.startswith("Parâmetro (")
        ]
        self.assertFalse(self.app.exception)
        self.assertEqual(
            [bloco.text_input[0].value for bloco in blocos],
            ["Município de teste"] * 4,
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
        self.assertTrue(
            any(
                "Situação" in quadro.value
                and "Rascunho" in quadro.value["Situação"].tolist()
                for quadro in self.app.dataframe
            )
        )
        self.assertTrue(
            any(
                "Nenhuma ficha concluída" in aviso.value
                for aviso in self.app.info
            )
        )

    def test_concluir_e_exibir_resultado(self) -> None:
        self.preparar_ficha()
        for codigo, valor in zip(("10", "11.1", "11.2", "11.3"), (3, 4, 5, 6)):
            self.app.number_input(key=f"99_municipio_1_{codigo}").set_value(
                valor
            )
        next(
            campo
            for campo in self.app.checkbox
            if campo.label.startswith("Revisei")
        ).check()
        self.acionar("Salvar")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("Concluída salva" in aviso.value for aviso in self.app.success)
        )
        self.assertFalse(self.app.exception)
        quadros = [quadro.value for quadro in self.app.dataframe]
        resultado = next(
            quadro for quadro in quadros if "Nota1" in quadro.columns
        )
        self.assertEqual(resultado.iloc[0]["Nota1"], 0.58)
        self.assertEqual(resultado.iloc[0]["PARÂM 10"], 3)
        for codigo in ("11.1", "11.2", "11.3"):
            self.assertEqual(resultado.iloc[0][f"PARÂM {codigo}"], 4)

    def test_concluir_exige_confirmacao(self) -> None:
        self.preparar_ficha()
        self.acionar("Salvar")
        self.assertTrue(
            any(
                "marque a confirmação" in erro.value for erro in self.app.error
            )
        )
        self.assertFalse(self.app.success)

    def test_consultar_processo_nao_exige_confirmacao_para_consultar(self) -> None:
        campo = next(
            item
            for item in self.app.text_input
            if item.label == "Número do processo SEI"
        )
        campo.set_value("0000.00.0000099/2026-00")
        self.acionar("Consultar processo")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("Processo não cadastrado" in aviso.value for aviso in self.app.info)
        )

    def test_excluir_ficha_consultada(self) -> None:
        self.preparar_ficha()
        self.acionar("Salvar rascunho")
        next(
            item
            for item in self.app.text_input
            if item.label == "Número do processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Consultar processo")
        next(
            item
            for item in self.app.checkbox
            if item.label.startswith("Confirmo a exclusão")
        ).check()
        self.app.run()
        self.acionar("Excluir ficha")
        self.assertFalse(self.app.exception)
        self.assertIsNone(
            self.app.session_state.registro_consultado
        )


if __name__ == "__main__":
    unittest.main()
