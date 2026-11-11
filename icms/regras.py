"""Regras da ficha, independentes da interface e do armazenamento."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

PARAMETROS = (
    ("1.1", "Aspecto - Ecossistema/mapa"),
    ("1.2", "Aspecto - Área recuperação/mapa"),
    ("1.3", "Aspecto - ZVS/mapa"),
    ("2", "Reserva legal e APPs/mapa"),
    ("3", "Situação fundiária"),
    ("4", "Limites/mapa"),
    ("5.1", "Aspecto - PM"),
    ("5.2", "Aspecto - Sem PM"),
    ("6", "Combate incêndios/mapa"),
    ("7", "Conselhos"),
    ("8.1", "Aspecto - Colaboradores"),
    ("8.2", "Aspecto - Gestor"),
    ("8.3", "Aspecto - Capacitação"),
    ("9", "Infraestrutura e equipamentos"),
)
# Chaves de armazenamento existentes: 10, 11.1, 11.2 e 11.3.
# A numeração anterior da interface era diferente e foi corrigida.
MUNICIPAIS = ("10", "11.1", "11.2", "11.3")
NOMES_MUNICIPAIS = {
    "10": "Zona de Amortecimento",
    "11.1": "RH ou Recurso Material",
    "11.2": "Empréstimo de Sede",
    "11.3": "Recursos Financeiro",
}
ROTULOS_MUNICIPAIS = {codigo: codigo for codigo in MUNICIPAIS}
CASAS_DECIMAIS_FQ = 4
PRECISAO_FQ = Decimal(1).scaleb(-CASAS_DECIMAIS_FQ)


def agora() -> datetime:
    """Retorna o horário de Brasília, independente do servidor."""
    return datetime.now(ZoneInfo("America/Sao_Paulo"))


def normalizar_processo(valor: str) -> str:
    """Valida e padroniza a chave SEI do modelo fornecido."""
    digitos = re.sub(r"[.\s/\-]", "", valor)
    if not re.fullmatch(r"[0-9]{19}", digitos):
        raise ValueError("Informe o SEI no formato 0000.00.0000000/0000-00.")
    return (
        f"{digitos[:4]}.{digitos[4:6]}.{digitos[6:13]}/{digitos[13:17]}-{digitos[17:]}"
    )


def normalizar_nome_municipio(nome: str) -> str:
    """Reduz espaços e usa minúsculas, preservando os acentos do município."""
    return re.sub(r"\s+", " ", str(nome or "").strip()).lower()


def nova_linha_municipal(nome: str = "") -> dict[str, Any]:
    """Cria uma única linha compartilhada pelos quatro blocos expansíveis."""
    return {
        "nome": nome,
        **{
            codigo: {"gestor": None, "justificativa": "", "validado": None}
            for codigo in MUNICIPAIS
        },
    }


def _converter_municipio(municipio: dict[str, Any]) -> dict[str, Any]:
    """Converte pontuações antigas sem inventar os pontos do gestor."""
    convertido = nova_linha_municipal(str(municipio.get("nome") or ""))
    legado = bool(municipio.get("_legado", False))
    for codigo in MUNICIPAIS:
        dado = municipio.get(codigo)
        if isinstance(dado, dict):
            convertido[codigo] = {
                "gestor": dado.get("gestor"),
                "justificativa": dado.get("justificativa", ""),
                "validado": dado.get("validado"),
            }
        else:
            # A ficha histórica possui um único ponto, usado pelo FQ.
            # Não se pode presumir que foi o ponto atribuído pelo gestor.
            convertido[codigo]["validado"] = dado
            legado = True
    if legado:
        convertido["_legado"] = True
    return convertido


def normalizar_municipios(ficha: dict[str, Any]) -> dict[str, Any]:
    """Mantém apenas registros existentes e adapta fichas antigas de 13 linhas.

    Uma linha sem nome mas com pontuação é mantida para que a validação
    detecte o problema, em vez de descartar silenciosamente esses dados.
    """
    copia = deepcopy(ficha)
    convertidos = []
    for municipio in copia.get("municipios", []):
        convertido = _converter_municipio(municipio)
        com_valor = any(
            dado.get("gestor") is not None
            or dado.get("validado") is not None
            or bool(dado.get("justificativa"))
            for codigo in MUNICIPAIS
            for dado in (convertido[codigo],)
        )
        if convertido["nome"].strip() or com_valor:
            convertidos.append(convertido)
    copia["municipios"] = convertidos
    return copia


def nova_ficha() -> dict[str, Any]:
    """Cria ficha nova com uma linha inicial, sem 13 posições predefinidas."""
    hoje = agora().date()
    return {
        "processo": "",
        "orgao": "",
        "unidade": "",
        "esfera": "",
        "urfbio": "",
        "categoria": "",
        "pontuacao_categoria": 89,
        "responsavel": "",
        "tecnico": "",
        "analise": hoje.strftime("%m/%Y"),
        "recebimento": hoje.isoformat(),
        "parametros": {
            codigo: {
                "rotulo": f"{codigo} · {nome}",
                "gestor": None,
                "justificativa": "",
                "validado": None,
            }
            for codigo, nome in PARAMETROS
        },
        "municipios": [nova_linha_municipal()],
    }


def validar(ficha: dict[str, Any], concluir: bool = False) -> list[str]:
    """Valida rascunho ou conclusão sem confundir ausência de valor com zero."""
    erros: list[str] = []
    try:
        normalizar_processo(ficha["processo"])
    except (ValueError, KeyError, TypeError):
        erros.append("Informe um número SEI válido para salvar.")
    categoria = ficha.get("pontuacao_categoria")
    if type(categoria) is not int or not 1 <= categoria <= 999:
        erros.append("Pontuação da categoria: informe um inteiro de 1 a 999.")
    if not re.fullmatch(r"(0[1-9]|1[0-2])/[0-9]{4}", ficha.get("analise", "")):
        erros.append("Data de análise: use mm/aaaa.")
    try:
        datetime.strptime(ficha.get("recebimento", ""), "%Y-%m-%d")
    except (ValueError, TypeError):
        erros.append("Data de recebimento inválida.")
    if concluir and not ficha.get("unidade", "").strip():
        erros.append("Informe a unidade de conservação para concluir.")

    for codigo, _ in PARAMETROS:
        for campo in ("gestor", "validado"):
            valor = ficha["parametros"][codigo][campo]
            if valor is None:
                if concluir:
                    erros.append(f"Parâmetro {codigo}: preencha pontos {campo}.")
            elif type(valor) is not int or not 0 <= valor <= 9:
                erros.append(f"Parâmetro {codigo}: pontos {campo} devem ser de 0 a 9.")

    municipios = ficha.get("municipios", [])
    nomes: set[str] = set()
    for posicao, municipio in enumerate(municipios, 1):
        nome = str(municipio.get("nome") or "").strip()
        identificado = bool(nome and nome != "-")
        if identificado:
            chave_nome = normalizar_nome_municipio(nome)
            if chave_nome in nomes:
                erros.append(f"Município repetido na posição {posicao}.")
            nomes.add(chave_nome)
        for codigo in MUNICIPAIS:
            dados = municipio.get(codigo)
            if not isinstance(dados, dict):
                # Aceita fichas anteriores em memória sem sobrescrever os valores.
                dados = {"gestor": None, "validado": dados, "justificativa": ""}
                antigo = True
            else:
                antigo = bool(municipio.get("_legado"))
            for campo in ("gestor", "validado"):
                valor = dados.get(campo)
                if valor is not None and (
                    type(valor) is not int or not 0 <= valor <= 9
                ):
                    erros.append(
                        f"Município {posicao}, parâmetro {codigo}, "
                        f"pontos {campo}: use 0 a 9."
                    )
                if identificado and concluir and valor is None:
                    if campo != "gestor" or not antigo:
                        erros.append(f"{nome}: preencha pontos {campo} de {codigo}.")
            justificativa = dados.get("justificativa", "")
            if not isinstance(justificativa, str):
                erros.append(
                    f"Município {posicao}, parâmetro {codigo}: "
                    "justificativa inválida."
                )
            if not identificado and (
                dados.get("gestor") is not None
                or dados.get("validado") is not None
                or bool(justificativa)
            ):
                erros.append(f"Município {posicao}: há dados sem nome de município.")
    if concluir and not nomes:
        erros.append("Informe pelo menos um município para concluir.")
    return erros


def formatar_fq(soma: int, pontuacao_categoria: int) -> str:
    """Formata a pontuação final com quatro casas e vírgula decimal."""
    fator = (Decimal(soma) / Decimal(pontuacao_categoria)).quantize(
        PRECISAO_FQ, rounding=ROUND_HALF_UP
    )
    return format(fator, "f").replace(".", ",")


def calcular(ficha: dict[str, Any]) -> dict[str, Any]:
    """Calcula FQ por município a partir dos quatro pontos validados."""
    erros = validar(ficha, concluir=True)
    if erros:
        raise ValueError("\n".join(erros))
    total_validado = sum(ponto["validado"] for ponto in ficha["parametros"].values())
    totais = {codigo: 0 for codigo in MUNICIPAIS}
    resultados = []
    for municipio in ficha["municipios"]:
        nome = str(municipio["nome"]).strip()
        if nome in ("", "-"):
            continue
        pontos = {
            codigo: (
                municipio[codigo]["validado"]
                if isinstance(municipio[codigo], dict)
                else municipio[codigo]
            )
            for codigo in MUNICIPAIS
        }
        soma = total_validado + sum(pontos.values())
        fator = (Decimal(soma) / Decimal(ficha["pontuacao_categoria"])).quantize(
            PRECISAO_FQ, rounding=ROUND_HALF_UP
        )
        resultados.append(
            {
                "Município": nome,
                "Soma": soma,
                "FQ": format(fator, "f").replace(".", ","),
                "fq_numero": float(fator),
            }
        )
        for codigo in MUNICIPAIS:
            totais[codigo] += pontos[codigo]
    return {
        "total_validado": total_validado,
        "totais": totais,
        "municipios": resultados,
    }


def preparar(ficha: dict[str, Any]) -> dict[str, Any]:
    """Padroniza o SEI e converte fichas antigas sem apagar pontuações."""
    copia = normalizar_municipios(ficha)
    copia["processo"] = normalizar_processo(copia["processo"])
    for codigo, nome in PARAMETROS:
        copia["parametros"].setdefault(codigo, {}).setdefault(
            "rotulo", f"{codigo} · {nome}"
        )
    return copia
