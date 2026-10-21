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


def abrir(ficha: dict, versao: int = 0) -> None:
    """Abre uma ficha em um novo conjunto de campos da sessão."""
    st.session_state.ficha = deepcopy(ficha)
    st.session_state.versao = versao
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
    rotulo: str, valor: int | None, chave: str, minimo: int, maximo: int
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
if aviso := st.session_state.pop("aviso", None):
    st.success(aviso)

consulta, cadastro, resultados = st.tabs(
    ["Consulta/Edição", "Cadastro", "Resultados"]
)
with consulta:
    st.subheader("Localizar ficha")
    st.caption(
        "A consulta localiza rascunhos e fichas concluídas pelo número do processo. "
        "Consultar não altera o formulário; a substituição só ocorre se você escolher abrir a ficha."
    )
    with st.form("consulta"):
        busca = st.text_input(
            "Número do processo SEI", placeholder="0000.00.0000000/0000-00"
        )
        consultar = st.form_submit_button("Consultar processo")
    if consultar:
        try:
            processo_consultado = normalizar_processo(busca)
            st.session_state.processo_consultado = processo_consultado
            st.session_state.registro_consultado = repositorio.consultar(
                processo_consultado
            )
        except ValueError as erro:
            st.error(str(erro))
        except Exception:
            st.error(
                "Falha na consulta. Confira a conexão e tente novamente."
            )
    registro_consultado = st.session_state.get("registro_consultado")
    if registro_consultado:
        ficha_consultada = registro_consultado["ficha"]
        st.success(
            f"Ficha encontrada · Situação: {registro_consultado['status']} · "
            f"Versão {registro_consultado['versao']}"
        )
        st.write(
            f"**Unidade:** {ficha_consultada['unidade'] or 'não informada'}  \n"
            f"**Atualizada em:** {registro_consultado['atualizado_em']}"
        )
        st.caption(
            "A ficha será carregada no Cadastro para consulta ou edição. "
            "Dados ainda não salvos que estejam no Cadastro serão substituídos."
        )
        coluna_abrir, coluna_excluir = st.columns(2)
        with coluna_abrir:
            if st.button(
                "Abrir ficha no Cadastro",
                disabled=not pode_editar,
            ):
                abrir(ficha_consultada, registro_consultado["versao"])
                st.session_state.aviso = (
                    "Ficha aberta para consulta ou edição no Cadastro."
                )
                st.rerun()
        with coluna_excluir:
            confirmar_exclusao = st.checkbox(
                "Confirmo a exclusão desta ficha.",
                key=f"confirmar_exclusao_{st.session_state.processo_consultado}",
                disabled=not pode_editar,
            )
            if st.button(
                "Excluir ficha",
                disabled=not confirmar_exclusao or not pode_editar,
            ):
                try:
                    repositorio.excluir(
                        st.session_state.processo_consultado,
                        registro_consultado["versao"],
                        autor,
                    )
                    st.session_state.registro_consultado = None
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
    elif "registro_consultado" in st.session_state and st.session_state.get(
        "processo_consultado"
    ):
        st.info(
            "Processo não cadastrado. Use Cadastro para incluir uma nova ficha."
        )

with cadastro:
    st.subheader("Ficha de análise")
    st.caption(
        f"Versão carregada: {st.session_state.versao}. Rascunhos não alimentam o resultado."
    )
    if st.button("Iniciar nova ficha", disabled=not pode_editar):
        st.session_state.confirmar_nova_ficha = True
    if st.session_state.get("confirmar_nova_ficha"):
        st.warning(
            "Iniciar uma ficha nova limpa da tela os dados ainda não salvos. "
            "Fichas já salvas permanecem na base."
        )
        confirmar_nova, manter_atual = st.columns(2)
        with confirmar_nova:
            if st.button("Descartar e iniciar nova ficha", disabled=not pode_editar):
                abrir(nova_ficha())
                st.session_state.confirmar_nova_ficha = False
                st.rerun()
        with manter_atual:
            if st.button("Continuar com a ficha atual"):
                st.session_state.confirmar_nova_ficha = False
                st.rerun()
    ficha = deepcopy(st.session_state.ficha)
    prefixo = str(st.session_state.geracao)
    with st.form("ficha_" + prefixo):
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
                    campo == "processo" and st.session_state.versao > 0
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
                    label_visibility="collapsed",
                )
        with coluna_categoria:
            ficha["pontuacao_categoria"] = inteiro_em_linha(
                "Pontuação da categoria",
                ficha["pontuacao_categoria"],
                f"{prefixo}_pontuacao_categoria",
                1,
                999,
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
                    )
                with validado:
                    pontos["validado"] = inteiro_em_linha(
                        "Pontos Validados",
                        pontos["validado"],
                        f"{prefixo}_{codigo}_validado",
                        0,
                        9,
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
                        label_visibility="collapsed",
                    )
        st.markdown("#### Parâmetros por municípios")
        st.caption(
            "Preencha os nomes no bloco 10. Os outros três blocos utilizam "
            "os mesmos municípios, na mesma ordem. Cada bloco tem seus próprios "
            "valores de 0 a 9. Use Revisar preenchimento para atualizar os "
            "nomes exibidos e os totais após editar."
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
                            label_visibility="collapsed",
                        )
                # Soma o bloco; entradas vazias continuam ausentes na ficha.
                total_bloco = sum(
                    municipio[codigo] or 0 for municipio in ficha["municipios"]
                )
                st.caption(f"TOTAL — Parâmetro ({rotulo}): {total_bloco}")
        revisar = st.form_submit_button(
            "Revisar preenchimento", disabled=not pode_editar
        )
        rascunho = st.form_submit_button(
            "Salvar rascunho", disabled=not pode_editar
        )
        confirmado = st.checkbox(
            "Revisei os dados e confirmo a conclusão ou atualização da ficha."
        )
        concluir = st.form_submit_button("Salvar", disabled=not pode_editar)
    st.markdown("#### Resumo final da ficha")
    st.caption(
        "Quadro correspondente à parte inferior do modelo: soma dos pontos "
        "validados e dos parâmetros municipais, dividida pela pontuação da categoria."
    )
    try:
        st.dataframe(
            quadro_final_ficha(ficha),
            hide_index=True,
            width="stretch",
        )
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        st.info("O resumo será calculado após informar a pontuação da categoria.")
    if revisar or rascunho or concluir:
        st.session_state.ficha = deepcopy(ficha)
    if revisar:
        # A submissão do formulário atualiza a ficha; uma nova renderização
        # propaga os nomes do parâmetro 10 para os outros blocos municipais.
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
        if concluir and not confirmado:
            st.error(
                "Revise os dados e marque a confirmação antes de concluir."
            )
        else:
            try:
                salvo = repositorio.gravar(
                    ficha,
                    st.session_state.versao,
                    "Concluída" if concluir else "Rascunho",
                    autor,
                )
                st.session_state.versao = salvo["versao"]
                st.success(
                    f"{salvo['status']} salva e verificada. Versão {salvo['versao']}."
                )
            except (Conflito, ValueError) as erro:
                st.error(str(erro))
            except Exception:
                st.error(
                    "A gravação não pôde ser confirmada. Consulte o processo antes de reenviar."
                )

with resultados:
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
        if registros:
            st.markdown("#### Fichas salvas")
            fichas_salvas = pd.DataFrame(
                [
                    {
                        "Nº SEI": registro["ficha"]["processo"],
                        "Unidade": registro["ficha"]["unidade"],
                        "Situação": registro["status"],
                        "Última atualização": registro["atualizado_em"],
                    }
                    for registro in registros
                ]
            )
            if filtro:
                selecao_salvas = fichas_salvas["Nº SEI"].str.contains(
                    filtro, regex=False, case=False
                )
                selecao_salvas |= fichas_salvas["Unidade"].str.contains(
                    filtro, regex=False, case=False
                )
                fichas_salvas = fichas_salvas[selecao_salvas]
            st.dataframe(fichas_salvas, hide_index=True)
            st.caption(
                "Rascunhos ficam salvos para consulta e edição, mas não entram "
                "no resultado consolidado."
            )
        quadro = resultado_consolidado(registros)
        if quadro.empty:
            st.info("Nenhuma ficha concluída encontrada.")
        else:
            if filtro:
                selecao = quadro["Nº SEI"].str.contains(
                    filtro, regex=False, case=False
                )
                selecao |= quadro["REMETENTE - UCs"].str.contains(
                    filtro, regex=False, case=False
                )
                quadro = quadro[selecao]
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
                quadro, hide_index=True, column_config=configuracao
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
