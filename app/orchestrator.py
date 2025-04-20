# app/orchestrator.py

from app.db import init_db, SessionLocal, Workflow, TaskResult
from app.langgraph_workflow import build_workflow_graph
from app.tasks.registry import discover_tasks
from app.langgraph_workflow import build_workflow_graph


class Orchestrator:
    def __init__(self):
        init_db()
        self.db = SessionLocal()
        self.task_map = discover_tasks()

    def save_workflow(self, name: str, task_keys: list[str]):
        wf = Workflow(name=name, task_sequence=",".join(task_keys))
        self.db.add(wf)
        self.db.commit()
        return wf

    def run(
        self,
        input_text: str,
        task_keys: list[str],
        workflow_name: str = None,
        custom_edges: list[dict] = None
    ) -> dict[str, dict]:
        """
        Executes tasks via a LangGraph graph, with optional custom_edges.
        Returns a dict: { task_key: output }.
        """
        # 1) Optionally persist workflow definition
        if workflow_name:
            self.save_workflow(workflow_name, task_keys)

        # 2) Build & invoke the LangGraph workflow
        graph = build_workflow_graph(task_keys, custom_edges or [])
        initial_state = {"code": input_text, "results": {}}
        final_state = graph.invoke(initial_state)

        # 3) Return the merged results
        return final_state["results"]
