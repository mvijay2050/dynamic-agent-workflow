# app/orchestrator.py

from app.db import init_db, SessionLocal, Workflow
from app.langgraph_workflow import build_workflow_graph
from app.tasks.registry import discover_tasks

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
        mode: str = "Parallel",
        workflow_name: str = None,
        custom_edges: list[dict] = None
    ) -> dict[str, dict]:
        """
        Executes tasks according to mode:
        - Parallel: all tasks run independently in LangGraph
        - Sequential: feeds output of each task as input to the next
        - Custom: runs LangGraph with given custom_edges
        Returns a mapping of task_key to its output.
        """
        # Optionally persist workflow definition
        if workflow_name:
            self.save_workflow(workflow_name, task_keys)

        # Sequential execution: simple pipeline
        if mode == "Sequential":
            results: dict[str, dict] = {}
            data = input_text
            for key in task_keys:
                task = self.task_map[key]
                out = task.run(data)
                results[key] = out if isinstance(out, dict) else {key: out}
                # determine next input
                if isinstance(out, str):
                    data = out
                elif isinstance(out, dict) and out:
                    # pick first value
                    data = next(iter(out.values()))
                else:
                    data = str(out)
            return results

        # Parallel or Custom: build and invoke LangGraph
        edges = custom_edges if mode == "Custom" else []
        graph = build_workflow_graph(task_keys, edges)
        initial_state = {"code": input_text, "results": {}}
        final_state = graph.invoke(initial_state)
        return final_state.get("results", {})
