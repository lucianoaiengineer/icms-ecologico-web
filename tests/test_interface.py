"""Testes de fluxos do formulário sem conta externa."""

import os
import unittest
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest
from test_regras import ficha_valida


class TesteInterface(unittest.TestCase):
    """Verifica inicialização e ações essenciais do Streamlit."""

    def setUp(self) -> None:
        """Isola o repositório temporário entre os testes."""
        self.modo_anterior = os.environ.get("ICMS_MODO")
        os.environ["ICMS_MODO"] = "demonstracao"
        st.cache_resource.clear()
        caminho = Path(__file__).resolve().parents[1] / "app.py"
        self.app = AppTest.from_file(str(caminho), default_timeout=30).run()

    def tearDown(self) -> None:
        """Restaura o modo configurado antes do teste."""
        if self.modo_anterior is None:
            os.environ.pop("ICMS_MODO", None)
        else:
            os.environ["ICMS_MODO"] = self.modo_anterior

    def test_aplicacao_bloqueia_quando_modo_nao_foi_configurado(self) -> None:
        """Não abre a demonstração automaticamente em uma publicação nova."""
        os.environ.pop("ICMS_MODO", None)
        try:
            caminho = Path(__file__).resolve().parents[1] / "app.py"
            app = AppTest.from_file(str(caminho), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertTrue(
                any(
                    "Aplicação ainda não configurada" in aviso.value
                    for aviso in app.error
                )
            )
        finally:
            os.environ["ICMS_MODO"] = "demonstracao"

    def test_tela_de_acesso_nao_abre_autocadastro_sem_configuracao(self) -> None:
        """Exibe o acesso restrito e mantém o botão inativo sem OIDC."""
        os.environ["ICMS_MODO"] = "sheets"
        caminho = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(caminho), default_timeout=30).run()
        self.assertFalse(app.exception)
        botao = next(
            item
            for item in app.button
            if item.label == "Acesso institucional ainda não configurado"
        )
        self.assertTrue(botao.disabled)
        self.assertTrue(
            any("confirmação de e-mail" in item.value for item in app.markdown)
        )

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
            list(self.app.radio[0].options),
            ["Ficha", "Resultados"],
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
        self.acionar("Nova ficha")
        self.assertTrue(
            any("alterações não gravadas" in aviso.value for aviso in self.app.warning)
        )
        self.acionar("Descartar alterações e iniciar nova ficha")
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
            if c.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("rascunho" in aviso.value.lower() for aviso in self.app.success)
        )
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state.modulo, "Ficha")
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

    def test_totais_dos_parametros_e_dos_blocos_municipais(self) -> None:
        """Exibe totais do primeiro quadro e de cada fator municipal."""
        self.preparar_ficha()
        valores_gestor = [9, 0, 0, 9, 0, 4, 6, 1, 3, 6, 2, 2, 2, 3]
        for (codigo, _), valor in zip(
            ficha_valida()["parametros"].items(), valores_gestor
        ):
            self.app.number_input(key=f"99_{codigo}_gestor").set_value(valor)
        for codigo, valor in zip(("10", "11.1", "11.2", "11.3"), (1, 2, 3, 4)):
            self.app.number_input(key=f"99_municipio_1_{codigo}").set_value(valor)
        self.app.run()

        totais = {item.label: str(item.value) for item in self.app.metric}
        self.assertEqual(totais["Total — Pontos Gestor"], "47")
        self.assertEqual(totais["Total — Pontos Validados"], "34")
        blocos_municipais = [
            item
            for item in self.app.expander
            if item.label.startswith("Parâmetro (")
        ]
        for bloco, valor in zip(blocos_municipais, (1, 2, 3, 4)):
            self.assertTrue(
                any(
                    item.value == f"**TOTAL: {valor}**"
                    for item in bloco.markdown
                )
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
        self.app.radio[0].set_value("Resultados").run()
        self.assertFalse(
            any("Nota1" in quadro.value.columns for quadro in self.app.dataframe)
        )
        self.assertTrue(
            any(
                "Não há fichas concluídas" in aviso.value
                for aviso in self.app.info
            )
        )

    def test_concluir_e_exibir_resultado(self) -> None:
        self.preparar_ficha()
        for codigo, valor in zip(("10", "11.1", "11.2", "11.3"), (3, 4, 5, 6)):
            self.app.number_input(key=f"99_municipio_1_{codigo}").set_value(
                valor
            )
        self.acionar("Cadastrar")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("Concluída salva" in aviso.value for aviso in self.app.success)
        )
        self.assertFalse(self.app.exception)
        self.app.radio[0].set_value("Resultados").run()
        quadros = [quadro.value for quadro in self.app.dataframe]
        resultado = next(
            quadro for quadro in quadros if "Nota1" in quadro.columns
        )
        self.assertIn("Indicador", resultado.columns)
        self.assertEqual(resultado.iloc[0]["Indicador"], "Último cadastro")
        self.assertEqual(resultado.iloc[0]["Nota1"], 0.58)
        self.assertEqual(resultado.iloc[0]["PARÂM 10"], 3)
        for codigo in ("11.1", "11.2", "11.3"):
            self.assertEqual(resultado.iloc[0][f"PARÂM {codigo}"], 4)

    def test_cadastrar_nao_exige_checkbox_de_confirmacao(self) -> None:
        self.preparar_ficha()
        self.acionar("Cadastrar")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("Concluída salva" in aviso.value for aviso in self.app.success)
        )

    def test_atualizar_exige_alteracao_e_gera_versao_nova(self) -> None:
        self.preparar_ficha()
        self.acionar("Cadastrar")
        next(
            item
            for item in self.app.text_input
            if item.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")
        atualizar = next(
            botao for botao in self.app.button if botao.label == "Atualizar ficha"
        )
        self.assertTrue(atualizar.disabled)

        chave_unidade = f"{self.app.session_state.geracao}_unidade"
        self.app.text_input(key=chave_unidade).set_value("Unidade atualizada")
        self.app.run()
        self.assertFalse(
            next(
                botao
                for botao in self.app.button
                if botao.label == "Atualizar ficha"
            ).disabled
        )
        self.acionar("Atualizar ficha")
        self.assertEqual(self.app.session_state.versao, 2)
        self.assertEqual(
            self.app.session_state.ficha["unidade"], "Unidade atualizada"
        )

    def test_consultar_processo_nao_exige_confirmacao_para_consultar(self) -> None:
        campo = next(
            item
            for item in self.app.text_input
            if item.label == "Localizar pelo processo SEI"
        )
        campo.set_value("0000.00.0000099/2026-00")
        self.acionar("Localizar ficha")
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("Processo não localizado" in aviso.value for aviso in self.app.success)
        )
        self.assertEqual(self.app.session_state.modulo, "Ficha")
        self.assertEqual(
            self.app.session_state.ficha["processo"],
            "0000.00.0000099/2026-00",
        )

    def test_consulta_protege_alteracoes_nao_gravadas(self) -> None:
        self.preparar_ficha()
        self.acionar("Salvar rascunho")
        self.app.text_input(key="99_unidade").set_value("Alteração ainda não salva")
        self.app.run()
        next(
            item
            for item in self.app.text_input
            if item.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")

        self.assertEqual(self.app.session_state.modulo, "Ficha")
        self.assertTrue(
            any("alterações ainda não gravadas" in aviso.value for aviso in self.app.warning)
        )
        self.acionar("Descartar alterações e abrir ficha localizada")
        self.assertEqual(self.app.session_state.modulo, "Ficha")
        self.assertEqual(
            self.app.session_state.ficha["unidade"], "UC demonstrativa"
        )

    def test_excluir_ficha_carregada(self) -> None:
        self.preparar_ficha()
        self.acionar("Salvar rascunho")
        next(
            item
            for item in self.app.text_input
            if item.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")
        self.acionar("Excluir ficha")
        self.assertFalse(self.app.exception)
        self.acionar("Confirmar exclusão")
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state.modulo, "Ficha")


if __name__ == "__main__":
    unittest.main()
