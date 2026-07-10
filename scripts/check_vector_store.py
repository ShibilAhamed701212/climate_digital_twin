"""Check the contents of the vector store."""

import joblib

meta = joblib.load("knowledge/vector_store/metadata.pkl")
print(f"Total chunks: {len(meta)}")
for m in meta:
    title = m["title"][:50]
    cat = m["category"]
    size = len(m["content"])
    doc_id = m["document_id"][:12]
    print(f"  {doc_id}  {title:50s}  {cat:15s}  {size:5d}B")
