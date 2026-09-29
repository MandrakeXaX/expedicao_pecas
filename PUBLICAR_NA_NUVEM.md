# Publicar o app de expedição

Streamlit hospeda o app e oferece a URL HTTPS; Supabase guarda os pedidos e as fotos. Seu computador não precisa continuar ligado depois da publicação. Se o app local já usa o Supabase, use o MESMO projeto para manter os registros existentes.

## 1. Supabase

No projeto existente, abra o SQL Editor e execute `schema.sql` do pacote atualizado. O script cria estruturas ausentes e adiciona as colunas novas; não apaga os pedidos existentes. Confira a tabela `public.volumes` no Table Editor e o bucket privado `fotos-expedicao` em Storage.

Copie a URL do projeto na janela Connect. Em Project Settings > API Keys, use uma chave Secret (prefixo sb_secret_) exclusivamente no servidor. A configuração antiga SUPABASE_SERVICE_ROLE_KEY ainda é aceita para quem já está conectado. Não use a chave anon/publishable como chave administrativa desta versão.

## 2. GitHub

Crie um repositório para este app, por exemplo `expedicao_pecas`, e use a pasta que contém app.py como raiz. O pacote contém .gitignore para excluir o ambiente virtual e os segredos. Inclua:

- app.py, importacao.py, etiquetas.py, operacoes.py
- requirements.txt, modelo_importacao.xlsx
- schema.sql, atualizar_banco.sql
- .streamlit/config.toml e .streamlit/secrets.toml.example
- .gitignore e a documentação

Não inclua .venv ou .streamlit/secrets.toml. Se um secrets.toml já foi incluído em commits anteriores, o .gitignore não o remove do histórico; nesse caso remova o arquivo do repositório e troque a chave no Supabase.

Na pasta correta, para um repositório ainda não inicializado:

```powershell
git init
git add .
git status
git commit -m "Preparar controle de expedicao para nuvem"
git branch -M main
```

Confira `git status` antes de confirmar: secrets.toml e .venv não devem aparecer. Depois de criar o repositório vazio no GitHub, copie a URL real dele e execute os comandos abaixo, substituindo os dois campos do endereço:

```powershell
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

Se origin já existir, confira `git remote -v`. Para corrigir o endereço, use `git remote set-url origin URL_REAL`. Nunca use o repositório de outro app por engano.

## 3. Streamlit Community Cloud

Abra https://share.streamlit.io, conecte sua conta GitHub e clique Create app > Yup, I have an app. Selecione seu repositório, branch main e arquivo app.py. Escolha uma URL disponível.

Em Advanced settings, selecione Python 3.12 e preencha Secrets com os dados reais:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_SECRET_KEY = "sb_secret_SUA_CHAVE"
APP_PASSWORD = "SUA_SENHA_FORTE"
```

Se você mantém a chave antiga, cole SUPABASE_SERVICE_ROLE_KEY no lugar de SUPABASE_SECRET_KEY, como no arquivo local. Clique Save e Deploy. Não envie as chaves por chat ou screenshots.

## 4. Validar na URL publicada

Abra o link no computador e no celular. Entre com a senha do app; importe um pedido de teste e gere a etiqueta. No celular, use a câmera ou Enviar foto do QR; para leitores físicos, escolha Leitor / digitar. Tire/envie a foto da caixa e confirme. No computador, clique Atualizar dados e confira o status, abra a foto em Registros e exporte os registros filtrados. Verifique também que repetir a leitura não registra a saída duas vezes.

As fotos continuam privadas; o app gera um link temporário para consulta após o login. Os dias usam o fuso de Manaus. O painel mostra quando os dados foram consultados e oferece atualização manual; não usa sincronização automática em tempo real.

## 5. Atualizações posteriores

Depois de alterar os arquivos, execute git add, git commit e git push no repositório correto. O Streamlit acompanha as mudanças do repositório. Instalação de novas dependências pode levar mais tempo que uma alteração de código.

## Acesso e operação

Esta versão usa senha compartilhada. O responsável é informado manualmente, portanto não é uma identidade autenticada individualmente. Compartilhe URL e senha só com a equipe autorizada. Quando precisar de permissões por usuário, o próximo desenvolvimento é integrar Supabase Auth.

Se a rede cair na confirmação, o app consulta o registro e mantém a foto para não perder a evidência. Quando não consegue confirmar, pede consulta do volume antes de repetir. Fotos enviadas em tentativas inconclusivas podem ficar sem registro associado; a limpeza dessas fotos é uma tarefa administrativa posterior.

## Referências oficiais

- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- https://supabase.com/docs/guides/getting-started/api-keys
