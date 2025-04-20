from .base_task import BaseTask
from app.langchain_chains import documentation_chain

class DocumentationTask(BaseTask):
    @property
    def key(self): return "documentation"
    @property
    def name(self): return "Application Documentation"

    def run(self, input_text: str) -> dict:
        result = documentation_chain.run({"code": input_text})
        return {"documentation": result}
