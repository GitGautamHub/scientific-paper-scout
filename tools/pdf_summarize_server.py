import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PyPDF2 import PdfReader
import io
import time 
import os

from llm_client import LLMClient 
from config import LLM_MODEL

app = FastAPI()

llm_summarizer = LLMClient() 

class PDFSummarizeRequest(BaseModel):
    pdf_url: str

@app.post("/pdf_summarize")
async def pdf_summarize(request: PDFSummarizeRequest):
    pdf_url = request.pdf_url
    
    # 1. download PDF
    try:
        response = requests.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check if content type is PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            raise HTTPException(status_code=400, detail="Provided URL does not point to a PDF.")

        pdf_bytes = io.BytesIO(response.content)

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to download PDF from {pdf_url}: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error during PDF download: {e}")

    # 2. extract text from PDF
    text_content = ""
    try:
        reader = PdfReader(pdf_bytes)
        for page in reader.pages:
            text_content += page.extract_text() or "" # Handle pages with no extractable text
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="No readable text found in the PDF.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {e}")

    # 3. summarize using LLM
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant specialized in summarizing scientific papers. Summarize the provided text from a PDF succinctly and accurately."},
            {"role": "user", "content": f"Please summarize the following scientific paper text:\n\n{text_content[:8000]}"} # text limit to avoid token limit
        ]

        summary_chunks = []
        for chunk in llm_summarizer.generate_response(messages):
            if llm_summarizer.provider == "openai":
                content = chunk.choices[0].delta.content
                if content:
                    summary_chunks.append(content)
            elif llm_summarizer.provider == "anthropic":
               if hasattr(chunk.delta, 'text'):
                   summary_chunks.append(chunk.delta.text)
            elif llm_summarizer.provider == "google":
               if chunk.text:
                   summary_chunks.append(chunk.text)
        
        summary = "".join(summary_chunks)

        if not summary.strip():
            raise HTTPException(status_code=500, detail="LLM failed to generate a summary.")

        return {"status": "success", "summary": summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize PDF content with LLM: {e}")
