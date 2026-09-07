# 📖 Documentação — Finance Tracker

Sistema de controle financeiro pessoal para estudantes internacionais na China,
com suporte a duas moedas (RMB/XOF), múltiplos idiomas, tema claro/escuro e
relatórios em PDF. Construído em Python com Streamlit, usando Google Sheets
como banco de dados.

---

## 1. Visão Geral

| Item | Detalhe |
|---|---|
| **Arquivo principal** | `finance_tracker.py` (single-file app) |
| **Framework de interface** | [Streamlit](https://streamlit.io) |
| **Banco de dados** | Google Sheets (via API, biblioteca `gspread`) |
| **Gráficos** | Plotly |
| **Relatórios em PDF** | `fpdf2` |
| **Moedas** | RMB (¥) como primária, XOF (Franco CFA) como secundária |
| **Idiomas** | 🇬🇧 Inglês · 🇵🇹 Português · 🇫🇷 Francês · 🇨🇳 Chinês |
| **Público-alvo** | Estudante internacional na China, uso majoritariamente no celular |

O app não usa banco de dados local nem arquivo — todos os dados (receitas,
despesas, orçamento, contas, metas e configurações) ficam salvos numa
planilha do Google Sheets escolhida por você, o que permite hospedar o app
gratuitamente sem perder dados a cada reinício.

---

## 2. Arquitetura

```
┌─────────────────────┐        ┌──────────────────────┐
│   Navegador (você)  │◄──────►│   App Streamlit        │
│  desktop ou celular │  HTTP  │  (finance_tracker.py)  │
└─────────────────────┘        └──────────┬────────────┘
                                           │ API do Google
                                           │ (gspread)
                                           ▼
                                ┌──────────────────────┐
                                │   Google Sheets        │
                                │  (6 abas = 6 tabelas)  │
                                └──────────────────────┘
```

- O Streamlit roda o script inteiro de novo a cada interação (clique,
  formulário enviado, etc.) — é assim que qualquer app Streamlit funciona.
- Toda leitura/escrita de dados passa pela camada de funções descrita na
  Seção 5, que conversa com a planilha via `gspread`.
- Não há sessão de usuário/login — qualquer pessoa com o link do app e as
  credenciais do Google Sheets acessa os mesmos dados. É pensado para uso
  **individual** (uma pessoa, uma planilha).

---

## 3. Estrutura de Arquivos

| Arquivo | Função |
|---|---|
| `finance_tracker.py` | Código completo do app (interface + lógica + acesso a dados) |
| `requirements.txt` | Dependências Python (`streamlit`, `pandas`, `plotly`, `gspread`, `google-auth`, `fpdf2`) |
| `SETUP.md` | Guia passo a passo de configuração do Google Cloud + deploy |
| `.streamlit/secrets.toml` | Credenciais (não versionar — fica só local ou no painel do Streamlit Cloud) |

---

## 4. Modelo de Dados (planilhas)

O app cria automaticamente 6 abas na primeira execução, cada uma
funcionando como uma "tabela":

### `income` (Receitas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | inteiro | Identificador único (gerado pelo app) |
| `date` | texto (AAAA-MM-DD) | Data do recebimento |
| `source` | texto | Uma das 4 fontes fixas (bolsa, remessa, freelance, outro) |
| `amount_rmb` | número | Valor em RMB |
| `notes` | texto | Observação livre |

### `expenses` (Despesas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | inteiro | Identificador único |
| `date` | texto | Data do gasto |
| `category` | texto | Uma das 10 categorias fixas (com emoji) |
| `description` | texto | Descrição livre |
| `amount_rmb` | número | Valor em RMB |
| `payment_method` | texto | Alipay / WeChat Pay / Cash / Bank Card |

### `budgets` (Orçamento)
| Coluna | Tipo | Descrição |
|---|---|---|
| `category` | texto (chave) | Mesma categoria de `expenses` |
| `limit_rmb` | número | Limite mensal definido pelo usuário |

### `bills` (Contas Fixas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | inteiro | Identificador único |
| `bill_name` | texto | Nome da conta |
| `amount_rmb` | número | Valor |
| `due_date` | texto | Data de vencimento |
| `status` | texto | `Pending` ou `Paid` |
| `date_paid` | texto | Data em que foi paga (vazio se pendente) |

### `goals` (Metas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | inteiro | Identificador único |
| `goal_name` | texto | Nome da meta |
| `target_amount` | número | Valor alvo em RMB |
| `current_amount` | número | Valor já guardado |
| `deadline` | texto | Prazo |

### `settings` (Configurações)
| Coluna | Tipo | Descrição |
|---|---|---|
| `key` | texto (chave) | Nome da configuração |
| `value` | texto | Valor (armazenado sempre como texto) |

Chaves usadas: `exchange_rate`, `savings_goal_monthly`, `theme`, `language`,
`initialized` (flag interna que evita reseeding a cada execução).

> **Observação importante:** categorias, fontes de receita, métodos de
> pagamento e status ficam **sempre gravados em inglês** na planilha
> (ex: `"🍜 Food"`), independentemente do idioma escolhido na interface. Só
> a *exibição* é traduzida (função `tr_option`). Isso evita que trocar de
> idioma quebre filtros, somas e comparações que dependem do texto exato
> salvo anteriormente.

---

## 5. Camada de Acesso a Dados

Funções centrais em `finance_tracker.py` (Seção 2 do código):

| Função | O que faz |
|---|---|
| `get_client()` / `get_spreadsheet()` | Autentica e abre a planilha (cacheado por sessão) |
| `get_ws(nome)` | Retorna a aba; cria com o cabeçalho certo se não existir |
| `fetch_df(nome)` | Lê a aba inteira e devolve um `DataFrame` do pandas, já com os tipos numéricos convertidos |
| `append_row(nome, valores)` | Adiciona uma linha nova |
| `update_full_row(nome, linha, valores)` | Sobrescreve uma linha inteira |
| `find_row_by_value(nome, coluna, valor)` | Localiza o número da linha na planilha a partir de um valor (ex: um `id`) |
| `delete_row_by_id(nome, id)` | Remove a linha correspondente |
| `next_id(nome)` | Calcula o próximo `id` disponível (maior id atual + 1) |
| `get_setting` / `set_setting` | Lê/grava uma configuração na aba `settings` |
| `ensure_workbook_ready()` | Roda uma vez por sessão: cria abas ausentes e semeia valores padrão |

Todas as operações de escrita (`append_row`, `update_full_row`,
`delete_row_by_id`, `set_setting`) refletem **imediatamente** na planilha —
não existe cache de escrita nem fila. A leitura (`fetch_df`) também é
sempre feita na hora, sem cache, para garantir que o app mostre o dado mais
recente a cada interação.

---

## 6. Funcionalidades por Página

### 🏠 Dashboard
- Saldo atual, receita/despesa/saldo líquido do mês corrente (RMB + XOF).
- Barra de progresso da meta de poupança mensal.
- Gráfico de pizza: despesas por categoria (mês corrente).
- Gráfico de linha: gasto diário ao longo do mês corrente.

### 💵 Income (Receitas)
- Formulário: data, fonte, valor, observação.
- Histórico em tabela.
- Exclusão via seletor (mostra data · fonte · valor para fácil identificação).

### 🧾 Expenses (Despesas)
- Formulário: data, categoria, descrição, valor, método de pagamento.
- Histórico em tabela.
- Edição e exclusão via seletor de entrada.

### 📊 Monthly Budget (Orçamento)
- Define limite mensal por categoria.
- Compara gasto real vs. limite, com barra de progresso colorida:
  🟢 <70% · 🟡 70–90% · 🔴 >90%.

### 📌 Bills & Fixed Costs (Contas Fixas)
- Lista de contas recorrentes (dormitório, seguro-saúde, telefone, internet
  já vêm pré-cadastrados na primeira execução).
- Alterna status Pendente/Pago por linha (registra a data automaticamente).
- Total de contas pendentes.

### 🎯 Savings & Goals (Metas)
- Cria metas com nome, valor alvo, valor já guardado e prazo.
- Cartões com barra de progresso: 🟢 ≥70% · 🟡 40–70% · 🔴 <40%.
- Botão para incrementar o valor guardado.

### 📄 Reports (Relatórios)
- Seleciona qualquer mês/ano já registrado.
- Resumo (receita, despesa, saldo, taxa de poupança), gráfico por categoria,
  maiores despesas individuais, adesão ao orçamento, status de contas e
  metas.
- Botão para baixar um **PDF** com o mesmo conteúdo, gerado na hora
  (`fpdf2`, sem serviço externo).
  - *Limitação conhecida:* o PDF usa fontes padrão (Helvetica) sem suporte
    a caracteres chineses — nesse caso o texto do PDF aparece só em
    caracteres latinos, mesmo com o app em 中文 (a tela normal do app
    continua 100% em chinês).

---

## 7. Configurações (barra lateral)

| Configuração | Onde é salva | Efeito |
|---|---|---|
| Idioma | `settings.language` | Traduz toda a interface (não afeta os dados salvos) |
| Tema (claro/escuro) | `settings.theme` | Só visual |
| Taxa de câmbio (1 RMB = ? XOF) | `settings.exchange_rate` | Usada em todas as conversões RMB→XOF exibidas |
| Meta de poupança mensal | `settings.savings_goal_monthly` | Base da barra de progresso no Dashboard |
| Exportar CSV | — | Baixa `income`/`expenses` direto do navegador |
| Abrir planilha no Google | — | Link direto para editar os dados manualmente, se precisar |

---

## 8. Segurança e Privacidade

- O app usa uma **conta de serviço do Google** (não sua conta pessoal) para
  acessar a planilha — as credenciais ficam nos "Secrets" do Streamlit
  Cloud, nunca no código-fonte nem no repositório GitHub.
- Qualquer pessoa com a URL pública do app consegue usá-lo e ver/editar os
  mesmos dados — **não há tela de login**. Se isso for uma preocupação,
  considere: (a) manter a URL do app fora de lugares públicos, ou (b)
  adicionar autenticação (ex: `streamlit-authenticator`) — não incluído por
  padrão para manter o projeto simples.
- A planilha em si tem os controles de compartilhamento normais do Google
  Drive — você pode revisar quem tem acesso a qualquer momento em
  Compartilhar → Gerenciar acesso.

---

## 9. Limitações Conhecidas

| Limitação | Detalhe |
|---|---|
| Sem autenticação de usuário | Qualquer um com o link acessa os mesmos dados |
| Um usuário por planilha | Não foi desenhado para múltiplos usuários simultâneos com dados separados |
| Cota da API do Google Sheets | 60 leituras e 60 escritas por minuto por usuário (gratuito) — suficiente para uso pessoal normal |
| PDF sem suporte a chinês | Ver Seção 6 → Reports |
| Sem exclusão em massa | Exclusões são feitas uma entrada por vez |
| Sem anexos/comprovantes | O app guarda só valores e texto, não imagens de recibos |

---

## 10. Instalação e Deploy

Guia completo em **`SETUP.md`**. Resumo:

1. Criar projeto no Google Cloud + ativar Sheets API e Drive API.
2. Criar conta de serviço + baixar chave `.json`.
3. Criar a planilha e compartilhar com o e-mail da conta de serviço.
4. Preencher `secrets.toml` com as credenciais + ID da planilha.
5. Subir `finance_tracker.py` e `requirements.txt` para o GitHub.
6. Deploy gratuito em [share.streamlit.io](https://share.streamlit.io)
   (Streamlit Community Cloud), colando os secrets no painel do app.

---

## 11. Solução de Problemas

| Sintoma | Causa provável | Onde resolver |
|---|---|---|
| "⚠️ Could not connect to Google Sheets" | Secrets ausentes/errados ou planilha não compartilhada | `SETUP.md`, Seção 3 |
| Categoria/fonte aparece em inglês mesmo com idioma trocado | Comportamento esperado — só a exibição traduz, o dado salvo é sempre em inglês | Seção 4 (nota) |
| Valor de câmbio ou meta "sumiu" e voltou ao padrão | Célula da planilha ficou vazia/corrompida — o app tem um *fallback* automático para o padrão | Editar de novo em ⚙️ Configurações |
| App lento ao carregar | Normal na primeira abertura de cada sessão (cria/verifica as 6 abas uma vez) | — |
| PDF com texto chinês faltando | Limitação conhecida das fontes padrão do gerador de PDF | Ver Seção 6 |

---

## 12. Possíveis Melhorias Futuras

- Autenticação de usuário (login) para uso multi-pessoa com dados isolados.
- Upload de foto/comprovante junto com cada despesa.
- Notificações de conta próxima do vencimento.
- Suporte a mais moedas além de RMB/XOF.
- Fonte Unicode embutida no PDF para suportar 中文 no relatório exportado.
- Categorias/fontes/métodos de pagamento personalizáveis pelo usuário (hoje
  são fixos no código).

---

## 13. Glossário Rápido

- **RMB (¥)** — Yuan chinês, moeda primária do app.
- **XOF** — Franco CFA da África Ocidental, moeda secundária.
- **`gspread`** — biblioteca Python usada para ler/escrever no Google Sheets.
- **Service account (conta de serviço)** — identidade do Google usada pelo
  app para acessar a planilha sem precisar da sua senha pessoal.
- **Secrets** — credenciais sensíveis guardadas fora do código, injetadas
  pelo Streamlit em tempo de execução.
