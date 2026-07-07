"""
DOGE Monitor - Data Fetching Script
Fetches Dogecoin price, market data, on-chain metrics, and whale transactions.
Generates a structured JSON report.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

# ── Config ──────────────────────────────────────────────
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BLOCKCHAIR_BASE = "https://api.blockchair.com"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")

# Beijing timezone
TZ = timezone(timedelta(hours=8))

# ── Helpers ─────────────────────────────────────────────

def fetch_coingecko():
    """Fetch DOGE price and market data from CoinGecko."""
    url = f"{COINGECKO_BASE}/coins/dogecoin"
    params = {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    market = data.get("market_data", {})
    return {
        "price_usd": market.get("current_price", {}).get("usd"),
        "price_btc": market.get("current_price", {}).get("btc"),
        "change_24h_pct": market.get("price_change_percentage_24h"),
        "change_7d_pct": market.get("price_change_percentage_7d"),
        "change_30d_pct": market.get("price_change_percentage_30d"),
        "market_cap_usd": market.get("market_cap", {}).get("usd"),
        "volume_24h_usd": market.get("total_volume", {}).get("usd"),
        "market_cap_rank": data.get("market_cap_rank"),
        "ath_usd": market.get("ath", {}).get("usd"),
        "ath_date": market.get("ath_date", {}).get("usd"),
        "atl_usd": market.get("atl", {}).get("usd"),
        "atl_date": market.get("atl_date", {}).get("usd"),
        "high_24h_usd": market.get("high_24h", {}).get("usd"),
        "low_24h_usd": market.get("low_24h", {}).get("usd"),
        "circulating_supply": market.get("circulating_supply"),
        "total_supply": market.get("total_supply"),
        "max_supply": market.get("max_supply"),
    }


def fetch_blockchair():
    """Fetch on-chain stats from Blockchair (free tier, no key needed)."""
    url = f"{BLOCKCHAIR_BASE}/dogecoin/stats"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", {})

    return {
        "blocks": data.get("blocks"),
        "transactions_24h": data.get("transactions_24h"),
        "circulation": data.get("circulation"),
        "difficulty": data.get("difficulty"),
        "hashrate_24h": data.get("hashrate_24h"),
        "mempool_transactions": data.get("mempool_transactions"),
        "mempool_size": data.get("mempool_size"),
        "mempool_tps": data.get("mempool_tps"),
        "mempool_total_fee_usd": data.get("mempool_total_fee_usd"),
        "average_transaction_fee_24h_usd": data.get("average_transaction_fee_24h_usd"),
        "median_transaction_fee_24h_usd": data.get("median_transaction_fee_24h_usd"),
        "fee_24h_usd": data.get("fee_24h_usd"),
        "largest_transaction_24h_usd": (data.get("largest_transaction_24h") or {}).get("value_usd", 0),
        "nodes": data.get("nodes"),
        "outputs_24h": data.get("outputs_24h"),
    }


def analyze_whales(price_data, chain_data):
    """
    Infer whale activity from on-chain stats.
    Uses largest_tx, volume patterns, fees, and tx count as proxies.
    """
    largest_tx = chain_data.get("largest_transaction_24h_usd") or 0
    tx_count = chain_data.get("transactions_24h") or 0
    fee_total = chain_data.get("fee_24h_usd") or 0
    avg_fee = chain_data.get("average_transaction_fee_24h_usd") or 0
    median_fee = chain_data.get("median_transaction_fee_24h_usd") or 0
    mempool_txs = chain_data.get("mempool_transactions") or 0
    outputs_24h = chain_data.get("outputs_24h") or 0

    vol = price_data.get("volume_24h_usd") or 0
    mcap = price_data.get("market_cap_usd") or 1
    price = price_data.get("price_usd") or 0

    # ── Whale Activity Score (0-100) ─────────────────────
    score = 0
    signals = []

    # 1. Largest single tx
    if largest_tx > 10000000:
        score += 30
        signals.append(f"24h最大单笔${largest_tx:,.0f}，千万级巨鲸出动")
    elif largest_tx > 5000000:
        score += 22
        signals.append(f"24h最大单笔${largest_tx:,.0f}")
    elif largest_tx > 1000000:
        score += 15
        signals.append(f"24h最大转账${largest_tx:,.0f}")
    elif largest_tx > 100000:
        score += 8

    # 2. Average tx size (total output / output count)
    if outputs_24h > 0 and price > 0:
        avg_output_doge = chain_data.get("circulation", 0)
        # Estimate: total value moved ≈ volume * some factor
        est_avg_tx = (vol / tx_count) if tx_count > 0 else 0
        if est_avg_tx > 50000:
            score += 20
            signals.append(f"估计均笔交易${est_avg_tx:,.0f}，大单占比高")
        elif est_avg_tx > 10000:
            score += 12
        elif est_avg_tx > 5000:
            score += 6

    # 3. Volume / MCap ratio (high = active whales trading)
    vol_ratio = vol / mcap if mcap else 0
    if vol_ratio > 0.12:
        score += 20
        signals.append(f"换手率{vol_ratio*100:.1f}%，资金进出频繁")
    elif vol_ratio > 0.07:
        score += 12
    elif vol_ratio > 0.04:
        score += 6

    # 4. Fee spike (whales pay higher fees for priority)
    if avg_fee and median_fee and median_fee > 0 and avg_fee / max(median_fee, 0.0001) > 2:
        score += 15
        signals.append("手续费分布不均，大额优先费增加")

    # 5. Mempool congestion (large pending tx)
    if mempool_txs > 100:
        score += 10
        signals.append(f"Mempool {mempool_txs}笔待处理，网络拥堵")
    elif mempool_txs > 50:
        score += 5

    # 6. Total fee spend (high = network demand)
    if fee_total > 20000:
        score += 10
        signals.append(f"24h总手续费${fee_total:,.0f}，网络繁忙")
    elif fee_total > 5000:
        score += 5

    # 7. Tx count trend
    if tx_count > 50000:
        score += 10
        signals.append(f"日交易{tx_count:,}笔，链上高度活跃")
    elif tx_count > 30000:
        score += 5

    # ── Determine activity level ──────────────────────────
    if score >= 65:
        activity_cn = "高度活跃 🔥🔥"
    elif score >= 40:
        activity_cn = "温和活跃 🔥"
    elif score >= 20:
        activity_cn = "有动静"
    else:
        activity_cn = "低迷 💤"

    # ── Direction inference ──────────────────────────────
    vol_mcap_pct = round(vol_ratio * 100, 1)
    est_avg = round(vol / tx_count, 0) if tx_count > 0 else 0

    summary_text = "；".join(signals) if signals else (
        f"近24h链上无明显巨鲸异动。最大转账${largest_tx:,.0f}。"
        if largest_tx > 0 else "正在累积链上数据..."
    )

    return {
        "status": "ok",
        "activity_level": activity_cn,
        "activity_score": score,
        "summary": summary_text,
        "largest_tx_24h_usd": largest_tx,
        "est_avg_tx_usd": est_avg,
        "fee_total_24h_usd": fee_total,
        "avg_fee_usd": avg_fee,
        "vol_mcap_ratio_pct": vol_mcap_pct,
        "mempool_count": mempool_txs,
        "tx_count_24h": tx_count,
    }


def analyze_data(price_data, chain_data, whale_analysis):
    """Generate human-readable analysis based on the data."""
    conclusions = []

    # Price trend
    change_24h = price_data.get("change_24h_pct") or 0
    change_7d = price_data.get("change_7d_pct") or 0

    if change_24h > 5:
        conclusions.append("短期强势上涨，注意是否放量突破阻力")
    elif change_24h > 2:
        conclusions.append("短线企稳反弹")
    elif change_24h < -5:
        conclusions.append("短期急跌，关注下方支撑")
    elif change_24h < -2:
        conclusions.append("短线走弱，观望为主")
    else:
        conclusions.append("短线横盘震荡")

    if change_7d < -10:
        conclusions.append("7日跌幅较大，可能出现超跌反弹机会")
    elif change_7d > 10:
        conclusions.append("7日涨幅较大，追高需谨慎")

    # On-chain
    txs = chain_data.get("transactions_24h") or 0
    mempool_txs = chain_data.get("mempool_transactions") or 0
    hashrate = chain_data.get("hashrate_24h") or "N/A"

    if txs > 50000:
        conclusions.append("链上交易活跃度较高")
    elif txs < 20000:
        conclusions.append("链上交易冷清，市场参与度低")

    # Whale integration
    if whale_analysis.get("status") == "ok":
        conclusions.append(f"巨鲸：{whale_analysis['activity_level']}，" + whale_analysis["summary"])

    # Volume analysis
    vol = price_data.get("volume_24h_usd") or 0
    mcap = price_data.get("market_cap_usd") or 1
    vol_ratio = vol / mcap if mcap else 0
    if vol_ratio > 0.15:
        conclusions.append("换手率偏高，多空分歧大")
    elif vol_ratio < 0.03:
        conclusions.append("换手率极低，变盘在即")

    # Key levels
    price = price_data.get("price_usd") or 0
    support = round(price * 0.93, 5)
    resistance = round(price * 1.07, 5)
    major_support = round(price * 0.88, 5)
    major_resistance = round(price * 1.12, 5)

    # Determine phase (enhanced with whale data)
    if change_24h > 0 and vol_ratio > 0.08:
        phase = "放量上涨，关注是否有持续资金进场"
    elif change_24h > 0 and vol_ratio < 0.03:
        phase = "无量反弹，可信度较低"
    elif change_24h < 0 and vol_ratio > 0.08:
        phase = "放量下跌，等企稳再考虑入场"
    elif change_24h < 0 and vol_ratio < 0.03:
        phase = "缩量阴跌，观望"
    else:
        phase = "窄幅整理，等待方向选择"

    # Add whale context to phase
    if whale_analysis.get("status") == "ok":
        w_1m = whale_analysis.get("whale_tx_count_1m", 0)
        if w_1m >= 3 and change_24h < 1 and change_24h > -1:
            phase += "（巨鲸暗中活跃）"

    return {
        "summary": "；".join(conclusions),
        "phase": phase,
        "support": support,
        "resistance": resistance,
        "major_support": major_support,
        "major_resistance": major_resistance,
        "key_indicators": {
            "vol_mcap_ratio": round(vol_ratio * 100, 1),
            "transactions_24h": txs,
            "hashrate_24h": hashrate,
            "mempool_txs": mempool_txs,
        }
    }


def main():
    now = datetime.now(TZ)
    hour = now.hour
    report_type = "morning" if hour < 15 else "evening"

    print(f"[{now.isoformat()}] Fetching DOGE data for {report_type} report...")

    # Fetch data
    price_data = fetch_coingecko()
    print(f"  Price: ${price_data['price_usd']} | 24h: {price_data['change_24h_pct']:.1f}%")

    chain_data = fetch_blockchair()
    print(f"  Chain: {chain_data['transactions_24h']} tx/24h | mempool: {chain_data['mempool_transactions']}")

    # Analyze (whale analysis uses chain stats + price data)
    whale_analysis = analyze_whales(price_data, chain_data)
    analysis = analyze_data(price_data, chain_data, whale_analysis)

    # Build report
    report = {
        "timestamp": now.isoformat(),
        "type": report_type,
        "price": price_data,
        "chain": chain_data,
        "whale": whale_analysis,
        "analysis": analysis,
    }

    # Write latest.json
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    latest_path = os.path.join(OUTPUT_DIR, "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {latest_path}")

    # Write historical report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    hist_filename = f"{now.strftime('%Y-%m-%d')}-{report_type}.json"
    hist_path = os.path.join(REPORTS_DIR, hist_filename)
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {hist_path}")

    # Update report index
    index_path = os.path.join(REPORTS_DIR, "index.json")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        index = []

    index.append({
        "timestamp": now.isoformat(),
        "type": report_type,
        "price": price_data["price_usd"],
        "change_24h": price_data["change_24h_pct"],
        "summary": analysis["summary"],
    })
    index = index[-60:]
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print("Done!")
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
