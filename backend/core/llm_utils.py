import logging
from typing import Any, Dict, List

from langchain.prompts import PromptTemplate
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Define a Pydantic model for structured output
class QueryAnalysis(BaseModel):
    """Structured representation of a query's analysis."""
    query: str
    topics: List[str]
    complexity: str
    intent: str

def analyze_query_with_llm(llm: BaseLanguageModel, query: str) -> Dict[str, Any]:
    """
    Analyze a user's query using an LLM to extract topics, complexity, and intent.
    """
    parser = JsonOutputParser(pydantic_object=QueryAnalysis)

    prompt = PromptTemplate(
        template="""
Analyze the user's query and provide a structured analysis in JSON format.
The query is: "{query}"

Your analysis should identify the following:
1.  **topics**: A list of the main subjects or topics the query is about.
    Choose from the following list or add a new one if necessary:
    - technical
    - experience
    - skills
    - about
    - creative
    - project
    - general
2.  **complexity**: The estimated complexity of the query.
    Choose one: simple, moderate, complex.
3.  **intent**: The user's likely intent.
    Choose one: question, retrieval, explanation, general.

{format_instructions}
""",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        response = chain.invoke({"query": query})
        return response
    except Exception as e:
        logger.error(f"Error analyzing query with LLM: {e}")
        # Fallback to a simple default
        return {
            "query": query,
            "topics": ["general"],
            "complexity": "simple",
            "intent": "general",
        }

from langchain.output_parsers import CommaSeparatedListOutputParser

def extract_topics_with_llm(llm: BaseLanguageModel, text: str) -> List[str]:
    """
    Extract relevant topics from a text chunk using an LLM.
    """
    output_parser = CommaSeparatedListOutputParser()

    prompt = PromptTemplate(
        template="""
You are an expert at analyzing text and extracting key topics.
Analyze the following text chunk and extract a comma-separated list of 1-5 main topics that describe its content.
The topics should be concise and relevant.
Choose from the following list if applicable, but you can also generate new topics if needed:
- technical
- experience
- skills
- about
- creative
- project
- personal
- code
- documentation

Text chunk:
"{text}"

Your comma-separated list of topics:
""",
        input_variables=["text"],
    )

    chain = prompt | llm | output_parser

    try:
        # Limit text size to avoid excessive token usage
        max_text_length = 2000
        truncated_text = text[:max_text_length]

        response = chain.invoke({"text": truncated_text})
        # Sanitize and clean up topics
        return [topic.strip().lower() for topic in response if topic.strip()]
    except Exception as e:
        logger.error(f"Error extracting topics with LLM: {e}")
        # Fallback to a default topic
        return ["general"]

def rerank_documents_with_llm(llm: BaseLanguageModel, query: str, documents: List[Any]) -> List[Any]:
    """
    Re-rank a list of documents based on their relevance to a query using an LLM.
    """
    if not documents:
        return []

    output_parser = CommaSeparatedListOutputParser()

    document_snippets = "\n".join(
        [f"Document {i}: {doc.page_content[:500]}..." for i, doc in enumerate(documents)]
    )

    prompt = PromptTemplate(
        template="""
You are an expert relevance ranker. I will provide you with a user query and a list of document snippets, each with an index.
Your task is to return a comma-separated list of the indices, ordered from most relevant to least relevant.
Only return the indices that are relevant to the query.

User Query: "{query}"

Documents:
{document_snippets}

Re-ordered list of relevant indices (most relevant first):
""",
        input_variables=["query", "document_snippets"],
    )

    chain = prompt | llm | output_parser

    try:
        response = chain.invoke({"query": query, "document_snippets": document_snippets})

        reordered_indices = [int(i.strip()) for i in response]

        # Create a new list of documents in the re-ordered sequence
        reordered_docs = [documents[i] for i in reordered_indices if i < len(documents)]

        return reordered_docs
    except Exception as e:
        logger.error(f"Error re-ranking documents with LLM: {e}")
        # Fallback to original order if re-ranking fails
        return documents
