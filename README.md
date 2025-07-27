# Solana Transaction Fetcher

This project is designed to fetch and store transaction data for a specific **Solana wallet address** using the **Solana JSON-RPC API**. It first collects recent **transaction signatures** and stores them in **MongoDB**, then fetches **detailed transaction data** for each signature and stores that as well.

You can run the process either in separate steps using `sign.py` and `solana.py`, or all at once using the integrated script `main1.py`.

---

## Key Features

- Fetches up to **20,000+ transaction signatures** using pagination.
- Automatically skips duplicates using MongoDB indexes.
- Handles **rate-limiting** with retry logic using `time.sleep`.
- Extracts and displays:
  - SOL balance changes
  - Token transfers
  - Fees, slot numbers, and timestamps
- Saves all transaction data in a structured format in MongoDB.
- Can be run in **modular steps** or as a **combined workflow**.

---

## Script Breakdown

### `sign.py`
- Fetches recent **transaction signatures** for a given Solana address.
- Stores them in MongoDB (`solana_data.signaturesss` collection).
- Uses "time.sleep(2)" between requests and backs off with sleep(60) on HTTP 429 errors.
- Uses "before" parameter to paginate backward through historical transactions.

### `solana.py`
- Fetch detailed **transaction details** for previously saved Solana signatures and store them.
- Shows raw instructions and base64-encoded data if run with verbose argument.
- MongoDB with _id = signature (upserts the full transaction object).
-  Gracefully skips failed fetches and prints errors.

### `main1.py`
- Integrates both `sign.py` and `solana.py` in a single workflow.
- Runs the complete pipeline: from signature fetch to detailed transaction storage.

---
## Requirements

- Python 3.x  
- MongoDB  
- A working Solana RPC URL (e.g., `https://api.mainnet-beta.solana.com`)

##  How to Use

- Set your MongoDB URI, RPC URL, and other settings in config.py.
- Add the Solana wallet address in main1.py or sign.py.
- Make sure MongoDB is running.
- Run the full pipeline.

  ## Output
  
| Field | Meaning |
| --- | --- |
| `_id` | Unique transaction signature on Solana |
| `blockTime` | Time when the transaction was confirmed |

### meta data

| Field | Meaning |
| --- | --- |
| `computeUnitsConsumed` | Computing power used (like gas in Ethereum) |
| `fee` | Transaction cost in SOL |
| `err` | Shows `null` = Success  |
| `innerInstructions` | Additional internal program calls |
| `logMessages` | Debug logs for internal operations |
| `preBalances` | SOL balances before the transaction |
| `postBalances` | SOL balances after the transaction |
| `preTokenBalances` | Token balances before the transaction |
| `postTokenBalances` | Token balances after the transaction |

### Inner Instruction ( parsed info)

| Field | What it means |
| --- | --- |
| `type` | `getAccountDataSize` — Checks token account storage size needed |
| `extensionTypes`  | tell whether the owner can be changed later or not . eg:- `immutableOwner` — Owner cannot be changed later |
| `mint` | `So111...` — Token mint address (Wrapped SOL) |
| `program` |  Used Solana's token program . eg - `spl-token` |
| `programId` |  On-chain ID of token program |
| `stackHeight` | Internal depth for tracing nested instructions |

### Logs =  These are **very useful for debugging** or understanding what exactly happened during a transaction — like program calls, instructions, gas/compute usage, and success/failure statuses.
| Section | What It Means |
| --- | --- |
| `ComputeBudget` | Sets how much compute power the tx can use |
|  |  `success` log = accepted compute budget |
| `Associated Token Account` | Creates token account for holding a new token |
| `CreateIdempotent` | Creates account only if it doesn't already exist |
| `GetAccountDataSize` | Checks space needed for token account |
| `System Program` | Creates accounts, sends SOL, manages rent |
| `InitializeImmutableOwner` | Locks account owner permanently |
| `Upgrade Warning` | Warns about using newer SPL Token version |
| `InitializeAccount3` | Final setup for token account to be usable |
| `Compute Used` | Logs compute units per step |
| `Success` | Shows step completed without error  |

### postBalances = Shows SOL balances (in lamports) **after** the transaction.(1 SOL = 1,000,000,000 lamports)


### postTokenBalances = This shows the **token balances** (not SOL) **after** the transaction for each token account involved.
| Field | Meaning |
| --- | --- |
| `accountIndex` | Matches entry in postBalances array |
| `mint` | Identifies token type |
| `owner` | Wallet address owning the token account |
| `programId` | Token program ID  |
| `amount` | Raw token amount.  |
| `decimals` | Number of decimal places used  |
| `uiAmount` | Human-readable token amount  |

### preBalances =Shows SOL balances before the transaction

| Field | Meaning |
| --- | --- |
| `status` | Transaction succeeded or not |
| `slot` |  Block number on Solana chain |
| `rewards` | staking/validator rewards given or not |

### Generic Meaning of Parsed Instruction Fields under TRANSACTION HEADING
| Field | Meaning |
| --- | --- |
| `pubkey` | Public key (wallet address) |
| `signer` |  the transaction is signed or not  |
| `source` | Directly used in transaction or not  |
| `writable` | Account can be updated during tx |
| `type` | Kind of action: `transfer`, `createIdempotent`, etc. |
| `account` | Address being modified (token account) |
| `mint` | Token mint address (defines token type) |
| `source` | Wallet or token account sending funds or creating another account |
| `wallet` | Main wallet involved |
| `tokenProgram` | SPL Token Program (`Tokenkeg...`) |
| `systemProgram` | Solana's core program for creating accounts, transfers, rent, etc. |
| `program` | High-level program name used like `spl-token` |
| `programId` | Actual on-chain address of the program |
| `stackHeight` | Depth of nested instruction call (for debugging) |
### Metadata

| Field | Meaning |
| --- | --- |
| `recentBlockhash` | Block hash to prevent replay attacks (expires in ~2 mins) |
| `signatures` | Signed proof by wallet of transaction ownership |
| `version` | Legacy or versioned transaction (for advanced features) |

