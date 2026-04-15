"""
============================================================
  MARKET INTELLIGENCE BRIEFING — AUTO-DELIVERY SYSTEM
  Gemini 2.0 Flash REST API — direct HTTP, no SDK
============================================================
"""

import smtplib
import os
import re
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz


# ─────────────────────────────────────────────
#  THE FOUR PROMPTS
# ─────────────────────────────────────────────

MORNING_PROMPT = """
You are my personal financial and geopolitical intelligence analyst. I am pivoting into a career in finance and use this briefing to stay sharp on global markets and macro developments. I am UK-based, financially literate but still building expertise. Compile a structured morning briefing covering overnight developments and what to watch today. Be analytical — explain why things matter and the mechanism behind market moves. This is how I learn, not just stay informed.

Primary focus regions: US, UK, Eurozone, Japan. Include other regions only if genuinely market-moving.

Structure the briefing exactly as follows:

**1. OVERNIGHT MARKET SNAPSHOT**
Closing/overnight moves for: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225, and significant Asian markets. Key FX: GBP/USD, EUR/USD, USD/JPY, DXY. Commodities: Brent Crude, Gold, any notable movers. Crypto only if a major development occurred. End with one sentence: the dominant theme or mood of overnight markets.

**2. MACRO PULSE**
Any overnight or this-morning data releases: inflation, jobs, PMIs, GDP, retail sales, central bank speeches. For each: what the number was, what was expected, and the market reaction. Flag any upcoming tier-1 data due today.

**3. CENTRAL BANK WATCH**
Fed, ECB, BoE, Bank of Japan. Any policy signals, rate decisions, speeches, or shifts in forward guidance. What is the market pricing in for the next meeting of each? Note any divergence between central banks and why it matters for FX and bonds.

**4. TOP 3 STORIES DRIVING MARKETS TODAY**
The three most consequential developments from the last 12 hours. For each: what happened, why it is moving markets (explain the mechanism), and what to watch as it develops.

**5. GEOPOLITICS AND GLOBAL AFFAIRS**
Key developments with real financial or economic consequences. US politics and policy (tariffs, fiscal, regulation), US-China, Middle East, Russia-Ukraine, European politics, UK-specific news.

**6. SECTORS, EARNINGS AND NOTABLE MOVERS**
Significant earnings, analyst calls, M&A, IPO news, sector rotation. Flag UK-specific equity stories separately.

**7. WHAT TO WATCH TODAY**
Scheduled data releases, central bank speakers, earnings due today, geopolitical deadlines. This is my agenda for the day.

**8. THE ANALYST'S TAKE**
4-6 sentences synthesising everything. What is the single most important macro or market dynamic right now? What is the market narrative? What should I be watching over the next 24-48 hours? Briefly explain a concept where relevant. This is where I learn.

Keep total length appropriate for a focused 15-20 minute read. Use bold headers and sub-bullets. Be precise with numbers.
""".strip()


EVENING_PROMPT = """
You are my personal financial and geopolitical intelligence analyst. I am pivoting into a career in finance and use this briefing to understand what drove markets today and what is setting up for tomorrow. I am UK-based, building expertise in markets and macro. Compile a structured evening briefing covering today's full session. Explain the why behind moves — I want to understand market mechanisms, not just see numbers.

Primary focus regions: US, UK, Eurozone, Japan. Include other regions only if genuinely significant.

Structure the briefing exactly as follows:

**1. TODAY'S MARKET CLOSE**
Final closing numbers for: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225. Key FX closes: GBP/USD, EUR/USD, USD/JPY, DXY. Commodities: Brent, Gold, notable movers. US Treasury yields (2yr and 10yr) — note significant moves and explain why they matter. One sentence: the story of today's session.

**2. WHY MARKETS MOVED THE WAY THEY DID**
Most important section. Explain the cause and effect of today's major moves. What was the catalyst? What was the mechanism? Was it macro data, Fed commentary, earnings, geopolitics, or flows? Explain the chain of reasoning the market used.

**3. TODAY'S TOP 3 STORIES**
The three most impactful stories of the day. For each: what happened, the market reaction and why, and whether this is a one-day story or something with legs.

**4. GEOPOLITICS AND GLOBAL AFFAIRS UPDATE**
Developments with economic or market consequences. US policy, US-China, Middle East, Russia-Ukraine, European politics, UK domestic. Flag anything quietly building that markets may not be fully pricing yet.

**5. DATA AND CENTRAL BANKS — TODAY'S SCORECARD**
Economic data released today and how it shifted the macro picture. Central bank commentary and how it moved rate expectations. Where markets are pricing the next rate moves for Fed, ECB, BoE and BoJ.

**6. EARNINGS, SECTORS AND CORPORATE NEWS**
Notable earnings beats/misses and what they signal about the broader economy. Major M&A, analyst calls, sector moves. UK equity highlights separately.

**7. WHAT'S SETTING UP FOR TOMORROW**
Key data releases, central bank speakers, earnings, geopolitical events scheduled for tomorrow and the rest of the week. What are the known risk events?

**8. THE ANALYST'S TAKE**
4-6 sentences synthesising today. What was the dominant narrative? Did anything surprise? What concept did today illustrate that is worth understanding more deeply? Leave me with the one thing I should be thinking about overnight.

Keep total length appropriate for a focused 15-20 minute read. Be precise with numbers.
""".strip()


SATURDAY_PROMPT = """
You are my personal financial and geopolitical intelligence analyst. I am pivoting into a career in finance and use this weekly roundup to consolidate everything that happened this week. I am UK-based building deep expertise in markets and macro. Compile a comprehensive weekly roundup covering Monday through Friday just ended. Go deeper than the daily briefings. Explain themes, trends, and narratives that built across the week.

Primary focus regions: US, UK, Eurozone, Japan. Include other regions if genuinely significant.

Structure the briefing exactly as follows:

**1. WEEKLY MARKET SCORECARD**
Full week performance for: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225. Weekly FX moves: GBP/USD, EUR/USD, USD/JPY, DXY — where they started and finished. Commodities: Brent Crude, Gold, notable movers. US 2yr and 10yr Treasury yields — end vs Monday open. One sentence: the defining theme of markets this week.

**2. THE WEEK'S NARRATIVE**
Synthesise the overarching story of the week as a coherent narrative, not a bullet list. What was the market obsessing over? How did the narrative evolve from Monday to Friday? Were there turning points? What was the dominant risk sentiment and why?

**3. THE TOP 5 STORIES OF THE WEEK**
The five most consequential developments. For each: what happened and when, why it mattered to markets, the mechanism behind the market reaction, and whether it is resolved or still developing.

**4. CENTRAL BANKS THIS WEEK**
Any Fed, ECB, BoE, or BoJ activity — decisions, minutes, speeches, forward guidance shifts. How did rate expectations shift across the week? Explain any divergence between central banks and what it means for FX.

**5. GEOPOLITICS AND GLOBAL AFFAIRS — THE WEEK IN REVIEW**
Most significant geopolitical developments with real market consequences. US policy, US-China, Middle East, Russia-Ukraine, European politics, UK domestic.

**6. SECTORS, EARNINGS AND CORPORATE HIGHLIGHTS**
Most important earnings — beats, misses, and what they signal. Major M&A, IPOs, analyst calls. Sector rotation trends. UK equity highlights separately.

**7. MACRO DATA ROUNDUP**
All significant economic data released this week across US, UK, Eurozone, Japan. For each: what it showed, what was expected, and what it means for the macro picture.

**8. CONCEPT OF THE WEEK**
One market concept or mechanism that featured prominently this week — explained clearly and in depth so I genuinely understand it. Make it directly relevant to this week's events.

**9. THE ANALYST'S WEEKLY TAKE**
6-8 sentences synthesising the week. What was most important? What is the dominant macro regime right now and is it changing? What should I carry into next week as my core mental model?

Aim for a thorough 25-30 minute read. Be precise with numbers and percentages.
""".strip()


SUNDAY_PROMPT = """
You are my personal financial and geopolitical intelligence analyst. I am pivoting into a career in finance and use this Sunday preview to walk into the week prepared and informed. I am UK-based building expertise in markets and macro. Compile a detailed preview of the week ahead — the economic data calendar, central bank events, earnings, geopolitical flashpoints, and the macro themes that will dominate.

Primary focus regions: US, UK, Eurozone, Japan. Flag anything globally significant.

Structure the briefing exactly as follows:

**1. THE WEEK AHEAD — AT A GLANCE**
8-10 bullet overview of the most important scheduled events in chronological order.

**2. ECONOMIC DATA CALENDAR — THE BIG RELEASES**
For each major release this week across US, UK, Eurozone, Japan: what is being released and when (UK time), previous reading, market consensus expectation, why this release matters right now, and what a beat or miss could mean for markets. Flag the single most important release of the week and why.

**3. CENTRAL BANK EVENTS**
Scheduled rate decisions, minutes, speeches, press conferences from Fed, ECB, BoE, BoJ. For each: what is expected, what the market is pricing in, and what surprise scenarios could move markets.

**4. EARNINGS SEASON WATCH**
Key companies reporting this week. For each major release: market expectations, what to watch beyond headline numbers, and what results could signal about the broader economy.

**5. GEOPOLITICAL CALENDAR AND FLASHPOINTS**
Scheduled political events with market impact. Flag slow-burning situations that could escalate this week.

**6. KEY RISKS THIS WEEK**
3-5 specific risk scenarios — both upside and downside — with the potential market impact of each.

**7. THEMES TO WATCH**
The 2-3 overarching macro themes or narratives that will likely dominate the week's trading.

**8. HOW TO THINK ABOUT THIS WEEK**
5-6 sentences. What is the market's key question right now? What single event is most likely to shift the macro narrative? Where could the consensus be wrong? Leave me with a clear mental model to carry into Monday.

Aim for a thorough 20-25 minute read. Include specific dates, UK times, and consensus forecasts where available.
""".strip()


# ─────────────────────────────────────────────
#  DETERMINE WHICH BRIEFING TO RUN
# ─────────────────────────────────────────────

def get_briefing_config():
    uk_tz = pytz.timezone("Europe/London")
    now = datetime.now(uk_tz)
    day = now.weekday()
    date_str = now.strftime("%A, %d %B %Y")

    if day == 5:
        return SATURDAY_PROMPT, "Weekly Market Roundup — " + date_str
    elif day == 6:
        return SUNDAY_PROMPT, "Week Ahead Preview — " + date_str
    else:
        if now.hour < 14:
            return MORNING_PROMPT, "Morning Market Briefing — " + date_str
        else:
            return EVENING_PROMPT, "Evening Market Briefing — " + date_str


# ─────────────────────────────────────────────
#  CALL GEMINI REST API — WITH SEARCH, FALLBACK WITHOUT
# ─────────────────────────────────────────────

def call_gemini(api_key, prompt, use_search):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent?key=" + api_key
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "maxOutputTokens": 8000,
            "temperature": 0.4
        }
    }

    if use_search:
        payload["tools"] = [{"google_search": {}}]

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload, timeout=300)
    response.raise_for_status()

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates in response: " + str(data))

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [p.get("text", "") for p in parts if "text" in p]
    return "\n\n".join(text_parts)


def generate_briefing(prompt):
    api_key = os.environ["GEMINI_API_KEY"].strip()

    # Try with Google Search grounding first
    try:
        print("Attempting with Google Search grounding...")
        result = call_gemini(api_key, prompt, use_search=True)
        print("Search grounding succeeded.")
        return result
    except requests.exceptions.HTTPError as e:
        print("Search grounding failed (" + str(e) + "), falling back to base model...")

    # Fallback: generate without search grounding
    search_note = (
        "Note: Use your most recent training knowledge to provide the best "
        "possible market briefing. Be clear where data may not be fully current "
        "and provide context based on the most recent trends you are aware of.\n\n"
    )
    return call_gemini(api_key, search_note + prompt, use_search=False)


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
            len(stripped) > 4
        )

        if is_header:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = stripped.strip("*")
            html_lines.append('<h2 class="section-header">' + content + "</h2>")

        elif stripped.startswith("- "):
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
            html_lines.append('<hr class="divider">')

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

    body_html = "\n".join(html_lines)

    html = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
    html += "<meta charset=\"UTF-8\">\n"
    html += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
    html += "<title>" + subject + "</title>\n<style>\n"
    html += "body{font-family:Georgia,serif;background-color:#f4f4f0;margin:0;padding:20px;color:#1a1a1a}\n"
    html += ".container{max-width:720px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}\n"
    html += ".header{background:#0a2540;padding:28px 36px;color:#fff}\n"
    html += ".header h1{margin:0;font-size:22px;font-weight:700}\n"
    html += ".header p{margin:6px 0 0;font-size:13px;color:#8aa4c8;font-family:Arial,sans-serif}\n"
    html += ".content{padding:32px 36px;line-height:1.75}\n"
    html += "h2.section-header{font-size:16px;color:#0a2540;margin:32px 0 10px;padding:10px 14px;background:#f0f4fa;border-left:4px solid #1a73e8;border-radius:0 4px 4px 0}\n"
    html += "p{margin:0 0 14px;font-size:15px;color:#2d2d2d}\n"
    html += "ul{padding-left:20px;margin:8px 0 16px}\n"
    html += "li{margin-bottom:7px;font-size:15px;color:#2d2d2d}\n"
    html += "strong{color:#0a2540}\n"
    html += "hr.divider{border:none;border-top:1px solid #e8e8e8;margin:24px 0}\n"
    html += ".footer{background:#f9f9f7;border-top:1px solid #e8e8e8;padding:16px 36px;font-family:Arial,sans-serif;font-size:12px;color:#888;text-align:center}\n"
    html += "</style>\n</head>\n<body>\n"
    html += "<div class=\"container\">\n"
    html += "  <div class=\"header\"><h1>" + subject + "</h1>\n"
    html += "  <p>Your personal market intelligence briefing — generated automatically</p></div>\n"
    html += "  <div class=\"content\">\n" + body_html + "\n  </div>\n"
    html += "  <div class=\"footer\">Generated by your market intelligence system &nbsp;|&nbsp; Powered by Google Gemini &nbsp;|&nbsp; Free</div>\n"
    html += "</div>\n</body>\n</html>"

    return html


# ─────────────────────────────────────────────
#  SEND EMAIL VIA OUTLOOK SMTP
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

    with smtplib.SMTP("smtp-mail.outlook.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    uk_tz = pytz.timezone("Europe/London")
    print("Starting briefing run at " + datetime.now(uk_tz).strftime("%Y-%m-%d %H:%M %Z"))

    prompt, subject = get_briefing_config()
    print("Briefing type: " + subject)

    raw_text = generate_briefing(prompt)
    print("Briefing generated — " + str(len(raw_text)) + " characters")

    html_body = convert_to_html(subject, raw_text)
    print("Sending email via Outlook SMTP...")
    send_email(subject, html_body, raw_text)
    print("Email sent successfully!")


if __name__ == "__main__":
    main()
