import os
import glob
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# --- NEW: Import slowapi components ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import your new modules
from .core.data_loader import load_all_documents
from .core.llm_chain import create_retrieval_chain_from_docs

load_dotenv()

# --- NEW: Setup the rate limiter ---
# This will apply a limit of 5 requests per minute to each user (identified by their IP address).
limiter = Limiter(key_func=get_remote_address)

# --- Setup Application at Startup ---
app = FastAPI()
# Add the rate limiter to the app's state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- (The rest of your setup code remains the same) ---
all_docs = load_all_documents()
retrieval_chain = create_retrieval_chain_from_docs(all_docs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str

def search_illustrations(search_term: str):
    try:
        with open("public/illustrations.json", "r") as f:
            illustrations = json.load(f)
        if not search_term or search_term == "all":
            return illustrations
        query_words = set(search_term.lower().split())
        results = [
            img for img in illustrations
            if not query_words.isdisjoint(set(img["title"].lower().split()) | set(t.lower() for t in img["tags"]))
        ]
        return results
    except FileNotFoundError:
        return []

@app.post("/query")
@limiter.limit("5/minute")  # --- NEW: Apply the rate limit to this endpoint ---
async def query_endpoint(request: Request, query: Query): # Add request: Request
    question = query.question.lower().strip()

    specific_image_keywords = ["show me images of", "show me drawings of", "show me illustrations of", "show me art of", "show me image of", "show me drawing of", "show me illustration of", "images of", "image of", "show me", "see", "art of", "illustration of", "drawing of"]
    all_image_keywords = ["your art", "your illustrations", "your drawings", "all images", "all my illustrations"]

    if question in all_image_keywords:
        images = search_illustrations("all")
        if images:
            return {"answer": "Of course! Here are my illustrations:", "images": ["/illustrations/" + img["file"] for img in images]}
        else:
            return {"answer": "I couldn't find any illustrations."}

    for keyword in specific_image_keywords:
        if question.startswith(keyword):
            search_term = question.replace(keyword, "", 1).strip()
            if not search_term: continue
            found_images = search_illustrations(search_term)
            if found_images:
                return {"answer": f"Here are illustrations for '{search_term}':", "images": ["/illustrations/" + img["file"] for img in found_images]}

    response = retrieval_chain.invoke({"input": query.question})
    return {"answer": response["answer"]}

print("Backend setup complete. Ready for queries.")