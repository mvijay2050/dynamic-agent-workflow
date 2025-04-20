from .base_task import BaseTask
from app.langchain_chains import cdm_chain

class CDMTask(BaseTask):
    @property
    def key(self): return "cdm"
    @property
    def name(self): return "Convert to Common Data Model In JSON formar."

    def run(self, input_text: str) -> dict:
        result = cdm_chain.run({"code": input_text})
        return {"cdm": result}
