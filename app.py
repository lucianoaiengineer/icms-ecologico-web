"""Interface web de cadastro, consulta e resultados do ICMS Ecológico."""

from __future__ import annotations

import html
import logging
import os
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
import streamlit as st

from icms.edicoes import chave_edicao
from icms.regras import (
    CASAS_DECIMAIS_FQ,
    MUNICIPAIS,
    PARAMETROS,
    NOMES_MUNICIPAIS,
    nova_linha_municipal,
    normalizar_nome_municipio,
    normalizar_municipios,
    calcular,
    normalizar_processo,
    nova_ficha,
)
from icms.repositorio import Conflito, Repositorio
from icms.relatorios import (
    colunas_resultado_alteradas,
    proteger_csv,
    quadro_final_ficha,
    resumo_fichas,
    renderizar_tabela,
    resultado_consolidado,
)

if TYPE_CHECKING:
    from icms.repositorio_sql import RepositorioSQL

registrador_log = logging.getLogger(__name__)

# Mantém as interfaces externas, regras do domínio e armazenamento separados.
st.set_page_config(page_title="Gestão de Fichas | ICMS Ecológico", layout="centered")

# Estilos separados do ponto de entrada. O arquivo faz parte da distribuição.
ESTILOS = Path(__file__).resolve().parent / "assets" / "estilos.css"
st.markdown(
    f"<style>{ESTILOS.read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)


def segredo(chave: str, padrao: Any = None) -> Any:
    """Lê configuração sem exigir arquivo de segredos na demonstração."""
    try:
        return st.secrets.get(chave, padrao)
    except FileNotFoundError:
        return padrao


def conectar(modo: str) -> Repositorio:
    """Isola a demonstração na sessão e compartilha conexões persistentes.

    Não usar cache global aqui: ele faria navegadores diferentes receberem
    o mesmo repositório temporário, afetando consultas e exclusões.
    """
    if modo == "demonstracao":
        if "repositorio_demonstracao" not in st.session_state:
            st.session_state.repositorio_demonstracao = Repositorio()
        return st.session_state.repositorio_demonstracao
    if modo == "banco":
        url = str(segredo("banco_url", os.environ.get("ICMS_BANCO_URL", ""))).strip()
        if not url:
            raise ValueError("Configure banco_url nos Secrets para o modo banco.")
        return conectar_banco(url)
    raise ValueError("Modo de armazenamento não reconhecido.")


@st.cache_resource
def conectar_banco(url: str) -> RepositorioSQL:
    """Abre o adaptador SQL somente no modo banco explicitamente configurado."""
    from icms.repositorio_sql import RepositorioSQL

    return RepositorioSQL(url)


def exibir_backup_demonstracao(repositorio: Repositorio) -> None:
    """Permite baixar e restaurar fichas enquanto a aplicação está em demonstração."""
    with st.expander("Backup temporário das fichas (CSV)"):
        st.caption(
            "Baixe o backup ao terminar. Em outro dia, envie esse arquivo para "
            "restaurar fichas e rascunhos nesta sessão de demonstração."
        )
        exportador_csv = getattr(repositorio, "exportar_backup_csv", None)
        restaurador_csv = getattr(repositorio, "restaurar_backup_csv", None)
        if not callable(exportador_csv) or not callable(restaurador_csv):
            st.warning(
                "O backup CSV não está disponível nesta versão. Atualize juntos "
                "app.py e icms/repositorio.py no GitHub."
            )
            return
        st.download_button(
            "Baixar backup completo das fichas",
            data=exportador_csv(),
            file_name="backup_fichas_icms.csv",
            mime="text/csv",
            help=(
                "Inclui conteúdo integral, situação, versão "
                "e histórico de cada ficha."
            ),
        )
        arquivo_backup = st.file_uploader(
            "Restaurar fichas de um backup CSV",
            type=["csv"],
            key="arquivo_backup_fichas",
            max_upload_size=50,
        )
        if arquivo_backup and st.button(
            "Restaurar fichas do CSV", key="restaurar_backup_fichas"
        ):
            try:
                quantidade_restaurada = restaurador_csv(arquivo_backup.getvalue())
                st.success(
                    f"Backup lido. {quantidade_restaurada} ficha(s) restaurada(s). "
                    "Consulte pelo número SEI para continuar."
                )
            except ValueError as erro:
                st.error(str(erro))


def identificar(modo: str) -> tuple[str, bool]:
    """Exige identidade e autorização antes de ler dados persistentes."""
    if modo == "demonstracao":
        return "demonstracao", True
    configuracao_autenticacao = segredo("auth")
    campos_autenticacao = (
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    )
    try:
        autenticacao_configurada = bool(
            configuracao_autenticacao
            and all(
                str(configuracao_autenticacao.get(campo, "")).strip()
                for campo in campos_autenticacao
            )
        )
    except AttributeError:
        autenticacao_configurada = False
    if not autenticacao_configurada:
        exibir_tela_acesso(autenticacao_configurada=False)
        st.stop()
    if not st.user.is_logged_in:
        exibir_tela_acesso(autenticacao_configurada=True)
        st.stop()
    endereco_email = str(st.user.get("email", "")).lower()
    editores = [str(editor).lower() for editor in segredo("editores", [])]
    leitores = [str(leitor).lower() for leitor in segredo("leitores", [])]
    if (
        not st.user.get("email_verified", False)
        or endereco_email not in editores + leitores
    ):
        st.error("Conta sem autorização para acessar esta aplicação.")
        st.button("Sair", on_click=st.logout)
        st.stop()
    st.sidebar.caption(endereco_email)
    st.sidebar.button("Sair", on_click=st.logout)
    return endereco_email, endereco_email in editores


def exibir_tela_acesso(
    *, autenticacao_configurada: bool, permitir_demo: bool = False
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
        if autenticacao_configurada:
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
              <p>As credenciais e a confirmação de e-mail são administradas
              pelo provedor institucional.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        endereco_recuperacao = str(segredo("url_recuperacao", "")).strip()
        endereco_suporte = str(segredo("url_suporte", "")).strip()
        if endereco_recuperacao.startswith("https://"):
            st.link_button("Esqueceu a senha? Recuperar acesso", endereco_recuperacao)
        if endereco_suporte.startswith("https://"):
            st.link_button("Solicitar acesso ou suporte", endereco_suporte)
        elif not endereco_recuperacao.startswith("https://"):
            st.caption(
                "Para recuperar a conta ou solicitar acesso, "
                "procure o suporte institucional."
            )
        if not autenticacao_configurada:
            st.caption(
                "O acesso institucional será liberado após configurar a "
                "autenticação. A demonstração aceita somente dados fictícios "
                "e não grava na base oficial."
            )


def abrir(
    ficha: dict[str, Any], versao: int = 0, situacao: str = ""
) -> None:
    """Abre uma ficha em um novo conjunto de campos da sessão."""
    ficha_aberta = normalizar_municipios(ficha)
    if not ficha_aberta["municipios"]:
        ficha_aberta["municipios"] = [nova_linha_municipal()]
    for codigo, nome in PARAMETROS:
        ficha_aberta["parametros"].setdefault(codigo, {}).setdefault(
            "rotulo", f"{codigo} · {nome}"
        )
    st.session_state.ficha = deepcopy(ficha_aberta)
    st.session_state.ficha_original = deepcopy(ficha_aberta)
    st.session_state.versao = versao
    st.session_state.status_ficha = situacao
    st.session_state.confirmar_exclusao = False
    st.session_state.geracao = st.session_state.get("geracao", 0) + 1
    st.session_state.pop("ultimo_autosalvamento", None)
    st.session_state.pop("autosalvo_chave", None)


def validar_troca_modulo() -> None:
    """Exige confirmação antes de sair do formulário modificado."""
    if (
        st.session_state.get("modulo") == "Resultados"
        and st.session_state.get("ficha") != st.session_state.get("ficha_original")
    ):
        st.session_state.modulo = "Ficha"
        st.session_state.confirmar_saida_modulo = True


def aviso_saida_navegador(alterado: bool, geracao: int) -> None:
    """Solicita confirmação nativa do navegador quando há edição pendente.

    O aviso é melhor esforço: navegadores móveis e encerramentos forçados podem
    ignorá-lo. O autosave em banco permanece a proteção principal.
    """
    st.html(
        f"""<script>
        (() => {{
          const ativo = {str(alterado).lower()};
          const campo = 'st-key-{geracao}_';
          window.__icmsAvisoEdicao = ativo;
          if (window.__icmsAvisoAntes) {{
            window.removeEventListener('beforeunload', window.__icmsAvisoAntes);
          }}
          if (window.__icmsDetectaDigitacao) {{
            document.removeEventListener('input', window.__icmsDetectaDigitacao, true);
          }}
          window.__icmsDetectaDigitacao = (evento) => {{
            if (evento.target.closest('[class*="' + campo + '"]')) {{
              window.__icmsAvisoEdicao = true;
            }}
          }};
          document.addEventListener('input', window.__icmsDetectaDigitacao, true);
          window.__icmsAvisoAntes = (evento) => {{
            if (window.__icmsAvisoEdicao) {{
              evento.preventDefault();
              evento.returnValue = '';
            }}
          }};
          window.addEventListener('beforeunload', window.__icmsAvisoAntes);
        }})();
        </script>""",
        unsafe_allow_javascript=True,
    )


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
    coluna_rotulo, coluna_valor = st.columns([0.24, 0.76], vertical_alignment="center")
    with coluna_rotulo:
        exibir_rotulo_formulario(rotulo)
    with (
        coluna_valor,
        st.container(key=chave_container_campo(chave, valor_original or "")),
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
    coluna_rotulo, coluna_valor = st.columns([0.24, 0.76], vertical_alignment="center")
    with coluna_rotulo:
        exibir_rotulo_formulario(rotulo)
    with coluna_valor, st.container(key=chave_container_campo(chave, valor_original)):
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


def diferencas_ficha(
    ficha_original: dict[str, Any], ficha_atual: dict[str, Any]
) -> list[str]:
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
        if ficha_original.get(campo) != ficha_atual.get(campo)
    ]
    for codigo, dados in ficha_atual["parametros"].items():
        antigo = ficha_original["parametros"].get(codigo, {})
        for campo, rotulo in (
            ("gestor", "Pontos Gestor"),
            ("justificativa", "Justificativa"),
            ("validado", "Pontos Validados"),
            ("rotulo", "Parâmetro"),
        ):
            if antigo.get(campo) != dados.get(campo):
                alterados.append(f"Parâmetro {codigo} · {rotulo}")
    anteriores = ficha_original.get("municipios", [])
    atuais = ficha_atual.get("municipios", [])
    for indice in range(max(len(anteriores), len(atuais))):
        posicao = indice + 1
        antigo = anteriores[indice] if indice < len(anteriores) else {}
        municipio = atuais[indice] if indice < len(atuais) else {}
        if antigo.get("nome") != municipio.get("nome"):
            alterados.append(f"Município {posicao} · Nome")
        for codigo in MUNICIPAIS:
            antigo_pontos = antigo.get(codigo) or {}
            novos_pontos = municipio.get(codigo) or {}
            if not isinstance(antigo_pontos, dict):
                antigo_pontos = {"validado": antigo_pontos}
            if not isinstance(novos_pontos, dict):
                novos_pontos = {"validado": novos_pontos}
            for campo, rotulo in (
                ("gestor", "Pontos Gestor"),
                ("justificativa", "Justificativa"),
                ("validado", "Pontos Validados"),
            ):
                if antigo_pontos.get(campo) != novos_pontos.get(campo):
                    alterados.append(
                        f"Município {posicao} · {NOMES_MUNICIPAIS[codigo]} "
                        f"· {rotulo}"
                    )
    return alterados


def capturar_campos_municipais(ficha: dict[str, Any], prefixo: str) -> None:
    """Preserva entradas de blocos fechados ao incluir/excluir uma linha."""
    for posicao, municipio in enumerate(ficha["municipios"], 1):
        chave_nome = f"{prefixo}_municipio_{posicao}"
        if chave_nome in st.session_state:
            municipio["nome"] = st.session_state[chave_nome]
        for codigo in MUNICIPAIS:
            for campo in ("gestor", "justificativa", "validado"):
                chave = f"{prefixo}_municipio_{posicao}_{codigo}_{campo}"
                if chave in st.session_state:
                    municipio[codigo][campo] = st.session_state[chave]


def padronizar_municipio_digitado(chave: str) -> None:
    """Normaliza o nome informado sem perder o valor do widget Streamlit."""
    st.session_state[chave] = normalizar_nome_municipio(st.session_state[chave])


def mudar_municipios(ficha: dict[str, Any], prefixo: str, excluir: int | None) -> None:
    """Altera a lista preservando pontuações e redefinindo chaves visuais."""
    capturar_campos_municipais(ficha, prefixo)
    if excluir is None:
        ficha["municipios"].append(nova_linha_municipal())
    else:
        del ficha["municipios"][excluir]
    st.session_state.ficha = deepcopy(ficha)
    st.session_state.geracao += 1
    st.rerun()


modo_configurado = segredo("modo", os.environ.get("ICMS_MODO", ""))
modo = str(modo_configurado).strip().lower()
if st.session_state.get("modo_demo_sessao", False):
    modo = "demonstracao"
elif modo not in ("demonstracao", "banco"):
    exibir_tela_acesso(autenticacao_configurada=False, permitir_demo=True)
    st.stop()
autor, pode_editar = identificar(modo)
# O cabeçalho aparece no alto, antes de todas as seções e controles.
CABECALHO_APROVADO = Path(__file__).resolve().parent / "assets" / "cabecalho_aprovado.png"
with st.container(key="cabecalho_visual_aplicacao"):
    if CABECALHO_APROVADO.is_file():
        st.image(str(CABECALHO_APROVADO), width="stretch")
    else:
        # Falta do recurso visual não deve impedir acesso às fichas.
        registrador_log.error("Cabeçalho visual ausente: %s", CABECALHO_APROVADO)
        st.markdown("### ICMS Ecológico · Ficha")
if modo == "demonstracao":
    st.markdown(
        '<div class="aviso-demo"><strong>Modo demonstração:</strong> use somente '
        "dados fictícios. Os registros ficam isolados nesta sessão do navegador, "
        "não são gravados na base oficial e desaparecem ao encerrar a sessão.</div>",
        unsafe_allow_html=True,
    )
# As setas acompanham a borda externa do formulário, inclusive em widescreen.
st.markdown(
    '<div id="inicio"></div><nav class="atalhos-rolagem" '
    'aria-label="Navegação vertical"><a href="#inicio" title="Ir ao início da página" '
    'aria-label="Ir ao início">↑</a><a href="#fim" title="Ir ao final" '
    'aria-label="Ir ao final">↓</a></nav>',
    unsafe_allow_html=True,
)
try:
    repositorio = conectar(modo)
# Os adaptadores de persistência podem lançar erros específicos de conexão.
except Exception:  # noqa: BLE001
    registrador_log.exception("Falha ao conectar à persistência configurada.")
    st.error(
        "Não foi possível abrir o banco de dados. Confira a conexão e as permissões."
    )
    st.stop()
if modo == "demonstracao":
    exibir_backup_demonstracao(repositorio)
elif modo == "banco":
    if repositorio.engine.dialect.name == "sqlite":
        st.warning(
            "Armazenamento SQLite local: é possível recuperar após "
            "reiniciar o navegador enquanto o arquivo existir. "
            "enquanto o arquivo do banco existir. No Streamlit Community Cloud o disco "
            "NÃO é persistente: use PostgreSQL externo para operação durável."
        )
    else:
        st.caption(
            "Banco PostgreSQL configurado. Alterações em edição "
            "recebem uma cópia automática."
        )
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
    on_change=validar_troca_modulo,
)

if st.session_state.get("confirmar_saida_modulo"):
    st.warning(
        "A ficha tem alterações ainda não confirmadas. Sair do formulário "
        "não atualiza a ficha oficial. No modo banco configurado, as "
        "alterações já enviadas ao servidor ficam em cópia separada e podem "
        "ser recuperadas com a mesma conta, se a ficha oficial não mudou. "
        "Na demonstração, alterações não salvas podem ser perdidas."
    )
    with st.container(horizontal=True, gap="small"):
        if st.button("Continuar editando", key="continuar_edicao"):
            st.session_state.confirmar_saida_modulo = False
            st.rerun()
        if st.button("Ir para Resultados sem gravar", key="sair_com_edicao"):
            st.session_state.confirmar_saida_modulo = False
            st.session_state.modulo_pendente = "Resultados"
            st.rerun()

if modulo == "Ficha":
    st.markdown(
        '<h1 class="icms-titulo-pagina"><span aria-hidden="true">▤</span>'
        ' Ficha</h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Informe o processo SEI para abrir uma ficha existente ou iniciar uma nova. "
        "A ficha encontrada abre neste mesmo módulo para edição."
    )
    if modo == "banco" and pode_editar:
        try:
            recuperaveis = repositorio.listar_edicoes(autor)
            # Não oferece recuperar o documento que já está aberto no mesmo estado.
            recuperaveis = [
                copia for copia in recuperaveis
                if copia["ficha"] != st.session_state.ficha
            ]
            if recuperaveis:
                with st.expander(
                    "Edições automáticas disponíveis para recuperação "
                    f"({len(recuperaveis)})",
                    expanded=False,
                ):
                    st.caption(
                        "Estas cópias não atualizam a ficha oficial "
                        "nem aparecem no relatório. "
                        "Verifique os dados e escolha Salvar/Atualizar após recuperar."
                    )
                    for indice, copia in enumerate(recuperaveis):
                        st.write(
                            f"SEI: {copia['processo'] or '(não informado)'} · "
                            f"Cópia: {copia['atualizado_em']}"
                        )
                        col_recuperar, col_descartar = st.columns([1, 1])
                        with col_recuperar:
                            if st.button("Recuperar edição", key=f"recuperar_{indice}"):
                                if (
                                    st.session_state.ficha
                                    != st.session_state.ficha_original
                                ):
                                    st.error(
                                        "A ficha atual já tem alterações. Salve ou "
                                        "descarte as alterações desta sessão antes "
                                        "de recuperar outra edição."
                                    )
                                else:
                                    atual = (
                                        repositorio.consultar(copia["processo"])
                                        if copia["processo"] else None
                                    )
                                    versao_atual = atual["versao"] if atual else 0
                                    if versao_atual != copia["versao"] or (
                                        atual and atual["status"] != copia["status"]
                                    ):
                                        st.error(
                                            "A ficha oficial mudou ou foi excluída "
                                            "desde esta edição. A recuperação foi "
                                            "bloqueada para proteger outras alterações."
                                        )
                                    else:
                                        abrir(
                                            copia["original"],
                                            copia["versao"],
                                            copia["status"],
                                        )
                                        recuperada = normalizar_municipios(
                                            copia["ficha"]
                                        )
                                        if not recuperada["municipios"]:
                                            recuperada["municipios"] = [
                                                nova_linha_municipal()
                                            ]
                                        st.session_state.ficha = recuperada
                                        st.session_state.geracao += 1
                                        st.session_state.aviso = (
                                            "Edição automática recuperada. "
                                            "Revise e confirme a gravação."
                                        )
                                        st.rerun()
                        with col_descartar:
                            if st.button("Descartar cópia", key=f"descartar_{indice}"):
                                repositorio.excluir_edicao(autor, copia["chave"])
                                st.rerun()
        except Exception:  # noqa: BLE001
            registrador_log.exception("Falha na lista de edições automáticas.")
            st.error("Não foi possível consultar as cópias automáticas.")
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
            tem_alteracoes = st.session_state.ficha != st.session_state.ficha_original
            if tem_alteracoes:
                st.session_state.consulta_pendente = {
                    "processo": processo_consultado,
                    "registro": registro,
                }
            elif registro:
                abrir(registro["ficha"], registro["versao"], registro["status"])
                st.rerun()
            else:
                ficha_nova = nova_ficha()
                ficha_nova["processo"] = processo_consultado
                abrir(ficha_nova)
                st.session_state.aviso = (
                    "Processo não localizado. Uma ficha nova foi "
                    "aberta com o SEI informado."
                )
                st.rerun()
        except ValueError as erro:
            st.error(str(erro))
        # A camada de integração pode lançar erros específicos de rede/autenticação.
        except Exception:  # noqa: BLE001
            registrador_log.exception("Falha ao consultar uma ficha.")
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
                if modo == "banco" and pode_editar:
                    repositorio.excluir_edicao(
                        autor, chave_edicao(st.session_state.ficha)
                    )
                registro = consulta_pendente["registro"]
                if registro:
                    abrir(registro["ficha"], registro["versao"], registro["status"])
                else:
                    ficha_nova = nova_ficha()
                    ficha_nova["processo"] = consulta_pendente["processo"]
                    abrir(ficha_nova)
                    st.session_state.aviso = (
                    "Processo não localizado. Uma ficha nova foi "
                    "aberta com o SEI informado."
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
                format_func=lambda indice: (
                    f"{rascunhos[indice]['ficha']['processo']} · "
                    f"{rascunhos[indice]['ficha']['unidade'] or 'Sem unidade'}"
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
                    st.rerun()
    else:
        st.caption("Não há rascunhos gravados.")

    st.divider()
    st.subheader("Dados da ficha")
    versao = st.session_state.versao
    situacao_atual = st.session_state.status_ficha
    tem_alteracoes = st.session_state.ficha != st.session_state.ficha_original
    if versao:
        st.info(
            f"Ficha {situacao_atual.lower()} · Versão {versao}. "
            "As alterações são gravadas somente quando você escolhe salvar."
        )
    else:
        st.caption("Preencha os dados e escolha Cadastrar ou Salvar rascunho.")
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
                not pode_editar or (campo == "processo" and st.session_state.versao > 0)
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
            valor_original=st.session_state.ficha_original.get("pontuacao_categoria"),
            desabilitado=not pode_editar,
        )
    ficha["analise"] = texto_em_linha(
        "Data de análise (mm/aaaa)",
        ficha["analise"],
        f"{prefixo}_analise",
        valor_original=st.session_state.ficha_original.get("analise", ""),
        placeholder="mm/aaaa",
    )
    rotulo_data, controle_data = st.columns([0.24, 0.76], vertical_alignment="center")
    with rotulo_data:
        exibir_rotulo_formulario("Data de recebimento")
    with controle_data:
        chave_recebimento = f"{prefixo}_recebimento"
        data_original = date.fromisoformat(
            st.session_state.ficha_original["recebimento"]
        )
        with st.container(key=chave_container_campo(chave_recebimento, data_original)):
            ficha["recebimento"] = st.date_input(
                "Data de recebimento",
                value=date.fromisoformat(ficha["recebimento"]),
                format="MM/DD/YYYY",
                key=chave_recebimento,
                disabled=not pode_editar,
                label_visibility="collapsed",
                width=180,
            ).isoformat()
    # Apresentação fiel à referência: cabeçalho compacto e linhas editáveis.
    with st.container(key="parametros_gerais_cartao"):
        st.markdown(
            '<h2 class="icms-titulo-secao">'
            '<span aria-hidden="true">☷</span> Parâmetros</h2>',
            unsafe_allow_html=True,
        )
        proporcao_colunas = [3.25, 1.4, 4.35, 1.45]
        with st.container(key="cabecalho_parametros_gerais"):
            col_rotulo, col_gestor, col_just, col_validado = st.columns(
                proporcao_colunas, gap="small", vertical_alignment="center"
            )
            for coluna, titulo in (
                (col_rotulo, "Parâmetro"),
                (col_gestor, "Pontos do gestor"),
                (col_just, "Justificativa"),
                (col_validado, "Pontos validados"),
            ):
                with coluna:
                    st.markdown(f"**{titulo}**")
        for codigo, nome in PARAMETROS:
            pontos = ficha["parametros"][codigo]
            pontos_originais = st.session_state.ficha_original["parametros"].get(
                codigo, {}
            )
            with st.container(key=f"linha_parametro_{codigo.replace('.', '_')}"):
                (
                    coluna_parametro,
                    coluna_gestor,
                    coluna_justificativa,
                    coluna_validado,
                ) = st.columns(
                    proporcao_colunas, gap="small", vertical_alignment="center"
                )
                with coluna_parametro:
                    chave_rotulo = f"{prefixo}_{codigo}_rotulo"
                    rotulo_padrao = f"{codigo} · {nome}"
                    with st.container(
                        key=chave_container_campo(
                            chave_rotulo,
                            pontos_originais.get("rotulo", rotulo_padrao),
                        )
                    ):
                        # A edição do título existente é preservada; o CSS
                        # apresenta o controle como texto de uma linha.
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
                            height=68,
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

    st.markdown(
        '<h2 class="icms-titulo-municipios">'
        '<span aria-hidden="true">♣</span> Parâmetros por municípios</h2>',
        unsafe_allow_html=True,
    )
    # Uma única lista de municípios é compartilhada pelos quatro painéis.
    icones_municipais = {
        "10": ":material/location_on:",
        "11.1": ":material/layers:",
        "11.2": ":material/account_balance:",
        "11.3": ":material/payments:",
    }
    proporcao_municipal = [2.6, 1.25, 4.0, 1.3, 1.05]
    for codigo in MUNICIPAIS:
        with st.container(key=f"bloco_municipal_{codigo.replace('.', '_')}"):
            with st.expander(
                NOMES_MUNICIPAIS[codigo],
                expanded=False,
                icon=icones_municipais[codigo],
            ):
                with st.container(
                    key=f"cabecalho_municipal_{codigo.replace('.', '_')}"
                ):
                    col_nome, col_gestor, col_just, col_validado, col_acao = (
                        st.columns(
                            proporcao_municipal,
                            gap="small",
                            vertical_alignment="center",
                        )
                    )
                    for coluna, rotulo in (
                        (col_nome, "Município"),
                        (col_gestor, "Pontos do gestor"),
                        (col_just, "Justificativa"),
                        (col_validado, "Pontos validados"),
                    ):
                        with coluna:
                            st.markdown(f"**{rotulo}**")
                if not ficha["municipios"]:
                    st.info(
                        "Nenhum município cadastrado. "
                        "Adicione um registro no primeiro bloco."
                    )
                for posicao, municipio in enumerate(ficha["municipios"], 1):
                    originais = st.session_state.ficha_original.get(
                        "municipios", []
                    )
                    original = (
                        originais[posicao - 1] if posicao <= len(originais) else {}
                    )
                    original_pontos = original.get(codigo) or {}
                    if not isinstance(original_pontos, dict):
                        original_pontos = {"validado": original_pontos}
                    with st.container(key=f"linha_municipal_{codigo.replace('.', '_')}_{posicao}"):
                        (
                            coluna_nome,
                            coluna_gestor,
                            coluna_just,
                            coluna_validado,
                            coluna_acao,
                        ) = st.columns(
                            proporcao_municipal,
                            gap="small",
                            vertical_alignment="center",
                        )
                        with coluna_nome:
                            if codigo == "10":
                                chave_nome = f"{prefixo}_municipio_{posicao}"
                                with st.container(
                                    key=chave_container_campo(
                                        chave_nome, original.get("nome", "")
                                    )
                                ):
                                    municipio["nome"] = st.text_input(
                                        f"Nome do município {posicao}",
                                        value=municipio["nome"],
                                        key=chave_nome,
                                        placeholder="Nome do município",
                                        disabled=not pode_editar,
                                        on_change=padronizar_municipio_digitado,
                                        args=(chave_nome,),
                                        label_visibility="collapsed",
                                    )
                            else:
                                st.text_input(
                                    f"Nome do município {posicao}",
                                    value=municipio["nome"],
                                    key=(
                                        f"{prefixo}_somente_nome_{codigo}_{posicao}"
                                        f"_{municipio['nome']}"
                                    ),
                                    disabled=True,
                                    label_visibility="collapsed",
                                )
                        identificado = municipio["nome"].strip() not in ("", "-")
                        pontos = municipio[codigo]
                        for coluna, campo, rotulo in (
                            (coluna_gestor, "gestor", "Pontos Gestor"),
                            (coluna_validado, "validado", "Pontos Validados"),
                        ):
                            with coluna:
                                chave = (
                                    f"{prefixo}_municipio_{posicao}_{codigo}_{campo}"
                                )
                                with st.container(
                                    key=chave_container_campo(
                                        chave, original_pontos.get(campo)
                                    )
                                ):
                                    pontos[campo] = st.number_input(
                                        f"{rotulo} de {NOMES_MUNICIPAIS[codigo]} "
                                        f"para o município {posicao}",
                                        min_value=0,
                                        max_value=9,
                                        value=pontos[campo],
                                        step=1,
                                        key=chave,
                                        disabled=not pode_editar or not identificado,
                                        label_visibility="collapsed",
                                    )
                        with coluna_just:
                            chave_just = (
                                f"{prefixo}_municipio_{posicao}_{codigo}"
                                "_justificativa"
                            )
                            with st.container(
                                key=chave_container_campo(
                                    chave_just,
                                    original_pontos.get("justificativa", ""),
                                )
                            ):
                                pontos["justificativa"] = st.text_area(
                                    f"Justificativa de {NOMES_MUNICIPAIS[codigo]} "
                                    f"para o município {posicao}",
                                    value=pontos["justificativa"],
                                    key=chave_just,
                                    height=68,
                                    disabled=not pode_editar or not identificado,
                                    label_visibility="collapsed",
                                )
                        with coluna_acao:
                            if codigo == "10" and pode_editar:
                                if st.button(
                                    "Remover",
                                    key=f"{prefixo}_remover_municipio_{posicao}",
                                    help=f"Remover registro {posicao}",
                                ):
                                    mudar_municipios(ficha, prefixo, posicao - 1)
                if codigo == "10" and pode_editar:
                    sem_nome = any(
                        not m["nome"].strip() or m["nome"].strip() == "-"
                        for m in ficha["municipios"]
                    )
                    with st.container(key="acoes_adicionar_municipio"):
                        col_botao, col_ajuda = st.columns(
                            [2.2, 7.8], gap="medium", vertical_alignment="center"
                        )
                        with col_botao:
                            if st.button(
                                "Adicionar registro",
                                key=f"{prefixo}_adicionar_municipio",
                                disabled=sem_nome,
                                icon=":material/add_circle:",
                            ):
                                mudar_municipios(ficha, prefixo, None)
                        with col_ajuda:
                            st.caption(
                                "ⓘ Os nomes são padronizados automaticamente: "
                                "minúsculas e sem espaços excedentes."
                            )
    # A cópia automática não é a ficha oficial. Somente Salvar/Atualizar
    # modifica o registro e o relatório do sistema.
    st.session_state.ficha = deepcopy(ficha)
    tem_alteracoes = ficha != st.session_state.ficha_original
    if tem_alteracoes and modo == "banco" and pode_editar:
        try:
            assinatura = (ficha, st.session_state.versao)
            if assinatura != st.session_state.get("ultimo_autosalvamento"):
                repositorio.salvar_edicao(
                    autor, ficha, st.session_state.ficha_original,
                    st.session_state.versao, st.session_state.status_ficha,
                )
                chave_atual = chave_edicao(ficha)
                chave_anterior = st.session_state.get("autosalvo_chave")
                if chave_anterior and chave_anterior != chave_atual:
                    repositorio.excluir_edicao(autor, chave_anterior)
                st.session_state.autosalvo_chave = chave_atual
                st.session_state.ultimo_autosalvamento = deepcopy(assinatura)
            st.caption(
                "Cópia de edição registrada automaticamente no banco. "
                "A ficha oficial só muda após Salvar/Atualizar."
            )
        except Exception:  # noqa: BLE001
            registrador_log.exception("Falha no salvamento automático da edição.")
            st.error(
                "A edição NÃO foi salva automaticamente. "
                "Não feche a página antes de salvar ou resolver a conexão."
            )
    if not tem_alteracoes and modo == "banco" and pode_editar:
        chave_anterior = st.session_state.get("autosalvo_chave")
        if chave_anterior:
            try:
                repositorio.excluir_edicao(autor, chave_anterior)
                st.session_state.pop("autosalvo_chave", None)
                st.session_state.pop("ultimo_autosalvamento", None)
            except Exception:  # noqa: BLE001
                registrador_log.exception(
                    "Falha ao limpar edição automática revertida."
                )
                st.warning("Não foi possível limpar a cópia automática antiga.")
    campos_alterados = diferencas_ficha(st.session_state.ficha_original, ficha)
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
    if tem_alteracoes:
        if st.button(
            "Descartar alterações desta sessão", key="descartar_edicao_sessao"
        ):
            if modo == "banco" and pode_editar:
                repositorio.excluir_edicao(
                    autor, str(ficha.get("processo", "")).strip() or "__nova__"
                )
            abrir(st.session_state.ficha_original, versao, situacao_atual)
            st.session_state.aviso = "Alterações não gravadas descartadas."
            st.rerun()
    rascunho = False
    concluir = False
    atualizar = False
    # As ações ficam próximas, alinhadas à direita e com quebra em telas estreitas.
    with st.container(
        key="acoes_ficha",
        horizontal=True,
        horizontal_alignment="right",
        gap="small",
    ):
        revisar = st.button("Revisar preenchimento")
        if versao == 0:
            rascunho = st.button("Salvar rascunho", disabled=not pode_editar)
            concluir = st.button("Cadastrar", disabled=not pode_editar)
        elif situacao_atual == "Concluída":
            atualizar = st.button(
                "Atualizar ficha",
                disabled=not pode_editar or not tem_alteracoes,
            )
            concluir = atualizar
        else:
            rascunho = st.button(
                "Salvar alterações",
                disabled=not pode_editar or not tem_alteracoes,
            )
            concluir = st.button("Concluir ficha", disabled=not pode_editar)
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
            st.markdown(
                renderizar_tabela(
                    pd.DataFrame(calculo["municipios"])[["Município", "Soma", "FQ"]]
                ),
                unsafe_allow_html=True,
            )
        except ValueError as erro:
            pendencias = [linha for linha in str(erro).splitlines() if linha]
            st.error("Há campos obrigatórios pendentes ou dados inválidos:")
            for pendencia in pendencias:
                st.markdown(f"- {pendencia}")
        except (KeyError, TypeError, ZeroDivisionError):
            st.error(
                "Não foi possível gerar a revisão. Confira os dados e tente novamente."
            )
    if rascunho or concluir:
        try:
            situacao_destino = "Concluída" if concluir else "Rascunho"
            registro_atual = (
                repositorio.consultar(ficha["processo"]) if versao > 0 else None
            )
            if (
                registro_atual
                and registro_atual["ficha"] == ficha
                and registro_atual["status"] == situacao_destino
            ):
                mensagem_salvamento = (
                    "Nenhuma alteração detectada. A ficha não foi gravada novamente."
                )
                salvo = registro_atual
            else:
                salvo = repositorio.gravar(
                    ficha,
                    st.session_state.versao,
                    situacao_destino,
                    autor,
                )
                mensagem_salvamento = (
                    f"{salvo['status']} salva e verificada. Versão {salvo['versao']}."
                )
            if modo == "banco":
                try:
                    repositorio.excluir_edicao(
                        autor, str(salvo["ficha"].get("processo", "")).strip()
                    )
                except Exception:  # noqa: BLE001
                    # A ficha oficial já foi confirmada: falha secundária na
                    # limpeza da cópia não pode converter sucesso em erro.
                    registrador_log.exception(
                        "Gravação confirmada; não foi possível limpar cópia automática."
                    )
            st.session_state.ficha = deepcopy(salvo["ficha"])
            st.session_state.ficha_original = deepcopy(salvo["ficha"])
            st.session_state.versao = salvo["versao"]
            st.session_state.status_ficha = salvo["status"]
            tem_alteracoes = False
            # Atualiza a versão da ficha na mesma ação, sem exigir um segundo clique.
            st.session_state.aviso = mensagem_salvamento
            st.rerun()
        except (Conflito, ValueError) as erro:
            st.error(str(erro))
        # A persistência remota usa SDKs com exceções específicas por provedor.
        except Exception:  # noqa: BLE001
            registrador_log.exception("Falha ao salvar ou confirmar uma ficha.")
            st.error(
                "A gravação não pôde ser confirmada. "
                "Consulte o processo antes de reenviar."
            )
    if versao > 0:
        if st.button(
            "Excluir ficha",
            key="excluir_ficha",
            disabled=not pode_editar or tem_alteracoes,
        ):
            st.session_state.confirmar_exclusao = True
        if tem_alteracoes:
            st.caption(
                "Grave ou descarte as alterações antes de excluir a ficha salva."
            )
        if st.session_state.get("confirmar_exclusao"):
            st.warning(
                f"Confirme a exclusão da ficha do processo {ficha['processo']}. "
                "A operação remove a ficha da consulta "
                "e registra o evento no histórico."
            )
            # Controles pequenos, adjacentes e alinhados na mesma linha.
            with st.container(
                horizontal=True,
                horizontal_alignment="left",
                gap="small",
                key="acoes_confirmacao_exclusao",
            ):
                if st.button(
                    "Confirmar exclusão",
                    type="primary",
                    key="acao_confirmar_exclusao",
                    disabled=not pode_editar or tem_alteracoes,
                ):
                    try:
                        repositorio.excluir(
                            ficha["processo"],
                            st.session_state.versao,
                            autor,
                        )
                        abrir(nova_ficha())
                        # Exibe imediatamente a lista atualizada de concluídas;
                        # o relatório é refeito a partir da base, sem cache.
                        st.session_state.modulo_pendente = "Resultados"
                        st.session_state.aviso = (
                            "Ficha excluída. Ela não aparece mais nos Resultados. "
                            "A exclusão foi registrada no histórico."
                        )
                        st.rerun()
                    except (Conflito, ValueError) as erro:
                        st.error(str(erro))
                    # Mantém erro técnico no log e mostra orientação segura ao usuário.
                    except Exception:  # noqa: BLE001
                        registrador_log.exception("Falha ao excluir uma ficha.")
                        st.error(
                            "A exclusão não foi confirmada. "
                            "Consulte novamente antes de repetir."
                        )
                if st.button("Cancelar exclusão", key="cancelar_exclusao"):
                    st.session_state.confirmar_exclusao = False
                    st.rerun()
else:
    st.subheader("Resultados consolidados")
    st.caption(
        "Consulte as fichas concluídas agrupadas por processo SEI. "
        "A identificação e os parâmetros gerais aparecem uma única vez; "
        f"os municípios vinculados ficam detalhados abaixo, com FQ exibido em {CASAS_DECIMAIS_FQ} casas decimais."
    )
    filtro = st.text_input("Filtrar por processo, unidade ou município")
    try:
        registros = repositorio.listar()
        concluidas = [
            registro for registro in registros if registro["status"] == "Concluída"
        ]
        quadro_resumo = resumo_fichas(concluidas)
        quadro_municipios = resultado_consolidado(concluidas)
        if quadro_resumo.empty:
            st.info(
                "Não há fichas concluídas para exibir. "
                "Os rascunhos ficam no módulo Ficha."
            )
        else:
            if filtro:
                filtro_resumo = quadro_resumo["Nº SEI"].astype(str).str.contains(
                    filtro, regex=False, case=False
                )
                filtro_resumo |= quadro_resumo["REMETENTE - UCs"].astype(str).str.contains(
                    filtro, regex=False, case=False
                )
                if not quadro_municipios.empty:
                    filtro_resumo |= quadro_resumo["Nº SEI"].isin(
                        quadro_municipios.loc[
                            quadro_municipios["Município"].astype(str).str.contains(
                                filtro, regex=False, case=False
                            ),
                            "Nº SEI",
                        ]
                    )
                quadro_resumo = quadro_resumo[filtro_resumo]
                if not quadro_municipios.empty:
                    quadro_municipios = quadro_municipios[
                        quadro_municipios["Nº SEI"].isin(quadro_resumo["Nº SEI"])
                    ]

            st.markdown(
                f'<div class="resumo-resultados">{len(quadro_resumo)} ficha(s) concluída(s) encontrada(s).</div>',
                unsafe_allow_html=True,
            )

            col_csv_fichas, col_csv_municipios = st.columns([1, 1], gap="small")
            with col_csv_fichas:
                st.download_button(
                    "Baixar CSV — fichas",
                    proteger_csv(quadro_resumo),
                    "resumo_fichas_icms.csv",
                    "text/csv",
                    use_container_width=True,
                )
            with col_csv_municipios:
                st.download_button(
                    "Baixar CSV — municípios",
                    proteger_csv(quadro_municipios),
                    "resultado_fq_municipios.csv",
                    "text/csv",
                    use_container_width=True,
                )

            destaques_por_processo = {
                registro["ficha"]["processo"]: colunas_resultado_alteradas(
                    registro.get("alteracoes_ultima_versao", {}),
                    segredo("totais_resultado", {}),
                )
                for registro in concluidas
            }

            for _, linha_resumo in quadro_resumo.sort_values(by=["DATA RECEBIDA", "Nº SEI"], ascending=[False, True]).iterrows():
                processo = linha_resumo["Nº SEI"]
                registro = next(
                    registro
                    for registro in concluidas
                    if registro["ficha"]["processo"] == processo
                )
                ficha = registro["ficha"]
                parametros_gerais = pd.DataFrame(
                    [
                        {
                            "Parâmetro": f"{codigo} · {nome}",
                            "Pontos validados": ficha["parametros"][codigo]["validado"],
                        }
                        for codigo, nome in PARAMETROS
                    ]
                )
                municipios_processo = quadro_municipios.loc[
                    quadro_municipios["Nº SEI"] == processo,
                    ["Município", "PARÂM 10", "PARÂM 11.1", "PARÂM 11.2", "PARÂM 11.3", "SOMA PARÂMETROS", "FQ"],
                ].copy()
                titulo = (
                    f"{processo} · {linha_resumo['REMETENTE - UCs']} "
                    f"· {int(linha_resumo['Municípios cadastrados'])} município(s)"
                )
                with st.expander(titulo, expanded=False):
                    col_id, col_param = st.columns([1.1, 1.4], gap="large")
                    with col_id:
                        identificacao = pd.DataFrame(
                            [
                                {"Campo": "Nº SEI", "Valor": linha_resumo["Nº SEI"]},
                                {"Campo": "Data recebida", "Valor": linha_resumo["DATA RECEBIDA"]},
                                {"Campo": "Remetente - UCs", "Valor": linha_resumo["REMETENTE - UCs"]},
                                {"Campo": "Esfera", "Valor": linha_resumo["Esfera"]},
                                {"Campo": "URFBio", "Valor": linha_resumo["URFBio"]},
                                {"Campo": "Responsável", "Valor": linha_resumo["RESPONSÁVEL"]},
                                {"Campo": "Municípios cadastrados", "Valor": linha_resumo["Municípios cadastrados"]},
                            ]
                        )
                        st.markdown("##### Identificação")
                        st.markdown(renderizar_tabela(identificacao), unsafe_allow_html=True)
                    with col_param:
                        st.markdown("##### Parâmetros gerais")
                        st.markdown(
                            renderizar_tabela(
                                parametros_gerais,
                                {processo: destaques_por_processo.get(processo, set())},
                            ),
                            unsafe_allow_html=True,
                        )
                    st.markdown("##### Municípios vinculados")
                    st.markdown(renderizar_tabela(municipios_processo), unsafe_allow_html=True)
                    if processo == st.session_state.get("ficha_original", {}).get("processo") and any(destaques_por_processo.get(processo, set())):
                        st.caption(
                            "Células em verde claro indicam dados alterados na última atualização salva desta ficha."
                        )
    except Exception:  # noqa: BLE001
        registrador_log.exception("Falha ao montar a tabela consolidada.")
        st.error("Não foi possível montar o resultado. Confira as fichas e a conexão.")

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


# Aviso nativo de saída. Não substitui o salvamento transacional no banco.
aviso_saida_navegador(
    st.session_state.ficha != st.session_state.ficha_original,
    int(st.session_state.get("geracao", 0)),
)
