# streamlit_app.py

import os
from dotenv import load_dotenv

# 1) Load .env before anything else
load_dotenv()

import streamlit as st
import json, ast

# 2) Early check for Salesforce Gateway env vars
required_env = [
    "SF_LLM_URL", "SF_LLM_MODEL", "SF_LLM_API_KEY",
    "SF_FEATURE_ID", "SF_TENANT_ID", "SF_VERIFY_PATH"
]
missing = [var for var in required_env if not os.getenv(var)]
if missing:
    st.error(
        f"⚠️ Missing environment variables: {', '.join(missing)}.\n"
        "Please add them to your .env file and restart."
    )
    st.stop()

# 0) Select source technology
AVAILABLE_TECHS = ["TIBCO", "BizTalk", "Camel", "Kafka", "MQ"]
st.sidebar.header("0. Source Technology")
tech = st.sidebar.selectbox("Pick your source tech", AVAILABLE_TECHS)

# 3) Safe to import rest (after env check)
from app.db import SessionLocal, CustomTask
from app.orchestrator import Orchestrator
from app.tasks.registry import discover_tasks
from app.langgraph_workflow import build_workflow_graph
from langgraph.graph import START, END

# UI setup
st.set_page_config(page_title="Multi‑Tech Migration Analyzer", layout="wide")
st.title("🔄 Multi‑Tech Migration Analyzer (MVP)")

# ➕ 1. Add New Custom Task
st.sidebar.header("➕ Add New Custom Task")
with st.sidebar.form("add_custom_task"):
    new_name   = st.text_input("Task Name")
    new_key    = st.text_input("Task Key (unique)")
    new_prompt = st.text_area("Prompt Template (use `{code}`)", height=120)
    if st.form_submit_button("Create Task"):
        if not (new_name and new_key and new_prompt):
            st.error("All fields are required.")
        else:
            db = SessionLocal()
            db.add(CustomTask(
                key=new_key.strip(),
                name=new_name.strip(),
                prompt_template=new_prompt.strip(),
                technology=tech
            ))
            db.commit()
            st.success(f"✅ Custom task added for '{tech}'. Refresh sidebar to see it.")

# 🔧 2. Manage Custom Tasks
st.sidebar.header("🔧 Manage Custom Tasks")
db = SessionLocal()
for ct in db.query(CustomTask).filter(CustomTask.technology == tech).order_by(CustomTask.key):
    with st.sidebar.expander(f"{ct.name} — `{ct.key}`"):
        edit_name = st.text_input("Name", ct.name, key=f"name_{ct.key}")
        edit_prompt = st.text_area("Prompt Template", ct.prompt_template,
                                   key=f"prompt_{ct.key}", height=100)
        c1, c2 = st.columns(2)
        if c1.button("Save Changes", key=f"save_{ct.key}"):
            ct.name = edit_name.strip()
            ct.prompt_template = edit_prompt.strip()
            db.commit()
            st.success("✅ Task updated; refresh to see.")
        if c2.button("Delete Task", key=f"delete_{ct.key}"):
            db.delete(ct)
            db.commit()
            st.warning("🗑️ Task deleted; refresh to see.")

# 📝 3. Provide Source Code or File
st.sidebar.header("3. Provide Source Code or File")
input_text = st.sidebar.text_area(f"Paste {tech} code/config", height=200)
uploaded = st.sidebar.file_uploader("...or upload any file", type=None)
if uploaded:
    try:
        input_text = uploaded.getvalue().decode("utf-8")
    except:
        st.sidebar.error("Non‑UTF8 file; please upload a text‑based file.")
        input_text = ""

# 🔍 4. Execution Mode
st.sidebar.header("4. Execution Mode")
mode = st.sidebar.selectbox("Select Mode:", ["Parallel", "Sequential", "Custom"])

# 🔧 5. Select / Order Tasks
task_map    = discover_tasks(tech)
display_map = {t.name: t.key for t in task_map.values()}
st.sidebar.header("5. Select / Order Tasks")
selected = st.sidebar.multiselect(
    "Choose tasks ▶",
    list(display_map.keys()),
    default=list(display_map.keys())[:3]
)
task_keys = [display_map[name] for name in selected]
workflow_name = st.sidebar.text_input("Save workflow (optional)")

st.sidebar.markdown("**Display Name → Internal Key**")
for disp, key in display_map.items():
    st.sidebar.text(f"- {disp} → `{key}`")

# ⚙️ 6. Define Custom Edges
st.sidebar.header("6. Define Custom Edges")
edges_example = r"""[
  {"source":"architecture","target":"components",
   "condition":"\"queue\" in results.get(\"architecture\",{}).get(\"services\",[])")"}
]"""
edges_json = st.sidebar.text_area(
    "Edges JSON/Python",
    value=st.session_state.get("custom_edges_json", edges_example),
    key="custom_edges_json",
    height=120
)
custom_edges = []
if mode == "Custom":
    try:
        custom_edges = json.loads(edges_json)
    except json.JSONDecodeError:
        try:
            custom_edges = ast.literal_eval(edges_json)
        except:
            custom_edges = []
elif mode == "Sequential":
    custom_edges = [
        {"source": task_keys[i], "target": task_keys[i+1]} 
        for i in range(len(task_keys)-1)
    ]
# Parallel: leave custom_edges = []

# 📈 7. Workflow Visualization
if task_keys:
    st.sidebar.header("7. Workflow Visualization")

    if mode == "Sequential":
        mermaid = "flowchart TD\n"
        for i in range(len(task_keys) - 1):
            mermaid += f"    {task_keys[i]} --> {task_keys[i+1]}\n"
        st.sidebar.code(mermaid, language="mermaid")

    elif mode == "Custom":
        if custom_edges:
            mermaid = "flowchart TD\n"
            for edge in custom_edges:
                src = edge["source"]; tgt = edge["target"]
                cond = edge.get("condition")
                if cond:
                    mermaid += f"    {src} --|{cond}| {tgt}\n"
                else:
                    mermaid += f"    {src} --> {tgt}\n"
            st.sidebar.code(mermaid, language="mermaid")
        else:
            st.sidebar.text("(No custom edges defined)")

    else:  # Parallel
        builder = build_workflow_graph(task_keys, custom_edges)
        try:
            mermaid_raw = builder.get_graph().to_mermaid()
            lines = [l for l in mermaid_raw.splitlines() if not l.strip().startswith("```")]
            clean = "\n".join(lines)
            st.sidebar.code(clean, language="mermaid")
        except Exception:
            inv = {v: k for k, v in display_map.items()}
            for edge in builder.get_graph().edges:
                s, t = edge[0], edge[1]
                st.sidebar.text(f"{inv.get(s,s)} → {inv.get(t,t)}")

# ▶ 8. Run Workflow
if st.sidebar.button("▶ Run Workflow"):
    if not input_text or not task_keys:
        st.sidebar.error("Please provide code & select tasks.")
    else:
        with st.spinner("Running tasks…"):
            results = Orchestrator(tech).run(
                input_text,
                task_keys,
                mode,
                workflow_name or None,
                custom_edges
            )

        # 📊 9. Display Results
        for disp_name, key in display_map.items():
            if key in results:
                st.subheader(disp_name)
                out = results[key]
                if key == "flowchart":
                    lines = [l.strip() for l in (out if isinstance(out,str) else out.get(key,"")).splitlines() if l.strip() and not l.strip().startswith("```")]
                    diagram = "\n".join(lines)
                    st.code(diagram, language="mermaid")
                elif key == "documentation":
                    st.markdown(out if isinstance(out,str) else out.get(key, ""))
                else:
                    txt = out if isinstance(out,str) else list(out.values())[0]
                    try:
                        st.json(json.loads(txt))
                    except:
                        st.code(txt)

        # 💾 10. Download Report
        st.download_button(
            "📥 Download Report JSON",
            json.dumps(results, indent=2),
            file_name="migration_report.json",
            mime="application/json"
        )
