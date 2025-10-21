# ChaosChain + Filecoin Pin Demo

Deliver durable, verifiable ChaosChain process proofs straight to Filecoin, without running an IPFS node or writing bespoke storage glue. This repository contains a wannabe-production-quality reference integration that anyone can clone, configure, and run end-to-end.

---

## Why This Matters

- **Agent accountability**: ChaosChain produces integrity proofs for every agent workflow. Persisting those proofs is essential for auditability.
- **Filecoin permanence**: The Filecoin Pin CLI funds CAR uploads on Calibration (or mainnet) and tracks on-chain storage deals. A pinned CID remains available even if the originating IPFS gateway disappears.
- **Zero middleware**: The integration calls the Filecoin Pin CLI directly from Python, so there is no API proxy, no local IPFS daemon, and no additional infrastructure to maintain.

---

## System Overview

```
┌─────────────┐      ┌────────────────┐      ┌──────────────────────┐
│ ChaosChain  │ ───► │ Custom Storage │ ───► │ filecoin-pin CLI     │
│ Agent SDK   │      │ Provider       │      │ (Filecoin + IPFS)    │
└─────────────┘      └────────────────┘      └──────────────────────┘
        │                        │                        │
        │ Integrity Proof JSON   │ temp file + CLI call   │ Storage deal + CID
        ▼                        ▼                        ▼
   receipts/*.json          ipfs://<CID>            Durable proof on Filecoin
```

Key components:

- `storage/filecoin_pin_provider.py` – wraps the `filecoin-pin` CLI for uploads, retrieval, and simple verification.
- `agent/agent.py` – registers a ChaosChain agent, executes a sample workload with `execute_with_integrity_proof`, and exports receipts.
- `test_storage_provider.py` – runs a diagnostic upload for the storage provider without invoking the full ChaosChain SDK.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | The Makefile bootstraps a virtual environment automatically. |
| Node.js 18+ | Needed to install the Filecoin Pin CLI (`npm install -g filecoin-pin`). |
| `filecoin-pin` CLI | Must be on your `PATH`, or point to it with `FILECOIN_PIN_PATH`. |
| ChaosChain wallets | Base-Sepolia private key for the agent and Filecoin Calibration private key for pinning. |
| RPC endpoints | HTTPS endpoints for Base-Sepolia and Filecoin Calibration (Alchemy, Infura, Glif, etc.). |

Access to the Filecoin Calibration faucet and Base-Sepolia faucet is required to fund the respective wallets with test FIL and ETH.

---

## Quick Start

```bash
git clone https://github.com/sgtpooki/chaoschain-filecoin-pin-demo.git
cd chaoschain-filecoin-pin-demo

# 1. Install Python dependencies in a local venv
make install

# 2. Configure environment
cp env.example .env
# edit .env with wallet keys, addresses, RPC URLs, and any CLI overrides

# 3. Validate configuration and generate ChaosChain wallet mapping
make setup

# 4. Run the full demo (executes the agent and pins the proof)
make demo
```

The demo prints the generated proof CID, confirmation that the upload landed on Filecoin, and stores a detailed receipt under `receipts/`.

---

## Configuration Reference

`env.example` documents every environment variable consumed by the integration. Copy it to `.env` and supply real values.

| Variable | Purpose |
|----------|---------|
| `CHAOS_NETWORK` | ChaosChain network (default `base-sepolia`). |
| `CHAOS_AGENT_NAME` | Name recorded on-chain for this agent. |
| `CHAOS_AGENT_DOMAIN` | Domain associated with the agent. |
| `CHAOS_AGENT_ROLE` | Role descriptor passed to ChaosChain (e.g. `server`). |
| `FILECOIN_PIN_PATH` | Override path to the `filecoin-pin` executable. |
| `FILECOIN_PIN_AUTO_FUND` | `true` to let the CLI top up deal balances automatically. |
| `FILECOIN_PIN_BARE` | `true` uploads files without a directory wrapper. |
| `FILECOIN_PIN_VERBOSE` | `true` enables verbose CLI output. |
| `BASE_SEPOLIA_PRIVATE_KEY` | Private key used to register the agent on Base-Sepolia. |
| `BASE_SEPOLIA_ADDRESS` | Optional address override. Derived from the private key if omitted. |
| `BASE_SEPOLIA_RPC_URL` | HTTPS RPC endpoint for Base-Sepolia. |
| `FILECOIN_CALIBRATION_PRIVATE_KEY` | Private key used by Filecoin Pin for storage deals. |
| `FILECOIN_CALIBRATION_RPC_URL` | HTTPS RPC endpoint for Filecoin Calibration. |

The Makefile sources `.env`, mirrors RPC variables to the hyphenated format expected by ChaosChain (`BASE-SEPOLIA_RPC_URL`), and materialises `chaoschain_wallets.json` based on `BASE_SEPOLIA_PRIVATE_KEY`.

---

## Make Targets

```
make install       # Create .venv/ and install requirements.txt
make setup         # Verify CLI dependencies, write chaoschain_wallets.json, sanity-check env vars
make demo          # Run the full agent workflow, pin the proof, save a receipt
make agent         # Execute agent/agent.py directly (same as demo without banner)
make test-storage  # Run test_storage_provider.py diagnostic upload
make check-env     # Validate the .env file and CLI availability
make clean         # Remove generated receipts
make test          # Run a connectivity checklist (CLI version, Python deps, env vars)
make results       # Pretty-print the most recent receipt
```

Each command echoes the steps it performs so you can integrate them into CI/CD or customise the flow for your environment.

---

## What Happens During `make demo`

1. The ChaosChain SDK is initialised with the custom `FilecoinPinStorageProvider`.
2. The agent identity is registered on Base-Sepolia if it does not already exist.
3. The sample `demo_function` runs under `execute_with_integrity_proof`, producing a deterministic hash of the payload.
4. The resulting proof JSON is written to a temporary file and handed to `filecoin-pin add`, which funds and submits a storage deal.
5. Metadata from the CLI output (root CID, piece CID, transaction hash) is captured and returned to ChaosChain.
6. The script verifies that the CID is retrievable via public IPFS gateways and stores a receipt at `receipts/chaos_proof_<timestamp>.json`.

The receipt contains both the execution result and the storage metadata so auditors can replay the full context of a proof.

---

## Repository Structure

```
agent/
  agent.py                 # ChaosChain agent orchestration script
storage/
  filecoin_pin_provider.py # Storage adapter that drives the filecoin-pin CLI
test_storage_provider.py   # Diagnostic harness for the storage adapter
Makefile                   # Developer entry points and validation helpers
requirements.txt           # Python dependencies (ChaosChain SDK, eth-account, requests)
env.example                # Configuration template
receipts/                  # Populated with JSON receipts after demo runs
PLAN.md                    # Development log used during implementation
```

---

## Inspecting Outputs

After running `make demo`, inspect the most recent receipt:

```bash
make results
```

To explore artifacts manually:

- Fetch the pinned proof (replace `<CID>` with the value printed by the agent):

  ```bash
  curl -s "https://<CID>.ipfs.dweb.link/chaoschain_proof.json" | jq
  ```

- View a stored receipt locally:

  ```bash
  jq '.' receipts/chaos_proof_<timestamp>.json
  ```

You can also open the `view_url` listed in the receipt, `https://<CID>.ipfs.dweb.link/chaoschain_proof.json`, in any browser to confirm availability across the network.

---

## Troubleshooting

| Symptom | Recommended Action |
|---------|--------------------|
| `filecoin-pin` command not found | Install with `npm install -g filecoin-pin`, or set `FILECOIN_PIN_PATH` to the binary path. |
| ChaosChain SDK import error | Run `make install` to populate the virtual environment. Activate `.venv/bin/activate` if calling scripts manually. |
| Missing wallet details | Ensure `.env` contains real keys (not the placeholders from `env.example`). The setup step aborts early if defaults remain. |
| CID not reachable immediately | Allow a few minutes for propagation. Use `make test-storage` or rerun `agent/agent.py` with `FILECOIN_PIN_VERBOSE=true` for more insight. |
| CLI returns non-zero exit code | The storage provider prints the captured stdout/stderr. Verify wallet funds on Calibration and that the CLI is authenticated. |

---

## Extending the Demo

- Swap `demo_function` for a real workload while keeping the storage provider unchanged.
- Configure the CLI for Filecoin mainnet once you are ready to exit Calibration.
- Integrate the `FilecoinPinStorageProvider` into other ChaosChain agents to create a consistent audit trail across services.

Pull requests that add monitoring hooks, structured logging, or integration tests are welcome.

---

## License

This demo is provided for educational and demonstration purposes. Review the ChaosChain and Filecoin Pin licenses when building commercial applications.
