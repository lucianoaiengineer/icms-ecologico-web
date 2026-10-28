# Backup CSV e dados sintéticos de teste

## O que foi corrigido

- O repositório de demonstração agora preserva as outras fichas ao cadastrar ou atualizar uma ficha.
- O backup CSV exporta e restaura o conteúdo completo das fichas, seu status, versão e histórico.
- Foi incluído um gerador independente de 10 ou mais fichas sintéticas. Ele não acessa a planilha oficial nem precisa descompactar o projeto.
- O CSV sintético segue o mesmo formato aceito pela opção **Restaurar fichas do CSV** no modo de demonstração.

## Arquivos que devem ser atualizados no GitHub

Publique juntos, no mesmo commit, os arquivos do pacote nestes caminhos do repositório:

- `app.py`
- `icms/regras.py`
- `icms/repositorio.py`

A correção crítica da preservação está em `icms/repositorio.py`. O arquivo `app.py` contém a interface de backup; `icms/regras.py` acompanha a versão compatível do modelo de ficha.

O script `gerar_dados_sinteticos.py` e o arquivo CSV não são necessários para executar o site. Mantenha o CSV de teste fora da base oficial e fora do GitHub; use-o somente para testar a demonstração.

## Importar o CSV de teste no site

1. Baixe `backup_fichas_icms_sinteticas.csv` para o computador. Se quiser, mova-o para `C:\Users\X4306221\Desktop\projeto\icms-ecologico`.
2. Abra o aplicativo depois que a atualização do GitHub terminar de ser implantada pelo Streamlit.
3. Entre no **Modo de demonstração**.
4. Abra **Backup temporário das fichas (CSV)**.
5. Escolha o CSV baixado em **Restaurar fichas de um backup CSV** e clique **Restaurar fichas do CSV**.
6. Consulte os registros pelos processos sintéticos ou abra **Resultados**.

As fichas trazem nomes como **MUNICÍPIO SINTÉTICO** e **NÃO OFICIAL** para não serem confundidas com dados reais. Os números de processo têm formato SEI válido apenas para permitir o teste do formulário. Não os use nem os envie para a base oficial.

## Gerar outro CSV no Google Colab

1. Baixe `gerar_dados_sinteticos.py` e envie-o para a sessão do Colab pelo painel **Arquivos → Fazer upload**.
2. Execute em uma célula:

   ```python
   %run /content/gerar_dados_sinteticos.py
   ```

3. O script cria `backup_fichas_icms_sinteticas.csv` em `/content` e inicia o download pelo navegador. Salve o arquivo baixado na pasta local do projeto.

O padrão é 10 fichas. Para gerar mais, use por exemplo:

```python
%run /content/gerar_dados_sinteticos.py --quantidade 20
```

O Colab não consegue gravar diretamente em `C:\Users\...`, que é uma pasta do computador local; o navegador baixa o CSV e então ele pode ser salvo ou movido para essa pasta.

## Persistência

No modo de demonstração, os registros ficam temporários. Baixe o backup antes de encerrar ou reiniciar a demonstração. O CSV de teste permite carregar novamente os 10 registros; para guardar alterações feitas durante o teste, baixe um backup novo antes de encerrar.
