"""Identificação de edições temporárias antes da gravação oficial."""

from __future__ import annotations

from typing import Any


def chave_edicao(ficha: dict[str, Any]) -> str:
    """Retorna o SEI informado ou um marcador interno para a ficha ainda nova."""
    return str(ficha.get("processo", "")).strip() or "__nova__"
