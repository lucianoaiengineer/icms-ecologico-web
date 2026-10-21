"""Interface web de cadastro, consulta e resultados do ICMS Ecológico."""

import os
from copy import deepcopy
from datetime import date

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
    [data-testid="stMainBlockContainer"] {
        max-width: 980px;
        padding-left: 1.25rem;
        padding-right: 1.25rem;
    }
    /* Mantém rótulos e controles na mesma linha em qualquer largura. */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center;
    }
    [data-testid="column"] {
        min-width: 0 !important;
    }
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
        [data-testid="stHorizontalBlock"] {
            gap: 0.5rem;
        }
        [data-testid="stTextInput"],
        [data-testid="stNumberInput"],
        [data-testid="stSelectbox"],
        [data-testid="stDateInput"],
        [data-testid="stTextArea"] {
            min-width: 0 !important;
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
    """Compartilha uma conexão e sua trava entre as sessões do servidor."""
    if modo == "demonstracao":
        return Repositorio()
    return RepositorioSheets(
        dict(st.secrets["gcp_service_account"]), str(st.secrets["planilha_id"])
    )


def identificar(modo: str) -> tuple[str, bool]:
    """Exige identidade e autorização antes de ler dados persistentes."""
    if modo == "demonstracao":
        return "demonstracao", True
    if not segredo("auth"):
        st.error(
            "Configure a autenticação antes de ativar o modo Google Sheets."
        )
        st.stop()
    if not st.user.is_logged_in:
        st.info("Entre com uma conta autorizada para acessar as fichas.")
        st.button("Entrar", on_click=st.login)
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


def abrir(
    ficha: dict, versao: int = 0, status: str = ""
) -> None:
    """Abre uma ficha em um novo conjunto de campos da sessão."""
    st.session_state.ficha = deepcopy(ficha)
    st.session_state.ficha_original = deepcopy(ficha)
    st.session_state.versao = versao
    st.session_state.status_ficha = status
    st.session_state.confirmar_exclusao = False
    st.session_state.confirmar_nova_ficha = False
    st.session_state.geracao = st.session_state.get("geracao", 0) + 1


def texto_em_linha(
    rotulo: str,
    valor: str,
    chave: str,
    *,
    desabilitado: bool = False,
    placeholder: str = "",
) -> str:
    """Desenha o rótulo à esquerda e o campo de texto à direita."""
    coluna_rotulo, coluna_valor = st.columns(
        [0.42, 0.58], vertical_alignment="center"
    )
    with coluna_rotulo:
        st.markdown(f"**{rotulo}**")
    with coluna_valor:
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
    desabilitado: bool = False,
) -> int | None:
    """Desenha o rótulo à esquerda e o campo numérico à direita."""
    coluna_rotulo, coluna_valor = st.columns(
        [0.42, 0.58], vertical_alignment="center"
    )
    with coluna_rotulo:
        st.markdown(f"**{rotulo}**")
    with coluna_valor:
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


st.title("ICMS Ecológico")
st.caption("Gestão de fichas do Fator de Qualidade")
modo = str(segredo("modo", os.environ.get("ICMS_MODO", "demonstracao")))
if modo not in ("demonstracao", "sheets"):
    st.error("Modo de execução inválido.")
    st.stop()
autor, pode_editar = identificar(modo)
if modo == "demonstracao":
    st.warning(
        "Demonstração: use somente dados sintéticos. Os registros são temporários, "
        "compartilhados entre visitantes deste servidor e podem desaparecer ao reiniciar."
    )
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
            desabilitado=(
                not pode_editar
                or (campo == "processo" and st.session_state.versao > 0)
            ),
        )
    coluna_esfera, coluna_categoria = st.columns(2)
    with coluna_esfera:
        rotulo, controle = st.columns([0.42, 0.58], vertical_alignment="center")
        with rotulo:
            st.markdown("**Esfera administrativa**")
        with controle:
            opcoes = ["", "Estadual", "Federal", "Municipal"]
            ficha["esfera"] = st.selectbox(
                "Esfera administrativa",
                opcoes,
                index=opcoes.index(ficha["esfera"]),
                key=f"{prefixo}_esfera",
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
            desabilitado=not pode_editar,
        )
    ficha["analise"] = texto_em_linha(
        "Data de análise (mm/aaaa)",
        ficha["analise"],
        f"{prefixo}_analise",
        placeholder="mm/aaaa",
    )
    rotulo_data, controle_data = st.columns(
        [0.42, 0.58], vertical_alignment="center"
    )
    with rotulo_data:
        st.markdown("**Data de recebimento**")
    with controle_data:
        ficha["recebimento"] = st.date_input(
            "Data de recebimento",
            value=date.fromisoformat(ficha["recebimento"]),
            format="MM/DD/YYYY",
            disabled=not pode_editar,
            label_visibility="collapsed",
        ).isoformat()
    st.markdown("#### Pontuações e justificativas")
    st.caption(
        "Campos vazios não equivalem a zero. Pontuações individuais: 0 a 9."
    )
    for codigo, nome in PARAMETROS:
        with st.expander(f"{codigo} · {nome}"):
            pontos = ficha["parametros"][codigo]
            gestor, validado = st.columns(2)
            with gestor:
                pontos["gestor"] = inteiro_em_linha(
                    "Pontos Gestor",
                    pontos["gestor"],
                    f"{prefixo}_{codigo}_gestor",
                    0,
                    9,
                    desabilitado=not pode_editar,
                )
            with validado:
                pontos["validado"] = inteiro_em_linha(
                    "Pontos Validados",
                    pontos["validado"],
                    f"{prefixo}_{codigo}_validado",
                    0,
                    9,
                    desabilitado=not pode_editar,
                )
            rotulo_justificativa, campo_justificativa = st.columns(
                [0.2, 0.8], vertical_alignment="top"
            )
            with rotulo_justificativa:
                st.markdown("**Justificativa**")
            with campo_justificativa:
                pontos["justificativa"] = st.text_area(
                    "Justificativa",
                    value=pontos["justificativa"],
                    key=f"{prefixo}_{codigo}_justificativa",
                    disabled=not pode_editar,
                    label_visibility="collapsed",
                )
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
                coluna_posicao, coluna_nome, coluna_valor = st.columns(
                    [1.1, 2.2, 1]
                )
                with coluna_posicao:
                    st.markdown(f"**Município {posicao}**")
                with coluna_nome:
                    if codigo == "10":
                        municipio["nome"] = st.text_input(
                            f"Nome do município {posicao}",
                            value=municipio["nome"],
                            placeholder="Digite o nome do município",
                            key=f"{prefixo}_municipio_{posicao}",
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
                    municipio[codigo] = st.number_input(
                        f"Valor do parâmetro ({rotulo}) para o município {posicao}",
                        min_value=0,
                        max_value=9,
                        value=municipio[codigo],
                        step=1,
                        key=f"{prefixo}_municipio_{posicao}_{codigo}",
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
        st.info(
            f"Há {len(campos_alterados)} campo(s) alterado(s), ainda sem gravação."
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
        st.dataframe(
            quadro_final_ficha(ficha),
            hide_index=True,
            width="stretch",
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
            st.dataframe(
                pd.DataFrame(calculo["municipios"])[
                    ["Município", "Soma", "FQ"]
                ],
                hide_index=True,
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
            configuracao = {
                "DATA RECEBIDA": st.column_config.DateColumn(
                    format="MM/DD/YYYY"
                )
            }
            configuracao.update(
                {
                    f"Nota{i}": st.column_config.NumberColumn(
                        format="%.2f"
                    )
                    for i in range(1, 14)
                }
            )
            st.dataframe(
                quadro_tela, hide_index=True, column_config=configuracao
            )
            st.caption(
                "'Último cadastro' marca a ficha concluída gravada mais recentemente; "
                "rascunhos não participam deste indicador."
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
