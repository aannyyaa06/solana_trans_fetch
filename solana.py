import base64
import requests
from datetime import datetime, timezone
from pymongo import MongoClient
import sys
import config  

client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
collection = db[config.COLLECTION_NAME]

def load_signatures(filename=config.SIGNATURES_FILE):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return []

def fetch_tx_detail(signature: str) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0
            }
        ]
    }
    response = requests.post(config.RPC_URL, json=payload)
    if response.status_code != 200:
        raise Exception(f"HTTP error: {response.status_code}")
    
    data = response.json()
    if not data.get("result"):
        raise Exception("Transaction not found or not available.")
    return data["result"]

def display_tx(tx: dict, verbose=False) -> None:
    meta = tx.get("meta", {})
    block_time = tx.get("blockTime")
    slot = tx.get("slot")
    tx_info = tx.get("transaction", {}).get("message", {})

    print("\nTransaction Details")
    print(f"Slot:         {slot}")
    if block_time:
        print(f"Timestamp:    {datetime.fromtimestamp(block_time, timezone.utc)} UTC")
    print(f"Fee:          {int(meta.get('fee', 0)) / 1e9:.9f} SOL")

    print("\nSOL Balance Changes:")
    post_balances = meta.get("postBalances", [])
    pre_balances = meta.get("preBalances", [])
    accounts = tx_info.get("accountKeys", [])
    for i in range(min(len(accounts), len(pre_balances))):
        delta = (post_balances[i] - pre_balances[i]) / 1e9
        if delta != 0:
            addr = accounts[i]['pubkey'] if isinstance(accounts[i], dict) else accounts[i]
            print(f"{addr}: {delta:+.9f} SOL")

    print("\nToken Transfers:")
    found_transfer = False
    for instr in meta.get("innerInstructions", []):
        for ix in instr.get("instructions", []):
            parsed = ix.get("parsed")
            if parsed and parsed.get("type") == "transfer":
                info = parsed.get("info", {})
                print(f"{info.get('mint')}: {info.get('amount')} from {info.get('source')} → {info.get('destination')}")
                found_transfer = True
            elif not parsed and 'data' in ix:
                try:
                    raw_data = base64.b64decode(ix['data'])
                    if raw_data and raw_data[0] == 3:  
                        amount = int.from_bytes(raw_data[1:9], byteorder="little")
                        src = ix['accounts'][0]
                        dst = ix['accounts'][1]
                        print(f"[RAW] {amount} tokens from {src} → {dst}")
                        found_transfer = True
                except Exception as e:
                    if verbose:
                        print(f"[DEBUG] Raw decode failed: {e}")
    if not found_transfer:
        print("No token transfers found.")

    if verbose:
        print("\nRaw Instructions:")
        for idx, ix in enumerate(tx_info.get("instructions", [])):
            print(f"\nInstruction {idx + 1}:")
            print(f"  Program ID: {ix.get('programId')}")
            print(f"  Data (base64): {ix.get('data')}")
            print(f"  Accounts: {ix.get('accounts')}")

if __name__ == "__main__":
    verbose = "verbose" in sys.argv
    signatures = load_signatures()
    if not signatures:
        print("[ERROR] No signatures found.")
        sys.exit(1)

    for signature in signatures:
        print(f"\n Fetching transaction: {signature}")
        try:
            tx = fetch_tx_detail(signature)
            display_tx(tx, verbose=verbose)

            tx["_id"] = signature
            result = collection.replace_one({"_id": signature}, tx, upsert=True)
            if result.upserted_id or result.modified_count:
                print(" Transaction saved to MongoDB.")
            else:
                print(" Transaction already exists. No changes made.")
        except Exception as e:
            print(f" Could not fetch or save transaction {signature}: {e}")
