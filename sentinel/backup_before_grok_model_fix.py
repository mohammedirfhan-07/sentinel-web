"""
SENTINEL — AI for Detecting Manipulative Digital Content
Backend: FastAPI server with Claude AI integration
"""

import os
import sys
import uuid
import json
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

import anthropic
import requests
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY", "").strip(' "\'')
if not GROK_API_KEY:
    print("=" * 60)
    print("ERROR: GROK_API_KEY not found.")
    print("1. Copy .env.example to .env")
    print("2. Add your Grok API key (from xAI)")
    print("=" * 60)
    sys.exit(1)

# In-memory storage
analysis_history: list[dict] = []

# FastAPI app
app = FastAPI(
    title="SENTINEL",
    description="AI for Detecting Manipulative Digital Content",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic Models ───────────────────────────────────────────────

class TextInput(BaseModel):
    content: str

class UrlInput(BaseModel):
    url: str

# ─── System Prompt ─────────────────────────────────────────────────

SYSTEM_PROMPT = """You are SENTINEL, an expert AI system for detecting manipulative digital content. 
You were built to protect people from psychological manipulation, coordinated 
influence operations, and disinformation campaigns.

When given content to analyze, respond ONLY with a valid JSON object. 
No preamble, no markdown, no explanation outside the JSON.

Return this exact structure:
{
  "risk_score": <integer 0-100>,
  "risk_level": "<LOW|MODERATE|HIGH|CRITICAL>",
  "verdict": "<one line verdict>",
  "techniques_detected": [
    {
      "name": "<technique name>",
      "severity": "<low|medium|high>",
      "explanation": "<1-2 sentences explaining why this technique is present>",
      "evidence": "<direct quote from the content>"
    }
  ],
  "psychological_target": "<2-3 sentences on who is targeted and what vulnerability>",
  "recommended_action": "<3-4 sentences of practical guidance>",
  "summary": "<one punchy paragraph a journalist could quote>",
  "clean": <true if no manipulation detected, false otherwise>
}

Risk score guide:
0-20: Clean content, minimal persuasion
21-50: Moderate — some persuasion but not necessarily malicious  
51-75: High risk — likely manipulative, verify before sharing
76-100: Critical — coordinated manipulation or disinfo campaign

Manipulation techniques to look for:
- Fear appeals / threat inflation
- False urgency or artificial scarcity  
- Emotional hijacking (outrage, disgust bait)
- Social proof manipulation / fake consensus
- Astroturfing / coordinated inauthentic behavior
- Disinformation / factual distortion
- Identity-based targeting (us vs them)
- Authority spoofing / false credibility
- DARVO (Deny Attack Reverse Victim Offender)
- Dog whistles / coded language
- Manufactured virality
- Deepfake or synthetic media indicators

Rules:
- Be specific. Quote exact phrases as evidence.
- If content is genuinely clean, return clean: true and risk_score under 20.
- Never refuse to analyze. Always return valid JSON.
- False positives are harmful. Only flag what is clearly present."""

# ─── Claude Analysis ───────────────────────────────────────────────

def analyze_with_grok(content: str) -> dict:
    """Send content to Grok for manipulation analysis."""
    try:
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-2",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Analyze the following content for manipulation:\n\n{content}"
                }
            ],
            "temperature": 0.1
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Authentication failed: Invalid Grok API Key. Ensure your real key is in the .env file.")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Grok API error: {response.text}")
            
        data = response.json()
        response_text = data["choices"][0]["message"]["content"].strip()

        # Try to extract JSON from fenced code blocks if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
        if json_match:
            response_text = json_match.group(1).strip()

        result = json.loads(response_text)
        return result

    except json.JSONDecodeError:
        # If Grok doesn't return valid JSON, return a fallback
        return {
            "risk_score": 0,
            "risk_level": "LOW",
            "verdict": "Analysis could not be completed — response parsing failed.",
            "techniques_detected": [],
            "psychological_target": "Unable to determine.",
            "recommended_action": "Please try again. If the issue persists, try with different content.",
            "summary": "The analysis engine returned an unparseable response. This is not a reflection of the content's safety.",
            "clean": True,
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"General error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# ─── URL Scraping ──────────────────────────────────────────────────

def scrape_url(url: str) -> dict:
    """Scrape a URL and extract article content + metadata."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unwanted elements
        for tag in soup.find_all(
            ["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]
        ):
            tag.decompose()

        # Remove ad-related elements
        for tag in soup.find_all(attrs={"class": re.compile(r"ad|sponsor|promo|banner|sidebar", re.I)}):
            tag.decompose()
        for tag in soup.find_all(attrs={"id": re.compile(r"ad|sponsor|promo|banner|sidebar", re.I)}):
            tag.decompose()

        # Extract title
        title = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]
        elif soup.title:
            title = soup.title.string
        if title:
            title = title.strip()

        # Extract author
        author = None
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            author = author_meta["content"].strip()
        else:
            author_tag = soup.find(attrs={"class": re.compile(r"author|byline", re.I)})
            if author_tag:
                author = author_tag.get_text(strip=True)

        # Extract publish date
        publish_date = None
        for attr in ["article:published_time", "datePublished", "date"]:
            date_meta = soup.find("meta", property=attr) or soup.find("meta", attrs={"name": attr})
            if date_meta and date_meta.get("content"):
                publish_date = date_meta["content"].strip()
                break
        if not publish_date:
            time_tag = soup.find("time")
            if time_tag:
                publish_date = time_tag.get("datetime") or time_tag.get_text(strip=True)

        # Extract meta description
        description = None
        desc_meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", property="og:description"
        )
        if desc_meta and desc_meta.get("content"):
            description = desc_meta["content"].strip()

        # Extract main content
        article_body = ""
        # Try common article containers
        article = (
            soup.find("article")
            or soup.find(attrs={"class": re.compile(r"article|post-content|entry-content|story-body", re.I)})
            or soup.find("main")
        )

        if article:
            paragraphs = article.find_all("p")
            article_body = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        
        if not article_body or len(article_body) < 100:
            # Fallback: get all paragraph text
            paragraphs = soup.find_all("p")
            article_body = "\n\n".join(
                p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20
            )

        if not article_body:
            # Last resort: get body text
            body = soup.find("body")
            if body:
                article_body = body.get_text(separator="\n", strip=True)

        # Fallback to metadata if body is still too short (e.g. JS-heavy SPAs)
        if len(article_body.strip()) < 50:
            fallback_parts = []
            if title: fallback_parts.append(title)
            if description: fallback_parts.append(description)
            if author: fallback_parts.append(f"By: {author}")
            fallback_text = "\n\n".join(fallback_parts)
            if fallback_text:
                article_body = fallback_text + "\n\n" + article_body

        domain = urlparse(url).netloc

        return {
            "success": True,
            "content": article_body[:10000],  # Cap at 10k chars
            "metadata": {
                "title": title,
                "author": author,
                "publish_date": publish_date,
                "domain": domain,
                "description": description,
            },
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out. The page took too long to respond."}
    except requests.exceptions.TooManyRedirects:
        return {"success": False, "error": "Too many redirects. The URL may be invalid."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Could not connect to the URL. Check if the address is correct."}
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "unknown"
        return {"success": False, "error": f"HTTP error {code}. The page may be paywalled or unavailable."}
    except Exception as e:
        return {"success": False, "error": f"Failed to scrape URL: {str(e)}"}

# ─── Build Report ──────────────────────────────────────────────────

def build_report(
    analysis: dict,
    content_type: str,
    input_preview: str,
    source_url: Optional[str] = None,
    scraped_metadata: Optional[dict] = None,
) -> dict:
    """Build a full SentinelReport object."""
    report = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_type": content_type,
        "input_preview": input_preview[:120],
        "source_url": source_url,
        "scraped_metadata": scraped_metadata
        or {"title": None, "author": None, "publish_date": None, "domain": None},
        "risk_score": analysis.get("risk_score", 0),
        "risk_level": analysis.get("risk_level", "LOW"),
        "verdict": analysis.get("verdict", ""),
        "techniques_detected": analysis.get("techniques_detected", []),
        "psychological_target": analysis.get("psychological_target", ""),
        "recommended_action": analysis.get("recommended_action", ""),
        "summary": analysis.get("summary", ""),
        "clean": analysis.get("clean", True),
    }

    # Store in history
    analysis_history.insert(0, report)
    # Keep only last 50
    if len(analysis_history) > 50:
        analysis_history.pop()

    return report

# ─── API Endpoints ─────────────────────────────────────────────────

@app.post("/api/analyze/text")
async def analyze_text(input_data: TextInput):
    """Analyze text content for manipulation."""
    content = input_data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    if len(content) < 10:
        raise HTTPException(status_code=400, detail="Content too short. Provide at least 10 characters.")

    analysis = analyze_with_grok(content)
    report = build_report(
        analysis=analysis,
        content_type="text",
        input_preview=content[:120],
    )
    return report


@app.post("/api/analyze/url")
async def analyze_url(input_data: UrlInput):
    """Scrape a URL and analyze its content for manipulation."""
    url = input_data.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    # Validate URL format
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL format.")

    # Scrape the URL
    scrape_result = scrape_url(url)
    if not scrape_result["success"]:
        raise HTTPException(status_code=422, detail=scrape_result["error"])

    content = scrape_result.get("content", "")
    if not content or len(content.strip()) < 15:
        raise HTTPException(
            status_code=422,
            detail="Could not extract enough readable text from this URL. It might be an image/video site, paywalled, or a web app.",
        )

    # Analyze the scraped content
    analysis = analyze_with_grok(content)
    report = build_report(
        analysis=analysis,
        content_type="url",
        input_preview=content[:120],
        source_url=url,
        scraped_metadata=scrape_result["metadata"],
    )
    return report


@app.get("/api/history")
async def get_history():
    """Return last 20 analyses."""
    items = []
    for item in analysis_history[:20]:
        items.append(
            {
                "id": item["id"],
                "timestamp": item["timestamp"],
                "input_preview": item["input_preview"],
                "risk_score": item["risk_score"],
                "risk_level": item["risk_level"],
                "content_type": item["content_type"],
            }
        )
    return {"history": items}


@app.get("/api/stats")
async def get_stats():
    """Return aggregate statistics."""
    total = len(analysis_history)
    if total == 0:
        return {
            "total_analyzed": 0,
            "avg_risk_score": 0,
            "high_risk_count": 0,
            "most_common_technique": "N/A",
        }

    scores = [item["risk_score"] for item in analysis_history]
    avg_score = round(sum(scores) / total, 1)
    high_risk = sum(1 for item in analysis_history if item["risk_level"] in ("HIGH", "CRITICAL"))

    # Find most common technique
    technique_counts: dict[str, int] = {}
    for item in analysis_history:
        for tech in item.get("techniques_detected", []):
            name = tech.get("name", "Unknown")
            technique_counts[name] = technique_counts.get(name, 0) + 1

    most_common = "N/A"
    if technique_counts:
        most_common = max(technique_counts, key=technique_counts.get)

    return {
        "total_analyzed": total,
        "avg_risk_score": avg_score,
        "high_risk_count": high_risk,
        "most_common_technique": most_common,
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0", "model": "grok-2"}


# ─── Serve Frontend ────────────────────────────────────────────────

# Mount static files
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def serve_index():
    """Serve the main SPA."""
    return FileResponse(os.path.join(frontend_dir, "index.html"))


# ─── Run ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  SENTINEL — AI for Detecting Manipulative Digital Content")
    print("  See through the noise. Protect the truth.")
    print("=" * 60)
    print()
    print("  Server running at:  http://localhost:8000")
    print("  API docs at:        http://localhost:8000/docs")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
