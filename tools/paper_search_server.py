import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import xml.etree.ElementTree as ET

app = FastAPI()

class PaperSearchRequest(BaseModel):
    query: str
    max_results: int = 5 # default

@app.post("/paper_search")
async def paper_search(request: PaperSearchRequest):
    query = request.query
    max_results = request.max_results

    arxiv_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    try:
        response = requests.get(arxiv_url, params=params, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.strip()
            summary = entry.find('atom:summary', ns).text.strip()
            
            pdf_link = None
            for link in entry.findall('atom:link', ns):
                if link.get('title') == 'pdf':
                    pdf_link = link.get('href')
                    break
            
            authors = [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)]
            published = entry.find('atom:published', ns).text
            
            papers.append({
                "title": title,
                "authors": authors,
                "published": published,
                "summary": summary,
                "pdf_url": pdf_link
            })
        
        return {"status": "success", "papers": papers}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to arXiv API: {e}")
    except ET.ParseError:
        raise HTTPException(status_code=500, detail="Failed to parse arXiv API response (invalid XML).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")