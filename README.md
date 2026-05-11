<div align="center">

# ◎ Solana Transaction Fetcher

### Signature Collection · Transaction Details · MongoDB Storage

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Database-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Solana](https://img.shields.io/badge/Solana-RPC%20API-9945FF?style=flat-square&logo=solana&logoColor=white)](https://solana.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## Overview

This project fetches and stores complete transaction data for a Solana wallet address using the **Solana JSON-RPC API**. It works in two stages — first collecting transaction signatures, then pulling the full details for each one — and saves everything structured in MongoDB.

You can run each stage separately (`sign.py` → `solana.py`) or just fire the whole pipeline at once with `main1.py`.

---

## Key Features

- Fetches **20,000+ transaction signatures** with automatic pagination
- Skips duplicates automatically via MongoDB indexes
- Built-in **rate-limit handling** — backs off with `sleep(60)` on HTTP 429 errors
- Extracts and stores:
  - SOL balance changes (pre/post)
  - Token transfers (pre/post token balances)
  - Fees, slot numbers, and timestamps
- Runs as a **modular two-step process** or a **single combined pipeline**

---

## Project Structure

```
solana-transaction-fetcher/
│
├── sign.py          # Step 1 — fetch and store transaction signatures
├── solana.py        # Step 2 — fetch and store full transaction details
├── main1.py         # Combined pipeline (runs both steps)
└── config.py        # MongoDB URI, RPC URL, and other settings
```

---

## Script Breakdown

### `sign.py`
Fetches recent transaction signatures for a given Solana wallet address and stores them in MongoDB (`solana_data.signaturesss`). Paginates backward through history using the `before` parameter, with a `sleep(2)` between requests and automatic backoff on rate-limit errors.

### `solana.py`
Reads the saved signatures from MongoDB and fetches the full transaction details for each one. Stores results with `_id = signature` using upserts, so re-runs are safe. Gracefully skips failed fetches and prints errors. Pass `--verbose` to see raw instructions and base64-encoded data.

### `main1.py`
Runs the complete pipeline end-to-end — signature collection first, then detailed transaction fetching — in a single command.

---

## Getting Started

**Prerequisites:**
- Python 3.x
- MongoDB (local or cloud)
- A working Solana RPC URL — e.g., `https://api.mainnet-beta.solana.com`

**Setup:**

```bash
# 1. Clone the repo
git clone https://github.com/your-username/solana-transaction-fetcher.git
cd solana-transaction-fetcher

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your config
nano config.py   # Add your MongoDB URI and RPC URL

# 4. Add the target wallet address in main1.py or sign.py

# 5. Make sure MongoDB is running, then launch
python main1.py
```

---

## MongoDB Output Reference

This section documents every field stored in MongoDB for each transaction.
<img width="930" height="557" alt="image" src="https://github.com/user-attachments/assets/ba31fdd1-7fdc-4140-bf58-25994e2c20fe" />


---

### Top-Level Fields

| Field | Meaning |
|---|---|
| `_id` | Unique transaction signature on Solana |
| `blockTime` | Unix timestamp when the transaction was confirmed |

---

### `meta` — Transaction Metadata

| Field | Meaning |
|---|---|
| `computeUnitsConsumed` | Computing power used — equivalent to gas in Ethereum |
| `fee` | Transaction cost in lamports (SOL) |
| `err` | `null` = success; otherwise contains the error |
| `innerInstructions` | Additional internal program calls triggered during execution |
| `logMessages` | Debug logs from each program invoked |
| `preBalances` | SOL balances of all accounts before the transaction |
| `postBalances` | SOL balances of all accounts after the transaction |
| `preTokenBalances` | Token (non-SOL) balances before the transaction |
| `postTokenBalances` | Token (non-SOL) balances after the transaction |

---

### Inner Instructions — Parsed Fields

| Field | Meaning |
|---|---|
| `type` | Action type — e.g., `getAccountDataSize` checks token account storage needed |
| `extensionTypes` | Token account properties — e.g., `immutableOwner` means owner can't be changed |
| `mint` | Token mint address — e.g., `So111...` = Wrapped SOL |
| `program` | High-level program name — e.g., `spl-token` |
| `programId` | On-chain address of the program |
| `stackHeight` | Nesting depth of the instruction (useful for debugging) |

---

### Log Messages Explained

Logs are the most useful part for understanding exactly what happened during a transaction — program calls, compute usage, and success/failure at each step.

| Log Entry | What It Means |
|---|---|
| `ComputeBudget` | Sets max compute power allowed for the transaction |
| `success` (ComputeBudget) | Compute budget was accepted |
| `Associated Token Account` | Creates a token account for holding a new token |
| `CreateIdempotent` | Creates account only if it doesn't already exist |
| `GetAccountDataSize` | Checks space required for a token account |
| `System Program` | Core Solana program — creates accounts, handles SOL transfers and rent |
| `InitializeImmutableOwner` | Permanently locks the account owner |
| `Upgrade Warning` | Warns about using a newer SPL Token version |
| `InitializeAccount3` | Final setup step to make a token account usable |
| `Compute Used` | Logs compute units consumed at each step |
| `Success` | Confirms the step completed without error |

---

### `postBalances`

SOL balances (in lamports) for all involved accounts **after** the transaction completed.

> 1 SOL = 1,000,000,000 lamports

---

### `postTokenBalances` — Token Balances After Transaction

| Field | Meaning |
|---|---|
| `accountIndex` | Matches the index in the `postBalances` array |
| `mint` | Token mint address — identifies the token type |
| `owner` | Wallet address that owns this token account |
| `programId` | Token program handling this account |
| `amount` | Raw token amount (before applying decimals) |
| `decimals` | Number of decimal places for this token |
| `uiAmount` | Human-readable token amount (amount ÷ 10^decimals) |

---

### `preBalances`

SOL balances **before** the transaction. Compare with `postBalances` to calculate exact SOL changes.

| Field | Meaning |
|---|---|
| `status` | Whether the transaction succeeded or failed |
| `slot` | Block number on the Solana chain |
| `rewards` | Any staking or validator rewards distributed in this slot |

---

### Transaction — Parsed Instruction Fields

| Field | Meaning |
|---|---|
| `pubkey` | Public key (wallet or program address) |
| `signer` | Whether this account signed the transaction |
| `source` | Whether this account was directly used in the transaction |
| `writable` | Whether this account's data can be modified during execution |
| `type` | Action type — `transfer`, `createIdempotent`, etc. |
| `account` | The token account being modified |
| `mint` | Token mint address (defines the token type) |
| `wallet` | Main wallet involved in the instruction |
| `tokenProgram` | SPL Token Program (`TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA`) |
| `systemProgram` | Solana's core program for account creation, SOL transfers, and rent |
| `program` | High-level program name — e.g., `spl-token` |
| `programId` | Actual on-chain address of the program |
| `stackHeight` | Nesting depth of the instruction call |

---

### Transaction Metadata

| Field | Meaning |
|---|---|
| `recentBlockhash` | Block hash used to prevent replay attacks — expires in ~2 minutes |
| `signatures` | Cryptographic proof signed by the wallet confirming transaction ownership |
| `version` | `legacy` or versioned transaction format (versioned enables advanced features like Address Lookup Tables) |

---

## License

MIT — use it however you like. See [LICENSE](LICENSE) for details.

---

<div align="center">

Built for Solana on-chain data collection and analysis

</div>

