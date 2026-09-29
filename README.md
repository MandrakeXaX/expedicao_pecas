# Controle de expedição

## Atualizar sua instalação

1. Pare o app com Ctrl+C.
2. No SQL Editor do seu projeto Supabase, execute `atualizar_banco.sql` (adiciona OS/OC, cliente e peso bruto sem excluir os registros).
3. Copie `app.py`, `importacao.py`, `etiquetas.py` e `modelo_importacao.xlsx` para a pasta do app. Preserve `.streamlit/secrets.toml` e `.venv`.
4. Execute `python -m streamlit run app.py`.

## Novo modelo: uma linha por código

Colunas: pedido, volume, total_volumes, tipo, codigos, quantidade, data_pedido, ordem de serviço, nome do cliente, peso_bruto.

Repita o número do pedido e da caixa nas linhas dos códigos. O app agrupa por pedido e caixa, somando a quantidade de códigos repetidos na mesma caixa. `peso_bruto` é o peso total da caixa em kg; o app usa apenas o primeiro peso preenchido de cada pedido e volume, ignorando os campos vazios e os valores seguintes. Peso ausente aparece como “Não informado”. No modelo incluso, as linhas e os pesos são exemplos: substitua pelos dados reais.

TIPO aceita Garantia ou Venda. Datas, tipo, OS/OC e cliente podem ser informados uma vez no pedido ou repetidos sem divergências. Os volumes devem formar uma sequência completa de 1 até total_volumes. Linhas sem pedido ou com quantidade/código inválido ficam no relatório de inconsistências; pedidos com erros não são parcialmente importados. O app aceita também o modelo simples anterior e a base operacional com Nº PEDIDO, CODIGO DA PEÇAS e QTD.

A planilha enviada como exemplo possui 23 linhas completas que se tornam 19 volumes; outras 16 linhas não possuem pedido/código e precisam ser completadas. Ela não possui peso bruto: acrescente essa coluna antes de usar os pesos.

As etiquetas PDF têm 100 × 100 mm, QR por pedido/caixa, OS/OC, cliente, peso e códigos/quantidades. Até três códigos por etiqueta; códigos adicionais geram etiquetas complementares para a mesma caixa e QR. Imprima a 100% de escala.

## Primeira instalação

1. Crie um projeto Supabase e execute `schema.sql` no SQL Editor.
2. No VS Code, abra a pasta e execute:
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```
3. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`; preencha a URL do projeto, a chave service_role e APP_PASSWORD. A chave deve ficar somente no servidor e não deve ser enviada ao GitHub.
4. Execute `python -m streamlit run app.py`.

## Nuvem e celular

Publique o projeto no Streamlit Community Cloud a partir do GitHub, com app.py como entrada. Configure os três segredos no serviço de hospedagem. A URL HTTPS permite acesso ao celular e câmera (com autorização do navegador). Os dados e fotos ficam no Supabase. A senha é compartilhada e o nome do responsável é informado na expedição; contas individuais ainda não foram implementadas.

Em Executar expedição, fotografe o QR da etiqueta ou digite seu texto, tire uma foto da caixa e informe o responsável para confirmar a saída. A atualização é feita no banco para evitar expedir a mesma caixa duas vezes. Em Registros, consulte fotos e exporte os dados Excel, incluindo OS/OC, cliente, peso e dias até a saída (ou de espera).

Pedidos com qualquer volume expedido são preservados durante a reimportação. STATUS DO PEDIDO e DATA DA EMBALAGEM na base operacional não representam confirmação de expedição. Dias de espera usam DATA PEDIDO e o fuso de Manaus.

## Atualização para publicação online

Use `PUBLICAR_NA_NUVEM.md` para publicar. A atualização também adiciona `operacoes.py` e `.streamlit/config.toml`; copie esses arquivos e atualize requirements.txt. Instale as dependências novamente antes de iniciar. A nova configuração aceita SUPABASE_SECRET_KEY e mantém compatibilidade com SUPABASE_SERVICE_ROLE_KEY. O app inclui botão Atualizar dados, busca por pedido/cliente/OS, exportação filtrada e envio de fotos do QR e do volume pelo celular. A foto é convertida para JPEG antes do envio e preservada se a confirmação cair.
