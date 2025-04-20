from .base_task import BaseTask
from app.langchain_chains import architecture_chain

class ArchitectureTask(BaseTask):
    @property
    def key(self): return "architecture"
    @property
    def name(self): return "Application Architecture"

    def run(self, input_text: str) -> dict:
        result = architecture_chain.run({"code": input_text})
        return {"architecture": result}
