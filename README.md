# ICMS Ecológico

**Aplicação web de gestão de fichas e cálculo do Fator de Qualidade (FQ)**

Aplicação desenvolvida em **Python e Streamlit** para organizar a análise de fichas por processo SEI, registrar pontuações municipais e reunir os resultados em um único lugar.

**Situação:** versão em desenvolvimento e homologação. A aplicação está preparada para demonstração e para persistência em banco SQL. A operação institucional com banco externo e autenticação precisa ser configurada e validada antes do uso de dados reais.

[Repositório no GitHub](https://github.com/lucianoaiengineer/icms-ecologico-web)

---

## O que é possível fazer

- **Cadastrar e consultar fichas** pelo número do processo SEI.
- **Salvar rascunhos** para continuar o preenchimento em outra ocasião, respeitando o tipo de armazenamento utilizado.
- **Revisar informações** e verificar pendências antes da conclusão.
- **Calcular o FQ** individualmente para cada município informado.
- **Atualizar ou excluir fichas**, com controle de versão e registro do histórico.
- **Consultar resultados consolidados** e exportá-los em CSV.

A consulta localiza registros **dentro da própria aplicação**. Não há conexão automática com o sistema SEI institucional.

## Como funciona uma ficha

**1. Localize o processo.** Informe o SEI no campo de busca. Se a ficha existir, seus dados serão apresentados; se não existir, o formulário será iniciado com o número informado.

**2. Preencha os dados.** Registre as informações gerais e as pontuações. Os nomes dos municípios são informados uma única vez e reutilizados nos quatro blocos municipais.

**3. Revise e grave.** Use **Revisar preenchimento** para conferir os dados sem gravá-los. Escolha **Salvar rascunho**, **Cadastrar** ou **Atualizar ficha**, conforme a situação.

**4. Consulte o resultado.** O módulo **Resultados** apresenta somente fichas concluídas. Uma ficha excluída deixa de constar da consulta e do próximo CSV exportado.

## Regras essenciais

| Assunto | Regra aplicada |
| --- | --- |
| **Processo SEI** | Identificação com 19 algarismos, normalizada no formato `0000.00.0000000/0000-00`. |
| **Parâmetros gerais** | 14 parâmetros, com pontos do gestor, justificativa e pontos validados. |
| **Municípios** | Até 13 posições, cada uma com quatro pontuações municipais. |
| **Pontuações** | Inteiros de **0 a 9**. Zero é um valor válido quando existe nome de município. |
| **Posição sem município** | Não permite pontuação, nem mesmo zero. |
| **Conclusão** | Exige os dados obrigatórios, os 14 conjuntos de pontos e ao menos um município com quatro valores. |
| **Versões** | Uma ficha concluída é atualizada como concluída. Gravações idênticas não geram nova versão. |

### Cálculo do FQ

Para cada município identificado:

```text
Soma = pontos validados dos 14 parâmetros gerais
     + quatro pontuações daquele município

FQ = Soma / pontuação da categoria
```

O resultado é arredondado para **quatro casas decimais**, com `Decimal` e `ROUND_HALF_UP`. Os pontos do gestor não entram nessa soma; a nota de um município não depende da nota dos demais.

### Relatório de resultados

O relatório e o CSV apresentam **50 colunas**, organizadas em quatro grupos:

| Grupo | Quantidade | Conteúdo |
| --- | ---: | --- |
| Identificação | 6 | Processo SEI, recebimento, unidade e demais dados de identificação. |
| Parâmetros | 18 | `PARÂM 1.1` até `PARÂM 9`, `PARÂM 10` e `PARÂM 11.1` a `11.3`. |
| Municípios | 13 | `Município1` a `Município13`. |
| Notas | 13 | `Nota1` a `Nota13`, com o FQ correspondente. |

Os 14 parâmetros gerais vêm dos **pontos validados**, não dos pontos do gestor. O `PARÂM 10` apresenta o total municipal da chave interna `10`.

**Validação ainda necessária:** o mapeamento dos três fatores finais (`11.1`, `11.2` e `11.3`) deve ser confirmado pela área responsável com as referências de cálculo institucionais. O padrão implementado utiliza o mesmo total interno para essas três colunas; isso **não deve ser confundido com aprovação da regra de negócio**.

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
| [`assets/estilos.css`](assets/estilos.css) | Define a aparência, a adaptação a diferentes telas e os atalhos laterais de navegação. |
| [`icms/regras.py`](icms/regras.py) | Contém validações, normalização do SEI e cálculo do FQ. |
| [`icms/repositorio.py`](icms/repositorio.py) | Gerencia fichas temporárias, versões, histórico e backups da demonstração. |
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

## Testes e homologação

Para executar a suíte de testes com as dependências instaladas:

```bash
python -m unittest discover -s tests -v
```

A aplicação utiliza convenções de **PEP 8**, docstrings e anotações de tipos. Isso não substitui a execução dos testes, da análise estática e da homologação no ambiente final.

Antes de utilizar dados reais, ainda é necessário conferir: regras finais dos fatores, acesso por perfil, gravação e recuperação em PostgreSQL, backup, concorrência, abertura em celular e comportamento visual dos formulários.

**Este README descreve o código preparado; não afirma que a versão já tenha sido publicada ou homologada em produção.**
