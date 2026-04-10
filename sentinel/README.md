# SENTINEL — AI for Detecting Manipulative Digital Content

> See through the noise. Protect the truth.

Built for the **bots.in Hackathon** · Powered by Claude AI

## Setup

1. Clone or download this project
2. Copy `.env.example` to `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run:
   ```bash
   python main.py
   ```
5. Open **http://localhost:8000** in your browser

## What it does

SENTINEL analyzes any digital content — text, social media posts, news articles, or URLs — and produces a structured **Manipulation Intelligence Report** identifying:

- Which manipulation techniques are present
- Who is being psychologically targeted
- A 0-100 risk score with color-coded severity
- Evidence pulled directly from the content
- Recommended action for readers, journalists, or platforms

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze/text` | Analyze text content |
| `POST` | `/api/analyze/url` | Scrape & analyze a URL |
| `GET` | `/api/history` | Last 20 analyses |
| `GET` | `/api/stats` | Aggregate statistics |
| `GET` | `/health` | Health check |

## Tech Stack

- **Backend:** FastAPI (Python)
- **AI:** Anthropic Claude API (claude-sonnet-4-20250514)
- **Scraping:** BeautifulSoup + requests
- **Frontend:** Vanilla HTML/CSS/JS

## Manipulation Techniques Detected

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

---

Built at **bots.in Hackathon** · 2025
