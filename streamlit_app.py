# streamlit_app.py

import os
from dotenv import load_dotenv

# 1) Load .env before anything else
load_dotenv()

import streamlit as st
import streamlit.components.v1 as components
import json, ast

# 2) Early check for Salesforce Gateway env variables
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

# 3) Safe to import rest now
from app.db import SessionLocal, CustomTask
from app.orchestrator import Orchestrator
from app.tasks.registry import discover_tasks
from app.langgraph_workflow import build_workflow_graph
from langgraph.graph import START, END

# Streamlit UI setup
st.set_page_config(page_title="Tibco→MuleSoft Migration", layout="wide")
st.title("🔄 Tibco → MuleSoft Migration Analyzer (MVP)")

# ➕ Add New Custom Task
st.sidebar.header("➕ Add New Task")
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
                prompt_template=new_prompt.strip()
            ))
            db.commit()
            st.success(f"✅ Custom task '{new_name}' added. Rerun to see it!")

# 🔧 Manage Existing Custom Tasks
st.sidebar.header("🔧 Manage Custom Tasks")
db = SessionLocal()
for ct in db.query(CustomTask).order_by(CustomTask.key):
    with st.sidebar.expander(f"{ct.name}  —  `{ct.key}`", expanded=False):
        edit_name = st.text_input("Name", value=ct.name, key=f"name_{ct.key}")
        edit_prompt = st.text_area("Prompt Template", value=ct.prompt_template,
                                   key=f"prompt_{ct.key}", height=100)
        col1, col2 = st.columns(2)
        if col1.button("Save Changes", key=f"save_{ct.key}"):
            ct.name = edit_name.strip()
            ct.prompt_template = edit_prompt.rstrip()
            db.commit()
            st.success(f"Saved updates for `{ct.key}`. Reloading...")
            st.experimental_rerun()
        if col2.button("Delete Task", key=f"delete_{ct.key}"):
            db.delete(ct)
            db.commit()
            st.warning(f"Deleted task `{ct.key}`. Reloading...")
            st.experimental_rerun()

# 1. Provide Tibco Code or File
st.sidebar.header("1. Provide Tibco Code or File")
input_text = st.sidebar.text_area("Paste code/config", height=200)
uploaded = st.sidebar.file_uploader(
    "...or upload any file (decoded as UTF-8)",
    type=None
)
if uploaded:
    try:
        raw = uploaded.getvalue()
        input_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        st.sidebar.error("Uploaded file is not UTF-8 text. Please upload a text-based file.")
        input_text = ""

# 2. Select / Order Tasks
task_map    = discover_tasks()                          # key → BaseTask
display_map = {t.name: t.key for t in task_map.values()}   # display name → key

st.sidebar.header("2. Select / Order Tasks")
selected = st.sidebar.multiselect(
    "Choose tasks ▶",
    list(display_map.keys()),
    default=list(display_map.keys())[:3]
)
task_keys = [display_map[name] for name in selected]
workflow_name = st.sidebar.text_input("Save workflow as (optional)")

# Show mapping for internal keys
st.sidebar.markdown("**Task Key → Internal Key**")
for disp, key in display_map.items():
    st.sidebar.text(f"- {disp} → `{key}`")

# 3. (Optional) Define Custom Edges
st.sidebar.header("3. (Optional) Define Custom Edges")
st.sidebar.caption("Use JSON (double-quotes) or Python literal (single-quotes).")
edges_example = r'''
[
  {
    "source": "architecture",
    "target": "components",
    "condition": "\"queue\" in results.get(\"architecture\", {}).get(\"services\", [])"
  }
]
'''
edges_json = st.sidebar.text_area(
    "Edges (JSON or Python literal)",
    value=edges_example,
    height=140
)

# Parse custom_edges
if edges_json.strip():
    try:
        custom_edges = json.loads(edges_json)
    except json.JSONDecodeError:
        try:
            custom_edges = ast.literal_eval(edges_json)
            if not isinstance(custom_edges, list):
                raise ValueError("Must be a list of edge dicts")
        except Exception as e:
            st.sidebar.error(f"Invalid edges format: {e}")
            custom_edges = []
else:
    custom_edges = []

# Visualize the workflow graph
if task_keys:
    st.sidebar.header("🔍 Workflow Visualization")
    builder = build_workflow_graph(task_keys, custom_edges)
    try:
        mermaid = builder.get_graph().to_mermaid()
        st.sidebar.code(f"```mermaid\n{mermaid}\n```", language="mermaid")
    except Exception:
        st.sidebar.text("Edges:")
        inv_map = {v: k for k, v in display_map.items()}
        graph_obj = builder.get_graph()
        for edge in graph_obj.edges:
            src_key, tgt_key = edge[0], edge[1]
            src_name = inv_map.get(src_key, "__start__" if src_key == START else src_key)
            tgt_name = inv_map.get(tgt_key, "__end__"   if tgt_key == END   else tgt_key)
            st.sidebar.text(f"{src_name} → {tgt_name}")

# ▶ Run Workflow
if st.sidebar.button("▶ Run Workflow"):
    if not input_text or not task_keys:
        st.sidebar.error("Please provide Tibco code & select at least one task.")
    else:
        with st.spinner("Running tasks…"):
            orch = Orchestrator()
            results = orch.run(
                input_text,
                task_keys,
                workflow_name or None,
                custom_edges
            )

        # Display outputs with correct rendering per task
        for disp_name, key in display_map.items():
            if key in results:
                st.subheader(disp_name)
                out = results[key]
                # FlowChart: render mermaid
                if key == "flowchart":
                    mermaid_str = out if isinstance(out, str) else out.get(key, "")
                    st.code(mermaid_str, language="mermaid")
                # Documentation: render Markdown
                elif key == "documentation":
                    doc = out if isinstance(out, str) else out.get(key, "")
                    st.markdown(doc)
                else:
                    # Try to parse JSON-producing tasks; else show code
                    text = out if isinstance(out, str) else list(out.values())[0]
                    try:
                        parsed = json.loads(text)
                        st.json(parsed)
                    except Exception:
                        st.code(text, language="json")

        # Download combined JSON report
        st.download_button(
            "📥 Download Report JSON",
            json.dumps(results, indent=2),
            file_name="tibco_migration_report.json",
            mime="application/json",
            key="download_report"
        )