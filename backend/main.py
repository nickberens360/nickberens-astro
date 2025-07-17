import os
import glob
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import your new modules
from .core.data_loader import load_all_documents
from .core.llm_chain import create_retrieval_chain_from_docs

load_dotenv()

# --- Setup Application at Startup ---
app = FastAPI()

# Load documents and create the retrieval chain once when the app starts
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


# --- NEW AND IMPROVED SEARCH FUNCTION ---
def search_illustrations(search_term: str):
    try:
        with open("public/illustrations.json", "r") as f:
            illustrations = json.load(f)

        if not search_term or search_term == "all":
            return illustrations

        # Tokenize the search query into a set of unique words
        query_words = set(search_term.lower().split())
        # Remove common "stop words" that don't add meaning
        stop_words = {"and", "the", "of", "a", "an", "with"}
        query_words = query_words - stop_words

        results = []
        for img in illustrations:
            # Create a combined set of all searchable words for the image
            image_words = set(img["title"].lower().split())
            for tag in img["tags"]:
                image_words.add(tag.lower())

            # --- THE CORE LOGIC FIX ---
            # Check if there is any intersection (at least one common word).
            # This performs an "OR" search for the keywords.
            if not query_words.isdisjoint(image_words):
                results.append(img)

        return results
    except FileNotFoundError:
        return []


@app.post("/query")
async def query_endpoint(query: Query):
    question = query.question.lower().strip()

    specific_image_keywords = [
        "images of", "image of",
        "illustrations of", "illustration of",
        "drawings of", "drawing of",
        "art of"
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