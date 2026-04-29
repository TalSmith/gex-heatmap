"""
GEX Heatmap — Streamlit App
Runs in browser, works on mobile, auto-refreshes.
Data: Yahoo Finance (free, 15-min delay during market hours)
AI:   Anthropic Claude (optional — add API key in sidebar)
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import anthropic
from streamlit_autorefresh import st_autorefresh

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GEX Heatmap",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark terminal CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* App background */
  .stApp, [data-testid="stAppViewContainer"] { background-color: #0d1117 !important; }
  [data-testid="stSidebar"] { background-color: #161b22 !important; }
  [data-testid="stSidebar"] * { color: #c9d1d9 !important; }
  h1,h2,h3,p,label,span { color: #c9d1d9 !important; }
  hr { border-color: #21262d !important; }

  /* Heatmap table */
  .gex-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Courier New', Courier, monospace;
    font-size: 13px;
  }
  .gex-table th {
    font-size: 11px;
    color: #8b949e;
    font-weight: 500;
    padding: 6px 12px;
    border-bottom: 1px solid #21262d;
    text-align: left;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .gex-table td {
    padding: 4px 12px;
    border-bottom: 0.5px solid rgba(255,255,255,0.04);
    color: #c9d1d9;
    vertical-align: middle;
  }
  .gex-table tr:hover td { background: rgba(255,255,255,0.04) !important; }

  /* Row highlight classes */
  .row-flip { background: rgba(186,117,23,0.18) !important; }
  .row-spot { background: rgba(55,138,221,0.08) !important; }
  .row-king { background: rgba(212,175,55,0.07) !important; }
  .row-gate { background: rgba(55,138,221,0.04) !important; }

  /* Exposure bars */
  .bar-wrap { display:flex; align-items:center; height:16px; }
  .bar-pos { height: 14px; border-radius: 2px; background: #00C896; display: inline-block; }
  .bar-neg { height: 14px; border-radius: 2px; background: #9B59B6; display: inline-block; }

  /* Level labels */
  .lbl { font-size: 10px; font-weight: 700; letter-spacing: 0.05em; margin-left: 5px; }
  .lbl-king { color: #D4AF37; }
  .lbl-flip { color: #C850C0; }
  .lbl-gate { color: #378ADD; }
  .lbl-spot { color: #00C896; }

  /* GEX value colors */
  .gex-pos { color: #00C896; }
  .gex-neg { color: #FF6B6B; }

  /* Header ticker chip */
  .ticker-header {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
  }

  /* AI summary box */
  .ai-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px 18px;
    margin-top: 16px;
    font-size: 14px;
    line-height: 1.7;
    color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  .footer {
    margin-top: 24px;
    font-family: monospace;
    font-size: 11px;
    color: #484f58;
    text-align: center;
  }
</style>
""", unsafe_allow_html=True)


# ── Constants ─────────────────────────────────────────────────────────────────
TICKERS = {
    "SPY  —  S&P 500 ETF":     "SPY",
    "QQQ  —  Nasdaq-100 ETF":  "QQQ",
    "IWM  —  Russell 2000 ETF":"IWM",
    "AAPL —  Apple":           "AAPL",
    "MSFT —  Microsoft":       "MSFT",
    "NVDA —  Nvidia":          "NVDA",
    "AMZN —  Amazon":          "AMZN",
    "META —  Meta":            "META",
    "GOOGL — Alphabet":        "GOOGL",
    "TSLA —  Tesla":           "TSLA",
    "AVGO —  Broadcom":        "AVGO",
    "JPM  —  JPMorgan":        "JPM",
    "BRK-B — Berkshire":       "BRK-B",
}

STRIKE_RANGE = 0.05   # show strikes within ±5% of spot price


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")

    selected_label = st.selectbox("Ticker", list(TICKERS.keys()), index=0)
    ticker_symbol  = TICKERS[selected_label]

    refresh_mins = st.slider("Auto-refresh (minutes)", min_value=1, max_value=30, value=15)

    st.markdown("---")
    st.markdown("## 🤖 AI Summary")

    # Support both: key typed in sidebar OR stored in Streamlit secrets (for cloud deploy)
    default_key = st.secrets.get("ANTHROPIC_API_KEY", "") if hasattr(st, "secrets") else ""
    api_key = st.text_input(
        "Anthropic API Key",
        value=default_key,
        type="password",
        placeholder="sk-ant-...",
        help="Get a free key at console.anthropic.com"
    )
    st.caption("Free tier at console.anthropic.com is plenty for this tool.")

    st.markdown("---")
    st.caption("Data: Yahoo Finance · 15-min delay")
    st.caption(f"Next refresh in ~{refresh_mins} min")


# ── Auto-refresh ──────────────────────────────────────────────────────────────
st_autorefresh(interval=refresh_mins * 60 * 1000, key="gex_autorefresh")


# ── Data helpers ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=60 * 14)   # cache for 14 minutes
def fetch_gex(symbol: str):
    """Pull options chain from Yahoo Finance and compute net GEX per strike."""
    stock  = yf.Ticker(symbol)
    info   = stock.fast_info
    spot   = float(info.last_price)
    prev   = float(info.previous_close)
    change = spot - prev
    pct    = change / prev * 100

    expiries = stock.options
    if not expiries:
        return None, spot, change, pct, []

    expiry = expiries[0]
    chain  = stock.option_chain(expiry)

    calls = chain.calls.copy()
    puts  = chain.puts.copy()

    # Filter to ±5% around spot
    lo, hi = spot * (1 - STRIKE_RANGE), spot * (1 + STRIKE_RANGE)
    calls  = calls[(calls.strike >= lo) & (calls.strike <= hi)].copy()
    puts   = puts[ (puts.strike  >= lo) & (puts.strike  <= hi)].copy()

    # Fill missing gamma with 0
    calls["gamma"]        = calls["gamma"].fillna(0)
    puts["gamma"]         = puts["gamma"].fillna(0)
    calls["openInterest"] = calls["openInterest"].fillna(0)
    puts["openInterest"]  = puts["openInterest"].fillna(0)

    # GEX = Gamma × OI × 100 × Spot²
    # Calls → dealers long gamma (+),  Puts → dealers short gamma (−)
    calls["gex"] =  calls["gamma"] * calls["openInterest"] * 100 * spot ** 2
    puts["gex"]  = -puts["gamma"]  * puts["openInterest"]  * 100 * spot ** 2

    call_agg = calls.groupby("strike").agg(
        call_gex=("gex", "sum"), call_oi=("openInterest", "sum")
    )
    put_agg = puts.groupby("strike").agg(
        put_gex=("gex", "sum"), put_oi=("openInterest", "sum")
    )

    df = call_agg.join(put_agg, how="outer").fillna(0)
    df["net_gex"] = df["call_gex"] + df["put_gex"]
    df["call_oi"] = df["call_oi"].astype(int)
    df["put_oi"]  = df["put_oi"].astype(int)
    df = df.sort_values("strike", ascending=False).reset_index()

    return df, spot, change, pct, expiries


def tag_levels(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    """Assign a level label to each notable strike."""
    df = df.copy()
    df["level"] = ""

    # SPOT — the two strikes bracketing current price
    df["_dist"] = (df["strike"] - spot).abs()
    spot_idxs = df["_dist"].nsmallest(2).index
    df.loc[spot_idxs, "level"] = "SPOT"

    # KING — top 2 strikes by positive net GEX (not already labelled)
    pos_df = df[(df["net_gex"] > 0) & (df["level"] == "")]
    if not pos_df.empty:
        king_idxs = pos_df["net_gex"].nlargest(2).index
        df.loc[king_idxs, "level"] = "KING"

    # FLIP — first strike going downward where GEX turns negative
    strikes_desc = df.sort_values("strike", ascending=False)
    prev_gex = None
    for idx, row in strikes_desc.iterrows():
        if df.loc[idx, "level"] != "":
            prev_gex = row["net_gex"]
            continue
        if prev_gex is not None and prev_gex >= 0 and row["net_gex"] < 0:
            df.loc[idx, "level"] = "FLIP"
            break
        prev_gex = row["net_gex"]

    # GATE — remaining zero-crossings
    gex_vals = df["net_gex"].values
    for i in range(1, len(gex_vals)):
        if df.loc[df.index[i], "level"] != "":
            continue
        if np.sign(gex_vals[i]) != np.sign(gex_vals[i - 1]) and gex_vals[i - 1] != 0:
            df.loc[df.index[i], "level"] = "GATE"

    df = df.drop(columns=["_dist"])
    return df


# ── Formatting ─────────────────────────────────────────────────────────────────

def fmt_gex(v: float) -> str:
    sign = "-" if v < 0 else "+"
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{sign}${a/1_000_000_000:.1f}B"
    if a >= 1_000_000:
        return f"{sign}${a/1_000_000:.1f}M"
    return f"{sign}${a/1_000:.0f}K"


def fmt_oi(v: int) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(v)


# ── HTML Table ────────────────────────────────────────────────────────────────

def build_table(df: pd.DataFrame, spot: float) -> str:
    max_abs = df["net_gex"].abs().max()
    if max_abs == 0:
        max_abs = 1

    rows = ""
    for _, r in df.iterrows():
        s       = r["strike"]
        gex     = r["net_gex"]
        level   = r["level"]
        is_spot = abs(s - spot) < 0.6

        # Row background
        row_cls = {
            "FLIP": "row-flip",
            "KING": "row-king",
            "GATE": "row-gate",
            "SPOT": "row-spot",
        }.get(level, "")

        # Level label badge
        label_map = {
            "KING": ('<span class="lbl lbl-king">👑 KING</span>',),
            "FLIP": ('<span class="lbl lbl-flip">↕ FLIP</span>',),
            "GATE": ('<span class="lbl lbl-gate">🛡 GATE</span>',),
            "SPOT": ('<span class="lbl lbl-spot">◄ SPOT</span>',),
        }
        label_html = label_map.get(level, ("",))[0]

        strike_style = (
            'style="font-weight:700;color:#EF9F27;"'
            if is_spot else
            'style="color:#c9d1d9;"'
        )

        gex_cls   = "gex-pos" if gex >= 0 else "gex-neg"
        bar_cls   = "bar-pos" if gex >= 0 else "bar-neg"
        bar_w     = max(int(abs(gex) / max_abs * 110), 2)

        rows += f"""
        <tr class="{row_cls}">
          <td {strike_style}>{int(s)}{label_html}</td>
          <td class="{gex_cls}">{fmt_gex(gex)}</td>
          <td><div class="bar-wrap"><span class="{bar_cls}" style="width:{bar_w}px;"></span></div></td>
          <td style="color:#8b949e;">{fmt_oi(r['call_oi'])}</td>
          <td style="color:#FF6B6B;">{fmt_oi(r['put_oi'])}</td>
        </tr>"""

    return f"""
    <table class="gex-table">
      <thead><tr>
        <th>Strike</th>
        <th>Net GEX</th>
        <th>Exposure</th>
        <th>Call OI</th>
        <th>Put OI</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


# ── AI Summary ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60 * 14)
def get_ai_summary(ticker: str, spot: float, summary_data: str, key: str) -> str:
    if not key:
        return ""
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=220,
            messages=[{"role": "user", "content": f"""You are a concise options market analyst. 
Analyze this GEX heatmap for {ticker} (spot ${spot:.2f}) and give a 3–4 sentence plain-English summary.
Cover: (1) whether the market is in positive or negative gamma territory overall, (2) key support/resistance levels from the KING and GATE strikes, (3) what the FLIP level means for near-term price action.
Be direct and practical. No disclaimers.

Data:
{summary_data}"""}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI summary unavailable — check your API key. ({e})"


# ── Main render ───────────────────────────────────────────────────────────────

st.markdown(f"# ⚡ GEX Heatmap")

with st.spinner(f"Loading {ticker_symbol}…"):
    result = fetch_gex(ticker_symbol)

if result[0] is None:
    st.error(f"No options data found for **{ticker_symbol}**. Markets may be closed or the ticker is invalid.")
    st.stop()

df, spot, change, pct, expiries = result
df = tag_levels(df, spot)

# ── Ticker header ─────────────────────────────────────────────────────────────
chg_color = "#00C896" if change >= 0 else "#FF6B6B"
chg_sign  = "+" if change >= 0 else ""
expiry    = expiries[0] if expiries else "—"

# Find flip level for the control node chip
flip_row = df[df["level"] == "FLIP"]
flip_strike = int(flip_row.iloc[0]["strike"]) if not flip_row.empty else "—"

st.markdown(f"""
<div class="ticker-header">
  <span style="font-family:monospace;font-size:20px;font-weight:700;color:#c9d1d9;">{ticker_symbol}</span>
  <span style="font-family:monospace;font-size:18px;color:#c9d1d9;">${spot:.2f}</span>
  <span style="font-family:monospace;font-size:14px;color:{chg_color};">{chg_sign}{change:.2f} ({chg_sign}{pct:.2f}%)</span>
  <span style="background:rgba(163,45,45,0.18);border:0.5px solid rgba(163,45,45,0.45);border-radius:6px;padding:4px 10px;font-family:monospace;font-size:12px;color:#FF6B6B;">
    ⚡ Flip Zone · {flip_strike}
  </span>
  <span style="margin-left:auto;font-family:monospace;font-size:12px;color:#8b949e;">Expiry: {expiry}</span>
</div>
""", unsafe_allow_html=True)

# ── Heatmap table ─────────────────────────────────────────────────────────────
st.markdown(build_table(df, spot), unsafe_allow_html=True)

# ── Legend ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:10px;font-family:monospace;font-size:11px;color:#8b949e;">
  <span>👑 <span style="color:#D4AF37;">KING</span> — highest positive GEX (strong support)</span>
  <span>↕ <span style="color:#C850C0;">FLIP</span> — gamma flip point (positive → negative)</span>
  <span>🛡 <span style="color:#378ADD;">GATE</span> — zero-crossing / key level</span>
  <span>◄ <span style="color:#00C896;">SPOT</span> — current price</span>
  <span style="color:#00C896;">■</span> Positive GEX &nbsp;&nbsp;
  <span style="color:#9B59B6;">■</span> Negative GEX
</div>
""", unsafe_allow_html=True)

# ── AI Summary ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🤖 AI Analysis")

if api_key:
    # Build a text summary of key levels to pass to Claude
    key_rows = df[df["level"] != ""].copy()
    summary_lines = [
        f"  [{r['level']}] Strike {int(r['strike'])}: {fmt_gex(r['net_gex'])} net GEX, "
        f"Call OI {fmt_oi(r['call_oi'])}, Put OI {fmt_oi(r['put_oi'])}"
        for _, r in key_rows.iterrows()
    ]
    pos_total = df[df["net_gex"] > 0]["net_gex"].sum()
    neg_total = df[df["net_gex"] < 0]["net_gex"].sum()
    summary_lines += [
        f"  Total +GEX: {fmt_gex(pos_total)}",
        f"  Total -GEX: {fmt_gex(neg_total)}",
        f"  Net GEX:    {fmt_gex(pos_total + neg_total)}",
    ]
    summary_data = "\n".join(summary_lines)

    with st.spinner("Analyzing…"):
        ai_text = get_ai_summary(ticker_symbol, spot, summary_data, api_key)

    if ai_text:
        st.markdown(f'<div class="ai-box">{ai_text}</div>', unsafe_allow_html=True)
else:
    st.info(
        "Add your Anthropic API key in the sidebar to enable AI analysis. "
        "Get a free key at **console.anthropic.com** — the free tier is plenty for this tool."
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="footer">
  Data: Yahoo Finance (15-min delay) · Refreshes every {refresh_mins} min · 
  Last loaded: {datetime.now().strftime("%Y-%m-%d  %H:%M:%S")}
</div>
""", unsafe_allow_html=True)
