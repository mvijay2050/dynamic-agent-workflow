# app/tasks/registry.py
import os
import importlib
from typing import Dict
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.db import SessionLocal, CustomTask
from app.tasks.base_task import BaseTask
from app.llm_client import SalesforceGatewayLLM
from langchain import LLMChain
from langchain.prompts import PromptTemplate

# 1) Ensure .env is loaded
load_dotenv()

# 2) Instantiate the same gateway_llm for custom tasks
gateway_llm = SalesforceGatewayLLM(
    model=os.getenv("SF_LLM_MODEL"),
    api_key=os.getenv("SF_LLM_API_KEY"),
    url=os.getenv("SF_LLM_URL"),
    generation_settings={
        "max_tokens": int(os.getenv("SF_LLM_MAX_TOKENS", "16384")),
        "temperature": os.getenv("SF_LLM_TEMPERATURE", "0.0"),
        "parameters": {}
    },
    headers_extra={
        "x-client-feature-id": os.getenv("SF_FEATURE_ID"),
        "x-sfdc-core-tenant-id": os.getenv("SF_TENANT_ID")
    },
    verify=os.getenv("SF_VERIFY_PATH")
)

def discover_tasks(for_tech: str) -> Dict[str, BaseTask]:
    """
    Discover both built-in and custom tasks filtered by source technology.

    :param for_tech: The source technology key (e.g. "TIBCO", "BizTalk").
    :return: Mapping of task_key to BaseTask instance.
    """
    tasks: Dict[str, BaseTask] = {}

    # Built-in tasks
    task_folder = os.path.dirname(__file__)
    for fname in os.listdir(task_folder):
        if not fname.endswith("_task.py") or fname == "base_task.py":
            continue
        module_name = f"app.tasks.{fname[:-3]}"
        mod = importlib.import_module(module_name)
        for attr in dir(mod):
            cls = getattr(mod, attr)
            if (
                isinstance(cls, type)
                and issubclass(cls, BaseTask)
                and cls is not BaseTask
            ):
                inst: BaseTask = cls()
                # Only include if this task supports the given technology
                if for_tech in getattr(inst, "supported_techs", []):
                    tasks[inst.key] = inst

    # Custom tasks from DB
    db: Session = SessionLocal()
    for ct in db.query(CustomTask).filter(CustomTask.technology == for_tech):
        prompt = PromptTemplate(input_variables=["code"], template=ct.prompt_template)
        chain  = LLMChain(llm=gateway_llm, prompt=prompt)

        class _Custom(BaseTask):
            @property
            def key(self) -> str:
                return ct.key

            @property
            def name(self) -> str:
                return ct.name

            # custom tasks inherit all techs or you can restrict
            supported_techs = [for_tech]

            def run(self, input_text: str) -> dict:
                out = chain.run({"code": input_text})
                return {ct.key: out}

        tasks[ct.key] = _Custom()

    return tasks
