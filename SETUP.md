# 🚀 SETUP.md — Finance Tracker com Supabase (grátis)

Tempo estimado: ~15 minutos. Custo: R$ 0 (planos gratuitos do Supabase,
GitHub e Streamlit Community Cloud).

---

## Passo 1 — Criar o projeto no Supabase

1. Acesse **supabase.com** → *Start your project* → entre com GitHub ou e-mail.
2. *New project* → escolha um nome (ex: `finance-tracker`), defina uma **senha
   do banco** (guarde-a, mas o app não usa) e escolha a região mais próxima de você.
3. Aguarde ~1–2 minutos até o projeto ficar pronto.

## Passo 2 — Criar as tabelas

1. No menu lateral: **SQL Editor → New query**.
2. Abra o arquivo `supabase_schema.sql`, copie **todo** o conteúdo, cole e clique **Run**.
3. Em **Table Editor** você deve ver 6 tabelas: `income`, `expenses`,
   `budgets`, `bills`, `goals`, `settings`.

> O script é seguro para rodar de novo (usa `IF NOT EXISTS`). Ele também
> ativa **Row Level Security** sem políticas: a chave pública não consegue
> ler nem gravar nada — só o seu app, com a chave secreta.

## Passo 3 — Pegar a URL e a chave secreta

1. **Project Settings → API Keys** (ou *Connect*).
2. Copie a **Project URL** (`https://xxxxxxxx.supabase.co`).
3. Na aba **Publishable and secret API keys**, copie a **Secret key**
   (`sb_secret_...`). Se não houver, clique em *Create new API keys*.
   - Projetos antigos ainda aceitam a chave legada `service_role`, mas o
     Supabase informa que as chaves legadas serão descontinuadas até o fim
     de 2026 — prefira a *secret key*.

⚠️ **A secret key dá acesso total ao banco.** Nunca a coloque no GitHub, em
prints ou em código de navegador. Ela só vai nos *secrets* do Streamlit.

## Passo 4 — Testar no seu computador (recomendado)

```bash
pip install -r requirements.txt
mkdir -p .streamlit
```

Crie o arquivo `.streamlit/secrets.toml`:

```toml
supabase_url = "https://xxxxxxxx.supabase.co"
supabase_key = "sb_secret_xxxxxxxxxxxxxxxxxxxx"
```

```bash
streamlit run finance_tracker.py
```

Na primeira execução o app grava os valores padrão (taxa 1 RMB = 85 XOF,
10 categorias de orçamento e 4 contas fixas). Se aparecer o aviso
"⚠️ Could not connect to Supabase", veja a tabela de problemas abaixo.

## Passo 5 — Subir para o GitHub

1. Crie um repositório e envie: `finance_tracker.py`, `requirements.txt`
   (e, opcionalmente, `supabase_schema.sql`, `tests/` e a documentação).
2. **Não envie** `.streamlit/secrets.toml`. Crie um `.gitignore` com:
   ```
   .streamlit/secrets.toml
   .venv/
   __pycache__/
   ```

## Passo 6 — Publicar no Streamlit Community Cloud

1. Acesse **share.streamlit.io** → entre com o GitHub → **New app**.
2. Escolha o repositório, a branch (`main`) e o arquivo `finance_tracker.py`.
3. Antes de clicar em *Deploy*, abra **Advanced settings → Secrets** e cole:
   ```toml
   supabase_url = "https://xxxxxxxx.supabase.co"
   supabase_key = "sb_secret_xxxxxxxxxxxxxxxxxxxx"
   ```
4. *Deploy*. Em 1–3 minutos você recebe um link `https://seu-app.streamlit.app`.
   Abra-o no celular e use *Adicionar à tela inicial* para virar um "app".

> Na China continental, a disponibilidade de `streamlit.app` e do painel do
> Supabase pode variar conforme a rede. Teste no seu celular, com os dados
> móveis e com o Wi-Fi da universidade, antes de depender dele.

---

## ⏸️ Importante: o plano gratuito pausa projetos inativos

No plano *Free*, o Supabase **pausa o projeto após 7 dias sem atividade**. Os
dados **não são apagados** — você só precisa clicar em *Restore project* no
painel. Enquanto estiver pausado, o app mostra o aviso de erro de conexão.

Duas formas de evitar:

1. **Usar o app pelo menos 1 vez por semana** (qualquer acesso conta).
2. **Ping automático (grátis):** coloque o arquivo `keepalive.yml` em
   `.github/workflows/keepalive.yml` no seu repositório e cadastre dois
   *secrets* em GitHub → Settings → Secrets and variables → Actions:
   - `SUPABASE_URL` — a Project URL
   - `SUPABASE_PUBLISHABLE_KEY` — a chave `sb_publishable_...` (**não** a secreta)

   Ele faz uma requisição a cada 3 dias. Observação: o GitHub pode desativar
   workflows agendados em repositórios sem nenhuma atividade por ~60 dias;
   se isso acontecer, é só reativar na aba *Actions*.

---

## 🔄 Migrar dados do Google Sheets (se você já usou a versão anterior)

1. Na planilha, abra cada aba (`income`, `expenses`, `bills`, `goals`,
   `budgets`, `settings`) → *Arquivo → Fazer download → CSV*.
2. No Supabase: **Table Editor → (tabela) → Insert → Import data from CSV**.
3. As colunas têm os mesmos nomes. Para `income`, `expenses`, `bills` e
   `goals`, mantenha a coluna `id` do CSV (o Postgres continua a numeração
   depois). Para `settings`, importe antes de abrir o app, ou apague a linha
   `initialized` para o app recriar os padrões.

---

## 🧯 Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| "Could not connect to Supabase" logo no início | URL/chave erradas nos secrets | Confira `supabase_url` (sem barra no final) e `supabase_key` |
| Mesmo aviso, mas os secrets estão certos | Projeto pausado (plano grátis, 7 dias) | Painel do Supabase → *Restore project* |
| `relation "public.income" does not exist` | `supabase_schema.sql` não foi executado | Passo 2 |
| `permission denied for table ...` | Faltam as permissões do papel de servidor | Rode de novo o bloco *Security* do `supabase_schema.sql` (GRANTs) |
| `Unregistered API key` / `Invalid API key` | URL e chave pertencem a projetos diferentes, chave copiada incompleta, ou chave *publishable* no lugar da *secret* | Em **Project Settings → API Keys**, copie a **Project URL** e a **Secret key** do mesmo projeto; atualize os secrets do Streamlit e reinicie/reimplante o app |
| Erro de `use_container_width` / `width` | Streamlit antigo | `pip install -U streamlit` (requirements pede `>=1.66`) |
| Dados "sumiram" depois de um tempo | Projeto novo/diferente nos secrets | Confirme que a URL aponta para o mesmo projeto de antes |

---

## Atualizar o app depois

Qualquer `git push` no repositório atualiza o app automaticamente no
Streamlit Cloud. Os dados ficam no Supabase, então nada se perde em
reinícios ou novos deploys.

## Rodar os testes automáticos (opcional)

```bash
python tests/e2e_test.py
```
Não precisa de conta nem de internet: usa um Supabase simulado em memória e
percorre todas as páginas, os 4 idiomas, criação/edição/exclusão e o PDF.
