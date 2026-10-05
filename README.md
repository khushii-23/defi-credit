Here is the complete `README.md` file formatted in standard GitHub Markdown.

I have placed it inside a code block so you can simply click the **"Copy code"** button in the top right corner and paste it directly into your project's `README.md` file.

```markdown
# 📊 DeFi Credit Scoring Engine

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.25+-FF4B4B.svg)
![Web3.py](https://img.shields.io/badge/Web3.py-6.0+-3C3C3D.svg)

An explainable, on-chain reputation system that evaluates an Ethereum wallet's decentralized lending history to generate a risk-adjusted credit score (300–850). 

Developed as part of an MSc Research Dissertation, this project bypasses easily manipulated heuristics (like raw ERC-20 transfer counts) by directly decoding receipt-level event logs via Keccak-256 topic signatures on the Aave V3 protocol.

---

## 🚀 Key Features

* **Deterministic Log Decoding:** Validates financial intent (`Supply`, `Borrow`, `Repay`, `LiquidationCall`) by decoding smart contract receipts via Web3.py, preventing spoofing from wash-trading or token churn.
* **Bounded Heuristic Scoring:** Translates on-chain history into a traditional 300–850 credit score using a strict rules engine.
* **Algorithmic Guardrails:** Employs "thin-file" gating (locking unverified/dormant accounts at 300) and a Hard Risk Cap (capping liquidated addresses at a maximum of 600).
* **Interactive Presentation Layer:** A responsive Streamlit dashboard featuring Plotly gauge charts, DeFi footprint metrics, and a factor-based explainability audit trail.
* **Automated Cohort Evaluation:** A built-in empirical testing script that batches evaluations across wallet cohorts and generates publication-ready Seaborn distribution plots.

## 🛠️ Technology Stack

* **Backend:** Python, FastAPI, Pydantic
* **Blockchain/RPC:** Web3.py, Alchemy RPC (Ethereum Mainnet)
* **Frontend Dashboard:** Streamlit, Plotly
* **Data Visualization:** Pandas, Matplotlib, Seaborn

## ⚙️ Prerequisites

You will need a free [Alchemy](https://www.alchemy.com/) account to query the Ethereum Mainnet.
* Python 3.9 or higher
* Alchemy API Key (Ethereum Mainnet)

## 📦 Installation & Setup

**1. Clone the repository:**
```bash
git clone [https://github.com/yourusername/defi-credit-scoring.git](https://github.com/yourusername/defi-credit-scoring.git)
cd defi-credit-scoring

```

**2. Create and activate a virtual environment:**

```bash
# On Windows (Powershell)
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

```

**3. Install the dependencies:**

```bash
python -m pip install fastapi uvicorn web3 python-dotenv requests streamlit plotly pandas matplotlib seaborn

```

**4. Environment Variables:**
Create a `.env` file in the root directory and add your Alchemy API key:

```env
ALCHEMY_API_KEY=your_alchemy_api_key_here

```

## 🖥️ Running the Application

The system relies on a microservices architecture. You will need to run the backend API and the frontend dashboard in separate terminal windows.

**Terminal 1: Start the FastAPI Backend**

```bash
python -m uvicorn app.main:app --reload

```

*The API will be available at `http://localhost:8000*`

**Terminal 2: Start the Streamlit Dashboard**

```bash
python -m streamlit run app/dashboard.py

```

*The dashboard will automatically open in your default web browser at `http://localhost:8501*`

## 📊 Running the Empirical Evaluation

To generate the academic distribution charts comparing healthy borrowers to liquidated accounts, run the evaluation script. This will query the backend against the addresses saved in `scripts/cohorts.json` and output a 300-DPI box plot (`score_distribution_chart.png`) to your root directory.

```bash
python scripts/evaluate_cohorts.py

```

## 🧠 How the Scoring Engine Works

The algorithm assigns points based on verified financial interactions with the Aave V3 Pool smart contract:

1. **Base Score:** All wallets begin at `300` (High Risk).
2. **Account Age (Max +150):** Prorated over 1 year, but *only* awarded if the wallet has `>0` verified DeFi interactions (Thin-file gate).
3. **DeFi Activity (Max +150):** `+3` points per verified lending interaction.
4. **Repayments (Max +150):** `+25` points per successful debt repayment.
5. **Supplies/Deposits (Max +100):** `+15` points per collateral deposit.
6. **Liquidations (Penalty -200):** Subtracted per liquidation event.
7. **Hard Risk Cap:** If a wallet has *any* historical liquidation, its maximum possible score is strictly capped at `600`, preventing algorithmic masking via high transaction volume.

## 📂 Project Structure

```text
defi-credit-scoring/
├── .env                        # Private Alchemy API Key (Not committed to Git)
├── app/
│   ├── main.py                 # FastAPI application and endpoints
│   ├── scoring.py              # Credit scoring mathematical logic and caps
│   ├── web3_client.py          # Alchemy RPC connection and log decoding
│   └── dashboard.py            # Streamlit frontend UI
├── scripts/
│   ├── cohorts.json            # Target dataset of Aave V3 Ethereum wallets
│   ├── evaluate_cohorts.py     # Batch processing and visualization script
│   └── extract_live_dataset.py # (Optional) Script to scrape live RPC logs
├── score_distribution_chart.png# Auto-generated evaluation box plot
└── README.md

```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

```

```
