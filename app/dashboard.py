import json
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="DeFi Credit Scoring", page_icon="📊", layout="wide")

DEFAULT_API_URL = "http://localhost:8000"
ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")

SCORE_MIN, SCORE_MAX = 300, 850
LIQUIDATION_CAP = 600

# Scoring model constants (from the project's methodology)
MAX_POINTS = {
    "Account Age": 150,
    "DeFi Tx Volume": 150,
    "Repayments": 150,
    "Collateral Deposits": 100,
}
MAX_LIQUIDATION_PENALTY = 500

st.markdown(
    """
    <style>
        .block-container {padding-top: 1.8rem; max-width: 1150px;}
        .score-badge {
            display:inline-block; padding:.35rem 1rem; border-radius:999px;
            font-weight:600; font-size:1.05rem; color:white;
        }
        div[data-testid="stMetric"] {
            background: rgba(128,128,128,.08);
            border: 1px solid rgba(128,128,128,.2);
            padding: 14px 16px; border-radius: 12px;
        }
        .pill {
            display:inline-block; padding:.1rem .6rem; border-radius:999px;
            font-size:.8rem; font-weight:600; margin-left:.5rem;
        }
        .pill-pos {background:rgba(46,204,113,.2); color:#27ae60;}
        .pill-neg {background:rgba(231,76,60,.2); color:#c0392b;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
st.session_state.setdefault("history", [])
st.session_state.setdefault("wallet_input", "")
st.session_state.setdefault("pending", None)


def use_history(addr: str):
    st.session_state["wallet_input"] = addr
    st.session_state["pending"] = addr


# ---------------------------------------------------------------------------
# Backend access
# ---------------------------------------------------------------------------
class ApiError(Exception):
    pass


@st.cache_data(ttl=600, show_spinner=False)
def _fetch(api_url: str, address: str) -> dict:
    """Cached call. Raises on failure so errors are never cached."""
    try:
        r = requests.get(f"{api_url}/score/{address}", timeout=180)
    except requests.exceptions.ConnectionError:
        raise ApiError("Failed to connect to the backend. Is the FastAPI server running?")
    except requests.exceptions.Timeout:
        raise ApiError("The backend took too long to respond. Please try again.")
    except requests.exceptions.RequestException as e:
        raise ApiError(f"Request failed: {e}")

    if r.status_code == 200:
        return r.json()

    try:
        detail = r.json().get("detail", "Unknown error")
    except ValueError:
        detail = r.text or "Unknown error"
    raise ApiError(f"API error ({r.status_code}): {detail}")


def get_score(api_url: str, address: str):
    try:
        return _fetch(api_url, address), None
    except ApiError as e:
        return None, str(e)


def remember(address: str, score: float):
    hist = [h for h in st.session_state["history"] if h["address"] != address]
    hist.insert(0, {"address": address, "score": score})
    st.session_state["history"] = hist[:6]


# ---------------------------------------------------------------------------
# Visual helpers
# ---------------------------------------------------------------------------
def score_band(score: float):
    if score >= 700:
        return "Low Risk", "#2ecc71"
    if score >= 500:
        return "Medium Risk", "#f39c12"
    return "High Risk", "#e74c3c"


def short(addr: str) -> str:
    return f"{addr[:6]}…{addr[-4:]}"


def score_gauge(score: float, capped: bool, height: int = 280) -> go.Figure:
    _, color = score_band(score)
    gauge = {
        "axis": {"range": [SCORE_MIN, SCORE_MAX]},
        "bar": {"color": color, "thickness": 0.3},
        "steps": [
            {"range": [SCORE_MIN, 500], "color": "rgba(231,76,60,.18)"},
            {"range": [500, 700], "color": "rgba(243,156,18,.18)"},
            {"range": [700, SCORE_MAX], "color": "rgba(46,204,113,.18)"},
        ],
    }
    if capped:
        gauge["threshold"] = {
            "line": {"color": "#c0392b", "width": 4},
            "thickness": 0.8,
            "value": LIQUIDATION_CAP,
        }
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"font": {"size": 58, "color": color}},
            gauge=gauge,
        )
    )
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=20, b=10))
    return fig


def action_pie(features: dict, height: int = 340):
    df = pd.DataFrame(
        {
            "Action": ["Deposits", "Borrows", "Repayments", "Liquidations"],
            "Count": [
                features.get("deposit_count", 0),
                features.get("borrow_count", 0),
                features.get("repayment_count", 0),
                features.get("liquidation_count", 0),
            ],
        }
    )
    df = df[df["Count"] > 0]
    if df.empty:
        return None
    fig = px.pie(
        df, values="Count", names="Action", color="Action", hole=0.45,
        color_discrete_map={
            "Deposits": "#2ecc71", "Repayments": "#3498db",
            "Borrows": "#f39c12", "Liquidations": "#e74c3c",
        },
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=False, height=height)
    return fig


def waterfall(data: dict):
    """Score waterfall. Needs a numeric 'points' on each explanation."""
    exps = [e for e in data.get("explanations", []) if isinstance(e.get("points"), (int, float))]
    if not exps:
        return None
    score = data["score"]
    labels = ["Base score"] + [e["factor"] for e in exps]
    values = [SCORE_MIN] + [e["points"] for e in exps]
    measure = ["absolute"] + ["relative"] * len(exps)

    adjustment = score - (SCORE_MIN + sum(e["points"] for e in exps))
    if abs(adjustment) > 0.5:
        labels.append("Cap adjustment")
        values.append(adjustment)
        measure.append("relative")

    labels.append("Final score")
    values.append(score)
    measure.append("total")

    fig = go.Figure(
        go.Waterfall(
            x=labels, y=values, measure=measure,
            increasing={"marker": {"color": "#2ecc71"}},
            decreasing={"marker": {"color": "#e74c3c"}},
            totals={"marker": {"color": "#3498db"}},
            connector={"line": {"color": "rgba(128,128,128,.5)"}},
        )
    )
    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(range=[SCORE_MIN - 20, SCORE_MAX + 20], title="Score"),
    )
    return fig


def max_points_chart():
    df = pd.DataFrame(
        {"Factor": list(MAX_POINTS) + ["Liquidation penalty"],
         "Points": list(MAX_POINTS.values()) + [-MAX_LIQUIDATION_PENALTY]}
    )
    df["Type"] = ["Positive"] * len(MAX_POINTS) + ["Penalty"]
    fig = px.bar(
        df, x="Points", y="Factor", orientation="h", color="Type",
        color_discrete_map={"Positive": "#2ecc71", "Penalty": "#e74c3c"}, text="Points",
    )
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    return fig


# ---------------------------------------------------------------------------
# Result rendering
# ---------------------------------------------------------------------------
def result_flags(data: dict):
    features = data.get("features", {})
    liquidated = features.get("liquidation_count", 0) > 0
    thin_file = bool(data.get("new_wallet")) or features.get("defi_transaction_count", 0) == 0
    return liquidated, thin_file


def render_flags(data: dict):
    liquidated, thin_file = result_flags(data)
    if data.get("new_wallet"):
        st.warning("This wallet has no on-chain history. Minimum score applied.")
    elif thin_file:
        st.warning(
            "**Thin-file wallet:** no proven DeFi lending history, so the baseline score "
            f"of {SCORE_MIN} applies. Account age and volume are ignored until lending is proven."
        )
    if liquidated:
        st.error(
            f"**Hard risk cap active:** this wallet has a historical liquidation, so its "
            f"score cannot exceed {LIQUIDATION_CAP} regardless of age or volume."
        )


def render_metrics(features: dict):
    lending = (
        features.get("deposit_count", 0)
        + features.get("borrow_count", 0)
        + features.get("repayment_count", 0)
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Account Age (Days)", int(features.get("wallet_age_days", 0)),
              help="Total days since the wallet's first recorded on-chain transfer.")
    c2.metric("Total Transactions", features.get("unique_transaction_count", 0),
              help="Total inbound and outbound transfers (including non-DeFi activity).")
    c3.metric("DeFi Transactions", features.get("defi_transaction_count", 0),
              help="Verified Aave V3 interactions decoded from transaction receipt logs.")
    c4, c5, c6 = st.columns(3)
    c4.metric("Protocols Used", features.get("protocol_count", 0),
              help="Number of unique DeFi protocols the wallet has engaged with.")
    c5.metric("Lending Actions", lending,
              help="Combined total of collateral deposits, borrows, and debt repayments.")
    c6.metric("Liquidations", features.get("liquidation_count", 0),
              help="Events where collateral was forcefully seized due to undercollateralization.")

    # Derived behaviour ratios
    st.markdown("##### Behaviour ratios")
    borrows = features.get("borrow_count", 0)
    repays = features.get("repayment_count", 0)
    total_tx = features.get("unique_transaction_count", 0)
    defi_tx = features.get("defi_transaction_count", 0)

    r1, r2 = st.columns(2)
    with r1:
        if borrows > 0:
            ratio = min(repays / borrows, 1.0)
            st.progress(ratio, text=f"Repayment-to-borrow ratio: {repays}/{borrows}")
        else:
            st.caption("Repayment-to-borrow ratio: no borrows recorded")
    with r2:
        if total_tx > 0:
            st.progress(min(defi_tx / total_tx, 1.0),
                        text=f"DeFi share of all activity: {defi_tx}/{total_tx}")
        else:
            st.caption("DeFi share of activity: no transactions recorded")
    st.caption("Note: only the 15 most recent lending interactions are decoded from receipts.")


def render_explanations(data: dict):
    exps = data.get("explanations", [])
    if not exps:
        st.info("No explanations were returned for this wallet.")
        return
    for e in exps:
        impact = e.get("impact")
        pts = e.get("points")
        pill = ""
        if isinstance(pts, (int, float)):
            cls = "pill-pos" if pts >= 0 else "pill-neg"
            pill = f"<span class='pill {cls}'>{pts:+.0f} pts</span>"
        text = f"**{e.get('factor', '')}**: {e.get('description', '')}"
        if impact == "positive":
            st.success(text, icon="➕")
        elif impact == "negative":
            st.error(text, icon="➖")
        else:
            st.info(text, icon="ℹ️")
        if pill:
            st.markdown(pill, unsafe_allow_html=True)


def render_full(data: dict, address: str, key: str):
    score = data["score"]
    features = data.get("features", {})
    liquidated, _ = result_flags(data)
    label, color = score_band(score)

    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
        st.subheader("Risk Assessment")
        st.plotly_chart(score_gauge(score, liquidated), use_container_width=True, key=f"g_{key}")
    with right:
        st.markdown(f"<span class='score-badge' style='background:{color}'>{label}</span>",
                    unsafe_allow_html=True)
        st.caption("Wallet")
        st.code(address, language=None)
        st.markdown(f"[View on Etherscan ↗](https://etherscan.io/address/{address})")
        st.download_button(
            "⬇️ Download result (JSON)", json.dumps(data, indent=2),
            file_name=f"credit_score_{address[:8]}.json", mime="application/json",
            key=f"dl_{key}",
        )

    render_flags(data)

    tab_why, tab_foot, tab_break = st.tabs(
        ["💡 Explanation", "🧾 DeFi Footprint", "🥧 Action Breakdown"]
    )
    with tab_why:
        st.subheader("Why did it get this score?")
        wf = waterfall(data)
        if wf:
            st.plotly_chart(wf, use_container_width=True, key=f"wf_{key}")
        else:
            st.caption(
                "Tip: return a numeric `points` field in each ScoreFactor to unlock a "
                "score waterfall chart here."
            )
        render_explanations(data)
    with tab_foot:
        st.subheader("DeFi Footprint Summary")
        render_metrics(features)
    with tab_break:
        st.subheader("DeFi Action Breakdown")
        fig = action_pie(features)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key=f"pie_{key}")
        else:
            st.info("Not enough DeFi lending data to generate an action breakdown chart.")


def render_compact(data: dict, address: str, key: str):
    score = data["score"]
    liquidated, _ = result_flags(data)
    label, color = score_band(score)
    st.markdown(f"**{short(address)}**  ·  "
                f"<span class='score-badge' style='background:{color};font-size:.85rem'>{label}</span>",
                unsafe_allow_html=True)
    st.plotly_chart(score_gauge(score, liquidated, height=230), use_container_width=True, key=f"cg_{key}")
    render_flags(data)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    api_url = st.text_input("Backend URL", DEFAULT_API_URL).rstrip("/")

    st.header("Recent wallets")
    if st.session_state["history"]:
        for i, h in enumerate(st.session_state["history"]):
            st.button(f"{short(h['address'])}  ·  {h['score']}", key=f"hist_{i}",
                      on_click=use_history, args=(h["address"],), use_container_width=True)
        if st.button("Clear history"):
            st.session_state["history"] = []
            st.rerun()
    else:
        st.caption("Analyzed wallets will appear here.")

    st.header("Score ranges")
    st.markdown("🟢 700+ : Low risk  \n🟠 500–699 : Medium risk  \n🔴 300–499 : High risk")
    st.caption("MSc Research Project · research prototype, not financial advice.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("📊 DeFi Credit Scoring Engine")
st.caption("An Explainable On-Chain Reputation System · Aave V3 · Ethereum Mainnet")

mode = st.radio("Mode", ["Single wallet", "Compare two wallets"], horizontal=True,
                label_visibility="collapsed")


def validate(addr: str):
    if not addr:
        return "Please enter a wallet address."
    if not ADDRESS_PATTERN.match(addr):
        return "Please enter a valid 42-character Ethereum address starting with 0x."
    return None


def analyze_with_status(address: str):
    with st.status("Analyzing wallet…", expanded=True) as status:
        st.write("Fetching asset transfers from Alchemy…")
        st.write("Decoding Aave V3 receipt logs…")
        data, err = get_score(api_url, address)
        if err:
            status.update(label="Analysis failed", state="error")
        else:
            status.update(label="Analysis complete", state="complete", expanded=False)
    return data, err


# ---------------------------------------------------------------------------
# Single wallet mode
# ---------------------------------------------------------------------------
tab_main, tab_method = st.tabs(["🔍 Analyze", "📖 Methodology"])

with tab_main:
    if mode == "Single wallet":
        with st.form("single_form"):
            c_in, c_btn = st.columns([5, 1], vertical_alignment="bottom")
            c_in.text_input("Ethereum wallet address (EIP-55 checksummed)",
                            placeholder="0x...", key="wallet_input")
            submitted = c_btn.form_submit_button("Analyze", type="primary",
                                                 use_container_width=True)

        address = None
        if st.session_state["pending"]:
            address = st.session_state["pending"]
            st.session_state["pending"] = None
        elif submitted:
            address = st.session_state["wallet_input"].strip()

        if address is not None:
            problem = validate(address)
            if problem:
                st.warning(problem) if not address else st.error(problem)
            else:
                data, err = analyze_with_status(address)
                if err:
                    st.error(err)
                    if "checksum" in err.lower():
                        st.caption("Tip: the backend enforces EIP-55 checksums. "
                                   "Copy the address with correct capitalization from Etherscan.")
                else:
                    remember(address, data["score"])
                    st.markdown("---")
                    render_full(data, address, key="single")

    # -----------------------------------------------------------------------
    # Compare mode
    # -----------------------------------------------------------------------
    else:
        with st.form("compare_form"):
            ca, cb = st.columns(2)
            addr_a = ca.text_input("Wallet A", placeholder="0x...")
            addr_b = cb.text_input("Wallet B", placeholder="0x...")
            go_compare = st.form_submit_button("Compare", type="primary")

        if go_compare:
            addr_a, addr_b = addr_a.strip(), addr_b.strip()
            problem = validate(addr_a) or validate(addr_b)
            if problem:
                st.error(problem)
            else:
                with st.spinner("Analyzing both wallets…"):
                    res_a, err_a = get_score(api_url, addr_a)
                    res_b, err_b = get_score(api_url, addr_b)

                if err_a or err_b:
                    if err_a:
                        st.error(f"Wallet A: {err_a}")
                    if err_b:
                        st.error(f"Wallet B: {err_b}")
                else:
                    remember(addr_a, res_a["score"])
                    remember(addr_b, res_b["score"])
                    st.markdown("---")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        render_compact(res_a, addr_a, "a")
                    with col_b:
                        render_compact(res_b, addr_b, "b")

                    delta = res_a["score"] - res_b["score"]
                    st.info(f"Score difference (A − B): **{delta:+d}**" if isinstance(delta, int)
                            else f"Score difference (A − B): **{delta:+.0f}**")

                    fa, fb = res_a.get("features", {}), res_b.get("features", {})
                    keys = sorted(set(fa) | set(fb))
                    table = pd.DataFrame(
                        {"Metric": [k.replace("_", " ").title() for k in keys],
                         "Wallet A": [fa.get(k, 0) for k in keys],
                         "Wallet B": [fb.get(k, 0) for k in keys]}
                    )
                    st.subheader("Feature comparison")
                    st.dataframe(table, hide_index=True, use_container_width=True)

with tab_method:
    st.subheader("How the score is calculated")
    st.markdown(
        f"""
        The score is bounded between **{SCORE_MIN}** (high risk) and **{SCORE_MAX}** (low risk).

        - **Verified lending only:** actions are decoded from Aave V3 Pool event logs
          (`Deposit`, `Borrow`, `Repay`, `LiquidationCall`) rather than inferred from token transfers.
        - **Thin-file rule:** wallets with no proven DeFi lending history receive the baseline
          score of {SCORE_MIN}. Age and volume are ignored until lending is proven.
        - **Positive factors:** Account Age (up to 150), DeFi Tx Volume (up to 150),
          Repayments (up to 150), Collateral Deposits (up to 100).
        - **Penalty:** up to {MAX_LIQUIDATION_PENALTY} points deducted for liquidations.
        - **Hard cap:** any wallet with a historical liquidation is capped at {LIQUIDATION_CAP}.
        - **RPC limit:** receipts are decoded for the 15 most recent lending interactions.
        """
    )
    st.plotly_chart(max_points_chart(), use_container_width=True, key="maxpts")
    st.caption("This is a research prototype and does not constitute financial advice.")