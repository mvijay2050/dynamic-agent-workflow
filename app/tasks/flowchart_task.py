from .base_task import BaseTask
from app.langchain_chains import flowchart_chain

class FlowChartTask(BaseTask):
    @property
    def key(self): return "flowchart"
    @property
    def name(self): return "Application FlowChart"

    def run(self, input_text: str) -> dict:
        result = flowchart_chain.run({"code": input_text})
        return {"flowchart": result}
