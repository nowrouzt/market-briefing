"""
============================================================
  MARKET INTELLIGENCE BRIEFING — AUTO-DELIVERY SYSTEM
  Powered by: Groq API (free) + RSS News Feeds (free)
  No rate limit issues. No SDK. Completely reliable.
============================================================
"""

import smtplib
import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import pytz


# ─────────────────────────────────────────────
#  RSS FEED SOURCES
# ─────────────────────────────────────────────

RSS_FEEDS = [
    ("Reuters Business",   "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Markets",    "https://feeds.reuters.com/reuters/money"),
    ("BBC Business",       "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("CNBC Markets",       "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
    ("CNBC Finance",       "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("Yahoo Finance",      "https://finance.yahoo.com/news/rssindex"),
    ("MarketWatch",        "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Investing.com",      "https://www.investing.com/rss/news.rss"),
    ("FT Markets",         "https://www.ft.com/markets?format=rss"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MarketBriefingBot/1.0)"
}


def fetch_rss(name, url, max_items=15):
    """Fetch and parse a single RSS feed. Returns list of (title, summary, date) tuples."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # Handle both RSS and Atom formats
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        results = []
        for item in items[:max_items]:
            title = (item.findtext("title") or
                     item.findtext("atom:title", namespaces=ns) or "").strip()
            summary = (item.findtext("description") or
                       item.findtext("atom:summary", namespaces=ns) or "").strip()
            # Strip HTML tags from summary
            summary = re.sub(r"<[^>]+>", "", summary)[:300]

            if title:
                results.append(title + ((" — " + summary) if summary else ""))

        print("  [OK] " + name + ": " + str(len(results)) + " items")
        return results

    except Exception as e:
        print("  [SKIP] " + name + ": " + str(e))
        return []


def gather_news():
    """Fetch all RSS feeds and compile into a single news context string."""
    print("Fetching live news from RSS feeds...")
    all_items = []

    for name, url in RSS_FEEDS:
        items = fetch_rss(name, url)
        if items:
            all_items.append("=== " + name + " ===")
            all_items.extend(["- " + item for item in items])
            all_items.append("")

    if not all_items:
        return "No live news feeds available. Use your most recent training knowledge."

    context = "\n".join(all_items)
    print("News context compiled: " + str(len(context)) + " characters from " +
          str(sum(1 for n, u in RSS_FEEDS)) + " sources")
    return context


# ─────────────────────────────────────────────
#  THE FOUR PROMPTS
# ─────────────────────────────────────────────

def build_prompt(briefing_type, news_context, date_str):

    base_persona = (
        "You are a world-class financial and geopolitical intelligence analyst. "
        "I am pivoting into a career in financial markets and use your briefings "
        "to stay sharp and build deep expertise. I am UK-based. "
        "Below is a live feed of today's top financial and geopolitical news headlines. "
        "Use these as your primary source of information to write the briefing. "
        "Be analytical — don't just report what happened, explain WHY it matters "
        "and the MECHANISM behind market moves. This is how I learn.\n\n"
        "TODAY'S LIVE NEWS FEED:\n"
        "------------------------\n"
        + news_context +
        "\n------------------------\n\n"
        "Primary focus regions: US, UK, Eurozone, Japan. "
        "Include others only if genuinely market-moving.\n\n"
    )

    if briefing_type == "morning":
        structure = """Write a MORNING MARKET BRIEFING for """ + date_str + """. Structure it exactly as follows:

**1. OVERNIGHT MARKET SNAPSHOT**
Overnight/closing moves for: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225, and notable Asian markets. Key FX: GBP/USD, EUR/USD, USD/JPY, DXY. Commodities: Brent Crude, Gold, notable movers. Crypto only if major. End with one sentence: the dominant theme or mood of overnight markets.

**2. MACRO PULSE**
Overnight/morning data releases: inflation, jobs, PMIs, GDP, retail sales, central bank speeches. For each: the number, what was expected, and the market reaction. Flag tier-1 data due today.

**3. CENTRAL BANK WATCH**
Fed, ECB, BoE, Bank of Japan. Policy signals, rate decisions, speeches, forward guidance shifts. What is the market pricing in for the next meeting of each? Note divergences between central banks and why it matters for FX and bonds.

**4. TOP 3 STORIES DRIVING MARKETS TODAY**
The three most consequential developments from the last 12 hours. For each: what happened, why it is moving markets (explain the mechanism), and what to watch as it develops.

**5. GEOPOLITICS AND GLOBAL AFFAIRS**
Developments with real financial consequences. US politics/policy (tariffs, fiscal, regulation), US-China, Middle East, Russia-Ukraine, European politics, UK news.

**6. SECTORS, EARNINGS AND NOTABLE MOVERS**
Significant earnings, analyst calls, M&A, IPOs, sector rotation. UK equity stories separately.

**7. WHAT TO WATCH TODAY**
Scheduled data releases, central bank speakers, earnings today, geopolitical deadlines. My agenda for the day.

**8. THE ANALYST'S TAKE**
4-6 sentences. The single most important macro or market dynamic right now. The market narrative. What to watch over the next 24-48 hours. Briefly explain a concept where relevant — this is where I learn.

Keep total length appropriate for a focused 15-20 minute read. Use bold headers and sub-bullets. Be precise with numbers."""

    elif briefing_type == "evening":
        structure = """Write an EVENING MARKET BRIEFING / DEBRIEF for """ + date_str + """. Structure it exactly as follows:

**1. TODAY'S MARKET CLOSE**
Final closing numbers: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225. Key FX closes: GBP/USD, EUR/USD, USD/JPY, DXY. Commodities: Brent, Gold, notable movers. US Treasury yields (2yr and 10yr) — note significant moves and explain why they matter. One sentence: the story of today's session.

**2. WHY MARKETS MOVED THE WAY THEY DID**
Most important section. The cause and effect of today's major moves. What was the catalyst? What was the mechanism? Was it macro data, Fed commentary, earnings, geopolitics, or flows? Explain the chain of reasoning the market used — not just what happened.

**3. TODAY'S TOP 3 STORIES**
The three most impactful stories of the day. For each: what happened, the market reaction and why, and whether this is a one-day story or something with legs.

**4. GEOPOLITICS AND GLOBAL AFFAIRS UPDATE**
Developments with economic or market consequences. US policy, US-China, Middle East, Russia-Ukraine, European politics, UK domestic. Flag anything quietly building that markets may not be fully pricing yet.

**5. DATA AND CENTRAL BANKS — TODAY'S SCORECARD**
Economic data released today and how it shifted the macro picture. Central bank commentary and how it moved rate expectations. Where markets are pricing the next rate moves for Fed, ECB, BoE and BoJ.

**6. EARNINGS, SECTORS AND CORPORATE NEWS**
Notable earnings beats/misses and what they signal about the broader economy. Major M&A, analyst calls, sector moves. UK equity highlights separately.

**7. WHAT'S SETTING UP FOR TOMORROW**
Key data releases, central bank speakers, earnings, geopolitical events scheduled for tomorrow and the rest of the week. The known risk events.

**8. THE ANALYST'S TAKE**
4-6 sentences. The dominant narrative. Did anything surprise? What concept did today illustrate worth understanding more deeply? Leave me with the one thing I should be thinking about overnight.

Keep total length appropriate for a focused 15-20 minute read. Be precise with numbers."""

    elif briefing_type == "saturday":
        structure = """Write a WEEKLY MARKET ROUNDUP covering the week just ended (Monday to Friday). Date: """ + date_str + """. Structure it exactly as follows:

**1. WEEKLY MARKET SCORECARD**
Full week performance: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225. Weekly FX moves: GBP/USD, EUR/USD, USD/JPY, DXY — start vs finish. Commodities: Brent Crude, Gold, notable movers. US 2yr and 10yr Treasury yields — end vs Monday open. One sentence: the defining theme of markets this week.

**2. THE WEEK'S NARRATIVE**
Synthesise the overarching story of the week as a coherent narrative — NOT a day-by-day list. What was the market obsessing over? How did the narrative evolve from Monday to Friday? Were there turning points? What was the dominant risk sentiment and why?

**3. THE TOP 5 STORIES OF THE WEEK**
The five most consequential developments. For each: what happened and when, why it mattered to markets, the mechanism behind the reaction, and whether it is resolved or still developing.

**4. CENTRAL BANKS THIS WEEK**
Any Fed, ECB, BoE, or BoJ activity — decisions, minutes, speeches, guidance shifts. How did rate expectations shift across the week? Explain any central bank divergence and what it means for FX.

**5. GEOPOLITICS AND GLOBAL AFFAIRS — THE WEEK IN REVIEW**
Most significant geopolitical developments with real market consequences. US policy, US-China, Middle East, Russia-Ukraine, European politics, UK domestic.

**6. SECTORS, EARNINGS AND CORPORATE HIGHLIGHTS**
Most important earnings — beats, misses, and what they signal about the economy. Major M&A, IPOs, analyst calls. Sector rotation trends. UK equity highlights separately.

**7. MACRO DATA ROUNDUP**
All significant economic data released this week across US, UK, Eurozone, Japan. For each: what it showed, what was expected, and what it means for the macro picture.

**8. CONCEPT OF THE WEEK**
One market concept or mechanism that featured prominently this week — explained clearly and in depth so I genuinely understand it. Make it directly relevant to this week's events.

**9. THE ANALYST'S WEEKLY TAKE**
6-8 sentences. What was most important this week? What is the dominant macro regime right now and is it changing? What should I carry into next week as my core mental model?

Aim for a thorough 25-30 minute read. Be precise with numbers and percentages."""

    else:  # sunday
        structure = """Write a WEEK AHEAD PREVIEW for the coming week. Date: """ + date_str + """. Structure it exactly as follows:

**1. THE WEEK AHEAD — AT A GLANCE**
8-10 bullet overview of the most important scheduled events in chronological order for the week ahead.

**2. ECONOMIC DATA CALENDAR — THE BIG RELEASES**
For each major release due this week across US, UK, Eurozone, Japan: what is being released and when (UK time), previous reading, market consensus expectation, why this release matters right now given the current macro environment, and what a beat or miss could mean for markets. Flag the single most important release of the week and why.

**3. CENTRAL BANK EVENTS**
Scheduled rate decisions, minutes, speeches, press conferences from Fed, ECB, BoE, BoJ. For each: what is expected, what the market is pricing in, and what surprise scenarios could move markets.

**4. EARNINGS SEASON WATCH**
Key companies reporting this week. For each major release: market expectations, what to watch beyond headline numbers, and what results could signal about the broader economy or sector.

**5. GEOPOLITICAL CALENDAR AND FLASHPOINTS**
Scheduled political events with market impact. Flag slow-burning situations that could escalate this week.

**6. KEY RISKS THIS WEEK**
3-5 specific risk scenarios — both upside and downside surprises — with the potential market impact of each.

**7. THEMES TO WATCH**
The 2-3 overarching macro themes or narratives that will likely dominate the week's trading and how this week's events feed into them.

**8. HOW TO THINK ABOUT THIS WEEK**
5-6 sentences. What is the market's key question right now? What single event is most likely to shift the macro narrative? Where could the consensus be wrong? Leave me with a clear mental model to carry into Monday.

Aim for a thorough 20-25 minute read. Include specific dates, UK times, and consensus forecasts where available."""

    return base_persona + structure


# ─────────────────────────────────────────────
#  DETERMINE WHICH BRIEFING TO RUN
# ─────────────────────────────────────────────

def get_briefing_config():
    uk_tz = pytz.timezone("Europe/London")
    now = datetime.now(uk_tz)
    day = now.weekday()
    date_str = now.strftime("%A, %d %B %Y")

    if day == 5:
        return "saturday", "Weekly Market Roundup — " + date_str
    elif day == 6:
        return "sunday", "Week Ahead Preview — " + date_str
    elif now.hour < 14:
        return "morning", "Morning Market Briefing — " + date_str
    else:
        return "evening", "Evening Market Briefing — " + date_str


# ─────────────────────────────────────────────
#  CALL GROQ API (FREE, RELIABLE, FAST)
# ─────────────────────────────────────────────

def generate_briefing(full_prompt):
    api_key = os.environ["GROQ_API_KEY"].strip()

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a world-class financial market analyst and intelligence briefer. "
                    "You write clear, precise, analytical briefings that explain not just what "
                    "happened in markets but why — the mechanisms, the cause and effect, the "
                    "implications. You write for someone building serious expertise in financial "
                    "markets. Always be precise with numbers. Always explain market mechanisms."
                )
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ],
        "max_tokens": 8000,
        "temperature": 0.4
    }

    print("Calling Groq API (llama-3.3-70b-versatile)...")
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()

    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    print("Groq response received: " + str(len(text)) + " characters")
    return text


# ─────────────────────────────────────────────
#  FORMAT AS HTML EMAIL
# ─────────────────────────────────────────────

def convert_to_html(subject, raw_text):
    lines = raw_text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        is_header = (
            stripped.startswith("**") and
            stripped.endswith("**") and
            len(stripped) > 4 and
            stripped.count("**") == 2
        )

        if is_header:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = stripped.strip("*")
            html_lines.append('<h2 class="sh">' + content + "</h2>")

        elif stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = stripped[2:]
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            html_lines.append("<li>" + content + "</li>")

        elif stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = stripped[2:]
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            html_lines.append("<li>" + content + "</li>")

        elif stripped == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append('<hr class="d">')

        elif stripped == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False

        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", stripped)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            if content:
                html_lines.append("<p>" + content + "</p>")

    if in_list:
        html_lines.append("</ul>")

    body = "\n".join(html_lines)

    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + subject + "</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f4f4f0;margin:0;padding:20px;color:#1a1a1a}"
        ".wrap{max-width:720px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}"
        ".hdr{background:#0a2540;padding:28px 36px;color:#fff}"
        ".hdr h1{margin:0;font-size:22px;font-weight:700}"
        ".hdr p{margin:6px 0 0;font-size:13px;color:#8aa4c8;font-family:Arial,sans-serif}"
        ".body{padding:32px 36px;line-height:1.8}"
        "h2.sh{font-size:16px;color:#0a2540;margin:32px 0 10px;padding:10px 14px;"
        "background:#f0f4fa;border-left:4px solid #1a73e8;border-radius:0 4px 4px 0}"
        "p{margin:0 0 14px;font-size:15px;color:#2d2d2d}"
        "ul{padding-left:20px;margin:8px 0 16px}"
        "li{margin-bottom:8px;font-size:15px;color:#2d2d2d}"
        "strong{color:#0a2540}"
        "hr.d{border:none;border-top:1px solid #e8e8e8;margin:24px 0}"
        ".ftr{background:#f9f9f7;border-top:1px solid #e8e8e8;padding:16px 36px;"
        "font-family:Arial,sans-serif;font-size:12px;color:#888;text-align:center}"
        "</style></head><body>"
        "<div class='wrap'>"
        "<div class='hdr'><h1>" + subject + "</h1>"
        "<p>Your personal market intelligence briefing &mdash; generated automatically</p></div>"
        "<div class='body'>" + body + "</div>"
        "<div class='ftr'>Generated by your market intelligence system &nbsp;&bull;&nbsp; "
        "Powered by Groq + Live RSS News Feeds &nbsp;&bull;&nbsp; Free</div>"
        "</div></body></html>"
    )


# ─────────────────────────────────────────────
#  SEND EMAIL VIA OUTLOOK SMTP
# ─────────────────────────────────────────────

def send_email(subject, html_body, plain_body):
    sender    = os.environ["EMAIL_ADDRESS"].strip()
    password  = os.environ["EMAIL_PASSWORD"].strip()
    recipient = os.environ.get("RECIPIENT_EMAIL", sender).strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = "Market Intelligence <" + sender + ">"
    msg["To"]      = recipient

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    print("Connecting to Outlook SMTP...")
    with smtplib.SMTP("smtp-mail.outlook.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
    print("Email sent to " + recipient)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    uk_tz = pytz.timezone("Europe/London")
    print("=" * 50)
    print("Market Briefing System Starting")
    print(datetime.now(uk_tz).strftime("%Y-%m-%d %H:%M %Z"))
    print("=" * 50)

    briefing_type, subject = get_briefing_config()
    print("Briefing type: " + subject)

    # Step 1: Gather live news
    news_context = gather_news()

    # Step 2: Build full prompt
    full_prompt = build_prompt(briefing_type, news_context, subject)

    # Step 3: Generate briefing via Groq
    raw_text = generate_briefing(full_prompt)

    # Step 4: Format and send
    html_body = convert_to_html(subject, raw_text)
    send_email(subject, html_body, raw_text)

    print("=" * 50)
    print("Done. Briefing delivered successfully.")
    print("=" * 50)


if __name__ == "__main__":
    main()
