"""Interface web de cadastro, consulta e resultados do ICMS Ecológico."""

import html
import os
from copy import deepcopy
from datetime import date
from numbers import Real
from typing import Any

import pandas as pd
import streamlit as st

from icms.regras import (
    MUNICIPAIS,
    PARAMETROS,
    ROTULOS_MUNICIPAIS,
    calcular,
    normalizar_processo,
    nova_ficha,
)
from icms.repositorio import Conflito, Repositorio, RepositorioSheets

st.set_page_config(
    page_title="Gestão de Fichas | ICMS Ecológico", layout="centered"
)

st.markdown(
    """
    <style>
    :root {
        --ief-cinza-fundo: #f3f4f6;
        --ief-verde-medio: #2f6b3c;
        --ief-verde-escuro: #234b2e;
        --ief-verde-contorno: #4b8b55;
        --ief-texto: #24352a;
        --ief-texto-secundario: #46574a;
        --ief-terra: #8b6b3e;
    }
    [data-testid="stAppViewContainer"] {
        background: var(--ief-cinza-fundo) !important;
        color: var(--ief-texto) !important;
    }
    [data-testid="stHeader"] {
        background: rgba(243, 244, 246, 0.96) !important;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 980px;
        margin: 1.1rem auto 2rem auto;
        padding-left: 1.25rem;
        padding-right: 1.25rem;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        color: var(--ief-texto) !important;
        background: #ffffff !important;
        border: 2px solid var(--ief-verde-escuro);
        border-radius: 0.8rem;
        box-shadow: 0 5px 20px #24452b0d;
        box-sizing: border-box;
    }
    [data-testid="stMainBlockContainer"]:has(.st-key-cartao_acesso) {
        width: 100%;
        max-width: 980px;
        min-height: calc(100vh - 2rem);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin: auto;
        padding-top: 1rem;
        padding-bottom: 1rem;
        background: transparent !important;
        border: 0 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }
    [data-testid="stMainBlockContainer"]:has(.st-key-resultados_grade) {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-cartao_acesso) {
        width: min(360px, calc(100vw - 2rem));
        max-width: 360px;
        margin: auto !important;
        padding: 1.2rem clamp(1rem, 5vw, 1.4rem) !important;
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1px solid #d8e5d2;
        border-top: 5px solid var(--ief-verde-medio);
        border-radius: 0.8rem;
        box-shadow: 0 12px 35px #24452b18;
        box-sizing: border-box;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-cartao_acesso) > div {
        background: #ffffff !important;
    }
    .st-key-cartao_acesso {
        width: min(360px, calc(100vw - 2rem)) !important;
        max-width: 360px !important;
        margin: auto !important;
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: var(--ief-texto) !important;
    }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stExpander"] summary,
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
        color: var(--ief-texto-secundario) !important;
        opacity: 1 !important;
    }
    [data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #477a3e !important;
        border-radius: 0.35rem !important;
    }
    [data-testid="stExpander"] summary {
        color: #111111 !important;
        font-weight: 700 !important;
    }
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stWidgetLabel"] p,
    label {
        color: var(--ief-texto) !important;
        opacity: 1 !important;
    }
    [data-testid="stMarkdownContainer"] strong {
        color: #111111 !important;
    }
    /* Delimita visualmente o próprio controle: o tema do Streamlit pode
       ocultar a borda do invólucro BaseWeb, por isso a linha também vai no input. */
    [data-testid="stTextInput"] [data-baseweb="input"],
    [data-testid="stNumberInput"] [data-baseweb="input"],
    [data-testid="stDateInput"] [data-baseweb="input"] {
        min-height: 2.35rem;
        background: #ffffff !important;
        border: 1px solid var(--ief-verde-contorno) !important;
        border-radius: 0.25rem !important;
        box-shadow: none !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input {
        min-height: 2.35rem;
        box-sizing: border-box !important;
        background: #ffffff !important;
        border: 1px solid var(--ief-verde-contorno) !important;
        border-radius: 0.25rem !important;
        box-shadow: none !important;
    }
    [data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
    [data-testid="stNumberInput"] [data-baseweb="input"]:focus-within,
    [data-testid="stDateInput"] [data-baseweb="input"]:focus-within,
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stDateInput"] input:focus {
        border: 2px solid var(--ief-verde-escuro) !important;
        outline: none !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        min-height: 2.35rem;
        box-sizing: border-box !important;
        background: #ffffff !important;
        border: 1px solid var(--ief-verde-contorno) !important;
        border-radius: 0.25rem !important;
        box-shadow: none !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
        border: 2px solid var(--ief-verde-escuro) !important;
    }
    [data-testid="stForm"] {
        padding: 0.75rem;
        background: #ffffff !important;
        border: 1px solid #477a3e !important;
        border-radius: 0.35rem !important;
    }
    [data-testid="stTextArea"] [data-baseweb="textarea"] {
        min-height: 6rem !important;
        background: #ffffff !important;
        border: 1px solid #477a3e !important;
        border-radius: 0.3rem !important;
        box-shadow: none !important;
    }
    [data-testid="stTextArea"] textarea {
        display: block !important;
        width: 100% !important;
        min-height: 6rem !important;
        box-sizing: border-box !important;
        padding: 0.65rem 0.75rem !important;
        color: var(--ief-texto) !important;
        background: #ffffff !important;
        border: 1px solid #477a3e !important;
        border-radius: 0.3rem !important;
        box-shadow: none !important;
        opacity: 1 !important;
    }
    [data-testid="stTextArea"] textarea:focus {
        border: 2px solid var(--ief-verde-escuro) !important;
        outline: none !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTextArea"] textarea {
        color: var(--ief-texto) !important;
        background: #ffffff !important;
        opacity: 1 !important;
    }
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder {
        color: #59675b !important;
        opacity: 1 !important;
    }
    .acesso-marca {
        margin-bottom: 1.5rem;
        color: var(--ief-verde-escuro);
        text-align: center;
    }
    .acesso-marca .folha {
        display: block;
        margin-bottom: 0.45rem;
        color: var(--ief-verde-medio);
        font-size: 2rem;
    }
    .acesso-marca h1 {
        margin: 0;
        font-size: 1.55rem;
        font-weight: 700;
    }
    .acesso-marca p {
        margin: 0.45rem 0 0;
        color: #526257;
    }
    .acesso-ajuda {
        margin-top: 1rem;
        color: #42564a;
        font-size: 0.92rem;
        line-height: 1.55;
    }
    .acesso-ajuda a {
        color: var(--ief-verde-escuro) !important;
        font-weight: 600;
    }
    div.stButton > button[kind="primary"] {
        border-color: var(--ief-verde-medio) !important;
        background: var(--ief-verde-medio) !important;
        color: #ffffff !important;
        font-weight: 650;
    }
    div.stButton > button[kind="primary"]:hover {
        border-color: var(--ief-verde-escuro) !important;
        background: var(--ief-verde-escuro) !important;
        color: #ffffff !important;
    }
    div.stButton > button[kind="primary"]:disabled {
        border-color: #cbd9c8 !important;
        background: #e8efe5 !important;
        color: #4c5d4e !important;
        opacity: 1 !important;
        cursor: not-allowed;
    }
    .aviso-demo {
        margin: 0.75rem 0 1rem;
        padding: 0.8rem 1rem;
        border: 1px solid #c8dbc2;
        border-left: 4px solid #6c9b67;
        border-radius: 0.45rem;
        background: #eff6eb;
        color: #29452e;
        line-height: 1.5;
    }
    .aviso-demo strong {
        color: #234b2e;
    }
    /* Mantém rótulos e controles na mesma linha em qualquer largura. */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center;
    }
    [data-testid="column"] {
        min-width: 0 !important;
    }
    .atalhos-rolagem {
        position: fixed;
        right: 1rem;
        top: 50%;
        transform: translateY(-50%);
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
        z-index: 999;
    }
    .atalhos-rolagem a {
        width: 2.7rem;
        height: 2.7rem;
        display: grid;
        place-items: center;
        border-radius: 999px;
        background: #174a72;
        color: #fff !important;
        font-size: 1.35rem;
        font-weight: 700;
        text-decoration: none !important;
        box-shadow: 0 2px 8px #0003;
    }
    .atalhos-rolagem a:hover {
        background: #0d3554;
    }
    .linha-parametro {
        border: 0;
        border-top: 1px solid #477a3e;
        margin: 0.15rem 0 0.7rem;
    }
    /* A tabela controla o próprio fundo e as bordas, sem o canvas do dataframe. */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-resultados_grade) {
        padding: 0 !important;
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-resultados_grade) > div,
    .st-key-resultados_grade {
        background: transparent !important;
        color: var(--ief-texto) !important;
    }
    .tabela-planilha-rolagem {
        width: 100%;
        max-height: 650px;
        overflow: auto;
        background: #ffffff !important;
        border: 2px solid var(--ief-verde-escuro);
        border-radius: 0.4rem;
        box-sizing: border-box;
    }
    table.tabela-planilha {
        width: max-content;
        min-width: 100%;
        border-collapse: collapse !important;
        background: #ffffff !important;
        color: var(--ief-texto) !important;
    }
    .tabela-planilha th,
    .tabela-planilha td {
        min-width: 6rem;
        padding: 0.55rem 0.65rem;
        border: 1px solid #477a3e !important;
        background: #ffffff !important;
        color: #344238 !important;
        text-align: left;
        white-space: nowrap;
    }
    .tabela-planilha th {
        position: sticky;
        top: 0;
        z-index: 2;
        background: #ffffff !important;
        color: #111111 !important;
        font-weight: 700;
    }
    .tabela-planilha td.celula-alterada {
        background: #eaf4df !important;
        color: #234b2e !important;
        font-weight: 600;
    }
    /* Verde suave destaca somente o campo cujo valor difere da ficha aberta. */
    [class*="st-key-campo_alterado_"] input,
    [class*="st-key-campo_alterado_"] textarea,
    [class*="st-key-campo_alterado_"] [data-baseweb="input"],
    [class*="st-key-campo_alterado_"] [data-baseweb="select"] > div {
        background: #eaf4df !important;
        border-color: #477a3e !important;
        box-shadow: 0 0 0 2px #477a3e24 !important;
    }
    .aviso-alteracoes {
        margin: 0.75rem 0;
        padding: 0.75rem 1rem;
        color: #234b2e;
        background: #eaf4df;
        border: 1px solid #8eae7d;
        border-left: 4px solid #477a3e;
        border-radius: 0.4rem;
    }
    .rotulo-form-linha {
        color: #111111;
        font-weight: 600;
        line-height: 1.35;
        text-align: right;
    }
    .rodape-institucional {
        margin-top: 3rem;
        color: #fff;
        background: #83a398;
        border-radius: 0.25rem 0.25rem 0 0;
        overflow: hidden;
        font-size: 0.82rem;
    }
    .rodape-principal,
    .rodape-inferior {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 1.1rem 1.25rem;
    }
    .rodape-marca {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        line-height: 1.35;
    }
    .rodape-marca strong {
        font-size: 1.7rem;
        letter-spacing: 0.08em;
    }
    .rodape-links {
        text-align: right;
    }
    .rodape-institucional a {
        color: #fff !important;
        text-decoration: underline;
        text-underline-offset: 0.15em;
    }
    .rodape-inferior {
        background: #6f9085;
        font-size: 0.72rem;
    }
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
            margin-top: 0.5rem;
            border-radius: 0.6rem;
        }
        [data-testid="stMainBlockContainer"]:has(.st-key-cartao_acesso) {
            min-height: calc(100vh - 1rem);
            margin: auto;
            border: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-cartao_acesso),
        .st-key-cartao_acesso {
            width: calc(100vw - 2rem) !important;
            max-width: 360px !important;
        }
        [data-testid="stHorizontalBlock"] {
            gap: 0.5rem;
        }
        [data-testid="stHorizontalBlock"]:has(.rotulo-form-linha) {
            flex-wrap: wrap !important;
            row-gap: 0.1rem;
        }
        [data-testid="stHorizontalBlock"]:has(.rotulo-form-linha)
        > [data-testid="column"] {
            flex: 1 1 100% !important;
            width: 100% !important;
        }
        .rotulo-form-linha {
            text-align: left;
        }
        [data-testid="stTextInput"],
        [data-testid="stNumberInput"],
        [data-testid="stSelectbox"],
        [data-testid="stDateInput"],
        [data-testid="stTextArea"] {
            min-width: 0 !important;
        }
        .atalhos-rolagem {
            right: 0.35rem;
        }
        .atalhos-rolagem a {
            width: 2.3rem;
            height: 2.3rem;
        }
        .rodape-principal,
        .rodape-inferior {
            align-items: flex-start;
            flex-direction: column;
            padding: 0.9rem 0.75rem;
        }
        .rodape-links {
            text-align: left;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def segredo(chave: str, padrao: object = None) -> object:
    """Lê configuração sem exigir arquivo de segredos na demonstração."""
    try:
        return st.secrets.get(chave, padrao)
    except FileNotFoundError:
        return padrao


@st.cache_resource
def conectar(modo: str) -> Repositorio:
    """Isola demonstrações por navegador e compartilha só a conexão Sheets."""
    if modo == "demonstracao":
        if "repositorio_demonstracao" not in st.session_state:
            st.session_state.repositorio_demonstracao = Repositorio()
        return st.session_state.repositorio_demonstracao
    return conectar_sheets()


@st.cache_resource
def conectar_sheets() -> RepositorioSheets:
    """Compartilha a conexão persistente com a planilha configurada."""
    return RepositorioSheets(
        dict(st.secrets["gcp_service_account"]), str(st.secrets["planilha_id"])
    )


def identificar(modo: str) -> tuple[str, bool]:
    """Exige identidade e autorização antes de ler dados persistentes."""
    if modo == "demonstracao":
        return "demonstracao", True
    configuracao_auth = segredo("auth")
    campos_auth = (
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    )
    try:
        auth_configurada = bool(
            configuracao_auth
            and all(
                str(configuracao_auth.get(campo, "")).strip()
                for campo in campos_auth
            )
        )
    except AttributeError:
        auth_configurada = False
    if not auth_configurada:
        exibir_tela_acesso(auth_configurada=False)
        st.stop()
    if not st.user.is_logged_in:
        exibir_tela_acesso(auth_configurada=True)
        st.stop()
    email = str(st.user.get("email", "")).lower()
    editores = [str(e).lower() for e in segredo("editores", [])]
    leitores = [str(e).lower() for e in segredo("leitores", [])]
    if (
        not st.user.get("email_verified", False)
        or email not in editores + leitores
    ):
        st.error("Conta sem autorização para acessar esta aplicação.")
        st.button("Sair", on_click=st.logout)
        st.stop()
    st.sidebar.caption(email)
    st.sidebar.button("Sair", on_click=st.logout)
    return email, email in editores


def exibir_tela_acesso(
    *, auth_configurada: bool, permitir_demo: bool = False
) -> None:
    """Apresenta o acesso institucional e orienta recuperação da conta."""
    with st.container(
        border=True,
        key="cartao_acesso",
        width=360,
        horizontal_alignment="center",
    ):
        st.markdown(
                """
                <div class="acesso-marca">
                  <span class="folha" aria-hidden="true">🌿</span>
                  <h1>ICMS Ecológico</h1>
                  <p>Gestão de fichas do Fator de Qualidade</p>
                </div>
                """,
                unsafe_allow_html=True,
        )
        if auth_configurada:
            st.button(
                "Entrar com conta institucional",
                type="primary",
                use_container_width=True,
                on_click=st.login,
            )
        elif permitir_demo:
            st.caption("Acesso institucional ainda não configurado.")
            if st.button(
                "Continuar na demonstração",
                use_container_width=True,
                key="abrir_demonstracao",
            ):
                st.session_state.modo_demo_sessao = True
                st.rerun()
        else:
            st.button(
                "Acesso institucional ainda não configurado",
                type="primary",
                use_container_width=True,
                disabled=True,
            )
        st.markdown(
            """
            <div class="acesso-ajuda">
              <p>O acesso é restrito a contas previamente autorizadas.</p>
              <p>As credenciais e a confirmação de e-mail são administradas pelo provedor institucional.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        url_recuperacao = str(segredo("url_recuperacao", "")).strip()
        url_suporte = str(segredo("url_suporte", "")).strip()
        if url_recuperacao.startswith("https://"):
            st.link_button("Esqueceu a senha? Recuperar acesso", url_recuperacao)
        if url_suporte.startswith("https://"):
            st.link_button("Solicitar acesso ou suporte", url_suporte)
        elif not url_recuperacao.startswith("https://"):
            st.caption(
                "Para recuperar a conta ou solicitar acesso, procure o suporte institucional."
            )
        if not auth_configurada:
            st.caption(
                "O acesso institucional será liberado após a configuração da autenticação. "
                "A demonstração aceita somente dados fictícios e não grava na base oficial."
            )


def abrir(
    ficha: dict, versao: int = 0, status: str = ""
) -> None:
    """Abre uma ficha em um novo conjunto de campos da sessão."""
    ficha_aberta = deepcopy(ficha)
    for codigo, nome in PARAMETROS:
        ficha_aberta["parametros"].setdefault(codigo, {}).setdefault(
            "rotulo", f"{codigo} · {nome}"
        )
    st.session_state.ficha = deepcopy(ficha_aberta)
    st.session_state.ficha_original = deepcopy(ficha_aberta)
    st.session_state.versao = versao
    st.session_state.status_ficha = status
    st.session_state.confirmar_exclusao = False
    st.session_state.confirmar_nova_ficha = False
    st.session_state.geracao = st.session_state.get("geracao", 0) + 1


def chave_container_campo(chave: str, valor_original: Any) -> str:
    """Marca o controle cuja edição diverge da versão aberta da ficha."""
    valor_atual = st.session_state.get(chave, valor_original)
    estado = "alterado" if valor_atual != valor_original else "normal"
    identificador = chave.replace(".", "_").replace("-", "_")
    return f"campo_{estado}_{identificador}"


def exibir_rotulo_formulario(rotulo: str) -> None:
    """Exibe o rótulo alinhado junto ao controle correspondente."""
    st.markdown(
        f'<div class="rotulo-form-linha">{html.escape(rotulo)}</div>',
        unsafe_allow_html=True,
    )


def texto_em_linha(
    rotulo: str,
    valor: str,
    chave: str,
    *,
    valor_original: str | None = None,
    desabilitado: bool = False,
    placeholder: str = "",
) -> str:
    """Desenha o rótulo à esquerda e o campo de texto à direita."""
    coluna_rotulo, coluna_valor = st.columns(
        [0.24, 0.76], vertical_alignment="center"
    )
    with coluna_rotulo:
        exibir_rotulo_formulario(rotulo)
    with coluna_valor:
        with st.container(
            key=chave_container_campo(chave, valor_original or "")
        ):
            return st.text_input(
                rotulo,
                value=valor,
                key=chave,
                disabled=desabilitado,
                placeholder=placeholder,
                label_visibility="collapsed",
            )


def inteiro_em_linha(
    rotulo: str,
    valor: int | None,
    chave: str,
    minimo: int,
    maximo: int,
    *,
    valor_original: int | None = None,
    desabilitado: bool = False,
) -> int | None:
    """Desenha o rótulo à esquerda e o campo numérico à direita."""
    coluna_rotulo, coluna_valor = st.columns(
        [0.24, 0.76], vertical_alignment="center"
    )
    with coluna_rotulo:
        exibir_rotulo_formulario(rotulo)
    with coluna_valor:
        with st.container(key=chave_container_campo(chave, valor_original)):
            return st.number_input(
                rotulo,
                min_value=minimo,
                max_value=maximo,
                value=valor,
                step=1,
                key=chave,
                disabled=desabilitado,
                label_visibility="collapsed",
            )


def resultado_consolidado(registros: list[dict]) -> pd.DataFrame:
    """Monta o relatório a partir das fichas concluídas, sem segunda base."""
    mapa = {
        "10": "10",
        "11.1": "11.1",
        "11.2": "11.1",
        "11.3": "11.1",
    }
    mapa.update(dict(segredo("totais_resultado", {})))
    linhas = []
    for registro in registros:
        if registro["status"] != "Concluída":
            continue
        ficha = registro["ficha"]
        calculo = calcular(ficha)
        linha = {
            "Nº SEI": ficha["processo"],
            "DATA RECEBIDA": date.fromisoformat(ficha["recebimento"]),
            "REMETENTE - UCs": ficha["unidade"],
            "Esfera": ficha["esfera"],
            "URFBio": ficha["urfbio"],
            "RESPONSÁVEL": ficha["responsavel"],
        }
        for codigo, _ in PARAMETROS:
            linha[f"PARÂM {codigo}"] = ficha["parametros"][codigo]["validado"]
        for codigo in MUNICIPAIS:
            origem = mapa.get(codigo, "10" if codigo == "10" else "")
            linha[f"PARÂM {codigo}"] = calculo["totais"].get(origem)
        for posicao in range(13):
            municipio = ficha["municipios"][posicao]
            nome = municipio["nome"].strip()
            linha[f"Município{posicao + 1}"] = (
                nome if nome not in ("", "-") else "-"
            )
            nota = next(
                (m for m in calculo["municipios"] if m["Município"] == nome),
                None,
            )
            linha[f"Nota{posicao + 1}"] = (
                float(nota["FQ"].replace(",", ".")) if nota else None
            )
        linhas.append(linha)
    return pd.DataFrame(linhas)


def quadro_final_ficha(ficha: dict) -> pd.DataFrame:
    """Monta a parte inferior da ficha para os 13 municípios."""
    total_validado = sum(
        ponto.get("validado") or 0
        for ponto in ficha["parametros"].values()
    )
    linhas = []
    for posicao, municipio in enumerate(ficha["municipios"], 1):
        nome = municipio["nome"].strip()
        if not nome or nome == "-":
            linhas.append(
                {
                    "Posição": f"Município {posicao}",
                    "Município": "-",
                "SOMA PARÂMETROS": "-",
                    "PONTUAÇÃO FINAL FQ": "-",
                }
            )
            continue
        soma = total_validado + sum(
            municipio.get(codigo) or 0 for codigo in MUNICIPAIS
        )
        fq = soma / ficha["pontuacao_categoria"]
        linhas.append(
            {
                "Posição": f"Município {posicao}",
                "Município": nome,
                "SOMA PARÂMETROS": str(soma),
                "PONTUAÇÃO FINAL FQ": f"{fq:.2f}".replace(".", ","),
            }
        )
    return pd.DataFrame(linhas)


def renderizar_tabela(
    quadro: pd.DataFrame,
    destaques_por_processo: dict[str, set[str]] | None = None,
) -> str:
    """Renderiza grade HTML branca e rolável, sem linhas vazias do Streamlit."""
    colunas = list(quadro.columns)
    cabecalho = "".join(
        f"<th scope=\"col\">{html.escape(str(coluna))}</th>"
        for coluna in colunas
    )
    linhas = []
    for _, linha in quadro.iterrows():
        processo = str(linha.get("Nº SEI", ""))
        colunas_alteradas = (
            destaques_por_processo.get(processo, set())
            if destaques_por_processo
            else set()
        )
        celulas = []
        for coluna in colunas:
            valor = linha[coluna]
            if pd.isna(valor):
                texto = ""
            elif coluna == "DATA RECEBIDA" and hasattr(valor, "strftime"):
                texto = valor.strftime("%m/%d/%Y")
            elif coluna.startswith("Nota") and isinstance(valor, Real):
                texto = f"{valor:.2f}"
            elif isinstance(valor, Real) and not isinstance(valor, bool):
                texto = str(int(valor)) if float(valor).is_integer() else str(valor)
            else:
                texto = str(valor)
            classe = (
                ' class="celula-alterada"'
                if coluna in colunas_alteradas
                else ""
            )
            celulas.append(
                f"<td{classe}>{html.escape(texto)}</td>"
            )
        linhas.append(f"<tr>{''.join(celulas)}</tr>")
    return (
        '<div class="tabela-planilha-rolagem" role="region" '
        'aria-label="Tabela de dados; use as barras de rolagem para navegar" '
        'tabindex="0"><table class="tabela-planilha">'
        f"<thead><tr>{cabecalho}</tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody></table></div>"
    )


def colunas_resultado_alteradas(alteracoes: dict[str, Any]) -> set[str]:
    """Relaciona campos alterados da ficha às colunas visíveis no resultado."""
    colunas: set[str] = set()
    campos_diretos = {
        "unidade": "REMETENTE - UCs",
        "recebimento": "DATA RECEBIDA",
        "esfera": "Esfera",
        "urfbio": "URFBio",
        "responsavel": "RESPONSÁVEL",
    }
    for caminho in alteracoes:
        if caminho in campos_diretos:
            colunas.add(campos_diretos[caminho])
        elif caminho == "pontuacao_categoria":
            colunas.update(f"Nota{posicao}" for posicao in range(1, 14))
        elif caminho.startswith("parametros."):
            partes = caminho.split(".")
            if len(partes) == 3 and partes[2] == "validado":
                colunas.add(f"PARÂM {partes[1]}")
                colunas.update(f"Nota{posicao}" for posicao in range(1, 14))
        elif caminho.startswith("municipios[") and "]." in caminho:
            posicao_texto, campo = caminho[len("municipios["):].split("].", 1)
            if not posicao_texto.isdigit():
                continue
            posicao = int(posicao_texto)
            if not 1 <= posicao <= 13:
                continue
            if campo == "nome":
                colunas.update((f"Município{posicao}", f"Nota{posicao}"))
            elif campo in MUNICIPAIS:
                colunas.update((f"PARÂM {campo}", f"Nota{posicao}"))
    return colunas


def proteger_csv(quadro: pd.DataFrame) -> bytes:
    """Exporta CSV sem permitir fórmulas em campos de texto no Excel."""
    quadro = quadro.copy()
    for coluna in quadro.columns:
        if coluna == "DATA RECEBIDA":
            quadro[coluna] = quadro[coluna].map(
                lambda v: v.strftime("%m/%d/%Y")
            )
        else:
            quadro[coluna] = quadro[coluna].map(
                lambda v: (
                    "'" + v
                    if isinstance(v, str)
                    and v.lstrip().startswith(("=", "+", "-", "@"))
                    and v != "-"
                    else v
                )
            )
    return quadro.to_csv(
        index=False, sep=";", decimal=",", float_format="%.2f"
    ).encode("utf-8-sig")


def diferencas_ficha(original: dict, atual: dict) -> list[str]:
    """Lista os campos alterados para tornar a edição visível ao usuário."""
    nomes = {
        "processo": "Processo SEI",
        "orgao": "Órgão gestor",
        "unidade": "Nome da U.C.",
        "categoria": "Categoria da U.C.",
        "esfera": "Esfera administrativa",
        "urfbio": "URFBio",
        "responsavel": "Responsável GCMUC",
        "tecnico": "Responsável técnico",
        "pontuacao_categoria": "Pontuação da categoria",
        "analise": "Data de análise",
        "recebimento": "Data de recebimento",
    }
    alterados = [
        rotulo
        for campo, rotulo in nomes.items()
        if original.get(campo) != atual.get(campo)
    ]
    for codigo, dados in atual["parametros"].items():
        antigo = original["parametros"].get(codigo, {})
        for campo, rotulo in (
            ("gestor", "Pontos Gestor"),
            ("justificativa", "Justificativa"),
            ("validado", "Pontos Validados"),
            ("rotulo", "Parâmetro"),
        ):
            if antigo.get(campo) != dados.get(campo):
                alterados.append(f"Parâmetro {codigo} · {rotulo}")
    for posicao, municipio in enumerate(atual["municipios"], 1):
        antigo = original["municipios"][posicao - 1]
        if antigo.get("nome") != municipio.get("nome"):
            alterados.append(f"Município {posicao} · Nome")
        for codigo in MUNICIPAIS:
            if antigo.get(codigo) != municipio.get(codigo):
                alterados.append(
                    f"Município {posicao} · Parâmetro {ROTULOS_MUNICIPAIS[codigo]}"
                )
    return alterados


modo_configurado = segredo("modo", os.environ.get("ICMS_MODO", ""))
modo = str(modo_configurado).strip().lower()
if st.session_state.get("modo_demo_sessao", False):
    modo = "demonstracao"
elif modo not in ("demonstracao", "sheets"):
    exibir_tela_acesso(auth_configurada=False, permitir_demo=True)
    st.stop()
autor, pode_editar = identificar(modo)
if modo == "demonstracao":
    st.markdown(
        '<div class="aviso-demo"><strong>Modo demonstração:</strong> use somente '
        "dados fictícios. Os registros ficam isolados nesta sessão do navegador, "
        "não são gravados na base oficial e desaparecem ao encerrar a sessão.</div>",
        unsafe_allow_html=True,
    )
st.markdown(
    '<div id="inicio"></div><nav class="atalhos-rolagem" '
    'aria-label="Navegação vertical"><a href="#inicio" title="Ir ao início da página" '
    'aria-label="Ir ao início">↑</a><a href="#fim" title="Ir ao final" '
    'aria-label="Ir ao final">↓</a></nav>',
    unsafe_allow_html=True,
)
st.title("ICMS Ecológico")
st.caption("Gestão de fichas do Fator de Qualidade")
try:
    repositorio = conectar(modo)
except Exception:
    st.error(
        "Não foi possível abrir a base. Confira credenciais, permissões e cabeçalhos."
    )
    st.stop()
if "ficha" not in st.session_state:
    abrir(nova_ficha())
if "ficha_original" not in st.session_state:
    st.session_state.ficha_original = deepcopy(st.session_state.ficha)
if "status_ficha" not in st.session_state:
    st.session_state.status_ficha = ""
if "modulo" not in st.session_state:
    st.session_state.modulo = "Ficha"
if st.session_state.modulo in ("Cadastro", "Consulta"):
    st.session_state.modulo = "Ficha"
if "modulo_pendente" in st.session_state:
    st.session_state.modulo = st.session_state.pop("modulo_pendente")
if aviso := st.session_state.pop("aviso", None):
    st.success(aviso)

modulo = st.radio(
    "Módulo",
    ["Ficha", "Resultados"],
    horizontal=True,
    key="modulo",
    label_visibility="collapsed",
)

if modulo == "Ficha":
    st.subheader("Ficha · inclusão, consulta e edição")
    st.caption(
        "Localize uma ficha pelo processo SEI ou preencha uma nova. "
        "A ficha encontrada abre neste mesmo módulo para edição."
    )
    with st.form("localizar_ficha"):
        busca = st.text_input(
            "Localizar pelo processo SEI",
            placeholder="0000.00.0000000/0000-00",
        )
        consultar = st.form_submit_button("Localizar ficha")
    if consultar:
        try:
            processo_consultado = normalizar_processo(busca)
            registro = repositorio.consultar(processo_consultado)
            tem_alteracoes = (
                st.session_state.ficha != st.session_state.ficha_original
            )
            if tem_alteracoes:
                st.session_state.consulta_pendente = {
                    "processo": processo_consultado,
                    "registro": registro,
                }
            elif registro:
                abrir(registro["ficha"], registro["versao"], registro["status"])
                st.session_state.aviso = (
                    f"Ficha {registro['status'].lower()} carregada. "
                    "Edite os campos necessários e use Atualizar ficha ou Salvar alterações."
                )
                st.rerun()
            else:
                ficha_nova = nova_ficha()
                ficha_nova["processo"] = processo_consultado
                abrir(ficha_nova)
                st.session_state.aviso = (
                    "Processo não localizado. Uma ficha nova foi aberta com o SEI informado."
                )
                st.rerun()
        except ValueError as erro:
            st.error(str(erro))
        except Exception:
            st.error("Falha na consulta. Confira a conexão e tente novamente.")

    consulta_pendente = st.session_state.get("consulta_pendente")
    if consulta_pendente:
        st.warning(
            "A ficha atual tem alterações ainda não gravadas. Confirme o descarte "
            "antes de abrir a ficha localizada."
        )
        abrir_pendente, manter_atual = st.columns(2)
        with abrir_pendente:
            if st.button(
                "Descartar alterações e abrir ficha localizada", type="primary"
            ):
                registro = consulta_pendente["registro"]
                if registro:
                    abrir(registro["ficha"], registro["versao"], registro["status"])
                    st.session_state.aviso = "Ficha localizada carregada para edição."
                else:
                    ficha_nova = nova_ficha()
                    ficha_nova["processo"] = consulta_pendente["processo"]
                    abrir(ficha_nova)
                    st.session_state.aviso = (
                        "Processo não localizado. Uma ficha nova foi aberta com o SEI informado."
                    )
                st.session_state.pop("consulta_pendente", None)
                st.rerun()
        with manter_atual:
            if st.button("Continuar na ficha atual"):
                st.session_state.pop("consulta_pendente", None)
                st.rerun()

    rascunhos = [
        registro
        for registro in repositorio.listar()
        if registro["status"] == "Rascunho"
    ]
    if rascunhos:
        with st.expander(f"Abrir rascunho gravado ({len(rascunhos)})"):
            indice = st.selectbox(
                "Rascunhos disponíveis",
                options=range(len(rascunhos)),
                format_func=lambda i: (
                    f"{rascunhos[i]['ficha']['processo']} · "
                    f"{rascunhos[i]['ficha']['unidade'] or 'Unidade não informada'}"
                ),
                key="rascunho_indice",
            )
            if st.button("Abrir rascunho", disabled=not pode_editar):
                registro = rascunhos[indice]
                if st.session_state.ficha != st.session_state.ficha_original:
                    st.session_state.consulta_pendente = {
                        "processo": registro["ficha"]["processo"],
                        "registro": registro,
                    }
                    st.rerun()
                else:
                    abrir(registro["ficha"], registro["versao"], registro["status"])
                    st.session_state.aviso = "Rascunho carregado para continuação."
                    st.rerun()
    else:
        st.caption("Não há rascunhos gravados.")

    st.divider()
    st.subheader("Dados da ficha")
    versao = st.session_state.versao
    status_atual = st.session_state.status_ficha
    tem_alteracoes = (
        st.session_state.ficha != st.session_state.ficha_original
    )
    if versao:
        st.info(
            f"Ficha {status_atual.lower()} · Versão {versao}. "
            "As alterações são gravadas somente quando você escolhe salvar."
        )
    else:
        st.caption("Preencha os dados e escolha Cadastrar ou Salvar rascunho.")
    if st.button("Nova ficha", disabled=not pode_editar):
        if tem_alteracoes:
            st.session_state.confirmar_nova_ficha = True
        else:
            abrir(nova_ficha())
            st.rerun()
    if st.session_state.get("confirmar_nova_ficha"):
        st.warning(
            "Há alterações não gravadas. Descartá-las não remove fichas que já estejam salvas."
        )
        confirmar_nova, manter_atual = st.columns(2)
        with confirmar_nova:
            if st.button("Descartar alterações e iniciar nova ficha", disabled=not pode_editar):
                abrir(nova_ficha())
                st.session_state.confirmar_nova_ficha = False
                st.rerun()
        with manter_atual:
            if st.button("Manter ficha atual"):
                st.session_state.confirmar_nova_ficha = False
                st.rerun()
    ficha = deepcopy(st.session_state.ficha)
    prefixo = str(st.session_state.geracao)
    st.markdown("#### Identificação")
    for campo, rotulo in (
        ("processo", "Processo SEI"),
        ("orgao", "Órgão gestor"),
        ("unidade", "Nome da U.C."),
        ("categoria", "Categoria da U.C."),
        ("responsavel", "Responsável GCMUC"),
        ("tecnico", "Responsável técnico"),
        ("urfbio", "URFBio"),
    ):
        ficha[campo] = texto_em_linha(
            rotulo,
            ficha[campo],
            f"{prefixo}_{campo}",
            valor_original=st.session_state.ficha_original.get(campo, ""),
            desabilitado=(
                not pode_editar
                or (campo == "processo" and st.session_state.versao > 0)
            ),
        )
    coluna_esfera, coluna_categoria = st.columns(2)
    with coluna_esfera:
        rotulo, controle = st.columns([0.45, 0.55], vertical_alignment="center")
        with rotulo:
            exibir_rotulo_formulario("Esfera administrativa")
        with controle:
            opcoes = ["", "Estadual", "Federal", "Municipal"]
            chave_esfera = f"{prefixo}_esfera"
            with st.container(
                key=chave_container_campo(
                    chave_esfera,
                    st.session_state.ficha_original.get("esfera", ""),
                )
            ):
                ficha["esfera"] = st.selectbox(
                    "Esfera administrativa",
                    opcoes,
                    index=opcoes.index(ficha["esfera"]),
                    key=chave_esfera,
                    disabled=not pode_editar,
                    label_visibility="collapsed",
                )
    with coluna_categoria:
        ficha["pontuacao_categoria"] = inteiro_em_linha(
            "Pontuação da categoria",
            ficha["pontuacao_categoria"],
            f"{prefixo}_pontuacao_categoria",
            1,
            999,
            valor_original=st.session_state.ficha_original.get(
                "pontuacao_categoria"
            ),
            desabilitado=not pode_editar,
        )
    ficha["analise"] = texto_em_linha(
        "Data de análise (mm/aaaa)",
        ficha["analise"],
        f"{prefixo}_analise",
        valor_original=st.session_state.ficha_original.get("analise", ""),
        placeholder="mm/aaaa",
    )
    rotulo_data, controle_data = st.columns(
        [0.24, 0.76], vertical_alignment="center"
    )
    with rotulo_data:
        exibir_rotulo_formulario("Data de recebimento")
    with controle_data:
        chave_recebimento = f"{prefixo}_recebimento"
        data_original = date.fromisoformat(
            st.session_state.ficha_original["recebimento"]
        )
        with st.container(
            key=chave_container_campo(chave_recebimento, data_original)
        ):
            ficha["recebimento"] = st.date_input(
                "Data de recebimento",
                value=date.fromisoformat(ficha["recebimento"]),
                format="MM/DD/YYYY",
                key=chave_recebimento,
                disabled=not pode_editar,
                label_visibility="collapsed",
            ).isoformat()
    st.markdown("#### Pontuações e justificativas")
    st.caption(
        "Nos totais, campos vazios são considerados 0. Para concluir a ficha, "
        "os campos obrigatórios ainda precisam ser preenchidos. "
        "Pontuações individuais: 0 a 9."
    )
    proporcao_colunas = [2.2, 1.0, 3.3, 1.0]
    (
        cabecalho_parametro,
        cabecalho_gestor,
        cabecalho_justificativa,
        cabecalho_validado,
    ) = st.columns(proporcao_colunas, vertical_alignment="bottom")
    with cabecalho_parametro:
        st.markdown("**Parâmetro**")
    with cabecalho_gestor:
        st.markdown("**Pontos Gestor**")
    with cabecalho_justificativa:
        st.markdown("**Justificativa/Observação**")
    with cabecalho_validado:
        st.markdown("**Pontos Validados**")

    for codigo, nome in PARAMETROS:
        pontos = ficha["parametros"][codigo]
        pontos_originais = st.session_state.ficha_original["parametros"].get(
            codigo, {}
        )
        (
            coluna_parametro,
            coluna_gestor,
            coluna_justificativa,
            coluna_validado,
        ) = st.columns(proporcao_colunas, vertical_alignment="top")
        with coluna_parametro:
            chave_rotulo = f"{prefixo}_{codigo}_rotulo"
            rotulo_padrao = f"{codigo} · {nome}"
            with st.container(
                key=chave_container_campo(
                    chave_rotulo,
                    pontos_originais.get("rotulo", rotulo_padrao),
                )
            ):
                pontos["rotulo"] = st.text_input(
                    f"{codigo} · Parâmetro",
                    value=pontos.get("rotulo", rotulo_padrao),
                    key=chave_rotulo,
                    disabled=not pode_editar,
                    label_visibility="collapsed",
                )
        with coluna_gestor:
            chave_gestor = f"{prefixo}_{codigo}_gestor"
            with st.container(
                key=chave_container_campo(
                    chave_gestor, pontos_originais.get("gestor")
                )
            ):
                pontos["gestor"] = st.number_input(
                    f"{codigo} · Pontos Gestor",
                    min_value=0,
                    max_value=9,
                    value=pontos["gestor"],
                    step=1,
                    key=chave_gestor,
                    disabled=not pode_editar,
                    label_visibility="collapsed",
                )
        with coluna_justificativa:
            chave_justificativa = f"{prefixo}_{codigo}_justificativa"
            with st.container(
                key=chave_container_campo(
                    chave_justificativa,
                    pontos_originais.get("justificativa", ""),
                )
            ):
                pontos["justificativa"] = st.text_area(
                    f"{codigo} · Justificativa/Observação",
                    value=pontos["justificativa"],
                    key=chave_justificativa,
                    height=96,
                    disabled=not pode_editar,
                    label_visibility="collapsed",
                )
        with coluna_validado:
            chave_validado = f"{prefixo}_{codigo}_validado"
            with st.container(
                key=chave_container_campo(
                    chave_validado, pontos_originais.get("validado")
                )
            ):
                pontos["validado"] = st.number_input(
                    f"{codigo} · Pontos Validados",
                    min_value=0,
                    max_value=9,
                    value=pontos["validado"],
                    step=1,
                    key=chave_validado,
                    disabled=not pode_editar,
                    label_visibility="collapsed",
                )
        st.markdown('<hr class="linha-parametro">', unsafe_allow_html=True)
    total_gestor = sum(
        pontos["gestor"] or 0
        for pontos in ficha["parametros"].values()
    )
    total_validado = sum(
        pontos["validado"] or 0
        for pontos in ficha["parametros"].values()
    )
    st.markdown("**TOTAL DOS PARÂMETROS**")
    coluna_total_gestor, coluna_total_validado = st.columns(2)
    with coluna_total_gestor:
        st.metric("Total — Pontos Gestor", total_gestor)
    with coluna_total_validado:
        st.metric("Total — Pontos Validados", total_validado)
    st.markdown("#### Parâmetros por municípios")
    st.caption(
        "Preencha os nomes no bloco 10. Os outros três blocos utilizam "
        "os mesmos municípios, na mesma ordem. Cada bloco tem seus próprios "
        "valores de 0 a 9. Os totais e o resumo são atualizados enquanto você preenche."
    )
    for codigo in MUNICIPAIS:
        rotulo = ROTULOS_MUNICIPAIS[codigo]
        with st.expander(
            f"Parâmetro ({rotulo}) por Municípios", expanded=True
        ):
            cabecalho_posicao, cabecalho_municipio, cabecalho_valor = (
                st.columns([1.1, 2.2, 1])
            )
            with cabecalho_posicao:
                st.caption("Posição")
            with cabecalho_municipio:
                st.caption("Município")
            with cabecalho_valor:
                st.caption("Valor")
            for posicao, municipio in enumerate(ficha["municipios"], 1):
                municipio_original = st.session_state.ficha_original[
                    "municipios"
                ][posicao - 1]
                coluna_posicao, coluna_nome, coluna_valor = st.columns(
                    [1.1, 2.2, 1]
                )
                with coluna_posicao:
                    st.markdown(f"**Município {posicao}**")
                with coluna_nome:
                    if codigo == "10":
                        chave_nome = f"{prefixo}_municipio_{posicao}"
                        with st.container(
                            key=chave_container_campo(
                                chave_nome, municipio_original["nome"]
                            )
                        ):
                            municipio["nome"] = st.text_input(
                                f"Nome do município {posicao}",
                                value=municipio["nome"],
                                placeholder="Digite o nome do município",
                                key=chave_nome,
                                disabled=not pode_editar,
                                label_visibility="collapsed",
                            )
                    else:
                        # A identificação vem do primeiro bloco e não se duplica.
                        st.text_input(
                            f"Nome do município {posicao}",
                            value=municipio["nome"],
                            key=(f"{prefixo}_nome_{codigo}_{posicao}_"
                                 f"{municipio['nome']}"),
                            disabled=True,
                            label_visibility="collapsed",
                        )
                with coluna_valor:
                    chave_valor = f"{prefixo}_municipio_{posicao}_{codigo}"
                    with st.container(
                        key=chave_container_campo(
                            chave_valor, municipio_original[codigo]
                        )
                    ):
                        municipio[codigo] = st.number_input(
                            f"Valor do parâmetro ({rotulo}) para o município {posicao}",
                            min_value=0,
                            max_value=9,
                            value=municipio[codigo],
                            step=1,
                            key=chave_valor,
                            disabled=not pode_editar,
                            label_visibility="collapsed",
                        )
            # Soma o bloco; entradas vazias continuam ausentes na ficha.
            total_bloco = sum(
                municipio[codigo] or 0 for municipio in ficha["municipios"]
            )
            _, _, total_valor = st.columns([1.1, 2.2, 1])
            with total_valor:
                st.markdown(f"**TOTAL: {total_bloco}**")
    # Cada edição é mantida na sessão; a base só é alterada por uma ação explícita.
    st.session_state.ficha = deepcopy(ficha)
    tem_alteracoes = ficha != st.session_state.ficha_original
    campos_alterados = diferencas_ficha(
        st.session_state.ficha_original, ficha
    )
    if tem_alteracoes:
        st.markdown(
            f'<div class="aviso-alteracoes">Há {len(campos_alterados)} '
            "campo(s) alterado(s), ainda sem gravação; os campos destacados "
            "em verde claro estão diferentes da versão salva.</div>",
            unsafe_allow_html=True,
        )
        with st.expander("Ver campos alterados"):
            for campo_alterado in campos_alterados:
                st.markdown(f"- {campo_alterado}")
    botoes = st.columns(4)
    revisar = botoes[0].button("Revisar preenchimento")
    rascunho = False
    concluir = False
    atualizar = False
    if versao == 0:
        rascunho = botoes[1].button(
            "Salvar rascunho", disabled=not pode_editar
        )
        concluir = botoes[2].button("Cadastrar", disabled=not pode_editar)
    elif status_atual == "Concluída":
        atualizar = botoes[1].button(
            "Atualizar ficha",
            disabled=not pode_editar or not tem_alteracoes,
        )
        concluir = atualizar
    else:
        rascunho = botoes[1].button(
            "Salvar alterações",
            disabled=not pode_editar or not tem_alteracoes,
        )
        concluir = botoes[2].button(
            "Concluir ficha", disabled=not pode_editar
        )
    st.markdown("#### Resumo final da ficha")
    try:
        st.markdown(
            renderizar_tabela(quadro_final_ficha(ficha)),
            unsafe_allow_html=True,
        )
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        st.info("O resumo será calculado após informar a pontuação da categoria.")
    if revisar:
        # A revisão mostra validações sem gravar o registro na base.
        st.session_state.exibir_revisao = True
        st.rerun()
    if revisar or concluir or st.session_state.pop("exibir_revisao", False):
        st.markdown("#### Revisão do preenchimento")
        try:
            calculo = calcular(ficha)
            st.metric("Total validado", calculo["total_validado"])
            st.markdown(
                renderizar_tabela(
                    pd.DataFrame(calculo["municipios"])[
                        ["Município", "Soma", "FQ"]
                    ]
                ),
                unsafe_allow_html=True,
            )
        except ValueError as erro:
            pendencias = [linha for linha in str(erro).splitlines() if linha]
            st.error("Há campos obrigatórios pendentes ou dados inválidos:")
            for pendencia in pendencias:
                st.markdown(f"- {pendencia}")
        except Exception:
            st.error(
                "Não foi possível gerar a revisão. Confira os dados e tente novamente."
            )
    if rascunho or concluir:
        try:
            status_destino = "Concluída" if concluir else "Rascunho"
            registro_atual = (
                repositorio.consultar(ficha["processo"])
                if versao > 0
                else None
            )
            if (
                registro_atual
                and registro_atual["ficha"] == ficha
                and registro_atual["status"] == status_destino
            ):
                st.info(
                    "Nenhuma alteração detectada. A ficha não foi gravada novamente."
                )
                salvo = registro_atual
            else:
                salvo = repositorio.gravar(
                    ficha,
                    st.session_state.versao,
                    status_destino,
                    autor,
                )
                st.success(
                    f"{salvo['status']} salva e verificada. Versão {salvo['versao']}."
                )
            st.session_state.ficha = deepcopy(salvo["ficha"])
            st.session_state.ficha_original = deepcopy(salvo["ficha"])
            st.session_state.versao = salvo["versao"]
            st.session_state.status_ficha = salvo["status"]
            tem_alteracoes = False
        except (Conflito, ValueError) as erro:
            st.error(str(erro))
        except Exception:
            st.error(
                "A gravação não pôde ser confirmada. Consulte o processo antes de reenviar."
            )
    if versao > 0:
        if st.button(
            "Excluir ficha",
            disabled=not pode_editar or tem_alteracoes,
        ):
            st.session_state.confirmar_exclusao = True
        if tem_alteracoes:
            st.caption("Grave ou descarte as alterações antes de excluir a ficha salva.")
        if st.session_state.get("confirmar_exclusao"):
            st.warning(
                f"Confirme a exclusão da ficha do processo {ficha['processo']}. "
                "A operação remove a ficha da consulta e registra o evento no histórico."
            )
            confirmar, cancelar = st.columns(2)
            with confirmar:
                if st.button(
                    "Confirmar exclusão",
                    type="primary",
                    disabled=not pode_editar or tem_alteracoes,
                ):
                    try:
                        repositorio.excluir(
                            ficha["processo"],
                            st.session_state.versao,
                            autor,
                        )
                        st.session_state.confirmar_exclusao = False
                        abrir(nova_ficha())
                        st.session_state.modulo_pendente = "Ficha"
                        st.session_state.aviso = (
                            "Ficha excluída. O evento foi registrado no histórico."
                        )
                        st.rerun()
                    except (Conflito, ValueError) as erro:
                        st.error(str(erro))
                    except Exception:
                        st.error(
                            "A exclusão não foi confirmada. Consulte novamente antes de repetir."
                        )
            with cancelar:
                if st.button("Cancelar exclusão"):
                    st.session_state.confirmar_exclusao = False
                    st.rerun()
else:
    st.subheader("Resultados consolidados")
    st.caption(
        "Somente fichas concluídas. Notas exibidas com duas casas decimais."
    )
    st.caption(
        "No relatório, o total do bloco 10 alimenta o fator 10; o total do bloco 11 "
        "alimenta os fatores 11.1, 11.2 e 11.3, conforme definido para E44 e E60."
    )
    filtro = st.text_input("Filtrar por processo ou unidade")
    try:
        registros = repositorio.listar()
        concluidas = [
            registro
            for registro in registros
            if registro["status"] == "Concluída"
        ]
        processo_mais_recente = None
        if concluidas:
            datas_gravacao = [
                pd.to_datetime(
                    registro.get("atualizado_em"), utc=True, errors="coerce"
                )
                for registro in concluidas
            ]
            datas_validas = [
                (indice, data_gravacao)
                for indice, data_gravacao in enumerate(datas_gravacao)
                if not pd.isna(data_gravacao)
            ]
            indice_mais_recente = (
                max(datas_validas, key=lambda item: item[1])[0]
                if datas_validas
                else None
            )
            if indice_mais_recente is not None:
                processo_mais_recente = concluidas[indice_mais_recente]["ficha"][
                    "processo"
                ]
        quadro = resultado_consolidado(concluidas)
        if quadro.empty:
            st.info(
                "Não há fichas concluídas para exibir. Os rascunhos ficam no módulo Ficha."
            )
        else:
            if filtro:
                selecao = quadro["Nº SEI"].str.contains(
                    filtro, regex=False, case=False
                )
                selecao |= quadro["REMETENTE - UCs"].str.contains(
                    filtro, regex=False, case=False
                )
                quadro = quadro[selecao]
            quadro_tela = quadro.copy()
            if processo_mais_recente:
                quadro_tela.insert(
                    1,
                    "Indicador",
                    quadro_tela["Nº SEI"].map(
                        lambda processo: (
                            "Último cadastro"
                            if processo == processo_mais_recente
                            else ""
                        )
                    ),
                )
            destaques_por_processo = {
                registro["ficha"]["processo"]: colunas_resultado_alteradas(
                    registro.get("alteracoes_ultima_versao", {})
                )
                for registro in concluidas
            }
            tabela_quadro = renderizar_tabela(
                quadro_tela, destaques_por_processo
            )
            with st.container(key="resultados_grade"):
                st.markdown(tabela_quadro, unsafe_allow_html=True)
            st.caption(
                "'Último cadastro' marca a ficha concluída gravada mais recentemente; "
                "rascunhos não participam deste indicador. Use a barra da grade para "
                "percorrer as colunas e o controle de tela cheia para ampliar a consulta."
            )
            if any(destaques_por_processo.values()):
                st.caption(
                    "Células em verde claro indicam dados alterados na última "
                    "atualização salva da ficha."
                )
            st.download_button(
                "Baixar CSV",
                proteger_csv(quadro),
                "resultado_fq.csv",
                "text/csv",
            )
    except Exception:
        st.error(
            "Não foi possível montar o resultado. Confira as fichas e a conexão."
        )

st.markdown(
    """
    <footer class="rodape-institucional">
      <div class="rodape-principal">
        <div class="rodape-marca">
          <strong>IEF</strong>
          <span>Instituto Estadual de Florestas<br>Governo de Minas Gerais</span>
        </div>
        <div class="rodape-links">
          <a href="https://semad.mg.gov.br/politica-de-privacidade-do-sisema"
             target="_blank" rel="noopener noreferrer">
            Aspectos legais e responsabilidades · Política de Privacidade do Sisema
          </a>
        </div>
      </div>
      <div class="rodape-inferior">
        <span>Rodovia João Paulo II, 4143, Bairro Serra Verde · CEP 31630-900</span>
        <span>ICMS Ecológico · Aplicação de apoio</span>
      </div>
    </footer>
    <div id="fim"></div>
    """,
    unsafe_allow_html=True,
)
