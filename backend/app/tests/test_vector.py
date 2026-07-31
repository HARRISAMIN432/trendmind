from app.agents.embedding_agent import get_embedding_function
from app.vectorstore.chroma_client import get_vectorstore, query_similar_with_scores

import numpy as np

embedding_fn = get_embedding_function()
vectorstore = get_vectorstore(embedding_fn)

text = """
Microsoft
"""

doc = embedding_fn.embed_documents([text])[0]
query = embedding_fn.embed_query(text)

cosine = np.dot(doc, query) / (
    np.linalg.norm(doc) * np.linalg.norm(query)
)
print("Cosine similarity (self-check):", cosine)

# --- retrieve actual similar articles from Chroma Cloud ---
results = query_similar_with_scores(vectorstore, query, n_results=5)

print(f"\nTop {len(results)} retrieved docs:\n")
for r in results:
    title = r["metadata"].get("title", "(no title)")
    url = r["metadata"].get("url", "(no url)")
    match_percent = round(r["score"] * 100, 1) if r["score"] is not None else None
    print(f"  {match_percent}%  {title}")
    print(f"        {url}")
    print(f"        distance={r['distance']:.4f}")
    print()