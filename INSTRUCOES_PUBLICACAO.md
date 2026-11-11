# Publicação do layout aprovado — ICMS Ecológico

A atualização corresponde à **ficha original em Streamlit**, não a um novo sistema.
Nenhum arquivo do GitHub foi modificado automaticamente.

## Arquivos indispensáveis

- `app.py`
- `assets/estilos.css`
- `assets/cabecalho_aprovado.png` (faixa aprovada)
- `icms/regras.py`
- `.streamlit/config.toml`

O pacote **COMPLETO** contém os módulos Python, testes e documentação. O pacote
**ATUALIZACAO** inclui somente os arquivos novos ou alterados. Preserve a
hierarquia das pastas ao enviar para o GitHub; não envie os ZIPs como arquivos
isolados na raiz do repositório.

## Homologação no Streamlit

1. Faça backup das fichas de demonstração antes de publicar. Esse modo utiliza
   estado temporário e pode perder dados ao reiniciar a aplicação.
2. Confira o cabeçalho e a exibição da tabela compacta dos 14 parâmetros.
3. Confira os quatro painéis expansíveis com os títulos definidos pelo usuário.
4. Cadastre dois municípios, teste a normalização dos nomes, inclusão, remoção
   e reaproveitamento dos mesmos nomes nos outros três blocos.
5. Revise os pontos do gestor, as justificativas e os pontos validados de cada
   município e compare o FQ antes/depois.
6. Teste cadastro de rascunho, conclusão, consulta, atualização, exclusão e
   exportação dos resultados.
7. Confirme que a imagem e os estilos foram enviados às subpastas corretas.

## Verificações já realizadas

- Compilação Python: aprovada.
- Testes de domínio, relatórios, SQL de teste e estrutura: 62 aprovados.
- Renderização visual e suíte `streamlit.testing`: **não executadas** neste
  ambiente, porque Streamlit não está instalado. A aprovação visual no navegador
  permanece necessária.
- A exclusividade global de nomes municipais entre processos SEI ainda não é
  garantida entre sessões de demonstração independentes. Tratar em alteração
  específica posterior, antes de uso com registros oficiais.
