import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import the fuzzy matching library
from thefuzz import process

# Import your custom modules
from .core.data_loader import load_all_documents
from .core.llm_chain import create_retrieval_chain_from_docs

load_dotenv()

# --- Setup Application at Startup ---
app = FastAPI()

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


# --- YOUR CORRECTED FUZZY SEARCH FUNCTION ---
def search_illustrations(search_term: str):
    try:
        with open("public/illustrations.json", "r") as f:
            illustrations = json.load(f)

        if not search_term or search_term.lower() == "all":
            return [{"file": img["file"]} for img in illustrations]

        # Handle common singular/plural conversions
        search_terms = [search_term]
        if search_term.endswith('s'):
            # Add singular form (remove trailing 's')
            search_terms.append(search_term[:-1])
        else:
            # Add plural form (add 's')
            search_terms.append(search_term + 's')

        # Create a dictionary where keys are image files and values are searchable strings
        choices = {
            img["file"]: f"{img['title']} {' '.join(img['tags'])}"
            for img in illustrations
        }

        all_matches = []
        for term in search_terms:
            # Use thefuzz to find matches
            found_matches = process.extract(term, choices, limit=10)
            # Lower the threshold to 55 to be more lenient
            matches = [{"file": key} for match, score, key in found_matches if score >= 55]
            all_matches.extend(matches)

        # Remove duplicates
        unique_matches = []
        seen_files = set()
        for match in all_matches:
            if match["file"] not in seen_files:
                unique_matches.append(match)
                seen_files.add(match["file"])

        return unique_matches
    except FileNotFoundError:
        return []


@app.post("/query")
async def query_endpoint(query: Query):
    question = query.question.lower().strip()

    specific_image_keywords = [
        "images of", "image of", "drawings of", "drawing of", "illustrations of", "illustration of", "art of"
    ]
    all_image_phrases = [
        "show me all illustrations", "show all illustrations", "show me your illustrations",
        "show me all your art", "show me all images", "show me images", "show your art"
    ]

    for trigger in specific_image_keywords:
        if trigger in question:
            search_term = question.split(trigger, 1)[1].strip()
            if search_term:
                found_images = search_illustrations(search_term)
                if found_images:
                    image_urls = ["/illustrations/" + img["file"] for img in found_images]
                    return {"answer": f"Here are the illustrations I found for '{search_term}':", "images": image_urls}
                else:
                    return {
                        "answer": f"Sorry, I couldn't find any illustrations of '{search_term}'. You can ask to see all of my art."}

    if question in all_image_phrases:
        all_images = search_illustrations("all")
        if all_images:
            image_urls = ["/illustrations/" + img["file"] for img in all_images]
            return {"answer": "Of course! Here are some of my illustrations:", "images": image_urls}
        else:
            return {"answer": "I couldn't find any illustrations at the moment."}

    response = retrieval_chain.invoke({"input": query.question})
    return {"answer": response["answer"]}


print("Backend setup complete. Ready for queries.")