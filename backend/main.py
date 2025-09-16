from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import tempfile
import json
from dotenv import load_dotenv

from opensearch_client import OpenSearchClient
from pdf_processor import PDFProcessor
from rag_service import RAGService

load_dotenv()

app = FastAPI(title="RAG Document Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://rag-frontend-305551183348.asia-northeast3.run.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "RAG System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Initialize services with error handling
try:
    osearch_client = OpenSearchClient()
    print("OpenSearch client initialized")
except Exception as e:
    print(f"Warning: OpenSearch client initialization failed: {e}")
    osearch_client = None

try:
    pdf_processor = PDFProcessor()
    print("PDF processor initialized")
except Exception as e:
    print(f"Warning: PDF processor initialization failed: {e}")
    pdf_processor = None

try:
    rag_service = RAGService()
    print("RAG service initialized")
except Exception as e:
    print(f"Warning: RAG service initialization failed: {e}")
    rag_service = None

@app.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    document_title: str = Form(...),
    tags: str = Form(...),  # JSON string of tags
    organization: str = Form(...),
    document_type: str = Form(...),
    assistant_id: str = Form(...)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not osearch_client or not pdf_processor:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    try:
        # Parse tags from JSON string
        tags_list = json.loads(tags) if tags else []
        
        # Save uploaded PDF file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Process PDF
        processed_data = pdf_processor.process_pdf_for_storage(
            tmp_file_path,
            document_title,
            tags_list,
            organization,
            document_type,
            assistant_id
        )
        
        # Store in OpenSearch
        stored_chunks = []
        for chunk in processed_data['chunks']:
            chunk_id = osearch_client.add_document_chunk(chunk)
            stored_chunks.append(chunk_id)
        
        # Clean up temporary files
        os.unlink(tmp_file_path)
        
        return {
            "status": "success",
            "document_id": processed_data['document_id'],
            "total_chunks": processed_data['total_chunks'],
            "total_pages": processed_data['total_pages'],
            "stored_chunks": len(stored_chunks)
        }
        
    except Exception as e:
        # Clean up temporary files on error
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/assistants")
async def get_assistants(organization: str = None):
    if not osearch_client:
        return {"assistants": []}  # Return empty list if service unavailable
    try:
        assistants = osearch_client.get_assistants(organization)
        return {"assistants": assistants}
    except Exception as e:
        return {"assistants": []}

@app.post("/query")
async def query_documents(
    question: str = Form(...),
    assistant_id: Optional[str] = Form(None),
    assistant_ids: Optional[str] = Form(None),
    response_mode: str = Form("individual"),  # "individual" or "integrated"
    summary_mode: bool = Form(False)  # Enhanced summary mode
):
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service temporarily unavailable")
    
    try:
        # Handle multiple assistant IDs
        if assistant_ids:
            import json
            assistant_list = json.loads(assistant_ids)
            
            if response_mode == "individual":
                # Individual responses from each assistant
                response = rag_service.get_individual_answers(question, assistant_list, summary_mode)
            else:
                # Integrated response (current behavior)
                response = rag_service.get_answer(question, assistant_list, summary_mode)
        else:
            # Handle single assistant ID (backward compatibility)
            response = rag_service.get_answer(question, assistant_id, summary_mode)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/extract-keywords")
async def extract_keywords(
    text: str = Form(...)
):
    """OpenAI API를 사용하여 텍스트에서 키워드를 추출합니다."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service temporarily unavailable")
    
    try:
        keywords = rag_service.extract_keywords_with_openai(text)
        return {"keywords": keywords}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting keywords: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)