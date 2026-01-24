import os
import requests
import time
import xml.etree.ElementTree as ET
from google import genai
from telegram import Bot
import asyncio

# --- 1. CONFIGURATION ---
IB_TOKEN = os.environ.get("IB_TOKEN")
QUERY_ID = os.environ.get("QUERY_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Initialize Clients
client = genai.Client(api_key=GEMINI_API_KEY)
tg_bot = Bot(token=TELEGRAM_TOKEN)


def fetch_ibkr_portfolio():
    base_url = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest"
    res = requests.get(base_url, params={'t': IB_TOKEN, 'q': QUERY_ID, 'v': '3'})
    root = ET.fromstring(res.content)
    if root.find('Status').text != 'Success': return None

    ref_code = root.find('ReferenceCode').text
    url = root.find('Url').text
    time.sleep(10)  # Wait for report generation

    report_res = requests.get(url, params={'t': IB_TOKEN, 'q': ref_code, 'v': '3'})
    return report_res.content


def parse_xml_to_list(xml_data):
    root = ET.fromstring(xml_data)
    pos_list = []
    for pos in root.iter('OpenPosition'):
        pos_list.append({
            'symbol': pos.get('symbol'),
            'qty': pos.get('position'),
            'price': pos.get('markPrice')
        })
    return pos_list


def generate_table_1(analysis_data):
    # Table 1: Stocks/Qty/Action/Comments
    header = f"{'STOCK':<10} | {'QTY':<5} | {'ACTION':<5} | {'COMMENTS'}"
    separator = "-" * len(header)
    rows = []
    for item in analysis_data:
        # Expected analysis_data item: [Symbol, Qty, Action, Comment]
        row = f"{item[0]:<10} | {item[1]:<5} | {item[2]:<5} | {item[3]}"
        rows.append(row)
    return f"```\n{header}\n{separator}\n" + "\n".join(rows) + "\n```"


async def run_analysis():
    # 1. Fetch
    raw_xml = fetch_ibkr_portfolio()
    if not raw_xml: return
    positions = parse_xml_to_list(raw_xml)

    pos_context = "\n".join([f"{p['symbol']} ({p['qty']} shares)" for p in positions])

    # 2. AI Prompt
    prompt = (
        f"Analyze these Indian positions:\n{pos_context}\n\n"
        "Return the analysis in two parts:\n"
        "PART 1: A pipe-separated list: SYMBOL|QTY|ACTION(Buy/Sell/Hold)|SHORT_COMMENT\n"
        "PART 2: A pipe-separated list: RISK_FACTOR|IMPACT_LEVEL|MITIGATION_STRATEGY"
    )

    response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
    text = response.text

    # 3. Parsing and Formatting
    # (Simplified parsing logic: assuming AI returns structured lines)
    parts = text.split("PART 2")
    table1_raw = [line.split('|') for line in parts[0].split('\n') if '|' in line]
    table2_raw = [line.split('|') for line in parts[1].split('\n') if '|' in line]

    # Format Table 1
    t1_msg = "📊 *Portfolio Recommendations*\n" + generate_table_1(table1_raw)

    # Format Table 2 (Risk)
    t2_header = f"{'RISK FACTOR':<15} | {'IMPACT':<7} | {'MITIGATION'}"
    t2_rows = [f"{r[0]:<15} | {r[1]:<7} | {r[2]}" for r in table2_raw]
    t2_msg = "⚠️ *Risk Analysis Table*\n```\n" + t2_header + "\n" + ("-" * len(t2_header)) + "\n" + "\n".join(
        t2_rows) + "\n```"

    # 4. Send to Telegram
    await tg_bot.send_message(CHAT_ID, t1_msg, parse_mode='MarkdownV2')
    await tg_bot.send_message(CHAT_ID, t2_msg, parse_mode='MarkdownV2')


if __name__ == "__main__":
    asyncio.run(run_analysis())
