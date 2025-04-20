# app/langgraph_workflow.py

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, START, END
from app.tasks.registry import discover_tasks

# Define a state where 'results' is merged via dict '|'
class WorkflowState(TypedDict):
    code: str
    results: Annotated[Dict[str, Any], operator.or_]


def build_workflow_graph(
    task_keys: List[str],
    custom_edges: Optional[List[Dict[str, Any]]] = None
):
    """
    Build a LangGraph StateGraph that:
      • Starts selected tasks in parallel
      • Merges 'results' dicts using Python 3.9+ dict merge (|)
      • Applies optional conditional or sequential custom_edges
    """
    graph = StateGraph(WorkflowState)
    task_map = discover_tasks()
    valid = set(task_keys)

    # 1) Register each task as a node
    for key in task_keys:
        task = task_map[key]
        def node_fn(state: WorkflowState, t=task):
            out = t.run(state["code"])
            # Return a dict: merge via 'operator.or_'
            return {"results": out}
        graph.add_node(key, node_fn)

    # 2) Parallel entry
    for key in task_keys:
        graph.add_edge(START, key)

    # 3) Register finish points
    for key in task_keys:
        graph.set_finish_point(key)

    # 4) Apply custom edges if provided
    if custom_edges:
        for edge in custom_edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src not in valid or tgt not in valid:
                continue
            cond = edge.get("condition")
            if cond:
                def cond_fn(state: WorkflowState, expr=cond, target=tgt):
                    try:
                        return target if eval(expr, {}, {"results": state["results"]}) else END
                    except Exception:
                        return END
                graph.add_conditional_edges(
                    src,
                    cond_fn,
                    {tgt: tgt, END: END}
                )
            else:
                graph.add_edge(src, tgt)

    # Compile and return runnable graph
    return graph.compile()
