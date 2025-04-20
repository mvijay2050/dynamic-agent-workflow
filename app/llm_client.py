# app/llm_client.py
import os
import requests
from typing import Optional, List, Mapping, Any
from langchain.llms.base import LLM

class SalesforceGatewayLLM(LLM):
    """
    A LangChain LLM wrapper for Salesforce LLM Gateway.
    """
    model: str
    api_key: str
    url: str
    generation_settings: Mapping[str, Any]
    headers_extra: Mapping[str, str]
    verify: Optional[str] = None

    # Allow arbitrary types in Pydantic V2
    model_config = {
        "arbitrary_types_allowed": True
    }

    @property
    def _llm_type(self) -> str:
        return "salesforce_gateway"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        # Build request payload
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "model": self.model,
            "generation_settings": self.generation_settings,
            "parallel_calls": "true"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"API_KEY {self.api_key}",
            **self.headers_extra
        }
        # Send request
        resp = requests.post(
            self.url,
            json=body,
            headers=headers,
            verify=self.verify or True
        )
        resp.raise_for_status()
        data = resp.json()

        # 1) Salesforce v2 gateway wraps in 'generation_details' -> 'generations'
        gen_det = data.get("generation_details") or data.get("generation_details", {})
        if gen_det:
            gens = gen_det.get("generations")
            if isinstance(gens, list) and gens:
                first = gens[0]
                # nested message style
                if isinstance(first, dict) and "message" in first:
                    return first["message"].get("content", "")
                # direct content style
                content = first.get("content") or first.get("text")
                if isinstance(content, str):
                    return content

        # 2) Salesforce v1: top-level 'generations'
        if "generations" in data:
            gens = data.get("generations")
            if isinstance(gens, list) and gens:
                first = gens[0]
                if isinstance(first, dict) and "message" in first:
                    return first["message"].get("content", "")
                return first.get("content", "")

        # 3) OpenAI-style fallback
        if "choices" in data:
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                choice = choices[0]
                if isinstance(choice, dict):
                    if "message" in choice:
                        return choice["message"].get("content", "")
                    return choice.get("text", "")

        # 4) Unexpected format: return raw JSON or error
        raise ValueError(f"Could not extract content from response: {data}")
