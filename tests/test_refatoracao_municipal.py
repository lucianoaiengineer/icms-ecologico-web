"""Cenários de compatibilidade, inclusão dinâmica e segurança de registros."""

from __future__ import annotations

import csv
import io
import json
import unittest
from copy import deepcopy

from icms.regras import (
    MUNICIPAIS,
    calcular,
    normalizar_municipios,
    nova_ficha,
    nova_linha_municipal,
    preparar,
    validar,
)
from icms.repositorio import CABECALHO_BACKUP_CSV, Repositorio
from icms.relatorios import quadro_final_ficha, resultado_consolidado
from tests.test_regras import ficha_valida


class TesteRefatoracaoMunicipal(unittest.TestCase):
    """Evita perda de pontos ao adaptar o modelo com linhas dinâmicas."""

    def test_ficha_nova_tem_uma_linha_e_nao_treze(self) -> None:
        """Uma ficha começa com apenas uma entrada municipal em branco."""
        self.assertEqual(len(nova_ficha()["municipios"]), 1)

    def test_legado_preserva_validado_sem_inventar_gestor(self) -> None:
        """Transforma as 13 posições antigas preservando o FQ homologado."""
        ficha = ficha_valida()
        ficha["municipios"] = [
            {
                "nome": "Município demonstrativo",
                **{codigo: 0 for codigo in MUNICIPAIS},
            }
        ] + [
            {"nome": "", **{codigo: None for codigo in MUNICIPAIS}}
            for _ in range(12)
        ]
        preparada = preparar(ficha)
        self.assertEqual(len(preparada["municipios"]), 1)
        for codigo in MUNICIPAIS:
            pontos = preparada["municipios"][0][codigo]
            self.assertEqual(pontos["validado"], 0)
            self.assertIsNone(pontos["gestor"])
        self.assertTrue(preparada["municipios"][0]["_legado"])
        self.assertEqual(calcular(preparada)["municipios"][0]["FQ"], "0,3820")
        repositorio = Repositorio()
        repositorio.gravar(ficha, 0, "Concluída", "testes")
        self.assertEqual(resultado_consolidado(repositorio.listar()).shape[0], 1)

    def test_backup_csv_antigo_e_restaurado_e_calculado(self) -> None:
        """Importa uma linha CSV com JSON legado de 13 posições."""
        ficha = ficha_valida()
        ficha["municipios"] = [
            {
                "nome": "Município demonstrativo",
                **{codigo: 2 for codigo in MUNICIPAIS},
            }
        ] + [
            {"nome": "", **{codigo: None for codigo in MUNICIPAIS}}
            for _ in range(12)
        ]
        csv_texto = io.StringIO(newline="")
        escritor = csv.DictWriter(
            csv_texto, delimiter=";", fieldnames=CABECALHO_BACKUP_CSV
        )
        escritor.writeheader()
        escritor.writerow({
            "processo": ficha["processo"],
            "versao": 1,
            "status": "Concluída",
            "autor": "legado",
            "atualizado_em": "2026-11-10T10:00:00-03:00",
            "conteudo_json": json.dumps(ficha, ensure_ascii=False),
            "historico_json": "[]",
        })
        repo = Repositorio()
        self.assertEqual(repo.restaurar_backup_csv(csv_texto.getvalue().encode()), 1)
        registro = repo.consultar(ficha["processo"])
        self.assertEqual(len(registro["ficha"]["municipios"]), 1)
        self.assertEqual(calcular(registro["ficha"])["municipios"][0]["Soma"], 42)

    def test_gestor_e_validado_exigidos_em_registros_novos(self) -> None:
        """Campos novos seguem a regra dos parâmetros gerais para conclusão."""
        ficha = ficha_valida()
        ficha["municipios"][0]["11.2"]["gestor"] = None
        self.assertFalse(validar(ficha, concluir=False))
        self.assertTrue(any("gestor" in e for e in validar(ficha, concluir=True)))

    def test_pontuacao_sem_nome_nao_e_descartada_silenciosamente(self) -> None:
        """Uma linha inválida é preservada para informar o erro ao usuário."""
        ficha = ficha_valida()
        novo = nova_linha_municipal()
        novo["10"]["validado"] = 0
        ficha["municipios"].append(novo)
        normalizada = normalizar_municipios(ficha)
        self.assertEqual(len(normalizada["municipios"]), 2)
        self.assertTrue(any("sem nome" in e for e in validar(normalizada)))

    def test_justificativas_sao_independentes_e_persistidas(self) -> None:
        """Uma justificativa em 11.1 não altera outros parâmetros ou o FQ."""
        ficha = ficha_valida()
        original = calcular(ficha)["municipios"][0]["FQ"]
        ficha["municipios"][0]["11.1"]["justificativa"] = "Texto técnico"
        repositorio = Repositorio()
        salvo = repositorio.gravar(ficha, 0, "Concluída", "teste")
        self.assertEqual(
            salvo["ficha"]["municipios"][0]["11.1"]["justificativa"],
            "Texto técnico",
        )
        self.assertEqual(calcular(salvo["ficha"])["municipios"][0]["FQ"], original)
        self.assertEqual(
            salvo["ficha"]["municipios"][0]["10"]["justificativa"], ""
        )

    def test_remocao_intermediaria_nao_mistura_notas(self) -> None:
        """Ao remover uma linha, os parâmetros acompanham o município correto."""
        ficha = ficha_valida()
        for numero, valor in ((2, 4), (3, 8)):
            novo = nova_linha_municipal(f"Município {numero}")
            for codigo in MUNICIPAIS:
                novo[codigo].update(gestor=valor, validado=valor)
            ficha["municipios"].append(novo)
        ficha["municipios"].pop(1)
        notas = calcular(ficha)["municipios"]
        self.assertEqual(len(notas), 2)
        self.assertEqual(notas[1]["Município"], "Município 3")
        self.assertEqual(notas[1]["Soma"], 66)
        self.assertEqual(len(quadro_final_ficha(ficha)), 2)

    def test_nao_existe_limite_herdado_de_treze_municipios(self) -> None:
        """A quantidade de linhas não é determinada pelo modelo antigo."""
        ficha = ficha_valida()
        ficha["municipios"] = [
            nova_linha_municipal(f"Município sintético {i:03d}")
            for i in range(101)
        ]
        self.assertEqual(validar(ficha, concluir=False), [])


if __name__ == "__main__":
    unittest.main()
