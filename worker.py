import time
import requests
import xml.etree.ElementTree as ET
import duckdb
from screening import screen_entity_name

DB_PATH = "data/platform_state.duckdb"
SEC_RSS_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&datea=&dateb=&owner=include&count=40&output=atom"
HEADERS = {"User-Agent": "RegWatchCompliancePlatform admin@regwatch.io"}

def get_active_subscriptions():
    conn = duckdb.connect(DB_PATH)
    rows = conn.execute("SELECT ticker, slack_webhook FROM subscriptions").fetchall()
    conn.close()
    
    sub_map = {}
    for ticker, webhook in rows:
        sub_map.setdefault(ticker.upper(), []).append(webhook)
    return sub_map

def parse_sec_feed():
    try:
        response = requests.get(SEC_RSS_URL, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"[Worker] SEC RSS HTTP {response.status_code}")
            return []

        root = ET.fromstring(response.content)
        filings = []
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text if entry.find('atom:title', ns) is not None else ""
            link_elem = entry.find('atom:link', ns)
            link = link_elem.attrib['href'] if link_elem is not None else ""
            filings.append({"title": title, "link": link})
        return filings
    except Exception as e:
        print(f"[Worker Error] SEC Feed parse failed: {e}")
        return []

def dispatch_webhook(webhook_url: str, payload: dict):
    try:
        resp = requests.post(webhook_url, json=payload, timeout=5)
        print(f"[Worker] Webhook sent to {webhook_url} - Status: {resp.status_code}")
    except Exception as e:
        print(f"[Worker] Webhook delivery failed: {e}")

def run_worker_cycle():
    print("[Worker] Inspecting live SEC 8-K filings...")
    sub_map = get_active_subscriptions()
    if not sub_map:
        print("[Worker] No active subscriptions registered in DuckDB. Skipping cycle.")
        return

    filings = parse_sec_feed()
    print(f"[Worker] Fetched {len(filings)} recent filings from SEC EDGAR.")

    for filing in filings:
        for ticker, webhooks in sub_map.items():
            if ticker in filing["title"].upper():
                print(f"[Worker] MATCH FOUND for ticker {ticker}: {filing['title']}")
                screening_result = screen_entity_name(filing["title"], threshold=70)
                
                event_payload = {
                    "event_type": "sec.8k_filing_detected",
                    "ticker": ticker,
                    "filing_title": filing["title"],
                    "filing_url": filing["link"],
                    "screening_result": screening_result,
                    "timestamp": time.time()
                }
                
                for webhook_url in webhooks:
                    dispatch_webhook(webhook_url, event_payload)

# -------------------------------------------------------------------------
# CRITICAL: THIS BLOCK KEEPS THE WORKER RUNNING CONTINUOUSLY
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print("[Worker] Starting RegWatch Background Polling Worker...")
    while True:
        try:
            run_worker_cycle()
        except Exception as e:
            print(f"[Worker Main Loop Error] {e}")
        time.sleep(30)  # Sleep 30 seconds between polling cycles