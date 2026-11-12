"""Adequação explícita de exemplos sintéticos do backup municipal antigo.

Esta rotina não migra fichas reais nem altera a quantidade de municípios
intencionalmente vinculados a outros processos. Só reconhece o conjunto
histórico de 10 fichas sintéticas distribuído para testes do ICMS Ecológico.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from icms.regras import (
    MUNICIPAIS,
    calcular,
    normalizar_nome_municipio,
    preparar,
    validar,
)
from icms.repositorio import Repositorio

_PADRAO_SEI_EXEMPLO = re.compile(r"9999\.99\.92000(0[1-9]|10)/2026-00")
_NOMES_EXEMPLO = tuple(f"município sintético {i:02d}" for i in range(1, 14))


def indice_exemplo_legado(registro: dict[str, Any]) -> int | None:
    """Identifica somente o backup sintético de 13 municípios por processo.

    O município preservado é diferente em cada processo de demonstração,
    evitando que a mesma identificação apareça em fichas distintas.
    """
    ficha = registro.get("ficha")
    if not isinstance(ficha, dict):
        return None
    correspondencia = _PADRAO_SEI_EXEMPLO.fullmatch(str(ficha.get("processo", "")))
    if not correspondencia:
        return None
    if "uc sintética completa" not in str(ficha.get("unidade", "")).casefold():
        return None
    if registro.get("status") not in ("Concluída", "Rascunho"):
        return None
    municipios = ficha.get("municipios")
    if not isinstance(municipios, list) or len(municipios) != 13:
        return None
    nomes = tuple(
        normalizar_nome_municipio(m.get("nome", "")) for m in municipios
    )
    if nomes != _NOMES_EXEMPLO:
        return None
    if any(
        not isinstance(m.get(codigo), dict)
        or m[codigo].get("gestor") is not None
        for m in municipios
        for codigo in MUNICIPAIS
    ):
        return None
    return int(correspondencia.group(1)) - 1


def contar_exemplos_legados(registros: list[dict[str, Any]]) -> int:
    """Conta fichas do antigo exemplo de 13 municípios ainda não adequadas."""
    return sum(indice_exemplo_legado(registro) is not None for registro in registros)


def adequar_exemplos_legados(repositorio: Repositorio, autor: str) -> int:
    """Converte exemplos históricos a um município por ficha, com auditoria.

    Requer ação expressa do usuário. Faz uma pré-validação de todos os planos
    antes de gravar, e usa o mecanismo normal de versão e histórico.
    """
    if type(repositorio) is not Repositorio:
        raise ValueError("A adequação só é permitida no modo demonstração.")
    planos: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for registro in repositorio.listar():
        indice = indice_exemplo_legado(registro)
        if indice is None:
            continue
        ficha = deepcopy(registro["ficha"])
        ficha["municipios"] = [deepcopy(ficha["municipios"][indice])]
        ficha["municipios"][0]["nome"] = normalizar_nome_municipio(
            ficha["municipios"][0]["nome"]
        )
        ficha = preparar(ficha)
        erros = validar(ficha, concluir=registro["status"] == "Concluída")
        if erros:
            raise ValueError(
                f"A ficha {ficha['processo']} não pôde ser adequada: "
                + "; ".join(erros)
            )
        if registro["status"] == "Concluída":
            calcular(ficha)
        planos.append((registro, ficha))

    for registro, ficha in planos:
        repositorio.gravar(
            ficha,
            registro["versao"],
            registro["status"],
            autor,
        )
    return len(planos)
