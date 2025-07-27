import requests
import time
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import config  

client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
signatures_collection = db[config.SIGNATURES_COLLECTION]
tx_data_collection = db[config.TX_DATA_COLLECTION]

url = config.RPC_URL
address = config.ADDRESS
headers = {"Content-Type": "application/json"}

def fetch_and_save_signatures():
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
            signatures_collection.insert_one(latest_tx)
            print("Inserted latest transaction:", latest_tx["signature"])
        except DuplicateKeyError:
            pass
    else:
        print("No transactions found for latest fetch.")

    before = None
    batch_size = 1000
    max_transactions = 200
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
                    signatures_collection.insert_one(sig)
                    new_sigs += 1
                except DuplicateKeyError:
                    pass

            total_in_db = signatures_collection.count_documents({})
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
            if e.response.status_code == 429:
                print("Rate limit hit. Waiting for 60 seconds before retrying.")
                time.sleep(60)
                continue
            else:
                print(f"HTTP Error: {e}")
                break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

    print("Fetching signatures completed.")

def fetch_and_save_transaction_details():
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
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("result"):
            raise Exception("Transaction not found or not available.")
        return data["result"]

    print("\nFetching transaction details for saved signatures.")
    signatures = signatures_collection.distinct("signature")

    for signature in signatures:
        print(f"\nFetching transaction details for: {signature}")
        try:
            tx = fetch_tx_detail(signature)

            tx["_id"] = signature

            if "transaction" in tx and "message" in tx["transaction"]:
                accounts = tx["transaction"]["message"].get("accountKeys", [])
                
            if "slot" in tx:
                tx["block_number"] = tx["slot"]

            if "meta" in tx and "computeUnitsConsumed" in tx["meta"]:
                tx["gas"] = tx["meta"]["computeUnitsConsumed"]

            if "blockTime" in tx:
                tx["block_timestamp"] = tx["blockTime"]

            if "meta" in tx:
                tx["status"] = "success" if tx["meta"].get("err") is None else "failed"

        
            result = tx_data_collection.replace_one({"_id": signature}, tx, upsert=True)
            if result.upserted_id or result.modified_count:
                print("Transaction saved to MongoDB (tx_data).")
            else:
                print("Transaction already exists. No changes made.")

            time.sleep(0.5)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print("Rate limit hit (429). Waiting for 60 seconds before retrying.")
                time.sleep(60)
                continue
            else:
                print(f"HTTP Error fetching transaction {signature}: {e}")
        except Exception as e:
            print(f"Error fetching transaction {signature}: {e}")

    print("All transaction details fetched & stored successfully!")

if __name__ == "__main__":
    fetch_and_save_signatures()
    fetch_and_save_transaction_details()
    print("\n completed successfully!")
