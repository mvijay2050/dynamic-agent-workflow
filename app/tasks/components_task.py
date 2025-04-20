from .base_task import BaseTask
from app.langchain_chains import components_chain

class ComponentsTask(BaseTask):
    @property
    def key(self): return "components"
    @property
    def name(self): return "Application Components"

    def run(self, input_text: str) -> dict:
        result = components_chain.run({"code": input_text})
        return {"components": result}
