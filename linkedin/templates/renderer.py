# linkedin/actions/template.py
import logging
from typing import Dict, Any

import jinja2
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from linkedin.conf import AI_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def call_llm(prompt: str) -> str:
    """Call an LLM to generate content based on the prompt using LangChain and OpenAI."""
    # Check for required values; fail if missing
    if OPENAI_API_KEY is None:
        raise ValueError("OPENAI_API_KEY is not set in the environment or config.")

    logger.info(f"Calling '{AI_MODEL}'.")

    # Initialize the LangChain ChatOpenAI model with explicit API key
    llm = ChatOpenAI(model=AI_MODEL, temperature=0.7, api_key=OPENAI_API_KEY)  # Pass API key explicitly

    # Create a simple prompt template
    chat_prompt = ChatPromptTemplate.from_messages([
        ("human", "{prompt}"),
    ])

    # Chain the prompt with the LLM
    chain = chat_prompt | llm

    # Invoke the chain with the prompt
    response = chain.invoke({"prompt": prompt})

    # Extract the generated content
    return response.content.strip()


def render_template(template_file: str, template_type: str, context: Dict[str, Any]) -> str:
    logger.debug("Available template variables: %s", sorted(context.keys()))

    with open(template_file, 'r', encoding='utf-8') as f:
        template_str = f.read()

    match template_type:
        case 'jinja':
            return jinja2.Template(template_str).render(**context).strip()
        case 'ai_prompt':
            prompt = jinja2.Template(template_str).render(**context).strip()
            msg = call_llm(prompt)
            logger.debug(f"Sending: {msg}")
            return msg
        case _:
            raise ValueError(f"Unknown template_type: {template_type}")
