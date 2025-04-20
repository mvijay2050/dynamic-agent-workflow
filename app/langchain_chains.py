# app/langchain_chains.py
import os
from app.llm_client import SalesforceGatewayLLM
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Load settings from .env
LLM_URL      = os.getenv("SF_LLM_URL")
LLM_MODEL    = os.getenv("SF_LLM_MODEL")
LLM_API_KEY  = os.getenv("SF_LLM_API_KEY")
FEATURE_ID   = os.getenv("SF_FEATURE_ID")
TENANT_ID    = os.getenv("SF_TENANT_ID")
VERIFY_PATH  = os.getenv("SF_VERIFY_PATH")

# Initialize the Salesforce Gateway LLM client
gateway_llm = SalesforceGatewayLLM(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    url=LLM_URL,
    generation_settings={
        "max_tokens": int(os.getenv("SF_LLM_MAX_TOKENS", "16384")),
        "temperature": float(os.getenv("SF_LLM_TEMPERATURE", "0.0")),
        "parameters": {}
    },
    headers_extra={
        "x-client-feature-id": FEATURE_ID,
        "x-sfdc-core-tenant-id": TENANT_ID
    },
    verify=VERIFY_PATH
)

def _make_chain(template: str) -> LLMChain:
    """
    Helper to create a LangChain LLMChain using the Salesforce gateway.
    """
    prompt = PromptTemplate(input_variables=["code"], template=template)
    return LLMChain(llm=gateway_llm, prompt=prompt)

# Define individual chains for each task
architecture_chain = _make_chain(
    """
Analyze the following TIBCO application code and describe its high-level architecture in JSON:
{code}
"""
)

components_chain = _make_chain(
    """
List all major components in this TIBCO code as JSON:
{code}
"""
)

flowchart_chain = _make_chain(
    """
Generate mermaid.js syntax for a flowchart of this TIBCO code:
{code}
"""
)

documentation_chain = _make_chain(
    """
Write comprehensive developer documentation for this TIBCO application:
{code}
"""
)

cdm_chain = _make_chain(
    """
Convert the following TIBCO constructs into a JSON common data model:
{code}
"""
)
