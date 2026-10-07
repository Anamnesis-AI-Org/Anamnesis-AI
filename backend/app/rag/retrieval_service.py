import logging
import re
import asyncio
from app.rag.document_loader import WikipediaLoader, ResearchPaperLoader, HistoricalDatasetLoader, Document
from app.rag.embedding_service import get_embedding_service
from app.config import RAG_MAX_ARTICLES, RAG_MAX_PAPERS
from app.schemas import ScenarioContext

logger = logging.getLogger(__name__)

_retrieval_service = None


def get_retrieval_service():
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service


class RetrievalService:
    def __init__(self):
        self.embedding_service = get_embedding_service()
        # Seed historical dataset initially
        try:
            self.embedding_service.add_documents(HistoricalDatasetLoader.load_all())
        except Exception as e:
            logger.error("Failed to seed Historical Dataset: %s", e)

    async def retrieve(self, query_or_context: str | ScenarioContext, domain: str, n_results: int = 3) -> tuple[str, list[str], list[str]]:
        query = query_or_context.scenario if isinstance(query_or_context, ScenarioContext) else query_or_context

        # Decompose search queries if context is provided
        wikipedia_query = query
        arxiv_query = query
        wb_query = query
        un_query = query
        nasa_query = query
        noaa_query = query

        if isinstance(query_or_context, ScenarioContext):
            try:
                from app.rag.query_decomposer import decompose_query
                decomposed = await decompose_query(query_or_context)
                wikipedia_query = decomposed.get("wikipedia", query)
                arxiv_query = decomposed.get("arxiv", query)
                wb_query = decomposed.get("worldbank", query)
                un_query = decomposed.get("un_data", query)
                nasa_query = decomposed.get("nasa", query)
                noaa_query = decomposed.get("noaa", query)

                # Pick domain-specific primary query
                if domain == "history":
                    query = wikipedia_query
                elif domain == "economy":
                    query = wb_query
                elif domain == "society":
                    query = un_query
                elif domain == "climate":
                    query = noaa_query
                elif domain == "technology":
                    query = arxiv_query
            except Exception as e:
                logger.error("RAG Retrieval │ Failed decomposing query: %s", e)

        # Domain fingerprint for source activation (see task 2/5/6 below).
        text = query.lower()

        # Build tasks to fetch documents.
        tasks = []

        # 1. Wikipedia (always active).
        tasks.append(WikipediaLoader.load(wikipedia_query, max_articles=RAG_MAX_ARTICLES))

        # 3. World Bank (economy/history only).
        if domain in ("economy", "history"):
            from app.rag.sources.worldbank import WorldBankConnector
            tasks.append(WorldBankConnector.fetch(wb_query))

        # 4. UN Data (society/history only).
        if domain in ("society", "history"):
            from app.rag.sources.un_data import UNDataConnector
            tasks.append(UNDataConnector.fetch(un_query))

        # 5. NASA (climate/technology only).
        if domain in ("climate", "technology"):
            from app.rag.sources.nasa import NASAConnector
            tasks.append(NASAConnector.fetch(nasa_query))

        # 6. NOAA (climate only). NOAA is skipped for healthcare because a
        #    "what if Modi was PM" counterfactual does not belong to the
        #    climate/energy domain: the pipeline discards the query instead of
        #    returning a generic climate dataset.
        if domain == "climate":
            from app.rag.sources.noaa import NOAAConnector
            tasks.append(NOAAConnector.fetch(noaa_query))

        # Run fetches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        fetched_docs = []
        sources = ["Historical Datasets"]

        # Extract fetched documents
        for res in results:
            if isinstance(res, list):
                for doc in res:
                    if isinstance(doc, Document):
                        fetched_docs.append(doc)
                        if doc.metadata.get("source"):
                            sources.append(doc.metadata["source"])
            elif isinstance(res, Exception):
                logger.error("RAG Retrieval │ Source fetch task failed: %s", res)

        # Chunk the retrieved documents
        from app.rag.chunker import chunk_documents
        chunks = chunk_documents(fetched_docs, chunk_size=800, chunk_overlap=150)

        # Index chunks dynamically
        if chunks:
            try:
                self.embedding_service.add_documents(chunks)
            except Exception as e:
                logger.error("RAG Retrieval │ Failed to index document chunks: %s", e)

        # Query top matches from indexed chunks
        hits = []
        try:
            # Fetch up to 8 candidates for re-ranking
            hits = self.embedding_service.query_similar(query, n_results=8)
        except Exception as e:
            logger.error("RAG Retrieval │ Failed querying embedding service: %s", e)

        # Re-rank hits based on text keyword relevance and distance
        from app.rag.reranker import rerank_hits
        top_hits = rerank_hits(query, hits, top_k=n_results)

        # Format retrieved reference block
        retrieved_titles = []
        context_lines = [
            "━━━ RETRIEVED REFERENCE MATERIAL ━━━",
            "Relevant documents retrieved from Wikipedia, research papers, and domain portals:",
            ""
        ]

        for idx, hit in enumerate(top_hits, 1):
            title = hit["metadata"].get("title", "Untitled Document")
            source = hit["metadata"].get("source", "Unknown Source")
            url = hit["metadata"].get("url", "")

            citation = f"{source} - \"{title}\""
            if url:
                citation += f" ({url})"

            retrieved_titles.append(f"{source} - \"{title}\"")
            context_lines.append(f"[{idx}] {citation}")
            context_lines.append(hit["content"])
            context_lines.append("")

        context_lines.append("━━━ END RETRIEVED MATERIAL ━━━")
        context_str = "\n".join(context_lines)

        return context_str, retrieved_titles, list(set(sources))
