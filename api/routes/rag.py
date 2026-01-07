from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from api.services.rag_service import rag_service
from api.middleware.auth import verify_api_key
import logging

router = APIRouter(prefix="/api/rag", tags=["RAG Forensics"])
logger = logging.getLogger(__name__)

class RAGQuery(BaseModel):
    case_id: str
    query: str
    n_results: int = 5

class RAGResponse(BaseModel):
    documents: List[str]
    metadatas: List[dict]
    distances: List[float]

@router.post("/query", response_model=RAGResponse)
async def query_rag(request: RAGQuery, _=Depends(verify_api_key)):
    """
    Query the RAG system for a specific case
    """
    try:
        results = rag_service.query(request.case_id, request.query, request.n_results)
        if not results or not results['documents']:
            return {"documents": [], "metadatas": [], "distances": []}
        
        return {
            "documents": results['documents'][0],
            "metadatas": results['metadatas'][0],
            "distances": results['distances'][0] if 'distances' in results else []
        }
    except Exception as e:
        logger.error(f"Error querying RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
async def ingest_text(
    case_id: str = Form(...),
    text: str = Form(...),
    source: str = Form(...),
    _=Depends(verify_api_key)
):
    """
    Ingest text evidence into the RAG system
    """
    try:
        success = rag_service.add_document(case_id, text, {"source": source})
        if not success:
            raise HTTPException(status_code=500, detail="Failed to ingest document")
        return {"status": "success", "message": "Document ingested"}
    except Exception as e:
        logger.error(f"Error ingesting text: {e}")
        raise HTTPException(status_code=500, detail=str(e))
