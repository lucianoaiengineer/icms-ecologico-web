# ICMS Ecológico

**Protótipo funcional de gestão de fichas e apuração do Fator de Qualidade (FQ)**

<div align="justify">

O ICMS Ecológico é uma aplicação demonstrativa voltada à organização de fichas de análise de Unidades de Conservação (U.C.), identificadas por processo SEI. O protótipo reúne o preenchimento, a conferência das pontuações e a consulta dos resultados em um mesmo ambiente.

Sua criação responde a uma necessidade prática: diminuir a dependência de planilhas Excel, de cópias sucessivas de informações e de controles manuais para acompanhar as avaliações.

**O protótipo apresenta uma possibilidade de solução para a área de negócio.** Não constitui sistema institucional homologado nem determina quais tecnologias, controles ou procedimentos a Diretoria de Sistemas deverá adotar em eventual solução definitiva.

</div>

## Metadados da aplicação

| Item | Informação |
| --- | --- |
| **Nome** | ICMS Ecológico |
| **Natureza** | Protótipo funcional demonstrativo |
| **Finalidade** | Gestão de fichas, parâmetros e resultados do FQ |
| **Área de aplicação** | Avaliação de Unidades de Conservação |
| **Idioma da interface** | Português do Brasil |
| **Tecnologias utilizadas no protótipo** | Python, Streamlit e Pandas |
| **Identificação principal** | Número do processo SEI |
| **Modo demonstrado publicamente** | Demonstração com dados temporários por sessão |
| **Documentação** | README e fluxograma funcional no repositório |
| **Referência documental** | 13 de novembro de 2026 |
| **Repositório** | [lucianoaiengineer/icms-ecologico-web](https://github.com/lucianoaiengineer/icms-ecologico-web) |
| **Demonstração web** | [icms-ecologico.streamlit.app](https://icms-ecologico.streamlit.app/) |

## 1. Necessidade atendida

<div align="justify">

A análise de fichas envolve dados de identificação, critérios de pontuação, justificativas e resultados vinculados a municípios. Quando essas informações são mantidas em diversas planilhas, a consulta e a consolidação exigem trabalho manual repetitivo.

O protótipo demonstra um fluxo padronizado de registro, atualização e consulta. As informações compartilhadas pela ficha são cadastradas uma única vez, enquanto cada município possui suas próprias pontuações e seu FQ.

</div>

## 2. Funcionalidades demonstradas

| Funcionalidade | O que permite fazer |
| --- | --- |
| **Localizar ficha** | Consultar, na própria aplicação, um processo SEI já registrado. |
| **Cadastrar ficha** | Registrar identificação e parâmetros de uma nova avaliação. |
| **Salvar rascunho** | Guardar temporariamente o preenchimento ainda não concluído. |
| **Concluir ou atualizar** | Gravar uma ficha concluída e registrar alterações posteriores. |
| **Excluir ficha** | Excluir mediante confirmação, respeitando as verificações do sistema. |
| **Parâmetros gerais** | Registrar pontos do gestor, justificativas e pontos validados em 14 critérios. |
| **Municípios vinculados** | Incluir ou remover registros municipais em quantidade variável. |
| **Parâmetros municipais** | Preencher individualmente quatro critérios por município. |
| **Cálculo do FQ** | Calcular um resultado para cada município vinculado à ficha. |
| **Consolidado geral** | Consultar processos e resultados em uma tabela contínua. |
| **Consulta por processo** | Visualizar detalhadamente uma ficha selecionada. |
| **Exportações CSV** | Obter relatórios para apresentação ou análise de dados. |
| **Backup demonstrativo** | Exportar e restaurar fichas por meio de arquivo CSV. |

<div align="justify">

**Salvar rascunhos:** permite interromper o preenchimento e retomar depois. No modo demonstração, a disponibilidade desse rascunho depende da sessão ativa e do tipo de armazenamento utilizado.

A busca por processo SEI consulta os registros da aplicação. **Não há integração automática com o sistema SEI institucional.**

</div>

## 3. Organização da ficha

### Identificação

<div align="justify">

Reúne os dados do processo e da Unidade de Conservação: processo SEI, órgão gestor, nome e categoria da U.C., responsáveis, URFBio, esfera administrativa, pontuação da categoria e datas de análise e recebimento.

A seção é expansível e pode ser recolhida após a consulta ou o preenchimento, facilitando a navegação em fichas extensas.

</div>

### Parâmetros gerais

<div align="justify">

A ficha contém **14 parâmetros gerais**. Para cada um, o formulário mantém os campos de pontos do gestor, justificativa e pontos validados.

Essas pontuações gerais pertencem à ficha e são consideradas no cálculo de todos os municípios vinculados ao mesmo processo.

</div>

### Parâmetros por municípios

<div align="justify">

O cadastro começa com **um registro municipal**. A opção **Adicionar registro** permite incluir outros municípios, quando a ficha abranger mais de um. O usuário também pode remover registros adicionais.

O nome do município é informado no primeiro bloco e reaproveitado nos demais, evitando nova digitação. Ao editar um nome, a interface o converte para minúsculas e elimina espaços excedentes.

Os quatro blocos municipais são:

</div>

1. **Zona de Amortecimento** — identificador interno `10`.
2. **RH ou Recurso Material** — identificador interno `11.1`.
3. **Empréstimo de Sede** — identificador interno `11.2`.
4. **Recursos Financeiro** — identificador interno `11.3`.

<div align="justify">

Cada município possui campos próprios de pontos do gestor, justificativa e pontos validados nos quatro blocos. A quantidade de municípios não é definida antecipadamente.

O botão **Anexos** que aparece no formulário é apenas demonstrativo: ele está desabilitado e não envia nem armazena documentos PDF.

</div>

## 4. Cálculo do FQ

<div align="justify">

O Fator de Qualidade é calculado **individualmente para cada município**. Os 14 parâmetros gerais da ficha são compartilhados no cálculo, mas os quatro parâmetros municipais são específicos de cada município.

</div>

```text
Soma do município =
    soma dos pontos validados dos 14 parâmetros gerais da ficha
  + pontos validados de Zona de Amortecimento
  + pontos validados de RH ou Recurso Material
  + pontos validados de Empréstimo de Sede
  + pontos validados de Recursos Financeiro

FQ do município = Soma do município / pontuação da categoria
```

A relação entre registros e resultado é:

- **1 ficha**
- **N municípios vinculados**
- **1 FQ calculado para cada município**

<div align="justify">

O FQ é arredondado para **quatro casas decimais**, utilizando `Decimal` e `ROUND_HALF_UP`. Na soma entram os **pontos validados**; os pontos do gestor são registrados para análise, mas não substituem os valores validados no cálculo.

Um município não recebe uma nota agregada dos demais. Cada resultado corresponde às pontuações daquele município, somadas à parte geral da ficha.

</div>

## 5. Regras observadas

| Assunto | Comportamento existente |
| --- | --- |
| **Processo SEI** | Formato normalizado `0000.00.0000000/0000-00`, com 19 algarismos. |
| **Pontuações** | Valores inteiros de 0 a 9 nos parâmetros. |
| **Zero** | É pontuação válida quando o município está identificado. |
| **Município sem nome** | Não deve receber pontuações, inclusive zero. |
| **Conclusão** | Depende do preenchimento e da validação dos campos obrigatórios. |
| **Registros municipais** | Podem ser acrescentados conforme a necessidade; a ficha mantém ao menos uma linha. |
| **Fichas anteriores** | Pontuações antigas podem ser interpretadas como pontos validados, sem inventar pontos do gestor. |
| **Histórico** | Gravações e alterações possuem controles de versão no repositório utilizado. |
| **Exclusão** | Requer confirmação e atualiza os resultados apresentados. |

<div align="justify">

A exclusividade de um município entre diferentes processos SEI é uma necessidade de negócio identificada. **Sua garantia global ainda não está implementada entre sessões independentes do modo demonstração.**

</div>

## 6. Resultados e consultas

<div align="justify">

O módulo <strong>Resultados</strong> considera as fichas concluídas e oferece duas formas complementares de consulta.

</div>

| Visualização | Finalidade |
| --- | --- |
| **Consolidado geral** | Apresenta todos os processos em uma tabela contínua com 27 colunas. |
| **Consulta por processo** | Mostra a identificação, os parâmetros gerais e os municípios de um processo selecionado. |

<div align="justify">

No **Consolidado geral**, a identificação e os 14 parâmetros gerais são apresentados somente na primeira linha de cada processo. Quando existem outros municípios vinculados, suas pontuações e o FQ aparecem nas linhas seguintes, sem repetir visualmente os dados gerais.

Cada município corresponde a uma linha de resultado. A tabela acompanha a quantidade efetivamente cadastrada, sem reservar posições fixas para 13 municípios.

A consulta dispõe de pesquisa por processo e outros dados registrados na ficha. Os resultados podem ser exportados em CSV para conferência e análise.

</div>

### Diferença entre os dois CSVs

| Exportação | Uso principal |
| --- | --- |
| **Consolidado geral** | Reproduz a organização visual, evitando repetir a identificação nas linhas adicionais. |
| **Análise completa** | Repete o processo SEI e os parâmetros gerais em cada linha municipal, permitindo filtros e cruzamentos no Excel. |

<div align="justify">

As duas exportações contêm os mesmos resultados calculados. A repetição dos dados na versão analítica facilita o tratamento das informações e **não representa duplicação de fichas**.

Esses arquivos são relatórios, e **não substituem o backup completo** necessário para restaurar fichas.

</div>

## 7. Demonstração e continuidade dos registros

<div align="justify">

A aplicação pública funciona em **modo demonstração**, que utiliza registros temporários associados à sessão. É possível preencher, salvar rascunhos, concluir fichas e consultar resultados durante o uso.

Entretanto, a sessão não representa um repositório institucional permanente. Ao encerrá-la ou reiniciar a aplicação, registros mantidos apenas em memória podem deixar de estar disponíveis.

O protótipo permite baixar e restaurar um **backup CSV completo das fichas**, inclusive para continuar uma demonstração em outro computador. Os arquivos CSV de resultados não têm essa função de restauração.

Para apresentações, devem ser utilizados **somente dados fictícios**. O repositório contém amostras sintéticas, incluindo um conjunto atualizado com um município por ficha.

</div>

## 8. Possibilidades de armazenamento — sem definição institucional

<div align="justify">

O código existente contém recursos de armazenamento temporário e um módulo SQL preparado para funcionar, mediante configuração, com **SQLite ou PostgreSQL**. A existência desses recursos no protótipo **não significa que algum banco de dados tenha sido escolhido para a solução institucional**.

Em uma eventual continuidade do projeto, diferentes formas de armazenamento e de gestão de acesso poderão ser avaliadas pela Diretoria de Sistemas. A decisão dependerá dos requisitos da organização e não está definida neste README.

A modalidade com armazenamento compartilhado e autenticação institucional **não foi homologada como serviço de uso público**. Não se deve inferir que ela está operacional apenas porque o código contém componentes relacionados.

</div>

## 9. Referência técnica do protótipo

<div align="justify">

O código-fonte está disponível no repositório para consulta e avaliação. Seu ponto de entrada é o arquivo <code>app.py</code>, e as dependências são declaradas em <code>requirements.txt</code>.

Caso exista interesse em examinar o funcionamento em ambiente local, a execução em Python costuma envolver a instalação das dependências e a inicialização do Streamlit. A sequência abaixo é **apenas uma referência técnica**, não uma orientação de implantação institucional nem uma exigência para utilizar a demonstração já publicada.

</div>

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

<div align="justify">

A aplicação disponível na web pode ser acessada pelo navegador, sem que o visitante instale Python. A publicação de qualquer versão institucional, suas permissões e seus procedimentos operacionais constituem decisões independentes da demonstração.

</div>

## 10. Principais arquivos

| Item | Por quê |
| --- | --- |
| [`app.py`](app.py) | Apresenta a interface e coordena as ações disponíveis. |
| [`assets/estilos.css`](assets/estilos.css) | Define aparência, responsividade e estilos dos formulários. |
| [`assets/cabecalho_aprovado.png`](assets/cabecalho_aprovado.png) | Contém a imagem de identificação visual no topo da aplicação. |
| [`icms/regras.py`](icms/regras.py) | Reúne validações, normalização e cálculo do FQ. |
| [`icms/relatorios.py`](icms/relatorios.py) | Organiza resultados consolidados, consultas e CSVs. |
| [`icms/repositorio.py`](icms/repositorio.py) | Gerencia fichas, versões, histórico e backup demonstrativo. |
| [`icms/repositorio_sql.py`](icms/repositorio_sql.py) | Contém o adaptador SQL existente no código. |
| [`icms/demonstracao.py`](icms/demonstracao.py) | Trata a adequação de exemplos sintéticos antigos. |
| [`icms/edicoes.py`](icms/edicoes.py) | Auxilia a identificação de edições recuperáveis. |
| [`.streamlit/config.toml`](.streamlit/config.toml) | Define parâmetros do tema da interface. |
| [`requirements.txt`](requirements.txt) | Declara as dependências Python. |
| [`tests/`](tests/) | Reúne testes automatizados do protótipo. |
| [`levantamento_funcional/fluxograma.md`](levantamento_funcional/fluxograma.md) | Apresenta o fluxo funcional documentado. |

## 11. Limitações e pontos para avaliação

<div align="justify">

O protótipo demonstra a organização de fichas, o cadastro municipal dinâmico e o cálculo de resultados, mas não substitui a avaliação institucional de regras, responsabilidades e procedimentos.

Entre os limites identificados estão o uso público sem autenticação institucional operacional, os registros temporários da demonstração, a ausência de integração automática com o SEI e o controle de exclusividade municipal ainda não compartilhado entre sessões distintas.

A anexação de PDFs por município **não está implementada**: a interface exibe apenas um botão ilustrativo desabilitado.

A correspondência histórica de algumas referências de cálculo (E44/E60) ainda depende de confirmação da área de negócio. A apresentação atual utiliza os quatro parâmetros municipais existentes na aplicação.

</div>

---

<div align="justify">

**Síntese:** o ICMS Ecológico reúne, em um protótipo navegável, operações de cadastro, avaliação, cálculo e consolidação que hoje podem exigir controles paralelos. Seu valor principal é permitir que a área de negócio apresente concretamente a necessidade e discuta suas regras com a Diretoria de Sistemas, sem impor a adoção do software atual.

</div>
