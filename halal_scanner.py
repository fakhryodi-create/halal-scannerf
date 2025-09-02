# halal_scanner.py
import os
import time
import io
import pandas as pd
import requests
import yfinance as yf
import streamlit as st

ZOYA_API_BASE = "https://api.zoya.finance"

def zoya_is_halal(ticker: str, api_key: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    url = f"{ZOYA_API_BASE}/v1/stocks/{ticker}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {"isShariahCompliant": None}

def yahoo_data(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.get_info()
    return {
        "last_price": info.get("regularMarketPrice"),
        "previous_close": info.get("regularMarketPreviousClose"),
        "volume": info.get("volume"),
        "float_shares": info.get("floatShares"),
        "name": info.get("shortName") or info.get("longName")
    }

def compute_gap(last, prev):
    if last is None or prev is None: return None
    return (last - prev) / prev * 100

def passes_filters(row, min_price, max_price, min_volume, max_float, min_gap, max_gap):
    lp = row.get("last_price")
    vol = row.get("volume")
    fl = row.get("float_shares")
    gap = row.get("gap")
    if min_price and (lp is None or lp < min_price): return False
    if max_price and (lp is None or lp > max_price): return False
    if min_volume and (vol is None or vol < min_volume): return False
    if max_float and (fl is None or fl > max_float): return False
    if min_gap and (gap is None or gap < min_gap): return False
    if max_gap and (gap is None or gap > max_gap): return False
    return True

def make_tws_csv(df, exchange="SMART"):
    lines = [f"DES,{row['ticker']},STK,{exchange},,,,," for _, row in df.iterrows()]
    return "\n".join(lines)

st.title("Halal Stock Scanner — Zoya + Yahoo Finance")

with st.sidebar:
    zoya_key = st.text_input("Zoya API key")
    tickers_input = st.text_area("Tickers (comma or newline separated)", value="AAPL,MSFT,TSLA,AMZN")
    min_price = st.number_input("Min last price", value=0.0)
    max_price = st.number_input("Max last price", value=0.0)
    min_volume = st.number_input("Min volume", value=0.0)
    max_float = st.number_input("Max float", value=0.0)
    min_gap = st.number_input("Min gap %", value=0.0)
    max_gap = st.number_input("Max gap %", value=0.0)
    exchange_csv = st.text_input("TWS Exchange", value="SMART")
    run_scan = st.button("Scan")

if run_scan:
    tickers = [t.strip().upper() for t in tickers_input.replace("\n", ",").split(",") if t.strip()]
    rows = []
    for tk in tickers:
        y = yahoo_data(tk)
        z = zoya_is_halal(tk, zoya_key)
        gap = compute_gap(y.get("last_price"), y.get("previous_close"))
        row = {**y, "ticker": tk, "is_halal": z.get("isShariahCompliant"), "gap": gap}
        rows.append(row)
        time.sleep(0.1)
    df = pd.DataFrame(rows)
    filtered = df[df.apply(lambda r: passes_filters(
        r,
        min_price if min_price > 0 else None,
        max_price if max_price > 0 else None,
        min_volume if min_volume > 0 else None,
        max_float if max_float > 0 else None,
        min_gap if min_gap > 0 else None,
        max_gap if max_gap > 0 else None
    ), axis=1)]
    st.dataframe(filtered)
    st.download_button("Download TWS CSV", make_tws_csv(filtered, exchange_csv), file_name="tws_watchlist.csv")
