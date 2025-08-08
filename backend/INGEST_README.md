# Drop-in Knowledge Ingestion

1. Ensure `backend/knowledge/` exists. Drop PDFs/MD/HTML/TXT/DOCX/CSV/JSON there.
2. `pip install -r backend/requirements.txt` (or root requirements if you use that).
3. Start backend. On startup, it will sync knowledge into `backend/.chroma`.
4. `/query` will now search your existing sources **plus** the new `knowledge` retriever by default.
