# app/orchestrator.py

from typing import Optional
from app.db import init_db, SessionLocal, Workflow
from app.langgraph_workflow import build_workflow_graph
from app.tasks.registry import discover_tasks

class Orchestrator:
    def __init__(self, technology: Optional[str] = None):
        """
        Initialize the orchestrator for a given source technology.
        :param technology: e.g. "TIBCO", "BizTalk", etc.
        """
        # Ensure database tables exist
        init_db()
        self.db = SessionLocal()
        # Load only tasks supported for this technology
        self.task_map = discover_tasks(technology)

    def save_workflow(self, name: str, task_keys: list[str]):
        wf = Workflow(name=name, task_sequence=",".join(task_keys))
        self.db.add(wf)
        self.db.commit()
        return wf

    def run(
        self,
        input_text: str,
        task_keys: list[str],
        mode: str = "Parallel",
        workflow_name: str = None,
        custom_edges: list[dict] = None
    ) -> dict[str, dict]:
        """
        Executes tasks according to mode:
        - Parallel: all tasks run independently via LangGraph
        - Sequential: feeds output of each task as input to the next
        - Custom: runs LangGraph with given custom_edges

        Returns a mapping of task_key → its output (dict or string).
        """
        # Persist workflow if a name was given
        if workflow_name:
            self.save_workflow(workflow_name, task_keys)

        # 1) Sequential mode: pipeline each task's output to the next
        if mode == "Sequential":
            results: dict[str, dict] = {}
            data = input_text
            for key in task_keys:
                if key not in self.task_map:
                    continue  # skip unknown tasks
                task = self.task_map[key]
                out = task.run(data)
                # Normalize output
                results[key] = out if isinstance(out, dict) else {key: out}
                # Prepare next input
                if isinstance(out, str):
                    data = out
                else:
                    data = next(iter(results[key].values()), "")
            return results

        # 2) Parallel or Custom: build and invoke LangGraph
        edges = custom_edges if mode == "Custom" else []
        graph = build_workflow_graph(task_keys, edges)
        initial_state = {"code": input_text, "results": {}}
        final_state = graph.invoke(initial_state)
        return final_state.get("results", {})
