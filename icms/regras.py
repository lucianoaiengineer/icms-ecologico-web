"""Regras da ficha, independentes da interface e do armazenamento."""

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
# Preserva as chaves da versão anterior para não deslocar valores já salvos.
# Estas chaves são identificadores de armazenamento, não rótulos da ficha.
MUNICIPAIS = ("10", "11.1", "11.2", "11.3")
ROTULOS_MUNICIPAIS = {
    "10": "10",
    "11.1": "11",
    "11.2": "11.1",
    "11.3": "11.2",
}


def agora() -> datetime:
    """Retorna o horário de Brasília, independente do servidor."""
    return datetime.now(ZoneInfo("America/Sao_Paulo"))


def normalizar_processo(valor: str) -> str:
    """Valida e padroniza a chave SEI do modelo fornecido."""
    digitos = re.sub(r"[.\s/\-]", "", valor)
    if not re.fullmatch(r"[0-9]{19}", digitos):
        raise ValueError("Informe o SEI no formato 0000.00.0000000/0000-00.")
    return (
        f"{digitos[:4]}.{digitos[4:6]}.{digitos[6:13]}/"
        f"{digitos[13:17]}-{digitos[17:]}"
    )


def nova_ficha() -> dict[str, Any]:
    """Cria uma ficha vazia, com os padrões aprovados."""
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
            codigo: {"gestor": None, "justificativa": "", "validado": None}
            for codigo, _ in PARAMETROS
        },
        "municipios": [
            {"nome": "", **{codigo: None for codigo in MUNICIPAIS}}
            for _ in range(13)
        ],
    }


def validar(ficha: dict[str, Any], concluir: bool = False) -> list[str]:
    """Valida tipos e limites; conclusão exige entradas para calcular."""
    erros: list[str] = []
    try:
        normalizar_processo(ficha["processo"])
    except (ValueError, KeyError):
        erros.append("Informe um número SEI válido para salvar.")
    categoria = ficha.get("pontuacao_categoria")
    if type(categoria) is not int or not 1 <= categoria <= 999:
        erros.append("Pontuação da categoria: informe um inteiro de 1 a 999.")
    if not re.fullmatch(r"(0[1-9]|1[0-2])/[0-9]{4}", ficha.get("analise", "")):
        erros.append("Data de análise: use mm/aaaa.")
    try:
        datetime.strptime(ficha.get("recebimento", ""), "%Y-%m-%d")
    except ValueError:
        erros.append("Data de recebimento inválida.")
    if concluir and not ficha.get("unidade", "").strip():
        erros.append("Informe a unidade de conservação para concluir.")

    # Uma entrada ausente permanece distinta do zero informado.
    for codigo, _ in PARAMETROS:
        for campo in ("gestor", "validado"):
            valor = ficha["parametros"][codigo][campo]
            if valor is None:
                if concluir:
                    erros.append(
                        f"Parâmetro {codigo}: preencha pontos {campo}."
                    )
            elif type(valor) is not int or not 0 <= valor <= 9:
                erros.append(
                    f"Parâmetro {codigo}: pontos {campo} devem ser de 0 a 9."
                )
    municipios = ficha["municipios"]
    if len(municipios) != 13:
        erros.append("A ficha deve manter 13 posições de municípios.")
    nomes: set[str] = set()
    for posicao, municipio in enumerate(municipios, 1):
        nome = municipio["nome"].strip()
        if nome and nome != "-":
            if nome.casefold() in nomes:
                erros.append(f"Município repetido na posição {posicao}.")
            nomes.add(nome.casefold())
        for codigo in MUNICIPAIS:
            valor = municipio[codigo]
            if valor is not None and (
                type(valor) is not int or not 0 <= valor <= 9
            ):
                erros.append(
                    f"Município {posicao}, parâmetro {ROTULOS_MUNICIPAIS[codigo]}: use 0 a 9."
                )
            if not nome or nome == "-":
                if valor not in (None, 0):
                    erros.append(
                        f"Município {posicao}: há pontos sem nome de município."
                    )
            elif concluir and valor is None:
                erros.append(
                    f"{nome}: preencha o parâmetro {ROTULOS_MUNICIPAIS[codigo]}."
                )
    if concluir and not nomes:
        erros.append("Informe pelo menos um município para concluir.")
    return erros


def calcular(ficha: dict[str, Any]) -> dict[str, Any]:
    """Calcula FQ individual sem usar os totais consolidados municipais."""
    erros = validar(ficha, concluir=True)
    if erros:
        raise ValueError("\n".join(erros))
    total = sum(p["validado"] for p in ficha["parametros"].values())
    totais = {codigo: 0 for codigo in MUNICIPAIS}
    resultados = []
    for municipio in ficha["municipios"]:
        if municipio["nome"].strip() in ("", "-"):
            continue
        soma = total + sum(municipio[codigo] for codigo in MUNICIPAIS)
        fator = Decimal(soma) / Decimal(ficha["pontuacao_categoria"])
        resultados.append(
            {
                "Município": municipio["nome"].strip(),
                "Soma": soma,
                "FQ": format(
                    fator.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    "f",
                ).replace(".", ","),
                "fq_numero": float(fator),
            }
        )
        for codigo in MUNICIPAIS:
            totais[codigo] += municipio[codigo]
    return {
        "total_validado": total,
        "totais": totais,
        "municipios": resultados,
    }


def preparar(ficha: dict[str, Any]) -> dict[str, Any]:
    """Retorna cópia com chave normalizada, sem alterar a tela."""
    copia = deepcopy(ficha)
    copia["processo"] = normalizar_processo(copia["processo"])
    return copia
