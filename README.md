# Gestão de Fichas do ICMS Ecológico

## Objetivo

Cadastrar, consultar e editar fichas pelo processo SEI, calcular o Fator de
Qualidade por município e apresentar um resultado consolidado pela web.

Esta é a primeira versão de desenvolvimento. Não está publicada nem conectada
a uma conta Google. Os arquivos originais fornecidos não foram alterados.

## Estado da versão

- Interface Streamlit com Consulta/Edição, Cadastro e Resultados.
- Pontuações individuais inteiras de 0 a 9. Totais calculados.
- Categoria com padrão 89, editável. Data de análise mm/aaaa e recebimento
  com data completa do dia em Brasília, editável.
- Rascunhos, inclusão e atualização por SEI, verificação de versão e auditoria.
- FQ por município arredondado para duas casas, com vírgula na ficha.
- Repositório temporário para demonstração e adaptador Google Sheets.
- Autenticação OIDC e listas de leitores/editores no modo Google Sheets.
- Notebook para preparar e abrir a demonstração no Google Colab.

## Primeiro uso

Extraia o pacote no computador. Envie a pasta `web_icms` inteira, com todas
as subpastas, para Meu Drive. Abra `Iniciar_ICMS_Colab_v02.ipynb` no Colab.
Execute uma etapa por vez, de 1 a 4. Não use Executar tudo.
O notebook conecta o Drive, valida a estrutura e copia o código para uma pasta
temporária. Não solicita ZIP e não descompacta arquivos.
Leia `LEIA_PRIMEIRO.md` para os detalhes da correção.

O primeiro teste usa somente registros sintéticos, sem conta Google configurada.
No modo demonstração, todos os visitantes do mesmo servidor compartilham a base
temporária. Ela é apagada se o processo reiniciar. Não usar dados reais nesse modo.

## Estrutura

- `app.py`: interface, autorização e relatório de resultados.
- `icms/regras.py`: validação, valores padrão e cálculos.
- `icms/repositorio.py`: persistência e controle de versão.
- `preparar_base.py`: criação das duas abas técnicas em planilha de teste.
- `tests/`: verificações automatizadas.
- `segredos.exemplo.toml`: modelo sem credenciais reais.
- `Iniciar_ICMS_Colab_v02.ipynb`: preparação e execução no Colab.

## Persistência

A planilha Google de teste terá duas abas técnicas: `Fichas` e `Historico`.
A ficha completa é preservada em um conteúdo JSON por registro, com processo,
versão, status, autor e data também disponíveis em colunas. Essa opção reduz
gravações parciais e conserva a associação dos municípios aos parâmetros.
Não usa CSV como armazenamento. A tela Resultados é derivada das fichas
concluídas; exporta CSV sem criar outra base independente.

Esta versão usa um armazenamento técnico simples, diferente das abas normalizadas
propostas inicialmente. A equipe opera a ficha e o relatório pela aplicação.
O limite de conteúdo por célula é verificado antes da gravação. Não manipule
manualmente o JSON ou os cabeçalhos das abas técnicas.

No Sheets, a atualização da ficha e a inclusão do histórico usam uma única
chamada `spreadsheets.batchUpdate`. A verificação posterior confirma o conteúdo.
A aplicação não executa fórmulas inseridas como textos pelo usuário.

## Condições para três usuários

O objeto compartilhado pelo Streamlit mantém uma trava para as sessões de um
único processo Python. Uma versão esperada detecta edição desatualizada.
Esse mecanismo **não coordena réplicas, outro servidor ou edição direta no Sheets**.
Só haverá um servidor escrevendo nessa base; não executar o modo Sheets no Colab
simultaneamente com a publicação. Se essa condição mudar, rever a coordenação.

Uma ficha concluída não pode voltar a rascunho nesta versão. Edite e confirme
a nova conclusão; o resultado anterior permanece salvo até a atualização.
O processo não é editável depois de salvo para impedir troca acidental de chave.

## Pendências de negócio

1. Está definido E44 como total do parâmetro 10. A referência a E60 e aos três
   destinos 11.1, 11.2 e 11.3 permanece ambígua. Não foi presumida repetição nem
   substituição por três somas. A configuração `totais_resultado` permite apontar
   cada coluna ao total de um bloco depois da confirmação. Até lá, três colunas
   ficam vazias e o relatório apresenta o aviso.
2. Proposta para conclusão: SEI, unidade, datas, categoria válida, pontos do gestor
   e validados e pelo menos um município com os quatro valores preenchidos.
   Obrigatoriedade administrativa dos demais campos e justificativas ainda depende
   de aprovação. Rascunhos aceitam pontuações ausentes, mas não valores inválidos.
3. Cadastro de nomes padronizados de municípios e listas URFBio ainda não fornecido.
   Esses nomes são texto livre nesta versão; não foi inventada uma lista oficial.
4. Nas amostras, há pontos em posições sem município. A aplicação exige nome antes
   de aceitar pontuação diferente de zero. Essa regra de integridade é proposta
   e precisa ser validada com o usuário.
5. Limite de categoria 1 a 999 implementado como limite técnico inicial. Confirmar
   se existem categorias que exijam outro intervalo.

## Ativação Google Sheets — etapa posterior

Será orientada passo a passo: criar planilha de teste, configurar conta de serviço
com permissão na planilha, configurar OIDC Google e leitores/editores e publicar.
O login do usuário e a conta de serviço são configurações diferentes.
Não envie senhas nem chaves no chat. Não salve `secrets.toml` no GitHub.
Antes da publicação real, configurar segredos no painel da hospedagem e manter o
repositório e a aplicação privados. Fazer cópia de segurança e testar recuperação.

## Validação

Executar na pasta raiz: `python -m unittest discover -s tests -v`.
Os testes cobrem regras, concorrência na mesma instância e comportamentos da tela.
Ver detalhes em `VALIDACAO.md`.

Autenticação real, permissão da conta de serviço e gravação na API precisam ser
homologadas na conta autorizada. O acesso no Colab e a visualização em navegador
móvel ainda precisam ser verificados. Não é versão operacional homologada.

## Referências técnicas

- https://docs.streamlit.io/develop/concepts/connections/authentication
- https://developers.google.com/workspace/sheets/api/guides/batch
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app

Streamlit Community Cloud usa GitHub para publicar e pode hibernar sem tráfego.
O Colab é ambiente temporário de desenvolvimento e teste.
