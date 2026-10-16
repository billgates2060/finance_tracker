"""End-to-end smoke test (no network, no Supabase account needed).

Run from the project root:   python tests/e2e_test.py
Requires: pip install -r requirements.txt
It swaps the real `supabase` package for an in-memory fake, then drives every
page of the app with Streamlit's AppTest (add/edit/delete, all 4 languages,
reports + PDF).
"""
import sys, datetime, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fake_supabase
sys.modules["supabase"] = fake_supabase          # app does: from supabase import create_client
from streamlit.testing.v1 import AppTest

def fresh():
    fake_supabase.FakeClient.db_singleton = None
    at = AppTest.from_file(str(HERE.parent / "finance_tracker.py"), default_timeout=60)
    at.secrets["supabase_url"] = "https://abcdefgh.supabase.co"
    at.secrets["supabase_key"] = "sb_secret_test"
    return at

def goto(at, idx):
    at.sidebar.radio[0].set_value(at.sidebar.radio[0].options[idx]).run()
    assert not at.exception, [e.value for e in at.exception]

at = fresh(); at.run()
assert not at.exception, [e.value for e in at.exception]
db = fake_supabase.FakeClient.db_singleton
print("seed: settings", len(db.tables["settings"]), "| budgets", len(db.tables["budgets"]), "| bills", len(db.tables["bills"]))
assert len(db.tables["budgets"]) == 10 and len(db.tables["bills"]) == 4

for i, name in enumerate(["dashboard","income","expenses","budget","bills","goals","reports"]):
    goto(at, i); print("page OK:", name)

# ---- add income
goto(at, 1)
at.number_input[0].set_value(1500.0)
btn = [b for b in at.button if "Save Income" in b.label][0]; btn.click().run()
assert not at.exception, [e.value for e in at.exception]
print("income rows:", db.tables["income"])
assert len(db.tables["income"]) == 1 and db.tables["income"][0]["amount_rmb"] == 1500.0

# ---- add expense
goto(at, 2)
at.number_input[0].set_value(88.5)
[b for b in at.button if "Save Expense" in b.label][0].click().run()
assert not at.exception, [e.value for e in at.exception]
print("expense rows:", db.tables["expenses"])
assert len(db.tables["expenses"]) == 1

# ---- expenses page w/ data: edit form
sel = [s for s in at.selectbox if s.label == "Select entry"][0]
sel.set_value(db.tables["expenses"][0]["id"]).run()
assert not at.exception, [e.value for e in at.exception]
[b for b in at.button if "Update Entry" in b.label][0].click().run()
assert not at.exception, [e.value for e in at.exception]
print("expense after update:", db.tables["expenses"][0]["amount_rmb"])

# ---- budget save
goto(at, 3)
at.number_input[0].set_value(300.0)
[b for b in at.button if "Save All Budgets" in b.label][0].click().run()
assert not at.exception, [e.value for e in at.exception]
print("budget[0]:", db.tables["budgets"][0])
assert db.tables["budgets"][0]["limit_rmb"] == 300.0 and len(db.tables["budgets"]) == 10

# ---- bills: toggle status + delete
goto(at, 4)
st_sel = [s for s in at.selectbox if s.key and s.key.startswith("status_")][0]
st_sel.set_value("Paid").run()
assert not at.exception, [e.value for e in at.exception]
paid = [b for b in db.tables["bills"] if b["status"] == "Paid"]
print("paid bills:", paid)
assert len(paid) == 1 and paid[0]["date_paid"] == str(datetime.date.today())
[b for b in at.button if b.key and b.key.startswith("del_bill_")][0].click().run()
assert len(db.tables["bills"]) == 3

# ---- goals: add, increment, delete
goto(at, 5)
at.text_input[0].set_value("New Laptop")
at.number_input[0].set_value(5000.0)
[b for b in at.button if "Save Goal" in b.label][0].click().run()
assert not at.exception, [e.value for e in at.exception]
g = db.tables["goals"][0]; print("goal:", g)
inc = [n for n in at.number_input if n.key and n.key.startswith("add_")][0]; inc.set_value(250.0).run()
[b for b in at.button if b.key and b.key.startswith("upd_goal_")][0].click().run()
assert not at.exception, [e.value for e in at.exception]
print("goal after +250:", db.tables["goals"][0]["current_amount"])
assert db.tables["goals"][0]["current_amount"] == 250.0

# ---- dashboard + reports with data, every language
for lang_label in ["🇵🇹 Português", "🇫🇷 Français", "🇨🇳 中文", "🇬🇧 English"]:
    sb = [s for s in at.sidebar.selectbox if "Language" in s.label or "Idioma" in s.label or "Langue" in s.label or "语言" in s.label][0]
    sb.set_value(lang_label).run()
    assert not at.exception, [e.value for e in at.exception]
    for i in (0, 6):
        goto(at, i)
    print("language OK:", lang_label)
print("settings stored language:", [r for r in db.tables["settings"] if r["key"] == "language"])

# ---- delete income
goto(at, 1)
sel = [s for s in at.selectbox if s.label == "Select entry to delete"][0]
sel.set_value(db.tables["income"][0]["id"]).run()
[b for b in at.button if "Delete Selected" in b.label][0].click().run()
assert len(db.tables["income"]) == 0
print("ALL E2E CHECKS PASSED")
