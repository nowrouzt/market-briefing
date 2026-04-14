"""
============================================================
  MARKET INTELLIGENCE BRIEFING — AUTO-DELIVERY SYSTEM
  Powered by Google Gemini API (free tier) + Google Search
============================================================
  Generates and emails a financial/geopolitical briefing
  tailored to the day and time it runs.

  Schedule:
    Mon–Fri 7am  → Morning Briefing
    Mon–Fri 5pm  → Evening Briefing
    Saturday 8am → Weekly Roundup
    Sunday   8am → Weekly Preview
============================================================
"""

import smtplib
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz
import google.generativeai as genai


# ─────────────────────────────────────────────
#  THE FOUR PROMPTS
# ─────────────────────────────────────────────

MORNING_PROMPT = """
You are my personal financial and geopolitical intelligence analyst. I am pivoting into a career in finance and use this briefing to stay sharp on global markets and macro developments. I am UK-based, financially literate but still building expertise. Using live web search, compile a structured morning briefing covering overnight developments and what to watch today. Be analytical — don't just report what happened, explain *why it matters* and the *mechanism* behind it (e.g. why a strong dollar hurts emerging markets, why yield curve moves matter). This is how I learn, not just stay informed.

Primary focus regions: US, UK, Eurozone, Japan. Include other regions (Australia, China, EM etc.) only if the development is genuinely market-moving or macro-significant.

Structure the briefing exactly as follows:

---

**🌍 1. OVERNIGHT MARKET SNAPSHOT**
Closing/overnight moves for: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225, and any significant Asian markets. Key FX: GBP/USD, EUR/USD, USD/JPY, DXY. Commodities: Brent Crude, Gold, and any notable movers. Crypto only if a major development occurred. End with one sentence: the dominant theme or mood of overnight markets.

**📊 2. MACRO PULSE**
Any overnight or this-morning data releases: inflation prints, jobs data, PMIs, GDP, retail sales, central bank minutes or speeches. Cover the US, UK, Eurozone and Japan. For each release: what the number was, what was expected, and what the market reaction was. Flag any upcoming tier-1 data due today.

**🏦 3. CENTRAL BANK WATCH**
Fed, ECB, BoE, and Bank of Japan. Any policy signals, rate decisions, speeches, or shifts in forward guidance. What is the market currently pricing in for the next meeting of each? Note any divergence between central banks and why it matters for FX and bonds.

**🔥 4. TOP 3 STORIES DRIVING MARKETS TODAY**
The three most consequential developments from the last 12 hours. For each:
- What happened
- Why it is moving markets (explain the mechanism)
- What to watch as it develops

**🌐 5. GEOPOLITICS & GLOBAL AFFAIRS**
Key developments with real financial or economic consequences. Cover: US politics and policy (tariffs, fiscal, regulation), US-China, Middle East, Russia-Ukraine, European politics, and UK-specific news. Flag anything materially affecting trade, energy, supply chains, or risk sentiment.

**📈 6. SECTORS, EARNINGS & NOTABLE MOVERS**
Any significant earnings releases, guidance updates, analyst upgrades/downgrades, M&A, or IPO news. Note any sector rotation happening. Flag UK-specific equity stories separately.

**🎯 7. WHAT TO WATCH TODAY**
A forward-looking section: scheduled data releases, Fed/ECB/BoE speakers, earnings due today, and any geopolitical deadlines or votes. Think of this as my agenda for the day.

**🧠 8. THE ANALYST'S TAKE**
4–6 sentences. Synthesise everything: what is the single most important macro or market dynamic right now, what is the market narrative, and what should I be watching over the next 24–48 hours. Where relevant, briefly explain a concept I should understand. This is where I learn.

---
Keep total length appropriate for a focused 15–20 minute read. Use bold headers and sub-bullets. Be precise with numbers. Search for the most recent available data before writing every section.
""".strip()


EVENING_PROMPT = """
You are my personal financial and geopolitical intelligence analyst. I am pivoting into a career in finance and use this briefing to understand what drove markets today and what is setting up for tomorrow. I am UK-based, building expertise in markets and macro. Using live web search, compile a structured evening briefing covering today's full session. Explain the *why* behind moves — I want to understand market mechanisms, not just see numbers. This briefing should feel like a debrief: what happened, what it means, and what comes next.

Primary focus regions: US, UK, Eurozone, Japan. Include other regions only if genuinely significant.

Structure the briefing exactly as follows:

---

**📉 1. TODAY'S MARKET CLOSE**
Final closing numbers for: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225. Key FX closes: GBP/USD, EUR/USD, USD/JPY, DXY. Commodities: Brent, Gold, any notable movers. US Treasury yields (2yr and 10yr) — note any significant moves and explain why they matter. One sentence: the story of today's session in markets.

**🔍 2. WHY MARKETS MOVED THE WAY THEY DID**
This is the most important section. Explain the cause and effect of today's major market moves. What was the catalyst? What was the mechanism? Was it macro data, Fed commentary, earnings, geopolitics, or flows? Avoid just listing what happened — explain the chain of reasoning the market used.

**📰 3. TODAY'S TOP 3 STORIES**
The three most impactful stories of the day. For each:
- What happened
- The market reaction and why
- Whether this is a one-day story or something with legs

**🌐 4. GEOPOLITICS & GLOBAL AFFAIRS UPDATE**
Developments today with economic or market consequences. US policy, US-China, Middle East, Russia-Ukraine, European politics, UK domestic. Flag anything that is quietly building in the background that markets may not be fully pricing yet.

**📊 5. DATA & CENTRAL BANKS — TODAY'S SCORECARD**
Recap of any economic data released today and how it shifted the macro picture. Any central bank commentary and how it moved rate expectations. Update on where markets are pricing the next rate moves for Fed, ECB, BoE and BoJ.

**🏢 6. EARNINGS, SECTORS & CORPORATE NEWS**
Notable earnings beats/misses and what they signal about the broader economy. Any major M&A, analyst calls, sector-wide moves. UK equity highlights separately.

**🔭 7. WHAT'S SETTING UP FOR TOMORROW**
Key data releases, central bank speakers, earnings, and geopolitical events scheduled for tomorrow and the rest of the week. What are the known risk events? What is the market watching most closely right now?

**🧠 8. THE ANALYST'S TAKE**
4–6 sentences synthesising today. What was the dominant narrative? Did anything surprise? What concept or dynamic did today illustrate that is worth understanding more deeply? Leave me with the one thing I should be thinking about overnight.

---
Keep total length appropriate for a focused 15–20 minute read. Use bold headers and sub-bullets. Be precise with numbers. Search the most recent data available before writing every section.
""".strip()


SATURDAY_PROMPT = """
You are my personal financial and geopolitical intelligence analyst. I am pivoting into a career in finance and use this weekly roundup to consolidate everything that happened across global markets and world affairs this week. I am UK-based and building deep expertise in markets and macro. Using live web search, compile a comprehensive weekly roundup covering Monday through Friday of the week just ended. This is my most important read of the week — go deeper than the daily briefings. Explain themes, trends, and narratives that built across the week, not just individual daily events.

Primary focus regions: US, UK, Eurozone, Japan. Include other regions (China, Australia, EM etc.) if genuinely significant to the week's story.

Structure the briefing exactly as follows:

---

**📊 1. WEEKLY MARKET SCORECARD**
Full week performance for: S&P 500, Nasdaq, Dow, FTSE 100, DAX, CAC 40, Nikkei 225. Weekly FX moves: GBP/USD, EUR/USD, USD/JPY, DXY — where they started and where they finished. Commodities: Brent Crude, Gold, and any notable movers. US 2yr and 10yr Treasury yields — where they ended vs Monday open. One sentence: the defining theme of markets this week.

**📖 2. THE WEEK'S NARRATIVE**
Don't just list what happened day by day — synthesise the overarching story of the week. What was the market obsessing over? How did the narrative evolve from Monday to Friday? Were there turning points or inflection moments? What was the dominant risk sentiment (risk-on / risk-off) and why? Write this as a coherent story, not a bullet list.

**🔥 3. THE TOP 5 STORIES OF THE WEEK**
The five most consequential developments of the week. For each:
- What happened and when
- Why it mattered to markets
- The mechanism behind the market reaction
- Whether it is resolved or still developing

**🏦 4. CENTRAL BANKS THIS WEEK**
Recap of any Fed, ECB, BoE, or BoJ activity — decisions, minutes, speeches, or shifts in forward guidance. How did rate expectations shift across the week? What changed in the market's understanding of the monetary policy path? Explain any divergence between major central banks and what it means for FX.

**🌐 5. GEOPOLITICS & GLOBAL AFFAIRS — THE WEEK IN REVIEW**
The week's most significant geopolitical and global affairs developments with real economic or market consequences. US policy and politics, US-China, Middle East, Russia-Ukraine, European politics, UK domestic. Highlight anything that quietly escalated or de-escalated this week that markets may still be underestimating.

**📈 6. SECTORS, EARNINGS & CORPORATE HIGHLIGHTS**
The most important earnings of the week — beats, misses, and what they signal about the broader economy and corporate health. Any major M&A, IPOs, or analyst calls that moved markets. Sector rotation trends — what was bought, what was sold, and why. UK equity highlights separately.

**📉 7. MACRO DATA ROUNDUP**
All significant economic data released this week across the US, UK, Eurozone, and Japan. For each release: what it showed, what was expected, and what it means for the macro picture. How has the data collectively shifted the economic narrative this week?

**💡 8. CONCEPT OF THE WEEK**
One market concept, mechanism, or financial term that featured prominently this week — explained clearly and in depth so I genuinely understand it. Make it directly relevant to this week's events.

**🧠 9. THE ANALYST'S WEEKLY TAKE**
6–8 sentences. Your synthesis of the week: What was the most important thing that happened? What did markets get right or wrong? What is the dominant macro regime right now and is it changing? What should I carry into next week as my core mental model?

---
Aim for a thorough 25–30 minute read. Use bold headers and sub-bullets. Be precise with numbers and percentages. Search for final weekly closing data before writing the scorecard.
""".strip()


SUNDAY_PROMPT = """
You are my personal financial and geopolitical intelligence analyst. I am pivoting into a career in finance and use this Sunday preview to walk into the week prepared and informed. I am UK-based and building expertise in markets and macro. Using live web search, compile a detailed preview of the week ahead — the economic data calendar, central bank events, earnings, geopolitical flashpoints, and the macro themes that will dominate. I want to understand not just *what* is coming but *why it matters* and what the market is expecting.

Primary focus regions: US, UK, Eurozone, Japan. Flag anything globally significant.

Structure the briefing exactly as follows:

---

**🗓️ 1. THE WEEK AHEAD — AT A GLANCE**
A brief (8–10 bullet) overview of the most important scheduled events of the week in chronological order.

**📊 2. ECONOMIC DATA CALENDAR — THE BIG RELEASES**
For each major data release due this week across the US, UK, Eurozone, and Japan:
- What is being released and when (include UK time)
- What the previous reading was
- What the market consensus is expecting
- Why this particular release matters right now given the current macro environment
- What a beat or miss could mean for markets

Flag which release is the single most important of the week and why.

**🏦 3. CENTRAL BANK EVENTS**
Any scheduled rate decisions, meeting minutes, speeches, or press conferences from the Fed, ECB, BoE, and BoJ this week. For each: what is expected, what the market is pricing in, and what surprise scenarios could move markets.

**🏢 4. EARNINGS SEASON WATCH**
Key companies reporting this week. For each major earnings release:
- What the market expects (consensus EPS and revenue)
- What to watch beyond the headline numbers
- What the results could signal about the broader economy or sector

**🌐 5. GEOPOLITICAL CALENDAR & FLASHPOINTS**
Scheduled political events with potential market impact. Also flag any slow-burning geopolitical situations that could escalate this week.

**⚠️ 6. KEY RISKS THIS WEEK**
What could surprise markets — both upside and downside. Identify 3–5 specific risk scenarios and explain the potential market impact of each.

**🎯 7. THEMES TO WATCH**
The 2–3 overarching macro themes or market narratives that will likely dominate the week's trading.

**🧠 8. HOW TO THINK ABOUT THIS WEEK**
5–6 sentences. Your framing of the week: What is the market's key question right now? What single event is most likely to shift the macro narrative? Where could the consensus be wrong?

---
Aim for a thorough 20–25 minute read. Use bold headers and sub-bullets. Include specific dates, times in UK time, and consensus forecasts where available. Search for the latest economic calendar data before writing.
""".strip()


# ─────────────────────────────────────────────
#  DETERMINE WHICH BRIEFING TO RUN
# ─────────────────────────────────────────────

def get_briefing_config():
    uk_tz = pytz.timezone("Europe/London")
    now = datetime.now(uk_tz)
    day = now.weekday()  # 0 = Monday, 6 = Sunday
    date_str = now.strftime("%A, %d %B %Y")

    if day == 5:
        return SATURDAY_PROMPT, f"📅 Weekly Market Roundup — {date_str}"
    elif day == 6:
        return SUNDAY_PROMPT, f"🔭 Week Ahead Preview — {date_str}"
    else:
        if now.hour < 14:
            return MORNING_PROMPT, f"🌅 Morning Market Briefing — {date_str}"
        else:
            return EVENING_PROMPT, f"🌆 Evening Market Briefing — {date_str}"


# ─────────────────────────────────────────────
#  CALL GEMINI API WITH GOOGLE SEARCH GROUNDING
# ─────────────────────────────────────────────

def generate_briefing(prompt: str) -> str:
    """
    Sends the prompt to Gemini 2.0 Flash via the Google GenAI SDK
    with Google Search grounding enabled for live web data.
    """
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools=[{"google_search_retrieval": {}}]
    )

    response = model.generate_content(prompt)
    return response.text


# ─────────────────────────────────────────────
#  FORMAT AS A CLEAN HTML EMAIL
# ─────────────────────────────────────────────

def convert_to_html(subject: str, raw_text: str) -> str:
    lines = raw_text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        if re.match(r"^\*\*.*\*\*$", stripped) and any(
            emoji in stripped for emoji in ["🌍","📊","🏦","🔥","🌐","📈","🎯","🧠","📉","🔍","📰","🏢","🔭","📅","🗓️","⚠️","💡","📖"]
        ):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = stripped.strip("*")
            html_lines.append(f'<h2 class="section-header">{content}</h2>')

        elif stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = stripped[2:]
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            html_lines.append(f"<li>{content}</li>")

        elif stripped == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append('<hr class="divider">')

        elif stripped == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("")

        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", stripped)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            if content:
                html_lines.append(f"<p>{content}</p>")

    if in_list:
        html_lines.append("</ul>")

    body_html = "\n".join(html_lines)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
<style>
  body {{
    font-family: 'Georgia', serif;
    background-color: #f4f4f0;
    margin: 0;
    padding: 20px;
    color: #1a1a1a;
  }}
  .container {{
    max-width: 720px;
    margin: 0 auto;
    background: #ffffff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }}
  .header {{
    background: #0a2540;
    padding: 28px 36px;
    color: #ffffff;
  }}
  .header h1 {{
    margin: 0;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.3px;
  }}
  .header p {{
    margin: 6px 0 0;
    font-size: 13px;
    color: #8aa4c8;
    font-family: 'Arial', sans-serif;
  }}
  .content {{
    padding: 32px 36px;
    line-height: 1.75;
  }}
  h2.section-header {{
    font-size: 16px;
    color: #0a2540;
    margin: 32px 0 10px;
    padding: 10px 14px;
    background: #f0f4fa;
    border-left: 4px solid #1a73e8;
    border-radius: 0 4px 4px 0;
  }}
  p {{
    margin: 0 0 14px;
    font-size: 15px;
    color: #2d2d2d;
  }}
  ul {{
    padding-left: 20px;
    margin: 8px 0 16px;
  }}
  li {{
    margin-bottom: 7px;
    font-size: 15px;
    color: #2d2d2d;
  }}
  strong {{ color: #0a2540; }}
  hr.divider {{
    border: none;
    border-top: 1px solid #e8e8e8;
    margin: 24px 0;
  }}
  .footer {{
    background: #f9f9f7;
    border-top: 1px solid #e8e8e8;
    padding: 16px 36px;
    font-family: 'Arial', sans-serif;
    font-size: 12px;
    color: #888;
    text-align: center;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{subject}</h1>
    <p>Your personal market intelligence briefing — generated automatically</p>
  </div>
  <div class="content">
    {body_html}
  </div>
  <div class="footer">
    Generated by your market intelligence system &nbsp;|&nbsp;
    Powered by Google Gemini with live search &nbsp;|&nbsp; £0.00/month
  </div>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────
#  SEND EMAIL VIA OUTLOOK SMTP
# ─────────────────────────────────────────────

def send_email(subject: str, html_body: str, plain_body: str):
    sender    = os.environ["EMAIL_ADDRESS"]
    password  = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", sender)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Market Intelligence <{sender}>"
    msg["To"]      = recipient

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
    print(f"Starting briefing run at {datetime.now(uk_tz).strftime('%Y-%m-%d %H:%M %Z')}")

    prompt, subject = get_briefing_config()
    print(f"Briefing type: {subject}")

    print("Calling Gemini API with Google Search grounding...")
    raw_text = generate_briefing(prompt)
    print(f"Briefing generated — {len(raw_text)} characters")

    html_body = convert_to_html(subject, raw_text)
    print("Sending email via Outlook SMTP...")
    send_email(subject, html_body, raw_text)
    print("✅ Email sent successfully!")


if __name__ == "__main__":
    main()
