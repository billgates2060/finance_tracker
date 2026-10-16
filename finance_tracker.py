"""
================================================================================
 PERSONAL FINANCE TRACKER — for International Students in China
 Streamlit + Pandas + Plotly + Supabase (free Postgres) + fpdf2 (PDF reports)
 Multi-language: English / Português / Français / 中文 · Mobile-first design
================================================================================
SETUP REQUIRED BEFORE RUNNING — see SETUP.md:
    1) Create a free project at https://supabase.com
    2) Run `supabase_schema.sql` in Supabase -> SQL Editor (creates 6 tables).
    3) Put your Project URL + SECRET key in Streamlit "secrets":
           supabase_url = "https://xxxx.supabase.co"
           supabase_key = "sb_secret_..."
       (locally: .streamlit/secrets.toml — on Streamlit Cloud: app Settings ->
       Secrets). NEVER commit this key or put it in client-side code.

HOW TO RUN LOCALLY:
    pip install -r requirements.txt
    streamlit run finance_tracker.py
================================================================================
"""

import datetime

from supabase import create_client

import pandas as pd
import plotly.express as px
import streamlit as st
from fpdf import FPDF

# ==============================================================================
# 0. PAGE CONFIG
#    initial_sidebar_state="auto" -> expanded on desktop, collapsed on phones.
#    Forcing "expanded" would cover the whole screen with the sidebar on
#    first load on mobile, which is the opposite of mobile-first.
# ==============================================================================
st.set_page_config(
    page_title="Finance Tracker | Study in China 🇨🇳",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="auto",
)

TABLE_SCHEMAS = {
    "income":   ["id", "date", "source", "amount_rmb", "notes"],
    "expenses": ["id", "date", "category", "description", "amount_rmb", "payment_method"],
    "budgets":  ["category", "limit_rmb"],
    "bills":    ["id", "bill_name", "amount_rmb", "due_date", "status", "date_paid"],
    "goals":    ["id", "goal_name", "target_amount", "current_amount", "deadline"],
    "settings": ["key", "value"],
}
NUMERIC_COLUMNS = {
    "income": ["amount_rmb"], "expenses": ["amount_rmb"], "budgets": ["limit_rmb"],
    "bills": ["amount_rmb"], "goals": ["target_amount", "current_amount"], "settings": [],
}

# Canonical (stored) values never change with language — only their on-screen labels do.
EXPENSE_CATEGORIES = [
    "🍜 Food", "🚌 Transport", "📱 Communication", "🛒 Supermarket",
    "👕 Clothing", "💊 Health", "📚 Study Materials", "🎮 Leisure",
    "✈️ Travel", "🎁 Gifts/Misc",
]
INCOME_SOURCES = [
    "Scholarship Stipend", "Family Remittance via Western Union",
    "Freelance/Online Work", "Other",
]
PAYMENT_METHODS = ["Alipay", "WeChat Pay", "Cash", "Bank Card"]
BILL_STATUSES = ["Pending", "Paid"]

LANGUAGES = {"en": "🇬🇧 English", "pt": "🇵🇹 Português", "fr": "🇫🇷 Français", "zh": "🇨🇳 中文"}

# ==============================================================================
# 1. TRANSLATION TABLES
# ==============================================================================
CATEGORY_TR = {
    "🍜 Food": {"pt": "🍜 Alimentação", "fr": "🍜 Nourriture", "zh": "🍜 餐饮"},
    "🚌 Transport": {"pt": "🚌 Transporte", "fr": "🚌 Transport", "zh": "🚌 交通"},
    "📱 Communication": {"pt": "📱 Comunicação", "fr": "📱 Communication", "zh": "📱 通讯"},
    "🛒 Supermarket": {"pt": "🛒 Supermercado", "fr": "🛒 Supermarché", "zh": "🛒 超市"},
    "👕 Clothing": {"pt": "👕 Vestuário", "fr": "👕 Vêtements", "zh": "👕 服装"},
    "💊 Health": {"pt": "💊 Saúde", "fr": "💊 Santé", "zh": "💊 健康"},
    "📚 Study Materials": {"pt": "📚 Material de Estudo", "fr": "📚 Matériel d'étude", "zh": "📚 学习用品"},
    "🎮 Leisure": {"pt": "🎮 Lazer", "fr": "🎮 Loisirs", "zh": "🎮 休闲"},
    "✈️ Travel": {"pt": "✈️ Viagem", "fr": "✈️ Voyage", "zh": "✈️ 旅行"},
    "🎁 Gifts/Misc": {"pt": "🎁 Presentes/Outros", "fr": "🎁 Cadeaux/Divers", "zh": "🎁 礼物/其他"},
}
SOURCE_TR = {
    "Scholarship Stipend": {"pt": "Bolsa de Estudos", "fr": "Bourse d'études", "zh": "奖学金"},
    "Family Remittance via Western Union": {
        "pt": "Remessa Familiar via Western Union",
        "fr": "Envoi familial via Western Union",
        "zh": "家庭汇款（西联汇款）",
    },
    "Freelance/Online Work": {"pt": "Freelance/Trabalho Online", "fr": "Freelance / Travail en ligne", "zh": "自由职业/网络工作"},
    "Other": {"pt": "Outro", "fr": "Autre", "zh": "其他"},
}
PAYMENT_TR = {
    "Alipay": {"pt": "Alipay", "fr": "Alipay", "zh": "支付宝"},
    "WeChat Pay": {"pt": "WeChat Pay", "fr": "WeChat Pay", "zh": "微信支付"},
    "Cash": {"pt": "Dinheiro", "fr": "Espèces", "zh": "现金"},
    "Bank Card": {"pt": "Cartão Bancário", "fr": "Carte bancaire", "zh": "银行卡"},
}
STATUS_TR = {
    "Pending": {"pt": "Pendente", "fr": "En attente", "zh": "待付"},
    "Paid": {"pt": "Pago", "fr": "Payé", "zh": "已付"},
}
MONTH_NAMES = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "pt": ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
           "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"],
    "fr": ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
           "Août", "Septembre", "Octobre", "Novembre", "Décembre"],
    "zh": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
}

STRINGS = {
    "brand_title": {"en": "💰 Finance Tracker", "pt": "💰 Controle Financeiro", "fr": "💰 Suivi Financier", "zh": "💰 财务管家"},
    "brand_subtitle": {"en": "For international students in China 🇨🇳", "pt": "Para estudantes internacionais na China 🇨🇳", "fr": "Pour étudiants internationaux en Chine 🇨🇳", "zh": "为在华留学生打造 🇨🇳"},
    "nav_dashboard": {"en": "Dashboard", "pt": "Painel", "fr": "Tableau de bord", "zh": "仪表盘"},
    "nav_income": {"en": "Income", "pt": "Receitas", "fr": "Revenus", "zh": "收入"},
    "nav_expenses": {"en": "Expenses", "pt": "Despesas", "fr": "Dépenses", "zh": "支出"},
    "nav_budget": {"en": "Monthly Budget", "pt": "Orçamento Mensal", "fr": "Budget Mensuel", "zh": "月度预算"},
    "nav_bills": {"en": "Bills & Fixed Costs", "pt": "Contas Fixas", "fr": "Factures Fixes", "zh": "账单"},
    "nav_goals": {"en": "Savings & Goals", "pt": "Metas e Economia", "fr": "Épargne & Objectifs", "zh": "储蓄目标"},
    "nav_reports": {"en": "Reports", "pt": "Relatórios", "fr": "Rapports", "zh": "报告"},
    "settings_header": {"en": "⚙️ Settings", "pt": "⚙️ Configurações", "fr": "⚙️ Paramètres", "zh": "⚙️ 设置"},
    "language_label": {"en": "🌐 Language", "pt": "🌐 Idioma", "fr": "🌐 Langue", "zh": "🌐 语言"},
    "theme_label": {"en": "🌓 Theme", "pt": "🌓 Tema", "fr": "🌓 Thème", "zh": "🌓 主题"},
    "theme_light": {"en": "Light", "pt": "Claro", "fr": "Clair", "zh": "浅色"},
    "theme_dark": {"en": "Dark", "pt": "Escuro", "fr": "Sombre", "zh": "深色"},
    "rate_label": {"en": "💱 Exchange rate (1 RMB = ? XOF)", "pt": "💱 Taxa de câmbio (1 RMB = ? XOF)", "fr": "💱 Taux de change (1 RMB = ? XOF)", "zh": "💱 汇率（1 元 = ? 西非法郎）"},
    "rate_btn": {"en": "Update exchange rate", "pt": "Atualizar taxa de câmbio", "fr": "Mettre à jour le taux", "zh": "更新汇率"},
    "rate_updated": {"en": "Rate updated: 1 RMB = {rate} XOF", "pt": "Taxa atualizada: 1 RMB = {rate} XOF", "fr": "Taux mis à jour : 1 RMB = {rate} XOF", "zh": "汇率已更新：1 元 = {rate} 西非法郎"},
    "goal_label": {"en": "🎯 Monthly savings goal (RMB)", "pt": "🎯 Meta de poupança mensal (RMB)", "fr": "🎯 Objectif d'épargne mensuel (RMB)", "zh": "🎯 每月储蓄目标（元）"},
    "goal_btn": {"en": "Update savings goal", "pt": "Atualizar meta de poupança", "fr": "Mettre à jour l'objectif", "zh": "更新储蓄目标"},
    "goal_updated": {"en": "Savings goal updated!", "pt": "Meta de poupança atualizada!", "fr": "Objectif d'épargne mis à jour !", "zh": "储蓄目标已更新！"},
    "export_header": {"en": "📤 Export Data", "pt": "📤 Exportar Dados", "fr": "📤 Exporter les données", "zh": "📤 导出数据"},
    "income_csv": {"en": "Income CSV", "pt": "CSV de Receitas", "fr": "CSV Revenus", "zh": "收入 CSV"},
    "expenses_csv": {"en": "Expenses CSV", "pt": "CSV de Despesas", "fr": "CSV Dépenses", "zh": "支出 CSV"},
    "open_sheet": {"en": "📄 Open Supabase Dashboard", "pt": "📄 Abrir Painel do Supabase", "fr": "📄 Ouvrir le Tableau Supabase", "zh": "📄 打开 Supabase 控制台"},
    "tip": {"en": "💡 Tip: enter all amounts in RMB (¥). The app converts to XOF automatically.", "pt": "💡 Dica: digite todos os valores em RMB (¥). O app converte para XOF automaticamente.", "fr": "💡 Astuce : saisissez les montants en RMB (¥). L'app convertit en XOF automatiquement.", "zh": "💡 提示：请以人民币（¥）输入金额，系统会自动换算为西非法郎。"},
    "footer": {"en": "Made for students studying abroad 🎓 · Data stored in Supabase", "pt": "Feito para estudantes no exterior 🎓 · Dados salvos no Supabase", "fr": "Conçu pour les étudiants à l'étranger 🎓 · Données sur Supabase", "zh": "为留学生打造 🎓 · 数据保存在 Supabase"},
    "greet_morning": {"en": "Good morning ☀️", "pt": "Bom dia ☀️", "fr": "Bonjour ☀️", "zh": "早上好 ☀️"},
    "greet_afternoon": {"en": "Good afternoon 🌤️", "pt": "Boa tarde 🌤️", "fr": "Bon après-midi 🌤️", "zh": "下午好 🌤️"},
    "greet_evening": {"en": "Good evening 🌙", "pt": "Boa noite 🌙", "fr": "Bonsoir 🌙", "zh": "晚上好 🌙"},
    "select_placeholder": {"en": "— Select —", "pt": "— Selecionar —", "fr": "— Sélectionner —", "zh": "— 请选择 —"},

    "dash_title": {"en": "Dashboard", "pt": "Painel Geral", "fr": "Tableau de bord", "zh": "仪表盘"},
    "dash_overview": {"en": "Overview for {month} · 1 RMB = {rate} XOF", "pt": "Resumo de {month} · 1 RMB = {rate} XOF", "fr": "Aperçu de {month} · 1 RMB = {rate} XOF", "zh": "{month}概览 · 1 元 = {rate} 西非法郎"},
    "kpi_balance": {"en": "Current Balance", "pt": "Saldo Atual", "fr": "Solde Actuel", "zh": "当前余额"},
    "kpi_income_month": {"en": "Income (This Month)", "pt": "Receitas (Este Mês)", "fr": "Revenus (Ce Mois)", "zh": "本月收入"},
    "kpi_expenses_month": {"en": "Expenses (This Month)", "pt": "Despesas (Este Mês)", "fr": "Dépenses (Ce Mois)", "zh": "本月支出"},
    "kpi_net_month": {"en": "Net This Month", "pt": "Saldo Líquido do Mês", "fr": "Net Ce Mois", "zh": "本月结余"},
    "savings_progress_title": {"en": "🎯 Monthly Savings Goal Progress", "pt": "🎯 Progresso da Meta de Poupança", "fr": "🎯 Progression de l'objectif d'épargne", "zh": "🎯 月度储蓄目标进度"},
    "of_target": {"en": "of {target}", "pt": "de {target}", "fr": "sur {target}", "zh": "/ {target}"},
    "chart_expenses_by_cat": {"en": "🥧 Expenses by Category", "pt": "🥧 Despesas por Categoria", "fr": "🥧 Dépenses par Catégorie", "zh": "🥧 按类别支出"},
    "chart_daily_trend": {"en": "📈 Daily Spending Trend", "pt": "📈 Tendência de Gastos Diários", "fr": "📈 Tendance des Dépenses Quotidiennes", "zh": "📈 每日支出趋势"},
    "no_expenses_month": {"en": "No expenses recorded this month yet. Add some in the Expenses tab!", "pt": "Ainda não há despesas este mês. Adicione na aba Despesas!", "fr": "Aucune dépense ce mois-ci. Ajoutez-en dans l'onglet Dépenses !", "zh": "本月暂无支出记录，去支出页面添加吧！"},
    "no_daily_data": {"en": "No daily spending data yet this month.", "pt": "Ainda não há dados diários este mês.", "fr": "Aucune donnée quotidienne ce mois-ci.", "zh": "本月暂无每日数据。"},

    "income_title": {"en": "Income", "pt": "Receitas", "fr": "Revenus", "zh": "收入"},
    "income_caption": {"en": "Track scholarships, remittances, freelance income, and more.", "pt": "Acompanhe bolsas, remessas, trabalhos freelance e mais.", "fr": "Suivez bourses, envois de fonds, freelance et plus.", "zh": "记录奖学金、汇款、自由职业收入等。"},
    "add_income": {"en": "➕ Add New Income", "pt": "➕ Adicionar Nova Receita", "fr": "➕ Ajouter un Revenu", "zh": "➕ 添加收入"},
    "date_label": {"en": "Date", "pt": "Data", "fr": "Date", "zh": "日期"},
    "source_label": {"en": "Source", "pt": "Fonte", "fr": "Source", "zh": "来源"},
    "amount_label": {"en": "Amount (RMB)", "pt": "Valor (RMB)", "fr": "Montant (RMB)", "zh": "金额（元）"},
    "notes_label": {"en": "Notes (optional)", "pt": "Notas (opcional)", "fr": "Notes (optionnel)", "zh": "备注（可选）"},
    "save_income": {"en": "💾 Save Income", "pt": "💾 Salvar Receita", "fr": "💾 Enregistrer", "zh": "💾 保存收入"},
    "amount_error": {"en": "Please enter an amount greater than 0.", "pt": "Digite um valor maior que 0.", "fr": "Veuillez saisir un montant supérieur à 0.", "zh": "请输入大于 0 的金额。"},
    "income_added": {"en": "Added {amount} from {source}!", "pt": "Adicionado {amount} de {source}!", "fr": "Ajouté {amount} de {source} !", "zh": "已添加来自{source}的{amount}！"},
    "income_history": {"en": "📋 Income History", "pt": "📋 Histórico de Receitas", "fr": "📋 Historique des Revenus", "zh": "📋 收入记录"},
    "no_income": {"en": "No income recorded yet.", "pt": "Nenhuma receita registrada ainda.", "fr": "Aucun revenu enregistré.", "zh": "暂无收入记录。"},
    "select_delete_entry": {"en": "Select entry to delete", "pt": "Selecione a entrada para excluir", "fr": "Sélectionnez l'entrée à supprimer", "zh": "选择要删除的条目"},
    "delete_income_btn": {"en": "🗑️ Delete Selected Income Entry", "pt": "🗑️ Excluir Receita Selecionada", "fr": "🗑️ Supprimer le Revenu Sélectionné", "zh": "🗑️ 删除所选收入"},
    "entry_deleted": {"en": "Entry deleted.", "pt": "Entrada excluída.", "fr": "Entrée supprimée.", "zh": "已删除。"},

    "expenses_title": {"en": "Expenses", "pt": "Despesas", "fr": "Dépenses", "zh": "支出"},
    "expenses_caption": {"en": "Log your daily spending across categories and payment methods.", "pt": "Registre seus gastos diários por categoria e método de pagamento.", "fr": "Enregistrez vos dépenses par catégorie et mode de paiement.", "zh": "按类别和支付方式记录每日支出。"},
    "add_expense": {"en": "➕ Add New Expense", "pt": "➕ Adicionar Nova Despesa", "fr": "➕ Ajouter une Dépense", "zh": "➕ 添加支出"},
    "category_label": {"en": "Category", "pt": "Categoria", "fr": "Catégorie", "zh": "类别"},
    "description_label": {"en": "Description", "pt": "Descrição", "fr": "Description", "zh": "描述"},
    "payment_method_label": {"en": "Payment Method", "pt": "Método de Pagamento", "fr": "Mode de Paiement", "zh": "支付方式"},
    "save_expense": {"en": "💾 Save Expense", "pt": "💾 Salvar Despesa", "fr": "💾 Enregistrer", "zh": "💾 保存支出"},
    "expense_added": {"en": "Added {amount} for {category}!", "pt": "Adicionado {amount} em {category}!", "fr": "Ajouté {amount} pour {category} !", "zh": "已添加{category}支出{amount}！"},
    "expense_history": {"en": "📋 Expense History", "pt": "📋 Histórico de Despesas", "fr": "📋 Historique des Dépenses", "zh": "📋 支出记录"},
    "no_expenses_hist": {"en": "No expenses recorded yet.", "pt": "Nenhuma despesa registrada ainda.", "fr": "Aucune dépense enregistrée.", "zh": "暂无支出记录。"},
    "edit_delete_header": {"en": "✏️ Edit or 🗑️ Delete an Entry", "pt": "✏️ Editar ou 🗑️ Excluir uma Entrada", "fr": "✏️ Modifier ou 🗑️ Supprimer une Entrée", "zh": "✏️ 编辑或 🗑️ 删除条目"},
    "select_entry": {"en": "Select entry", "pt": "Selecione a entrada", "fr": "Sélectionnez l'entrée", "zh": "选择条目"},
    "update_entry": {"en": "✏️ Update Entry", "pt": "✏️ Atualizar Entrada", "fr": "✏️ Mettre à Jour", "zh": "✏️ 更新条目"},
    "delete_entry": {"en": "🗑️ Delete Entry", "pt": "🗑️ Excluir Entrada", "fr": "🗑️ Supprimer", "zh": "🗑️ 删除条目"},
    "entry_updated": {"en": "Entry updated!", "pt": "Entrada atualizada!", "fr": "Entrée mise à jour !", "zh": "已更新！"},

    "budget_title": {"en": "Monthly Budget", "pt": "Orçamento Mensal", "fr": "Budget Mensuel", "zh": "月度预算"},
    "budget_caption": {"en": "Set spending limits per category and track progress in real time.", "pt": "Defina limites de gastos por categoria e acompanhe em tempo real.", "fr": "Définissez des limites par catégorie et suivez-les en temps réel.", "zh": "为每个类别设置支出限额并实时追踪。"},
    "set_budget": {"en": "⚙️ Set / Update Budget Limits", "pt": "⚙️ Definir / Atualizar Limites", "fr": "⚙️ Définir / Mettre à Jour les Limites", "zh": "⚙️ 设置/更新预算限额"},
    "limit_suffix": {"en": "limit (RMB)", "pt": "limite (RMB)", "fr": "limite (RMB)", "zh": "限额（元）"},
    "save_budgets": {"en": "💾 Save All Budgets", "pt": "💾 Salvar Orçamentos", "fr": "💾 Enregistrer les Budgets", "zh": "💾 保存预算"},
    "budgets_updated": {"en": "Budgets updated!", "pt": "Orçamentos atualizados!", "fr": "Budgets mis à jour !", "zh": "预算已更新！"},
    "budget_vs_actual": {"en": "📉 Budget vs. Actual — {month}", "pt": "📉 Orçado vs. Real — {month}", "fr": "📉 Budget vs Réel — {month}", "zh": "📉 预算与实际支出 — {month}"},
    "no_limit": {"en": "No limit set", "pt": "Sem limite definido", "fr": "Aucune limite définie", "zh": "未设置限额"},
    "budget_legend": {"en": "🟢 Under 70% · 🟡 70–90% · 🔴 Over 90% of your limit.", "pt": "🟢 Abaixo de 70% · 🟡 70–90% · 🔴 Acima de 90% do limite.", "fr": "🟢 Moins de 70% · 🟡 70–90% · 🔴 Plus de 90% de la limite.", "zh": "🟢 低于70% · 🟡 70–90% · 🔴 超过90%限额"},

    "bills_title": {"en": "Bills & Fixed Costs", "pt": "Contas Fixas", "fr": "Factures Fixes", "zh": "固定账单"},
    "bills_caption": {"en": "Track recurring dormitory, insurance, phone, and internet payments.", "pt": "Acompanhe dormitório, seguro, telefone e internet.", "fr": "Suivez logement, assurance, téléphone et internet.", "zh": "追踪宿舍费、保险、话费和网费等固定支出。"},
    "add_bill": {"en": "➕ Add New Bill", "pt": "➕ Adicionar Nova Conta", "fr": "➕ Ajouter une Facture", "zh": "➕ 添加账单"},
    "bill_name_label": {"en": "Bill Name (e.g., Dormitory Fee)", "pt": "Nome da Conta (ex: Dormitório)", "fr": "Nom de la Facture (ex: Logement)", "zh": "账单名称（如：宿舍费）"},
    "due_date_label": {"en": "Due Date", "pt": "Data de Vencimento", "fr": "Date d'Échéance", "zh": "到期日"},
    "status_label": {"en": "Status", "pt": "Status", "fr": "Statut", "zh": "状态"},
    "date_paid_label": {"en": "Date Paid", "pt": "Data de Pagamento", "fr": "Date de Paiement", "zh": "支付日期"},
    "save_bill": {"en": "💾 Save Bill", "pt": "💾 Salvar Conta", "fr": "💾 Enregistrer", "zh": "💾 保存账单"},
    "bill_error": {"en": "Please provide a bill name and a valid amount.", "pt": "Informe o nome da conta e um valor válido.", "fr": "Veuillez indiquer un nom et un montant valide.", "zh": "请填写账单名称和有效金额。"},
    "bill_added": {"en": "Bill '{name}' added!", "pt": "Conta '{name}' adicionada!", "fr": "Facture '{name}' ajoutée !", "zh": "账单“{name}”已添加！"},
    "bills_checklist": {"en": "📋 Bills Checklist", "pt": "📋 Lista de Contas", "fr": "📋 Liste des Factures", "zh": "📋 账单清单"},
    "no_bills": {"en": "No bills tracked yet.", "pt": "Nenhuma conta cadastrada ainda.", "fr": "Aucune facture enregistrée.", "zh": "暂无账单记录。"},
    "due_prefix": {"en": "Due", "pt": "Vence", "fr": "Échéance", "zh": "到期"},
    "total_pending": {"en": "Total Pending Bills", "pt": "Total de Contas Pendentes", "fr": "Total des Factures en Attente", "zh": "待付账单总额"},

    "goals_title": {"en": "Savings & Goals", "pt": "Metas e Economia", "fr": "Épargne & Objectifs", "zh": "储蓄目标"},
    "goals_caption": {"en": "Set targets like 'New Laptop' or 'Trip to Beijing' and track progress.", "pt": "Defina metas como 'Novo Laptop' ou 'Viagem a Pequim' e acompanhe.", "fr": "Définissez des objectifs comme 'Nouvel Ordinateur' ou 'Voyage à Pékin'.", "zh": "设定“新笔记本电脑”或“北京之旅”等目标并追踪进度。"},
    "add_goal": {"en": "➕ Add New Goal", "pt": "➕ Adicionar Nova Meta", "fr": "➕ Ajouter un Objectif", "zh": "➕ 添加目标"},
    "goal_name_label": {"en": "Goal Name (e.g., New Laptop)", "pt": "Nome da Meta (ex: Novo Laptop)", "fr": "Nom de l'Objectif (ex: Nouvel Ordinateur)", "zh": "目标名称（如：新笔记本电脑）"},
    "target_amount_label": {"en": "Target Amount (RMB)", "pt": "Valor Alvo (RMB)", "fr": "Montant Cible (RMB)", "zh": "目标金额（元）"},
    "current_saved_label": {"en": "Current Saved Amount (RMB)", "pt": "Valor Já Poupado (RMB)", "fr": "Montant Déjà Épargné (RMB)", "zh": "当前已存金额（元）"},
    "deadline_label": {"en": "Deadline", "pt": "Prazo", "fr": "Date Limite", "zh": "截止日期"},
    "save_goal": {"en": "💾 Save Goal", "pt": "💾 Salvar Meta", "fr": "💾 Enregistrer l'Objectif", "zh": "💾 保存目标"},
    "goal_error": {"en": "Please provide a goal name and a target amount greater than 0.", "pt": "Informe o nome da meta e um valor alvo maior que 0.", "fr": "Veuillez indiquer un nom et un montant cible supérieur à 0.", "zh": "请填写目标名称和大于0的目标金额。"},
    "goal_added": {"en": "Goal '{name}' created!", "pt": "Meta '{name}' criada!", "fr": "Objectif '{name}' créé !", "zh": "目标“{name}”已创建！"},
    "your_goals": {"en": "🏆 Your Goals", "pt": "🏆 Suas Metas", "fr": "🏆 Vos Objectifs", "zh": "🏆 我的目标"},
    "no_goals": {"en": "No savings goals yet. Add one above!", "pt": "Nenhuma meta ainda. Adicione uma acima!", "fr": "Aucun objectif encore. Ajoutez-en un ci-dessus !", "zh": "暂无储蓄目标，请在上方添加！"},
    "add_savings_label": {"en": "Add to savings (RMB)", "pt": "Adicionar à poupança (RMB)", "fr": "Ajouter à l'épargne (RMB)", "zh": "增加储蓄金额（元）"},
    "update_btn": {"en": "➕ Update", "pt": "➕ Atualizar", "fr": "➕ Mettre à Jour", "zh": "➕ 更新"},
    "delete_goal_btn": {"en": "🗑️ Delete Goal", "pt": "🗑️ Excluir Meta", "fr": "🗑️ Supprimer l'Objectif", "zh": "🗑️ 删除目标"},
    "target_word": {"en": "target", "pt": "alvo", "fr": "cible", "zh": "目标"},

    "reports_title": {"en": "Reports", "pt": "Relatórios", "fr": "Rapports", "zh": "报告"},
    "reports_caption": {"en": "A clean, shareable summary of your finances for any month.", "pt": "Um resumo bonito e compartilhável das suas finanças para qualquer mês.", "fr": "Un résumé clair et partageable de vos finances pour tout mois.", "zh": "生成任意月份的清晰、可分享的财务摘要。"},
    "month_label": {"en": "Month", "pt": "Mês", "fr": "Mois", "zh": "月份"},
    "year_label": {"en": "Year", "pt": "Ano", "fr": "Année", "zh": "年份"},
    "report_income": {"en": "Total Income", "pt": "Total de Receitas", "fr": "Total des Revenus", "zh": "总收入"},
    "report_expenses": {"en": "Total Expenses", "pt": "Total de Despesas", "fr": "Total des Dépenses", "zh": "总支出"},
    "report_net": {"en": "Net Savings", "pt": "Economia Líquida", "fr": "Épargne Nette", "zh": "净结余"},
    "report_rate": {"en": "Savings Rate", "pt": "Taxa de Poupança", "fr": "Taux d'Épargne", "zh": "储蓄率"},
    "report_top_categories": {"en": "Spending by Category", "pt": "Gastos por Categoria", "fr": "Dépenses par Catégorie", "zh": "分类支出"},
    "report_top_expenses": {"en": "Largest Individual Expenses", "pt": "Maiores Despesas Individuais", "fr": "Plus Grandes Dépenses", "zh": "最大单笔支出"},
    "report_budget_status": {"en": "Budget Adherence", "pt": "Cumprimento do Orçamento", "fr": "Respect du Budget", "zh": "预算执行情况"},
    "report_bills_status": {"en": "Bills Status", "pt": "Status das Contas", "fr": "Statut des Factures", "zh": "账单状态"},
    "report_goals_status": {"en": "Goals Progress", "pt": "Progresso das Metas", "fr": "Progression des Objectifs", "zh": "目标进度"},
    "download_pdf": {"en": "⬇️ Download PDF Report", "pt": "⬇️ Baixar Relatório em PDF", "fr": "⬇️ Télécharger le Rapport PDF", "zh": "⬇️ 下载 PDF 报告"},
    "pdf_zh_note": {"en": "", "pt": "", "fr": "", "zh": "提示：PDF 导出仅支持拉丁字符 — 中文内容建议在网页上查看。"},
    "no_data_period": {"en": "No data recorded for this period yet.", "pt": "Ainda não há dados para este período.", "fr": "Aucune donnée pour cette période.", "zh": "该时间段暂无数据。"},
    "over_budget_label": {"en": "Over budget", "pt": "Acima do orçamento", "fr": "Dépassement", "zh": "超支类别"},
    "within_budget_label": {"en": "Within budget", "pt": "Dentro do orçamento", "fr": "Dans le budget", "zh": "预算内类别"},
    "bills_paid_of": {"en": "{paid} of {total} bills paid", "pt": "{paid} de {total} contas pagas", "fr": "{paid} sur {total} factures payées", "zh": "已支付 {paid}/{total} 笔账单"},
    "generated_on": {"en": "Generated on", "pt": "Gerado em", "fr": "Généré le", "zh": "生成时间"},
}


def month_name(month_num, lang_code):
    return MONTH_NAMES.get(lang_code, MONTH_NAMES["en"])[month_num - 1]


def tr_option(canonical, table, lang_code):
    if lang_code == "en":
        return canonical
    return table.get(canonical, {}).get(lang_code, canonical)


# ==============================================================================
# 2. SUPABASE CONNECTION LAYER
# ==============================================================================
@st.cache_resource(show_spinner="Connecting to Supabase...")
def get_supabase():
    """One client per server process. Uses the SECRET key (server-side only),
    which bypasses Row Level Security — so it must live only in Streamlit
    secrets, never in the repo or in browser code."""
    return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])


def supabase_dashboard_url():
    try:
        ref = st.secrets["supabase_url"].split("//")[1].split(".")[0]
        return f"https://supabase.com/dashboard/project/{ref}/editor"
    except Exception:
        return None


def _py(v):
    """Convert numpy scalars to native Python so they are JSON-serialisable."""
    return v.item() if hasattr(v, "item") else v


def fetch_df(table):
    """Read a whole table (paginated, so >1000 rows still work) into a typed
    DataFrame with a stable column order."""
    sb = get_supabase()
    cols = TABLE_SCHEMAS[table]
    order_col = "id" if "id" in cols else cols[0]
    rows, start, page = [], 0, 1000
    while True:
        res = sb.table(table).select("*").order(order_col).range(start, start + page - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page:
            break
        start += page

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols]
    for c in NUMERIC_COLUMNS.get(table, []):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    if "id" in df.columns and not df.empty:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    return df


def insert_row(table, data: dict):
    """Insert one row. Postgres generates `id` automatically."""
    get_supabase().table(table).insert({k: _py(v) for k, v in data.items()}).execute()


def update_row(table, id_value, data: dict, id_col="id"):
    get_supabase().table(table).update({k: _py(v) for k, v in data.items()}).eq(id_col, _py(id_value)).execute()


def delete_row(table, id_value, id_col="id"):
    get_supabase().table(table).delete().eq(id_col, _py(id_value)).execute()


def upsert_row(table, data: dict, conflict_col: str):
    get_supabase().table(table).upsert({k: _py(v) for k, v in data.items()}, on_conflict=conflict_col).execute()


def get_setting(key, default=None):
    df = fetch_df("settings")
    match = df[df["key"] == key]
    return match.iloc[0]["value"] if not match.empty else default


def get_float_setting(key, default):
    """Robust numeric read: falls back to `default` if the value is missing,
    blank, or not a number."""
    val = get_setting(key, default)
    try:
        return float(val)
    except (TypeError, ValueError):
        return float(default)


def set_setting(key, value):
    upsert_row("settings", {"key": key, "value": str(value)}, "key")


def ensure_database_ready():
    """Seed sensible defaults once. The tables themselves must already exist —
    run supabase_schema.sql in the Supabase SQL Editor first."""
    if get_setting("initialized") != "true":
        set_setting("exchange_rate", 85)
        set_setting("savings_goal_monthly", 500)
        set_setting("theme", "Light")
        set_setting("language", "en")

        budgets_df = fetch_df("budgets")
        existing_cats = set(budgets_df["category"]) if not budgets_df.empty else set()
        for cat in EXPENSE_CATEGORIES:
            if cat not in existing_cats:
                insert_row("budgets", {"category": cat, "limit_rmb": 0})

        if fetch_df("bills").empty:
            base = datetime.date.today()
            for bname, amt, day in [
                ("Dormitory Fee", 3000, 5), ("Health Insurance", 800, 1),
                ("Phone Plan (SIM)", 50, 10), ("Internet / Dorm WiFi", 30, 10),
            ]:
                insert_row("bills", {
                    "bill_name": bname, "amount_rmb": amt,
                    "due_date": str(base.replace(day=day)),
                    "status": "Pending", "date_paid": None,
                })

        set_setting("initialized", "true")


# Run the readiness check only once per browser session (not on every widget
# interaction) to avoid needless database round-trips.
if "workbook_ready" not in st.session_state:
    try:
        ensure_database_ready()
        st.session_state.workbook_ready = True
    except Exception as e:
        st.error(
            "⚠️ Could not connect to Supabase. Check `supabase_url` / `supabase_key` in "
            "your secrets, and that you ran `supabase_schema.sql`. On the free plan, a "
            "project idle for 7 days is paused — restore it in the Supabase dashboard "
            "(your data is kept). See SETUP.md."
        )
        st.exception(e)
        st.stop()

# ==============================================================================
# 3. GLOBAL STATE  (with defensive fallbacks in case the sheet has bad data)
# ==============================================================================
if "exchange_rate" not in st.session_state:
    st.session_state.exchange_rate = get_float_setting("exchange_rate", 85)
if "theme" not in st.session_state:
    theme_val = get_setting("theme", "Light")
    st.session_state.theme = theme_val if theme_val in ("Light", "Dark") else "Light"
if "lang" not in st.session_state:
    lang_val = get_setting("language", "en")
    st.session_state.lang = lang_val if lang_val in LANGUAGES else "en"

RATE = st.session_state.exchange_rate
lang = st.session_state.lang


def t(key, **kwargs):
    template = STRINGS.get(key, {}).get(lang) or STRINGS.get(key, {}).get("en", key)
    return template.format(**kwargs) if kwargs else template


def rmb_to_xof(amount_rmb):
    return amount_rmb * RATE


def fmt_rmb(x):
    return f"¥{x:,.2f}"


def fmt_xof(x):
    return f"{x:,.0f} XOF"


# ==============================================================================
# 4. THEME / MOBILE-FIRST RESPONSIVE CSS
# ==============================================================================
def inject_css(theme: str):
    if theme == "Dark":
        bg, card_bg, text, accent, accent2, subtext, border = (
            "#0e1117", "#1c2029", "#f5f5f5", "#5da9f0", "#a78bfa", "#a0a4ac", "#2a2f3a",
        )
    else:
        bg, card_bg, text, accent, accent2, subtext, border = (
            "#f7f9fc", "#ffffff", "#1a1a1a", "#2563eb", "#7c3aed", "#5c6470", "#e5e9f0",
        )

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html {{ -webkit-text-size-adjust: 100%; }}
        html, body, .stApp {{ font-family: 'Inter', -apple-system, sans-serif; background-color: {bg}; color: {text}; }}

        /* ---------- Core components ---------- */
        .hero-header {{
            background: linear-gradient(135deg, {accent} 0%, {accent2} 100%);
            color: #ffffff; border-radius: 18px; padding: 22px 26px; margin-bottom: 20px;
            box-shadow: 0 10px 28px rgba(37,99,235,0.22);
        }}
        .hero-header h1 {{ margin: 0; font-size: 1.5rem; font-weight: 800; line-height: 1.3; }}
        .hero-header p {{ margin: 6px 0 0 0; opacity: 0.92; font-size: 0.92rem; }}

        .metric-card {{
            background-color: {card_bg}; border: 1px solid {border}; border-radius: 16px;
            padding: 16px 18px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); margin-bottom: 10px;
            transition: transform .15s ease;
        }}
        .metric-card:hover {{ transform: translateY(-2px); }}
        .metric-title {{ font-size: 0.78rem; color: {subtext}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
        .metric-value {{ font-size: 1.5rem; font-weight: 800; color: {accent}; margin-top: 4px; word-break: break-word; }}
        .metric-sub {{ font-size: 0.84rem; color: {subtext}; }}

        .goal-card {{
            background-color: {card_bg}; border: 1px solid {border}; border-radius: 16px;
            padding: 16px 18px; margin-bottom: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }}

        section[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border}; }}
        div[data-testid="stExpander"] {{ background-color: {card_bg}; border-radius: 12px; border: 1px solid {border}; }}
        div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: auto; border: 1px solid {border}; -webkit-overflow-scrolling: touch; }}

        /* ---------- Touch-friendly controls (44px min tap target) ---------- */
        .stButton>button {{
            border-radius: 10px !important; font-weight: 600 !important; border: none !important;
            transition: all .15s ease !important; min-height: 44px !important;
        }}
        .stButton>button:hover {{ transform: translateY(-1px); box-shadow: 0 6px 14px rgba(0,0,0,0.15); }}
        .stButton>button:active {{ transform: translateY(0); }}
        div[data-baseweb="select"] > div {{ border-radius: 10px !important; min-height: 44px !important; }}
        .stTextInput>div>div>input, .stNumberInput>div>div>input, .stDateInput>div>div>input {{
            border-radius: 10px !important; min-height: 44px !important; font-size: 1rem !important;
        }}
        * {{ -webkit-tap-highlight-color: transparent; }}

        /* ---------- Tablet ---------- */
        @media (max-width: 768px) {{
            .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; padding-top: 1rem !important; }}
            .hero-header {{ padding: 18px 20px; border-radius: 14px; }}
            .hero-header h1 {{ font-size: 1.3rem; }}
            .hero-header p {{ font-size: 0.85rem; }}
            .metric-card {{ padding: 14px 16px; }}
            .metric-value {{ font-size: 1.3rem; }}
        }}

        /* ---------- Phones ---------- */
        @media (max-width: 480px) {{
            .block-container {{ padding-left: 0.75rem !important; padding-right: 0.75rem !important; }}
            .hero-header {{ padding: 16px 18px; }}
            .hero-header h1 {{ font-size: 1.15rem; }}
            .hero-header p {{ font-size: 0.8rem; }}
            .metric-card {{ padding: 12px 14px; margin-bottom: 8px; }}
            .metric-title {{ font-size: 0.72rem; }}
            .metric-value {{ font-size: 1.15rem; }}
            .metric-sub {{ font-size: 0.78rem; }}
            .goal-card {{ padding: 14px 16px; }}
            h3 {{ font-size: 1.05rem !important; }}
            h4 {{ font-size: 0.95rem !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css(st.session_state.theme)


def page_header(title, subtitle=""):
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f"""<div class="hero-header"><h1>{title}</h1>{sub_html}</div>""", unsafe_allow_html=True)


def metric_card(title, value_html, sub=""):
    st.markdown(
        f"""<div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value_html}</div>
            <div class="metric-sub">{sub}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def budget_progress_color(pct):
    """For spending vs. a limit: higher % used is WORSE. 🟢<70 · 🟡70-90 · 🔴>90"""
    return "#22c55e" if pct < 70 else ("#f59e0b" if pct <= 90 else "#ef4444")


def savings_progress_color(pct):
    """For progress toward a savings goal: higher % saved is BETTER.
    🟢≥70% · 🟡40-70% · 🔴<40%. Kept as its own function (rather than
    reusing budget_progress_color with an inverted number) so the meaning
    of each color stays unambiguous everywhere it's used."""
    return "#22c55e" if pct >= 70 else ("#f59e0b" if pct >= 40 else "#ef4444")


def colored_progress_bar(pct, color, height="14px"):
    pct_display = min(max(pct, 0), 100)
    st.markdown(
        f"""<div style="background-color:#e5e9f0; border-radius:8px; height:{height}; width:100%; overflow:hidden;">
            <div style="background-color:{color}; width:{pct_display}%; height:100%; border-radius:8px; transition: width 0.4s ease;"></div>
        </div>""",
        unsafe_allow_html=True,
    )


def greeting():
    hour = datetime.datetime.now().hour
    key = "greet_morning" if hour < 12 else ("greet_afternoon" if hour < 18 else "greet_evening")
    return t(key)


# ==============================================================================
# 5. SIDEBAR
# ==============================================================================
st.sidebar.markdown(f"## {t('brand_title')}")
st.sidebar.caption(t("brand_subtitle"))

PAGE_KEYS = ["dashboard", "income", "expenses", "budget", "bills", "goals", "reports"]
PAGE_ICONS = {"dashboard": "🏠", "income": "💵", "expenses": "🧾", "budget": "📊",
              "bills": "📌", "goals": "🎯", "reports": "📄"}
page_labels = [f"{PAGE_ICONS[k]} {t('nav_' + k)}" for k in PAGE_KEYS]
selected_label = st.sidebar.radio("nav", page_labels, label_visibility="collapsed")
page_key = PAGE_KEYS[page_labels.index(selected_label)]

st.sidebar.markdown("---")
with st.sidebar.expander(t("settings_header"), expanded=False):
    lang_choice_label = st.selectbox(t("language_label"), list(LANGUAGES.values()),
                                      index=list(LANGUAGES.keys()).index(lang))
    lang_choice = [k for k, v in LANGUAGES.items() if v == lang_choice_label][0]
    if lang_choice != lang:
        st.session_state.lang = lang_choice
        set_setting("language", lang_choice)
        st.rerun()

    theme_choice = st.selectbox(t("theme_label"), [t("theme_light"), t("theme_dark")],
                                 index=0 if st.session_state.theme == "Light" else 1)
    theme_choice_en = "Light" if theme_choice == t("theme_light") else "Dark"
    if theme_choice_en != st.session_state.theme:
        st.session_state.theme = theme_choice_en
        set_setting("theme", theme_choice_en)
        st.rerun()

    new_rate = st.number_input(t("rate_label"), min_value=1.0, value=float(RATE), step=0.5)
    if st.button(t("rate_btn"), width="stretch"):
        st.session_state.exchange_rate = new_rate
        set_setting("exchange_rate", new_rate)
        st.success(t("rate_updated", rate=new_rate))
        st.rerun()

    monthly_goal = st.number_input(t("goal_label"), min_value=0.0,
                                    value=get_float_setting("savings_goal_monthly", 500), step=50.0)
    if st.button(t("goal_btn"), width="stretch"):
        set_setting("savings_goal_monthly", monthly_goal)
        st.success(t("goal_updated"))
        st.rerun()

    st.markdown(f"**{t('export_header')}**")
    income_df_export = fetch_df("income")
    expenses_df_export = fetch_df("expenses")
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(t("income_csv"), income_df_export.to_csv(index=False).encode("utf-8"),
                            "income_export.csv", "text/csv", width="stretch")
    with col_b:
        st.download_button(t("expenses_csv"), expenses_df_export.to_csv(index=False).encode("utf-8"),
                            "expenses_export.csv", "text/csv", width="stretch")

    dash_url = supabase_dashboard_url()
    if dash_url:
        st.markdown("---")
        st.markdown(f"[{t('open_sheet')}]({dash_url})")

st.sidebar.markdown("---")
st.sidebar.info(t("tip"))

# ==============================================================================
# 6. LOAD CORE DATA
# ==============================================================================
income_df = fetch_df("income")
expenses_df = fetch_df("expenses")

if not income_df.empty:
    income_df["date"] = pd.to_datetime(income_df["date"], errors="coerce")
    income_df = income_df.sort_values("date", ascending=False)
if not expenses_df.empty:
    expenses_df["date"] = pd.to_datetime(expenses_df["date"], errors="coerce")
    expenses_df = expenses_df.sort_values("date", ascending=False)

today = datetime.date.today()
current_month, current_year = today.month, today.year


def month_filter(df, month, year):
    if df.empty:
        return df
    return df[(df["date"].dt.month == month) & (df["date"].dt.year == year)]


income_month = month_filter(income_df, current_month, current_year)
expenses_month = month_filter(expenses_df, current_month, current_year)

total_income_all = income_df["amount_rmb"].sum() if not income_df.empty else 0.0
total_expenses_all = expenses_df["amount_rmb"].sum() if not expenses_df.empty else 0.0
balance_rmb = total_income_all - total_expenses_all

total_income_month = income_month["amount_rmb"].sum() if not income_month.empty else 0.0
total_expenses_month = expenses_month["amount_rmb"].sum() if not expenses_month.empty else 0.0
net_month = total_income_month - total_expenses_month

# ==============================================================================
# 7. PAGE: DASHBOARD
# ==============================================================================
if page_key == "dashboard":
    page_header(
        f"{PAGE_ICONS['dashboard']} {t('dash_title')} — {greeting()}",
        t("dash_overview", month=month_name(current_month, lang) + f" {current_year}", rate=RATE),
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(t("kpi_balance"), fmt_rmb(balance_rmb), fmt_xof(rmb_to_xof(balance_rmb)))
    with c2:
        metric_card(t("kpi_income_month"), fmt_rmb(total_income_month), fmt_xof(rmb_to_xof(total_income_month)))
    with c3:
        metric_card(t("kpi_expenses_month"), fmt_rmb(total_expenses_month), fmt_xof(rmb_to_xof(total_expenses_month)))
    with c4:
        net_color = "🟢" if net_month >= 0 else "🔴"
        metric_card(f"{net_color} {t('kpi_net_month')}", fmt_rmb(net_month), fmt_xof(rmb_to_xof(net_month)))

    st.markdown(f"### {t('savings_progress_title')}")
    goal_target = get_float_setting("savings_goal_monthly", 500)
    saved_pct = 0 if goal_target <= 0 else max(0, (net_month / goal_target) * 100)
    col_g1, col_g2 = st.columns([3, 1])
    with col_g1:
        colored_progress_bar(saved_pct, savings_progress_color(saved_pct))
    with col_g2:
        st.markdown(f"**{saved_pct:.0f}%** {t('of_target', target=fmt_rmb(goal_target))}")

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown(f"#### {t('chart_expenses_by_cat')}")
        if not expenses_month.empty:
            cat_sum = expenses_month.groupby("category", as_index=False)["amount_rmb"].sum()
            cat_sum["Category"] = cat_sum["category"].apply(lambda c: tr_option(c, CATEGORY_TR, lang))
            fig_pie = px.pie(cat_sum, names="Category", values="amount_rmb", hole=0.5,
                              color_discrete_sequence=px.colors.qualitative.Set3)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10),
                                   legend=dict(orientation="h", yanchor="bottom", y=-0.3),
                                   paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, width="stretch")
        else:
            st.info(t("no_expenses_month"))

    with col_chart2:
        st.markdown(f"#### {t('chart_daily_trend')}")
        if not expenses_month.empty:
            daily = expenses_month.groupby(expenses_month["date"].dt.date, as_index=False)["amount_rmb"].sum()
            daily.columns = ["date", "amount_rmb"]
            fig_line = px.line(daily, x="date", y="amount_rmb", markers=True,
                                labels={"date": t("date_label"), "amount_rmb": t("amount_label")})
            fig_line.update_traces(line_color="#2563eb", fill="tozeroy", fillcolor="rgba(37,99,235,0.1)")
            fig_line.update_layout(margin=dict(t=10, b=10, l=10, r=10),
                                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_line, width="stretch")
        else:
            st.info(t("no_daily_data"))

# ==============================================================================
# 8. PAGE: INCOME
# ==============================================================================
elif page_key == "income":
    page_header(f"{PAGE_ICONS['income']} {t('income_title')}", t("income_caption"))

    with st.expander(t("add_income"), expanded=True):
        with st.form("income_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                i_date = st.date_input(t("date_label"), value=today)
                i_source = st.selectbox(t("source_label"), INCOME_SOURCES,
                                         format_func=lambda x: tr_option(x, SOURCE_TR, lang))
            with fc2:
                i_amount = st.number_input(t("amount_label"), min_value=0.0, step=10.0)
                i_notes = st.text_input(t("notes_label"))
            if st.form_submit_button(t("save_income"), width="stretch"):
                if i_amount <= 0:
                    st.error(t("amount_error"))
                else:
                    insert_row("income", {"date": str(i_date), "source": i_source, "amount_rmb": i_amount, "notes": i_notes})
                    st.success(t("income_added", amount=fmt_rmb(i_amount), source=tr_option(i_source, SOURCE_TR, lang)))
                    st.rerun()

    st.markdown(f"### {t('income_history')}")
    if income_df.empty:
        st.info(t("no_income"))
    else:
        display_df = income_df.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df["Source"] = display_df["source"].apply(lambda x: tr_option(x, SOURCE_TR, lang))
        display_df["XOF"] = (display_df["amount_rmb"] * RATE).round(0)
        display_df = display_df.rename(columns={"amount_rmb": t("amount_label"), "date": t("date_label"), "notes": t("notes_label")})
        st.dataframe(display_df[["id", t("date_label"), "Source", t("amount_label"), "XOF", t("notes_label")]],
                     width="stretch", hide_index=True)

        # Delete picker shows date · source · amount instead of a bare ID
        # number, so it's usable on a phone without scrolling back up to the
        # table to figure out which row a given ID belongs to.
        def income_entry_label(x):
            if x is None:
                return t("select_placeholder")
            r = income_df[income_df["id"] == x].iloc[0]
            return f"{r['date'].strftime('%Y-%m-%d')} · {tr_option(r['source'], SOURCE_TR, lang)} · {fmt_rmb(r['amount_rmb'])}"

        del_id = st.selectbox(t("select_delete_entry"), options=[None] + income_df["id"].tolist(),
                               format_func=income_entry_label)
        if del_id and st.button(t("delete_income_btn"), width="stretch"):
            delete_row("income", del_id)
            st.success(t("entry_deleted"))
            st.rerun()

# ==============================================================================
# 9. PAGE: EXPENSES
# ==============================================================================
elif page_key == "expenses":
    page_header(f"{PAGE_ICONS['expenses']} {t('expenses_title')}", t("expenses_caption"))

    with st.expander(t("add_expense"), expanded=True):
        with st.form("expense_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                e_date = st.date_input(t("date_label"), value=today, key="e_date")
                e_category = st.selectbox(t("category_label"), EXPENSE_CATEGORIES,
                                           format_func=lambda x: tr_option(x, CATEGORY_TR, lang))
                e_payment = st.selectbox(t("payment_method_label"), PAYMENT_METHODS,
                                          format_func=lambda x: tr_option(x, PAYMENT_TR, lang))
            with fc2:
                e_amount = st.number_input(t("amount_label"), min_value=0.0, step=5.0, key="e_amount")
                e_desc = st.text_input(t("description_label"))
            if st.form_submit_button(t("save_expense"), width="stretch"):
                if e_amount <= 0:
                    st.error(t("amount_error"))
                else:
                    insert_row("expenses", {"date": str(e_date), "category": e_category, "description": e_desc,
                                             "amount_rmb": e_amount, "payment_method": e_payment})
                    st.success(t("expense_added", amount=fmt_rmb(e_amount), category=tr_option(e_category, CATEGORY_TR, lang)))
                    st.rerun()

    st.markdown(f"### {t('expense_history')}")
    if expenses_df.empty:
        st.info(t("no_expenses_hist"))
    else:
        display_df = expenses_df.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df["Category"] = display_df["category"].apply(lambda x: tr_option(x, CATEGORY_TR, lang))
        display_df["Payment"] = display_df["payment_method"].apply(lambda x: tr_option(x, PAYMENT_TR, lang))
        display_df["XOF"] = (display_df["amount_rmb"] * RATE).round(0)
        display_df = display_df.rename(columns={"amount_rmb": t("amount_label"), "date": t("date_label"), "description": t("description_label")})
        st.dataframe(
            display_df[["id", t("date_label"), "Category", t("description_label"), t("amount_label"), "XOF", "Payment"]],
            width="stretch", hide_index=True,
        )

        st.markdown(f"#### {t('edit_delete_header')}")

        def expense_entry_label(x):
            if x is None:
                return t("select_placeholder")
            r = expenses_df[expenses_df["id"] == x].iloc[0]
            return f"{r['date'].strftime('%Y-%m-%d')} · {tr_option(r['category'], CATEGORY_TR, lang)} · {fmt_rmb(r['amount_rmb'])}"

        edit_id = st.selectbox(t("select_entry"), options=[None] + expenses_df["id"].tolist(),
                                format_func=expense_entry_label)
        if edit_id:
            row = expenses_df[expenses_df["id"] == edit_id].iloc[0]
            with st.form("edit_expense_form"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_date = st.date_input(t("date_label"), value=row["date"].date())
                    new_cat = st.selectbox(t("category_label"), EXPENSE_CATEGORIES,
                                            index=EXPENSE_CATEGORIES.index(row["category"]) if row["category"] in EXPENSE_CATEGORIES else 0,
                                            format_func=lambda x: tr_option(x, CATEGORY_TR, lang))
                    new_pay = st.selectbox(t("payment_method_label"), PAYMENT_METHODS,
                                            index=PAYMENT_METHODS.index(row["payment_method"]) if row["payment_method"] in PAYMENT_METHODS else 0,
                                            format_func=lambda x: tr_option(x, PAYMENT_TR, lang))
                with ec2:
                    new_amount = st.number_input(t("amount_label"), min_value=0.0, value=float(row["amount_rmb"]))
                    new_desc = st.text_input(t("description_label"), value=row["description"] if isinstance(row["description"], str) else "")

                col_upd, col_del = st.columns(2)
                with col_upd:
                    if st.form_submit_button(t("update_entry"), width="stretch"):
                        update_row("expenses", edit_id, {"date": str(new_date), "category": new_cat,
                                                          "description": new_desc, "amount_rmb": new_amount,
                                                          "payment_method": new_pay})
                        st.success(t("entry_updated"))
                        st.rerun()
                with col_del:
                    if st.form_submit_button(t("delete_entry"), width="stretch"):
                        delete_row("expenses", edit_id)
                        st.success(t("entry_deleted"))
                        st.rerun()

# ==============================================================================
# 10. PAGE: MONTHLY BUDGET
# ==============================================================================
elif page_key == "budget":
    page_header(f"{PAGE_ICONS['budget']} {t('budget_title')}", t("budget_caption"))

    budgets_df = fetch_df("budgets")

    with st.expander(t("set_budget"), expanded=False):
        with st.form("budget_form"):
            budget_inputs = {}
            cols = st.columns(2)
            for i, cat in enumerate(EXPENSE_CATEGORIES):
                current_limit = budgets_df.loc[budgets_df["category"] == cat, "limit_rmb"]
                current_limit = float(current_limit.iloc[0]) if not current_limit.empty else 0.0
                with cols[i % 2]:
                    budget_inputs[cat] = st.number_input(
                        f"{tr_option(cat, CATEGORY_TR, lang)} {t('limit_suffix')}",
                        min_value=0.0, value=current_limit, step=50.0, key=f"budget_{cat}",
                    )
            if st.form_submit_button(t("save_budgets"), width="stretch"):
                for cat, amt in budget_inputs.items():
                    upsert_row("budgets", {"category": cat, "limit_rmb": amt}, "category")
                st.success(t("budgets_updated"))
                st.rerun()

    st.markdown(f"### {t('budget_vs_actual', month=month_name(current_month, lang) + f' {current_year}')}")
    budgets_df = fetch_df("budgets")
    spend_by_cat = expenses_month.groupby("category")["amount_rmb"].sum().to_dict() if not expenses_month.empty else {}

    for cat in EXPENSE_CATEGORIES:
        limit_row = budgets_df.loc[budgets_df["category"] == cat, "limit_rmb"]
        limit = float(limit_row.iloc[0]) if not limit_row.empty else 0.0
        spent = spend_by_cat.get(cat, 0.0)
        pct = 0 if limit <= 0 else (spent / limit) * 100
        color = budget_progress_color(pct) if limit > 0 else "#9ca3af"

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{tr_option(cat, CATEGORY_TR, lang)}** — {fmt_rmb(spent)} / {fmt_rmb(limit) if limit > 0 else t('no_limit')}")
            colored_progress_bar(pct, color)
        with col2:
            st.markdown(f"<div style='text-align:right; font-weight:700; color:{color};'>{pct:.0f}%</div>", unsafe_allow_html=True)
        st.write("")

    st.caption(t("budget_legend"))

# ==============================================================================
# 11. PAGE: BILLS
# ==============================================================================
elif page_key == "bills":
    page_header(f"{PAGE_ICONS['bills']} {t('bills_title')}", t("bills_caption"))

    with st.expander(t("add_bill"), expanded=False):
        with st.form("bill_form", clear_on_submit=True):
            bc1, bc2 = st.columns(2)
            with bc1:
                b_name = st.text_input(t("bill_name_label"))
                b_amount = st.number_input(t("amount_label"), min_value=0.0, step=10.0)
            with bc2:
                b_due = st.date_input(t("due_date_label"), value=today)
                b_status = st.selectbox(t("status_label"), BILL_STATUSES,
                                         format_func=lambda x: tr_option(x, STATUS_TR, lang))
            b_paid_date = None
            if b_status == "Paid":
                b_paid_date = st.date_input(t("date_paid_label"), value=today, key="paid_date_new")
            if st.form_submit_button(t("save_bill"), width="stretch"):
                if not b_name or b_amount <= 0:
                    st.error(t("bill_error"))
                else:
                    insert_row("bills", {
                        "bill_name": b_name, "amount_rmb": b_amount, "due_date": str(b_due),
                        "status": b_status, "date_paid": str(b_paid_date) if b_paid_date else None,
                    })
                    st.success(t("bill_added", name=b_name))
                    st.rerun()

    st.markdown(f"### {t('bills_checklist')}")
    bills_df = fetch_df("bills")
    if not bills_df.empty:
        bills_df = bills_df.sort_values("due_date")
    if bills_df.empty:
        st.info(t("no_bills"))
    else:
        # Card-per-bill layout (rather than one wide row) keeps every field
        # readable without horizontal scrolling on a phone.
        for _, row in bills_df.iterrows():
            icon = "✅" if row["status"] == "Paid" else "⏳"
            with st.container():
                st.markdown(
                    f"""<div class="goal-card" style="margin-bottom:10px;">
                        <div style="font-weight:700;">{icon} {row['bill_name']}</div>
                        <div style="color:#8a8f99; font-size:0.85rem;">
                            {fmt_rmb(row['amount_rmb'])} · {t('due_prefix')}: {row['due_date'] or '—'}
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                bcol1, bcol2 = st.columns([3, 1])
                with bcol1:
                    new_status = st.selectbox(
                        t("status_label"), BILL_STATUSES,
                        index=BILL_STATUSES.index(row["status"]) if row["status"] in BILL_STATUSES else 0,
                        format_func=lambda x: tr_option(x, STATUS_TR, lang),
                        key=f"status_{row['id']}", label_visibility="collapsed",
                    )
                with bcol2:
                    delete_clicked = st.button("🗑️", key=f"del_bill_{row['id']}", width="stretch")

                if new_status != row["status"]:
                    paid_date = str(today) if new_status == "Paid" else None
                    update_row("bills", row["id"], {"status": new_status, "date_paid": paid_date})
                    st.rerun()
                if delete_clicked:
                    delete_row("bills", row["id"])
                    st.rerun()

        total_pending = bills_df.loc[bills_df["status"] == "Pending", "amount_rmb"].sum()
        st.markdown("---")
        metric_card(t("total_pending"), fmt_rmb(total_pending), fmt_xof(rmb_to_xof(total_pending)))

# ==============================================================================
# 12. PAGE: SAVINGS & GOALS
# ==============================================================================
elif page_key == "goals":
    page_header(f"{PAGE_ICONS['goals']} {t('goals_title')}", t("goals_caption"))

    with st.expander(t("add_goal"), expanded=True):
        with st.form("goal_form", clear_on_submit=True):
            gc1, gc2 = st.columns(2)
            with gc1:
                g_name = st.text_input(t("goal_name_label"))
                g_target = st.number_input(t("target_amount_label"), min_value=0.0, step=50.0)
            with gc2:
                g_current = st.number_input(t("current_saved_label"), min_value=0.0, step=10.0)
                g_deadline = st.date_input(t("deadline_label"), value=today + datetime.timedelta(days=90))
            if st.form_submit_button(t("save_goal"), width="stretch"):
                if not g_name or g_target <= 0:
                    st.error(t("goal_error"))
                else:
                    insert_row("goals", {"goal_name": g_name, "target_amount": g_target,
                                          "current_amount": g_current, "deadline": str(g_deadline)})
                    st.success(t("goal_added", name=g_name))
                    st.rerun()

    st.markdown(f"### {t('your_goals')}")
    goals_df = fetch_df("goals")
    if not goals_df.empty:
        goals_df = goals_df.sort_values("deadline")
    if goals_df.empty:
        st.info(t("no_goals"))
    else:
        # Single column on phones (Streamlit stacks columns under ~640px
        # automatically), two columns on wider screens.
        cols = st.columns(2)
        for i, (_, row) in enumerate(goals_df.iterrows()):
            pct = 0 if row["target_amount"] <= 0 else min(100, (row["current_amount"] / row["target_amount"]) * 100)
            color = savings_progress_color(pct)
            with cols[i % 2]:
                st.markdown(
                    f"""<div class="goal-card">
                        <div style="font-weight:700; font-size:1.1rem;">🎯 {row['goal_name']}</div>
                        <div style="color:#8a8f99; font-size:0.85rem; margin-bottom:8px;">
                            {t('deadline_label')}: {row['deadline'] or '—'}
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                colored_progress_bar(pct, color)
                st.markdown(
                    f"**{fmt_rmb(row['current_amount'])} / {fmt_rmb(row['target_amount'])}** "
                    f"({pct:.0f}%) &nbsp;|&nbsp; {fmt_xof(rmb_to_xof(row['target_amount']))} {t('target_word')}"
                )
                add_amt = st.number_input(t("add_savings_label"), min_value=0.0, step=10.0, key=f"add_{row['id']}")
                cbtn1, cbtn2 = st.columns(2)
                with cbtn1:
                    if st.button(t("update_btn"), key=f"upd_goal_{row['id']}", width="stretch"):
                        new_amt = row["current_amount"] + add_amt
                        update_row("goals", row["id"], {"current_amount": new_amt})
                        st.rerun()
                with cbtn2:
                    if st.button(t("delete_goal_btn"), key=f"del_goal_{row['id']}", width="stretch"):
                        delete_row("goals", row["id"])
                        st.rerun()
                st.write("")

# ==============================================================================
# 13. PAGE: REPORTS  (on-screen + downloadable PDF)
# ==============================================================================
elif page_key == "reports":
    page_header(f"{PAGE_ICONS['reports']} {t('reports_title')}", t("reports_caption"))

    rc1, rc2 = st.columns(2)
    with rc1:
        sel_month = st.selectbox(t("month_label"), list(range(1, 13)), index=current_month - 1,
                                  format_func=lambda m: month_name(m, lang))
    with rc2:
        years_seen = set([today.year])
        if not income_df.empty:
            years_seen |= set(income_df["date"].dt.year.dropna().astype(int).tolist())
        if not expenses_df.empty:
            years_seen |= set(expenses_df["date"].dt.year.dropna().astype(int).tolist())
        years_sorted = sorted(years_seen)
        sel_year = st.selectbox(t("year_label"), years_sorted, index=years_sorted.index(today.year))

    p_income = month_filter(income_df, sel_month, sel_year)
    p_expenses = month_filter(expenses_df, sel_month, sel_year)
    p_income_total = p_income["amount_rmb"].sum() if not p_income.empty else 0.0
    p_expenses_total = p_expenses["amount_rmb"].sum() if not p_expenses.empty else 0.0
    p_net = p_income_total - p_expenses_total
    p_rate = 0 if p_income_total <= 0 else (p_net / p_income_total) * 100

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(t("report_income"), fmt_rmb(p_income_total), fmt_xof(rmb_to_xof(p_income_total)))
    with c2:
        metric_card(t("report_expenses"), fmt_rmb(p_expenses_total), fmt_xof(rmb_to_xof(p_expenses_total)))
    with c3:
        metric_card(t("report_net"), fmt_rmb(p_net), fmt_xof(rmb_to_xof(p_net)))
    with c4:
        metric_card(t("report_rate"), f"{p_rate:.0f}%")

    budgets_df_r = fetch_df("budgets")
    bills_df_r = fetch_df("bills")
    goals_df_r = fetch_df("goals")

    if p_expenses.empty:
        st.info(t("no_data_period"))
    else:
        st.markdown(f"#### {t('report_top_categories')}")
        cat_sum = p_expenses.groupby("category", as_index=False)["amount_rmb"].sum().sort_values("amount_rmb", ascending=False)
        cat_sum["Category"] = cat_sum["category"].apply(lambda c: tr_option(c, CATEGORY_TR, lang))
        fig = px.bar(cat_sum, x="Category", y="amount_rmb", color="amount_rmb", color_continuous_scale="Blues", text_auto=".2s")
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False,
                           yaxis_title=t("amount_label"), xaxis_title="")
        st.plotly_chart(fig, width="stretch")

        st.markdown(f"#### {t('report_top_expenses')}")
        top_exp = p_expenses.sort_values("amount_rmb", ascending=False).head(5).copy()
        top_exp["Category"] = top_exp["category"].apply(lambda c: tr_option(c, CATEGORY_TR, lang))
        top_exp["date"] = top_exp["date"].dt.strftime("%Y-%m-%d")
        top_exp = top_exp.rename(columns={"date": t("date_label"), "description": t("description_label"), "amount_rmb": t("amount_label")})
        st.dataframe(top_exp[[t("date_label"), "Category", t("description_label"), t("amount_label")]],
                     width="stretch", hide_index=True)

    st.markdown(f"#### {t('report_budget_status')}")
    over_list, within_list = [], []
    for cat in EXPENSE_CATEGORIES:
        limit_row = budgets_df_r.loc[budgets_df_r["category"] == cat, "limit_rmb"]
        limit = float(limit_row.iloc[0]) if not limit_row.empty else 0.0
        spent = p_expenses.loc[p_expenses["category"] == cat, "amount_rmb"].sum() if not p_expenses.empty else 0.0
        if limit > 0:
            (over_list if spent > limit else within_list).append(tr_option(cat, CATEGORY_TR, lang))
    st.write(f"🔴 **{t('over_budget_label')}:** " + (", ".join(over_list) if over_list else "—"))
    st.write(f"🟢 **{t('within_budget_label')}:** " + (", ".join(within_list) if within_list else "—"))

    st.markdown(f"#### {t('report_bills_status')}")
    paid_count = int((bills_df_r["status"] == "Paid").sum()) if not bills_df_r.empty else 0
    st.write(t("bills_paid_of", paid=paid_count, total=len(bills_df_r)))

    st.markdown(f"#### {t('report_goals_status')}")
    if goals_df_r.empty:
        st.write("—")
    else:
        for _, g in goals_df_r.iterrows():
            gpct = 0 if g["target_amount"] <= 0 else min(100, (g["current_amount"] / g["target_amount"]) * 100)
            st.write(f"🎯 {g['goal_name']}: {gpct:.0f}%")

    st.markdown("---")

    # ---------- PDF BUILD ----------
    def pdf_safe(s):
        return "" if s is None else str(s).encode("latin-1", "ignore").decode("latin-1")

    def build_pdf():
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_fill_color(37, 99, 235)
        pdf.rect(0, 0, 210, 26, style="F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, 6)
        pdf.set_font("Helvetica", "B", 17)
        pdf.cell(0, 10, pdf_safe("Personal Finance Report"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(10, 16)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, pdf_safe(f"{month_name(sel_month, 'en')} {sel_year}"), new_x="LMARGIN", new_y="NEXT")

        pdf.set_y(34)
        pdf.set_text_color(20, 20, 20)

        def section_title(txt):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(37, 99, 235)
            pdf.cell(0, 9, pdf_safe(txt), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(20, 20, 20)
            pdf.set_font("Helvetica", "", 10.5)

        def kv_row(label, value):
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(90, 8, pdf_safe(label))
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 8, pdf_safe(value), new_x="LMARGIN", new_y="NEXT")

        section_title("Summary")
        kv_row("Total Income", f"RMB {p_income_total:,.2f}  (~{rmb_to_xof(p_income_total):,.0f} XOF)")
        kv_row("Total Expenses", f"RMB {p_expenses_total:,.2f}  (~{rmb_to_xof(p_expenses_total):,.0f} XOF)")
        kv_row("Net Savings", f"RMB {p_net:,.2f}  (~{rmb_to_xof(p_net):,.0f} XOF)")
        kv_row("Savings Rate", f"{p_rate:.0f}%")

        if not p_expenses.empty:
            section_title("Spending by Category")
            cat_tbl = p_expenses.groupby("category", as_index=False)["amount_rmb"].sum().sort_values("amount_rmb", ascending=False)
            for _, r in cat_tbl.iterrows():
                kv_row(tr_option(r["category"], CATEGORY_TR, "en"), f"RMB {r['amount_rmb']:,.2f}")

            section_title("Largest Individual Expenses")
            top5 = p_expenses.sort_values("amount_rmb", ascending=False).head(5)
            for _, r in top5.iterrows():
                label = f"{r['date'].strftime('%Y-%m-%d')} — {tr_option(r['category'], CATEGORY_TR, 'en')}"
                desc = f" ({r['description']})" if r.get("description") else ""
                kv_row(pdf_safe(label + desc), f"RMB {r['amount_rmb']:,.2f}")

        section_title("Budget Adherence")
        kv_row("Over budget", ", ".join(over_list) if over_list else "None")
        kv_row("Within budget", ", ".join(within_list) if within_list else "None")

        section_title("Bills Status")
        kv_row("Bills paid", f"{paid_count} of {len(bills_df_r)}")

        if not goals_df_r.empty:
            section_title("Goals Progress")
            for _, g in goals_df_r.iterrows():
                gpct = 0 if g["target_amount"] <= 0 else min(100, (g["current_amount"] / g["target_amount"]) * 100)
                kv_row(g["goal_name"], f"{gpct:.0f}%  ({g['current_amount']:,.0f} / {g['target_amount']:,.0f} RMB)")

        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 8, pdf_safe(f"Generated on {datetime.date.today().isoformat()} · 1 RMB = {RATE} XOF"), new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())

    pdf_bytes = build_pdf()
    st.download_button(t("download_pdf"), data=pdf_bytes,
                        file_name=f"finance_report_{sel_year}_{sel_month:02d}.pdf",
                        mime="application/pdf", width="stretch")
    if lang == "zh":
        st.caption(t("pdf_zh_note"))

# ==============================================================================
# FOOTER
# ==============================================================================
st.sidebar.markdown("---")
st.sidebar.caption(t("footer"))
