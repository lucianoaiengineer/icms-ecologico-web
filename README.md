# ICMS Ecológico

**Sistema web de gestão de fichas e cálculo do Fator de Qualidade (FQ)**

Aplicação desenvolvida em **Python e Streamlit** para organizar a análise de fichas por processo SEI, registrar pontuações municipais e reunir os resultados em um único lugar.

**Situação:** versão em desenvolvimento e homologação. A aplicação está preparada para demonstração e para persistência em banco SQL. A operação institucional com banco externo e autenticação precisa ser configurada e validada antes do uso de dados reais.

[Repositório no GitHub](https://github.com/lucianoaiengineer/icms-ecologico-web)

---

## O que é possível fazer

<p style="line-height: 2;">
    
- **Cadastrar e consultar fichas** pelo número do processo SEI.
- **Salvar rascunhos:** permite interromper o preenchimento e retomar depois. No modo demonstração, a disponibilidade desse rascunho depende da sessão ativa e do tipo de armazenamento utilizado.
- **Revisar informações** e verificar pendências antes da conclusão.
- **Calcular o FQ** individualmente para cada município informado.
- **Atualizar ou excluir fichas**, com controle de versão e registro do histórico.
- **Consultar resultados consolidados** e exportá-los em CSV.

</p>
A consulta localiza registros **dentro da própria aplicação**. Não há conexão automática com o sistema SEI institucional.

## Como funciona uma ficha

<p style="line-height: 3;">
    
**1. Localize o processo.** Informe o SEI no campo de busca. Se a ficha existir, seus dados serão apresentados; se não existir, o formulário será iniciado com o número informado.

**2. Preencha os dados.** Registre as informações gerais e as pontuações na tabela compacta, com justificativas ajustáveis. Em **Parâmetros por municípios**, abra **Zona de Amortecimento** para cadastrar nomes e use **Adicionar registro** quando necessário. Os nomes aparecem automaticamente nos outros blocos: **RH ou Recurso Material**, **Empréstimo de Sede** e **Recursos Financeiro**. Cada município possui pontos do gestor, justificativa e pontos validados por bloco.

**3. Revise e grave.** Use **Revisar preenchimento** para conferir os dados sem gravá-los. Escolha **Salvar rascunho**, **Cadastrar** ou **Atualizar ficha**, conforme a situação.

**4. Consulte o resultado.** O módulo **Resultados** apresenta somente fichas concluídas. Uma ficha excluída deixa de constar da consulta e do próximo CSV exportado.

</p>

## Regras essenciais

| Assunto | Regra aplicada |
| --- | --- |
| **Processo SEI** | Identificação com 19 algarismos, normalizada no formato `0000.00.0000000/0000-00`. |
| **Parâmetros gerais** | 14 parâmetros, com pontos do gestor, justificativa e pontos validados. |
| **Municípios** | Registros dinâmicos: um cadastro de nomes compartilhado por quatro blocos expansíveis. A interface normaliza novos nomes para minúsculas e elimina espaços excedentes ao concluir a edição. |
| **Pontuações** | Inteiros de **0 a 9**. Zero é um valor válido quando existe nome de município. |
| **Posição sem município** | Não permite pontuação, nem mesmo zero. |
| **Conclusão** | Exige os dados obrigatórios, os 14 conjuntos gerais e ao menos um município com pontos do gestor e validados nos quatro blocos. Dados históricos são adaptados sem atribuir pontos do gestor inexistentes. |
| **Versões** | Uma ficha concluída é atualizada como concluída. Gravações idênticas não geram nova versão. |

### Cálculo do FQ

Para cada município vinculado à ficha:

```text
Soma do município =
    soma dos pontos validados dos 14 parâmetros gerais da ficha
  + pontos validados de Zona de Amortecimento
  + pontos validados de RH ou Recurso Material
  + pontos validados de Empréstimo de Sede
  + pontos validados de Recursos Financeiro

FQ do município = Soma do município / pontuação da categoria
```

A relação entre ficha, municípios e resultado é:

- **1 ficha**
- **N municípios vinculados**
- **1 FQ calculado para cada município**

O resultado é arredondado para **quatro casas decimais**, com `Decimal` e `ROUND_HALF_UP`. Os pontos do gestor não entram nessa soma; a nota de um município não depende da nota dos demais.

### Relatórios de resultados

O módulo **Resultados** exibe, por padrão, o **Consolidado geral**: uma tabela
contínua com os processos SEI e as informações da ficha organizadas como na
planilha de referência. Há duas abas:

| Visão | Conteúdo |
| --- | --- |
| **Consolidado geral** | Uma tabela geral de 27 colunas: seis de identificação, 14 parâmetros gerais, nome do município, quatro parâmetros municipais, soma e FQ. |
| **Consulta por processo** | Seleção de um único SEI para consultar identificação, parâmetros gerais e municípios vinculados sem percorrer toda a tabela. |

No **Consolidado geral**, a primeira linha de cada SEI apresenta todos os dados
de identificação e os 14 parâmetros gerais, além dos dados do primeiro município.
Quando a ficha tem outros municípios, eles aparecem nas linhas seguintes, com
os dados gerais em branco e somente suas pontuações municipais, soma e FQ.
**Um município equivale a uma linha e não há quantidade fixa de municípios.**
As linhas ficam agrupadas por SEI, com divisórias entre processos e rolagem
horizontal para consultar todas as colunas.

A pesquisa por processo, unidade ou município preserva o conjunto de municípios
vinculados à ficha encontrada. Apenas fichas concluídas entram nas visualizações.
Fichas excluídas são retiradas do consolidado após sua exclusão confirmada.

Os dois CSVs atendem a finalidades diferentes:

- **Consolidado geral:** reproduz a tabela visual, com campos compartilhados vazios
  após a primeira linha do SEI.
- **Análise completa:** mantém o SEI e os parâmetros gerais em cada linha municipal,
  facilitando filtros, tabelas dinâmicas e cruzamentos no Excel.

Cada relatório apresenta as mesmas 27 colunas, mas com preenchimento diferente
nos registros municipais adicionais. O CSV de resultados não é um backup de fichas.

O formulário não apresenta mais a seção **TOTAL DOS PARÂMETROS** nem os indicadores de totais do gestor e dos pontos validados. Os cálculos internos necessários ao FQ permanecem intactos.

**Compatibilidade de fichas anteriores:** cada pontuação municipal antiga é aproveitada como *ponto validado*, preservando o cálculo. O ponto do gestor e a justificativa, inexistentes no modelo antigo, permanecem em branco; não são inventados. As 13 posições anteriores são reduzidas aos registros efetivamente preenchidos, sem descartar dados de uma posição inválida silenciosamente. O backup CSV antigo pode ser importado, sujeito à validação.

**Pendente de homologação:** a correspondência histórica das referências E44/E60 ainda depende de confirmação formal. A nova apresentação detalhada utiliza diretamente as quatro chaves existentes (`10`, `11.1`, `11.2`, `11.3`) para cada município.

---

## Onde os dados são guardados

A aplicação possui duas formas de execução:

| Modo | Como funciona | Limite importante |
| --- | --- | --- |
| **Demonstração** | Fichas em memória, isoladas por sessão do navegador. | Não garante preservação após fechar a sessão ou reiniciar a aplicação. Use somente dados fictícios. |
| **Banco** | Fichas, versões, histórico e cópias automáticas em **SQLite** ou **PostgreSQL**. | Exige configuração, permissões, backup e homologação. |

Para uso contínuo em hospedagem com disco temporário, o recomendado é um **PostgreSQL externo** administrado e protegido. SQLite é adequado somente quando o arquivo fica em armazenamento persistente sob controle do operador.

### Proteção das edições

Quando o modo **banco** estiver configurado, a aplicação pode guardar uma cópia provisória dos campos que já chegaram ao servidor. Ao retornar com a mesma conta autorizada, o usuário pode recuperar essa edição, desde que a ficha oficial não tenha sido alterada ou excluída.

**A cópia automática não conclui nem atualiza a ficha oficial.** A gravação oficial continua dependendo de uma ação explícita do usuário.

O navegador também pode alertar ao tentar abandonar a página com alterações pendentes. Nenhum desses recursos garante salvar uma tecla que ainda não foi transmitida ao servidor.

O modo **demonstração** oferece backup e restauração manual pelo arquivo `backup_fichas_icms.csv`. O CSV de resultados não substitui esse backup.

**Exemplos sintéticos atualizados:** o arquivo
`backup_fichas_icms_10_sinteticas_completas.csv` agora contém 10 fichas e **um
município distinto em cada ficha**. O modelo antigo continha 13 municípios
sintéticos por ficha. Se esses dados já tiverem sido restaurados em uma sessão,
a aplicação exibirá uma ação opcional para adequar somente o conjunto legado,
com confirmação e histórico. Fichas reais com múltiplos municípios não são
reduzidas. Veja [Como adequar exemplos antigos](AJUSTE_DADOS_DEMONSTRACAO_MUNICIPIOS.md).

---

## Como executar no computador

Recomendado: **Python 3.12**. As dependências do projeto estão no `requirements.txt`.

Na pasta raiz do projeto, execute:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Se não houver configuração de acesso institucional, escolha **Continuar na demonstração** e utilize apenas informações fictícias.

Para preparar um ambiente persistente, consulte o [Guia de persistência](GUIA_PERSISTENCIA.md) e a [Configuração de acesso](CONFIGURACAO_ACESSO_E_RESULTADOS.md). Credenciais devem permanecer nos **Secrets da hospedagem**, nunca no repositório.

## Arquivos do projeto

| Item | Por quê |
| --- | --- |
| [`app.py`](app.py) | Inicia a aplicação e coordena a interface, o acesso e as ações do formulário. |
| [`assets/estilos.css`](assets/estilos.css) | Define a aparência aprovada, campos compactos, quatro blocos expansíveis e atalhos laterais. |
| [`assets/cabecalho_aprovado.png`](assets/cabecalho_aprovado.png) | Exibe a faixa ilustrada do cabeçalho, recortada da referência aprovada para a ficha. |
| [`icms/regras.py`](icms/regras.py) | Contém validações, normalização do SEI e cálculo do FQ. |
| [`icms/repositorio.py`](icms/repositorio.py) | Gerencia fichas temporárias, versões, histórico e backups da demonstração. |
| [`icms/demonstracao.py`](icms/demonstracao.py) | Identifica e adequa exclusivamente o conjunto sintético legado de 13 municípios, após confirmação. |
| [`icms/repositorio_sql.py`](icms/repositorio_sql.py) | Implementa o armazenamento SQL e a recuperação de edições interrompidas. |
| [`icms/relatorios.py`](icms/relatorios.py) | Organiza as colunas, a grade de resultados e a exportação CSV. |
| [`icms/edicoes.py`](icms/edicoes.py) | Identifica as cópias de edição recuperáveis. |
| [`requirements.txt`](requirements.txt) | Declara as bibliotecas necessárias à aplicação. |
| [`.streamlit/config.toml`](.streamlit/config.toml) | Define o tema visual. |
| [`.gitignore`](.gitignore) | Evita versionar credenciais, caches e arquivos locais de banco. |
| [`tests/`](tests/) | Reúne os testes de regras, relatórios, persistência e interface. |
| [`pyproject.toml`](pyproject.toml) | Define as configurações de qualidade e formatação do código. |
| [`CONFIGURACAO_ACESSO_E_RESULTADOS.md`](CONFIGURACAO_ACESSO_E_RESULTADOS.md) | Explica autenticação, perfis e consulta de resultados. |
| [`GUIA_PERSISTENCIA.md`](GUIA_PERSISTENCIA.md) | Orienta a configuração e a homologação do armazenamento SQL. |
| [`PADROES_E_PUBLICACAO.md`](PADROES_E_PUBLICACAO.md) | Relaciona os arquivos a publicar e as verificações técnicas. |

## Layout visual da ficha

A ficha utiliza a apresentação aprovada em **11/11/2026**: cabeçalho ilustrado, título **Ficha**, cartão de 14 parâmetros gerais em linhas compactas, aviso azul com instruções de uso e os quatro cartões verdes expansíveis dos parâmetros municipais. Os controles são campos nativos do Streamlit; a imagem é utilizada somente no cabeçalho. O arquivo de referência visual está em `docs/referencia_visual_ficha_aprovada.png`.

Os novos nomes de municípios são convertidos para minúsculas, com um único espaço entre palavras e sem espaços externos. O nome informado no primeiro cartão é exibido nos demais sem repetição da digitação. Não foi introduzido um banco de dados novo nem modificada a fórmula do FQ.

**Pendente fora desta atualização visual:** a regra global que proíbe um município em processos SEI diferentes requer uma verificação na origem compartilhada dos registros. O modo demonstração usa repositórios isolados por sessão, e o conjunto sintético legado contém municípios repetidos entre fichas; nenhuma validação entre sessões diferentes é prometida nesta entrega.

## Testes e homologação

Para executar a suíte de testes com as dependências instaladas:

```bash
python -m unittest discover -s tests -v
```

A aplicação utiliza convenções de **PEP 8**, docstrings e anotações de tipos. Isso não substitui a execução dos testes, da análise estática e da homologação no ambiente final.

Antes de utilizar dados reais, ainda é necessário conferir: regras finais dos fatores, acesso por perfil, gravação e recuperação em PostgreSQL, backup, concorrência, abertura em celular e comportamento visual dos formulários.

**Este README descreve o código preparado; não afirma que a versão já tenha sido publicada ou homologada em produção.**
