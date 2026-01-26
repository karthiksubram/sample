import requests
import time
import os
from google import genai
import xml.etree.ElementTree as ET

from prettytable import PrettyTable
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from telegram.constants import ParseMode
import prettytable as pt
import time
import random
from google.genai.errors import ServerError

# Load .env early
load_dotenv()

# --- CONFIGURATION ---


IB_TOKEN = os.getenv('IB_TOKEN')
QUERY_ID = os.getenv('QUERY_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
AUTHORIZED_USER_ID = os.getenv('CHAT_ID')
client = genai.Client(api_key=GEMINI_API_KEY)


def get_ibkr_positions():
    # Step 1: Request the report
    base_url = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest"
    params = {'t': IB_TOKEN, 'q': QUERY_ID, 'v': '3'}

    response = requests.get(base_url, params=params)
    tree = ET.fromstring(response.content)

    if tree.find('Status').text == 'Success':
        code = tree.find('ReferenceCode').text
        url = tree.find('Url').text

        # Step 2: Wait and fetch (IBKR takes a few seconds to generate)
        time.sleep(5)
        fetch_params = {'t': IB_TOKEN, 'q': code, 'v': '3'}
        report_response = requests.get(url, params=fetch_params)
        return report_response.content
    else:
        return None


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


def parse_new_format(text):
    """Parse the new Start/End Part 1 & 2 format"""

    part1_data = []
    part2_data = []
    in_part1 = False
    in_part2 = False

    lines = text.split('\n')
    for line in lines:
        line = line.strip()

        # Part markers
        if line == 'Start Part 1':
            in_part1 = True
            in_part2 = False
            continue
        elif line == 'End Part 1':
            in_part1 = False
            continue
        elif line == 'Start Part 2':
            in_part2 = True
            continue
        elif line == 'End Part 2':
            in_part2 = False
            continue

        # Parse data rows (format: SYMBOL|QTY|ACTION|COMMENT)
        if '|' in line and (in_part1 or in_part2):
            cells = [cell.strip() for cell in line.split('|')]

            if in_part1 and len(cells) >= 4:
                part1_data.append(cells[:4])
            elif in_part2 and len(cells) >= 3:
                part2_data.append(cells[:3])

    return part1_data, part2_data

def is_503_error(e: Exception) -> bool:
    if isinstance(e, ServerError):
        # Case 1: response object exists
        if hasattr(e, "response") and e.response is not None:
            return getattr(e.response, "status_code", None) == 503

        # Case 2: fallback to message inspection
        msg = str(e).lower()
        return "503" in msg or "unavailable" in msg

    return False

MODELS = [
    "gemini-3-flash-preview",
    "gemini-1.5-flash",
    "gemini-1.0-pro"
]

def generate_with_fallback(client, prompt, retries=3):
    for model in MODELS:
        for attempt in range(retries):
            try:
                return client.models.generate_content(
                    model=model,
                    contents=prompt
                )
            except Exception as e:
                if is_503_error(e):
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait)
                else:
                    raise
    raise RuntimeError("All models unavailable")


async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(AUTHORIZED_USER_ID):
        await update.message.reply_text("You cannot use analysis feature...")
        return
    # 1. Fetch
    await update.message.reply_text("Fetching positions from IBKR...")
    raw_xml = fetch_ibkr_portfolio()
    if not raw_xml: return
    positions = parse_xml_to_list(raw_xml)

    pos_context = "\n".join([f"{p['symbol']} ({p['qty']} shares)" for p in positions])

    prompt = os.getenv("CPROMPT").format(pos_context=pos_context)

    await update.message.reply_text("Analyzing your positions...")

    # response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
    response = generate_with_fallback(client, prompt)

    text = response.text

    # 3. Parsing and Formatting
    # (Simplified parsing logic: assuming AI returns structured lines)
    t1, t2 = parse_new_format(text)
    table = pt.PrettyTable(['Symbol', 'Qty', 'Action', 'Comments'])
    table.hrules = pt.HRuleStyle.ALL
    table.vrules = pt.VRuleStyle.ALL
    table.align = {'Symbol': 'l', 'Qty': 'r', 'Action': 'c', 'Comments': 'l'}
    table.add_rows(t1)
    table.del_column("Comments")

    table_str = table.get_string(sortby='Action')

    # 4. Send to Telegram
    await update.message.reply_html(text=f'<pre>{table_str}</pre>')
    # await tg_bot.send_message(CHAT_ID, t2_msg, parse_mode='MarkdownV2')


def fmt(strNum):
    if strNum is None:
        return None
    return round(float(strNum), 2)


def parse_positions(xml_data):
    # This parses the XML specifically for 'OpenPosition' tags
    root = ET.fromstring(xml_data)
    positions = []
    for pos in root.iter('OpenPosition'):
        symbol = pos.get('symbol')
        qty = pos.get('position')
        mkt_val = pos.get('markPrice')
        # positions.append(f"🔹 {symbol}: {qty} @ {mkt_val}")
        positions.append(
            [pos.get('symbol'), pos.get('position'), fmt(pos.get('markPrice')), fmt(pos.get('positionValue')),
             fmt(pos.get('fifoPnlUnrealized'))])
    return positions


async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(AUTHORIZED_USER_ID):
        await update.message.reply_text("You cannot use this feature...")
        return

    await update.message.reply_text("Fetching positions from IBKR...")
    raw_xml = fetch_ibkr_portfolio()
    if not raw_xml: return
    table = pt.PrettyTable(['Symbol', 'Qty', 'Price', 'Value', 'PnL-Unrealized'])
    positions = parse_positions(raw_xml)

    table.hrules = pt.HRuleStyle.ALL
    table.vrules = pt.VRuleStyle.ALL
    table.align = {'Symbol': 'l', 'Qty': 'r', 'Price': 'r', 'Value': 'r', 'PnL-Unrealized': 'r'}
    table.add_rows(positions)
    table.del_column("PnL-Unrealized")
    table.del_column("Price")

    table_str = table.get_string(sortby='Value', reversesort=True)

    # 4. Send to Telegram
    await update.message.reply_html(text=f'<pre>{table_str}</pre>')


if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("p", positions_command))
    app.add_handler(CommandHandler("a", run_analysis))
    print("Bot is running...")
    app.run_polling()
