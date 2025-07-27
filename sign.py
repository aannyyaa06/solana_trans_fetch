import requests
import time
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

client = MongoClient("mongodb://localhost:27017/")
db = client["solana_data"]
collection = db["signaturesss"]

collection.create_index("signature", unique=True)

address = "73KyqfAK4g1BSxzbcAdZ3vUn5oBJUGjd7N4nFPooK8uz"
url = "https://api.mainnet-beta.solana.com"
headers = {"Content-Type": "application/json"}

latest_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getSignaturesForAddress",
    "params": [address, {"limit": 1, "commitment": "confirmed"}]
}

latest_response = requests.post(url, headers=headers, json=latest_payload)
latest_result = latest_response.json().get("result", [])

if latest_result:
    latest_tx = latest_result[0]
    try:
        collection.insert_one(latest_tx)
        print("Inserted latest transaction:", latest_tx["signature"])
    except DuplicateKeyError:
        pass
else:
    print("No transactions found for latest fetch.")

before = None  
batch_size = 1000
max_transactions = 20000
total_in_db = collection.count_documents({})
previous_before = None

while True:
    params = [address, {"limit": batch_size}]
    if before:
        params[1]["before"] = before

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": params
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json().get("result", [])

        if not result:
            print("No more transactions available.")
            break

        new_sigs = 0
        for sig in result:
            try:
                collection.insert_one(sig)
                new_sigs += 1
            except DuplicateKeyError:
                pass

        total_in_db = collection.count_documents({})
        print(f"Fetched {new_sigs} new transactions. Total in DB: {total_in_db}")

        if total_in_db >= max_transactions:
            print(f"Reached {max_transactions} transactions. Stopping.")
            break

        result_sorted = sorted(result, key=lambda x: x.get("blockTime", float('inf')))
        earliest_signature = result_sorted[0]["signature"]

        if earliest_signature == previous_before:
            print("No further progress detected. Ending to avoid infinite loop.")
            break

        previous_before = before
        before = earliest_signature

        time.sleep(2)

    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            print("Rate limit hit. Waiting for 60 seconds before retrying.")
            time.sleep(60)
            continue
        else:
            print(f"HTTP Error: {e}")
            break
    except Exception as e:
        print(f"Unexpected error: {e}")
        break

print("Fetching completed.")

