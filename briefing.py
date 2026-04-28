"""
============================================================
  MARKET INTELLIGENCE BRIEFING — AUTO-DELIVERY SYSTEM
  Powered by:
    - yfinance     -> live market prices
    - NewsAPI.org  -> fresh news (last 12-36 hours only)
    - Groq API     -> AI briefing generation
    - Gmail SMTP   -> email delivery
============================================================
"""

import smtplib
import os
import re
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
import pytz
import yfinance as yf


# ─────────────────────────────────────────────
#  LIVE MARKET DATA
# ─────────────────────────────────────────────

TICKERS = {
    "S&P 500":       "^GSPC",
    "Nasdaq":        "^IXIC",
    "Dow Jones":     "^DJI",
    "FTSE 100":      "^FTSE",
    "DAX":           "^GDAXI",
    "CAC 40":        "^FCHI",
    "Nikkei 225":    "^N225",
    "Hang Seng":     "^HSI",
    "GBP/USD":       "GBPUSD=X",
    "EUR/USD":       "EURUSD=X",
    "USD/JPY":       "USDJPY=X",
    "DXY":           "DX-Y.NYB",
    "Brent Crude":   "BZ=F",
    "Gold":          "GC=F",
    "Natural Gas":   "NG=F",
    "US 2yr Yield":  "^IRX",
    "US 10yr Yield": "^TNX",
}


def fetch_market_data():
    print("Fetching live market data from Yahoo Finance...")
    lines = []
    failed = []

    for name, ticker in TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d", interval="1d")
            if len(hist) < 1:
                failed.append(name)
                continue
            current = hist["Close"].iloc[-1]
            if len(hist) >= 2:
                prev = hist["Close"].iloc[-2]
                change = current - prev
                pct = (change / prev) * 100
                sign = "+" if change >= 0 else ""
                lines.append(
                    "{:<18} {:>10.2f}   ({}{:.2f} / {}{:.2f}%)".format(
                        name + ":", current, sign, change, sign, pct
                    )
                )
            else:
                lines.append("{:<18} {:>10.2f}".format(name + ":", current))
        except Exception as e:
            failed.append(name)

    if failed:
        print("  Could not fetch: " + ", ".join(failed))

    result = "\n".join(lines)
    print("  Fetched " + str(len(lines)) + " instruments")
    return result


# ─────────────────────────────────────────────
#  LIVE NEWS via NewsAPI.org
# ─────────────────────────────────────────────

def fetch_news(hours_back=14):
    api_key = os.environ.get("NEWS_API_KEY", "").strip()
    if not api_key:
        print("  WARNING: NEWS_API_KEY not set.")
        return "News unavailable."

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    from_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    queries = [
        {
            "label": "Markets & Finance",
            "params": {
                "q": (
                    "stock market OR S&P 500 OR FTSE OR Nasdaq OR DAX OR Nikkei "
                    "OR earnings OR forex OR oil OR gold OR bonds OR tariffs OR trade "
                    "OR recession OR inflation OR interest rates OR GDP"
                ),
                "language": "en",
                "sortBy": "publishedAt",
                "from": from_str,
                "pageSize": 25,
            }
        },
        {
            "label": "Macro Data Releases",
            "params": {
                "q": (
                    "Consumer Confidence OR PMI OR CPI OR inflation data OR jobs report "
                    "OR unemployment OR retail sales OR GDP growth OR industrial output "
                    "OR housing starts OR trade balance OR payrolls OR economic data "
                    "OR business confidence OR manufacturing output OR services sector"
                ),
                "language": "en",
                "sortBy": "publishedAt",
                "from": from_str,
                "pageSize": 25,
            }
        },
        {
            "label": "Central Bank Speeches & Policy",
            "params": {
                "q": (
                    "Lagarde OR Powell OR Bailey OR Ueda OR Schnabel OR Waller "
                    "OR Fed speech OR ECB speech OR Bank of England speech "
                    "OR Federal Reserve OR rate decision OR monetary policy "
                    "OR rate hike OR rate cut OR forward guidance OR hawkish OR dovish"
                ),
                "language": "en",
                "sortBy": "publishedAt",
                "from": from_str,
                "pageSize": 25,
            }
        },
        {
            "label": "Geopolitics & Global Affairs",
            "params": {
                "q": (
                    "geopolitics OR sanctions OR China economy OR US economy "
                    "OR Ukraine OR Middle East OR Trump policy OR OPEC "
                    "OR IMF OR World Bank OR trade war OR supply chain"
                ),
                "language": "en",
                "sortBy": "publishedAt",
                "from": from_str,
                "pageSize": 20,
            }
        }
    ]

    all_sections = []
    total_articles = 0
    seen_titles = set()

    for query in queries:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params=query["params"],
                headers={"X-Api-Key": api_key},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])

            fresh = []
            for article in articles:
                published = article.get("publishedAt", "")
                title = (article.get("title") or "").strip()
                source = article.get("source", {}).get("name", "")
                description = (article.get("description") or "").strip()

                if title in ("[Removed]", "") or not title:
                    continue
                if title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())

                try:
                    dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    age_hrs = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                    age_str = "{:.0f}h ago".format(age_hrs)
                    if dt < cutoff:
                        continue
                except Exception:
                    age_str = "recent"

                desc = re.sub(r"<[^>]+>", "", description)[:200] if description else ""
                fresh.append(
                    "  [" + age_str + "] [" + source + "] " + title +
                    (" -- " + desc if desc else "")
                )

            if fresh:
                all_sections.append("=== " + query["label"] + " ===")
                all_sections.extend(fresh)
                all_sections.append("")
                total_articles += len(fresh)
                print("  [OK] " + query["label"] + ": " + str(len(fresh)) + " fresh articles")

        except Exception as e:
            print("  [FAIL] " + query["label"] + ": " + str(e)[:80])

    if not all_sections:
        return "No recent news articles found in the last " + str(hours_back) + " hours."

    print("  Total fresh articles: " + str(total_articles))
    return "\n".join(all_sections)


# ─────────────────────────────────────────────
#  WHICH BRIEFING TO RUN
# ─────────────────────────────────────────────

def get_briefing_config():
    uk_tz = pytz.timezone("Europe/London")
    now = datetime.now(uk_tz)
    day = now.weekday()
    date_str = now.strftime("%A, %d %B %Y")

    if day == 5:
        return "saturday", "Weekly Market Roundup -- " + date_str, 36
    elif day == 6:
        return "sunday", "Week Ahead Preview -- " + date_str, 36
    elif now.hour < 14:
        return "morning", "Morning Market Briefing -- " + date_str, 14
    else:
        return "evening", "Evening Market Briefing -- " + date_str, 14


# ─────────────────────────────────────────────
#  BUILD PROMPT
# ─────────────────────────────────────────────

def build_prompt(briefing_type, market_data, news_context, subject):
    base = (
        "You are a world-class financial and geopolitical intelligence analyst. "
        "I am pivoting into a career in financial markets and use your briefings "
        "to stay sharp and build deep expertise. I am UK-based.\n\n"
        "CRITICAL RULES:\n"
        "1. The LIVE MARKET DATA below contains real prices fetched moments ago. "
        "Use these EXACT figures. Do NOT change, estimate, or invent any numbers.\n"
        "2. The NEWS section contains ONLY articles published in the last 12-36 hours. "
        "These are your source for what is happening right now. "
        "Reference as many relevant articles as possible from ALL four news categories. "
        "Do NOT say a section has no data if relevant articles exist in the feed.\n"
        "3. The news feed has four labelled categories: Markets & Finance, "
        "Macro Data Releases, Central Bank Speeches & Policy, and Geopolitics & Global Affairs. "
        "Use each category to populate the corresponding section of the briefing.\n"
        "4. If a specific data point is genuinely not in the feed, say so briefly "
        "then move on -- never pad with invented information.\n"
        "5. Explain WHY things are moving -- the mechanism, the cause and effect.\n\n"
        "LIVE MARKET DATA (use these exact numbers):\n"
        + market_data +
        "\n\n"
        "RECENT NEWS FEED (last 12-36 hours, four categories):\n"
        + news_context +
        "\n\n"
        "Primary focus: US, UK, Eurozone, Japan. Include others only if significant.\n\n"
    )

    if briefing_type == "morning":
        structure = (
            "Write a MORNING MARKET BRIEFING for " + subject + ".\n\n"
            "**1. OVERNIGHT MARKET SNAPSHOT**\n"
            "Use EXACT figures from live market data. Cover: S&P 500, Nasdaq, Dow, "
            "FTSE 100, DAX, CAC 40, Nikkei 225, Hang Seng. FX: GBP/USD, EUR/USD, "
            "USD/JPY, DXY. Commodities: Brent Crude, Gold. US 2yr and 10yr yields -- "
            "explain what significant moves signal. End with one sentence: the dominant "
            "theme of overnight markets.\n\n"
            "**2. MACRO PULSE**\n"
            "Use the Macro Data Releases category from the news feed. Report every "
            "economic data release mentioned. For each: the actual number, what was "
            "expected, and the market reaction. Flag any tier-1 data due later today.\n\n"
            "**3. CENTRAL BANK WATCH**\n"
            "Use the Central Bank Speeches & Policy category from the news feed. "
            "Report every central bank speech, statement, or policy signal mentioned -- "
            "Fed, ECB, BoE, BoJ. Include any scheduled speeches happening later today. "
            "What is the market pricing for each next meeting? Note any divergence "
            "between central banks and why it matters for FX and bonds.\n\n"
            "**4. TOP 3 STORIES DRIVING MARKETS TODAY**\n"
            "Use the Markets & Finance category. Pick the three most consequential stories. "
            "For each: what happened, why it is moving markets (explain the mechanism), "
            "and what to watch as it develops.\n\n"
            "**5. GEOPOLITICS AND GLOBAL AFFAIRS**\n"
            "Use the Geopolitics & Global Affairs category. Cover all significant "
            "developments with real financial consequences from the news feed.\n\n"
            "**6. SECTORS, EARNINGS AND NOTABLE MOVERS**\n"
            "From the Markets & Finance category: earnings, analyst calls, M&A, IPOs, "
            "sector rotation. UK equity stories separately.\n\n"
            "**7. WHAT TO WATCH TODAY**\n"
            "Based on the full news feed: scheduled data releases, central bank speakers, "
            "earnings, geopolitical deadlines due today or tomorrow.\n\n"
            "**8. THE ANALYST'S TAKE**\n"
            "4-6 sentences. The single most important dynamic right now. The market "
            "narrative. What to watch over the next 24-48 hours. Explain a concept "
            "where relevant.\n\n"
            "15-20 minute read. Bold headers. Sub-bullets. Exact numbers only."
        )

    elif briefing_type == "evening":
        structure = (
            "Write an EVENING MARKET BRIEFING for " + subject + ".\n\n"
            "**1. TODAY'S MARKET CLOSE**\n"
            "Use EXACT figures from live market data. S&P 500, Nasdaq, Dow, FTSE 100, "
            "DAX, CAC 40, Nikkei 225. FX: GBP/USD, EUR/USD, USD/JPY, DXY. "
            "Brent, Gold. US 2yr and 10yr yields -- explain significant moves. "
            "One sentence: the story of today's session.\n\n"
            "**2. WHY MARKETS MOVED THE WAY THEY DID**\n"
            "Most important section. Using today's news as evidence, explain the "
            "cause and effect of today's major moves. What was the catalyst? "
            "What was the mechanism? Explain the chain of reasoning the market used.\n\n"
            "**3. TODAY'S TOP 3 STORIES**\n"
            "From the Markets & Finance category: three most impactful stories. "
            "For each: what happened, the market reaction and why, and whether this "
            "is a one-day story or something with legs.\n\n"
            "**4. GEOPOLITICS AND GLOBAL AFFAIRS UPDATE**\n"
            "From the Geopolitics category: all developments with market consequences. "
            "Flag anything quietly building that markets may not be fully pricing yet.\n\n"
            "**5. DATA AND CENTRAL BANKS -- TODAY'S SCORECARD**\n"
            "From the Macro Data Releases and Central Bank categories: all economic "
            "data and central bank activity today. How did each shift the macro picture "
            "and rate expectations?\n\n"
            "**6. EARNINGS, SECTORS AND CORPORATE NEWS**\n"
            "From the Markets & Finance category: earnings beats/misses and what they "
            "signal. Major M&A, analyst calls, sector moves. UK highlights separately.\n\n"
            "**7. WHAT'S SETTING UP FOR TOMORROW**\n"
            "Based on the full news feed: key data, central bank speakers, earnings, "
            "and geopolitical events scheduled for tomorrow and this week.\n\n"
            "**8. THE ANALYST'S TAKE**\n"
            "4-6 sentences. The dominant narrative today. Did anything surprise? "
            "What concept did today illustrate? The one thing to think about overnight.\n\n"
            "15-20 minute read. Bold headers. Sub-bullets. Exact numbers only."
        )

    elif briefing_type == "saturday":
        structure = (
            "Write a WEEKLY MARKET ROUNDUP for " + subject + ".\n\n"
            "**1. WEEKLY MARKET SCORECARD**\n"
            "Use EXACT figures from live market data. S&P 500, Nasdaq, Dow, FTSE 100, "
            "DAX, CAC 40, Nikkei 225. FX: GBP/USD, EUR/USD, USD/JPY, DXY. "
            "Brent Crude, Gold. US 2yr and 10yr yields. "
            "One sentence: the defining theme of this week.\n\n"
            "**2. THE WEEK'S NARRATIVE**\n"
            "Synthesise the overarching story of the week as a coherent narrative -- "
            "not a day-by-day list. What did markets obsess over? How did the narrative "
            "evolve? Were there turning points? What was the dominant risk sentiment?\n\n"
            "**3. THE TOP 5 STORIES OF THE WEEK**\n"
            "The five most consequential developments from the news feed. For each: "
            "what happened, why it mattered, the mechanism, and whether resolved or developing.\n\n"
            "**4. CENTRAL BANKS THIS WEEK**\n"
            "From the Central Bank category: all Fed, ECB, BoE, BoJ activity. "
            "How did rate expectations shift? Explain any divergence and what it means for FX.\n\n"
            "**5. GEOPOLITICS AND GLOBAL AFFAIRS -- THE WEEK IN REVIEW**\n"
            "From the Geopolitics category: all significant developments with market consequences.\n\n"
            "**6. SECTORS, EARNINGS AND CORPORATE HIGHLIGHTS**\n"
            "Most important earnings -- beats, misses, what they signal. "
            "Major M&A, IPOs, analyst calls. Sector rotation trends. UK highlights.\n\n"
            "**7. MACRO DATA ROUNDUP**\n"
            "From the Macro Data Releases category: all significant economic data this week. "
            "For each: what it showed, what was expected, what it means.\n\n"
            "**8. CONCEPT OF THE WEEK**\n"
            "One market concept or mechanism that featured prominently this week -- "
            "explained clearly and in depth, directly relevant to this week's events.\n\n"
            "**9. THE ANALYST'S WEEKLY TAKE**\n"
            "6-8 sentences. What was most important? What is the dominant macro regime? "
            "Is it changing? What should I carry into next week as my core mental model?\n\n"
            "25-30 minute read. Precise numbers. Bold headers."
        )

    else:
        structure = (
            "Write a WEEK AHEAD PREVIEW for " + subject + ".\n\n"
            "**1. THE WEEK AHEAD -- AT A GLANCE**\n"
            "8-10 bullet overview of the most important scheduled events in chronological order.\n\n"
            "**2. ECONOMIC DATA CALENDAR -- THE BIG RELEASES**\n"
            "For each major release due this week across US, UK, Eurozone, Japan: "
            "what is being released and when (UK time), previous reading, "
            "market consensus expectation, why it matters right now, "
            "and what a beat or miss could mean for markets. "
            "Flag the single most important release and why.\n\n"
            "**3. CENTRAL BANK EVENTS**\n"
            "Scheduled decisions, minutes, speeches from Fed, ECB, BoE, BoJ. "
            "For each: what is expected, what the market is pricing in, "
            "and what surprise scenarios could move markets.\n\n"
            "**4. EARNINGS SEASON WATCH**\n"
            "Key companies reporting this week. For each: market expectations, "
            "what to watch beyond headlines, what results could signal.\n\n"
            "**5. GEOPOLITICAL CALENDAR AND FLASHPOINTS**\n"
            "Scheduled political events with market impact. "
            "Flag slow-burning situations that could escalate.\n\n"
            "**6. KEY RISKS THIS WEEK**\n"
            "3-5 specific risk scenarios -- upside and downside -- "
            "with the potential market impact of each.\n\n"
            "**7. THEMES TO WATCH**\n"
            "The 2-3 overarching macro themes that will dominate the week's trading.\n\n"
            "**8. HOW TO THINK ABOUT THIS WEEK**\n"
            "5-6 sentences. The market's key question right now. What single event "
            "is most likely to shift the macro narrative? Where could consensus be wrong? "
            "A clear mental model to carry into Monday.\n\n"
            "20-25 minute read. Specific dates, UK times, consensus forecasts. "
            "Use live market data for current levels."
        )

    return base + structure


# ─────────────────────────────────────────────
#  CALL GROQ API
# ─────────────────────────────────────────────

def generate_briefing(full_prompt):
    api_key = os.environ["GROQ_API_KEY"].strip()

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a world-class financial market analyst. "
                    "You write precise, analytical briefings explaining market mechanisms. "
                    "When live market data is provided, always use those exact figures. "
                    "When a news feed is provided, always reference the articles in it -- "
                    "never say a section has no data if relevant articles exist in the feed. "
                    "Never invent events or numbers not present in the data provided."
                )
            },
            {"role": "user", "content": full_prompt}
        ],
        "max_tokens": 8000,
        "temperature": 0.3
    }

    print("Calling Groq API...")
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=120
    )
    resp.raise_for_status()

    text = resp.json()["choices"][0]["message"]["content"]
    print("Groq response: " + str(len(text)) + " characters")
    return text


# ─────────────────────────────────────────────
#  FORMAT AS HTML EMAIL
# ─────────────────────────────────────────────

def convert_to_html(subject, raw_text, market_data):
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
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = stripped[2:]
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
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

    mkt_rows = ""
    for line in market_data.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 2:
            name_part = parts[0].strip()
            val_part = ":".join(parts[1:]).strip()
            color = "#2e7d32" if "+" in val_part else ("#c62828" if "(" in val_part and "-" in val_part else "#333")
            mkt_rows += (
                "<tr>"
                "<td style='padding:3px 16px 3px 0;color:#555;font-size:13px;white-space:nowrap'>" + name_part + "</td>"
                "<td style='padding:3px 0;font-size:13px;color:" + color + ";font-family:monospace;white-space:nowrap'>" + val_part + "</td>"
                "</tr>"
            )

    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + subject + "</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f4f4f0;margin:0;padding:20px;color:#1a1a1a}"
        ".wrap{max-width:760px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}"
        ".hdr{background:#0a2540;padding:28px 36px;color:#fff}"
        ".hdr h1{margin:0;font-size:22px;font-weight:700}"
        ".hdr p{margin:6px 0 0;font-size:13px;color:#8aa4c8;font-family:Arial,sans-serif}"
        ".mkt{background:#f8fafb;border-bottom:1px solid #e0e8f0;padding:16px 36px}"
        ".mkt h3{margin:0 0 10px;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#8aa4c8;font-family:Arial,sans-serif}"
        ".body{padding:32px 36px;line-height:1.8}"
        "h2.sh{font-size:16px;color:#0a2540;margin:32px 0 10px;padding:10px 14px;background:#f0f4fa;border-left:4px solid #1a73e8;border-radius:0 4px 4px 0}"
        "p{margin:0 0 14px;font-size:15px;color:#2d2d2d}"
        "ul{padding-left:20px;margin:8px 0 16px}"
        "li{margin-bottom:8px;font-size:15px;color:#2d2d2d}"
        "strong{color:#0a2540}"
        "hr.d{border:none;border-top:1px solid #e8e8e8;margin:24px 0}"
        ".ftr{background:#f9f9f7;border-top:1px solid #e8e8e8;padding:16px 36px;font-family:Arial,sans-serif;font-size:12px;color:#888;text-align:center}"
        "</style></head><body>"
        "<div class='wrap'>"
        "<div class='hdr'><h1>" + subject + "</h1>"
        "<p>Your personal market intelligence briefing &mdash; generated automatically</p></div>"
        "<div class='mkt'><h3>Live Market Snapshot</h3>"
        "<table border='0' cellpadding='0' cellspacing='0'>" + mkt_rows + "</table></div>"
        "<div class='body'>" + body + "</div>"
        "<div class='ftr'>"
        "Live prices: Yahoo Finance &nbsp;&bull;&nbsp; "
        "News: NewsAPI.org (last 12-36hrs) &nbsp;&bull;&nbsp; "
        "Analysis: Groq &nbsp;&bull;&nbsp; Free"
        "</div>"
        "</div></body></html>"
    )


# ─────────────────────────────────────────────
#  SEND EMAIL VIA GMAIL SMTP
# ─────────────────────────────────────────────

def send_email(subject, html_body, plain_body):
    sender = os.environ["EMAIL_ADDRESS"].strip()
    password = os.environ["EMAIL_PASSWORD"].strip()
    recipient = os.environ.get("RECIPIENT_EMAIL", sender).strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = "Market Intelligence <" + sender + ">"
    msg["To"] = recipient

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    print("Connecting to Gmail SMTP...")
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
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

    briefing_type, subject, hours_back = get_briefing_config()
    print("Briefing type: " + subject)

    market_data = fetch_market_data()
    news_context = fetch_news(hours_back=hours_back)
    full_prompt = build_prompt(briefing_type, market_data, news_context, subject)
    raw_text = generate_briefing(full_prompt)
    html_body = convert_to_html(subject, raw_text, market_data)
    send_email(subject, html_body, raw_text)

    print("=" * 50)
    print("Done. Briefing delivered successfully.")
    print("=" * 50)


if __name__ == "__main__":
    main()
