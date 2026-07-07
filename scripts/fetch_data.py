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

# Known exchange wallet patterns (partial address markers)
EXCHANGE_TAGS = {
    "binance": ["binance", "bnb", "bsc"],
    "robinhood": ["robinhood", "rh", "rhood"],
    "coinbase": ["coinbase", "cb"],
    "bybit": ["bybit"],
    "kraken": ["kraken"],
    "upbit": ["upbit"],
    "okx": ["okx", "okex"],
    "gate": ["gate.io", "gateio"],
    "kucoin": ["kucoin"],
    "huobi": ["huobi", "htx"],
}

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
        "largest_transaction_24h_usd": data.get("largest_transaction_24h_usd"),
        "nodes": data.get("nodes"),
        "outputs_24h": data.get("outputs_24h"),
    }


def fetch_whale_transactions():
    """
    Fetch the largest recent DOGE transactions from Blockchair.
    Returns whale activity summary.
    """
    url = f"{BLOCKCHAIR_BASE}/dogecoin/transactions"
    params = {
        "s": "value_usd(desc)",
        "limit": 25,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception as e:
        print(f"  Warning: whale tx fetch failed: {e}")
        return None

    if not data:
        return None

    whale_txs = []
    total_whale_volume = 0
    whale_count_100k = 0
    whale_count_1m = 0
    whale_count_10m = 0
    exchange_in = 0
    exchange_out = 0
    exchange_in_count = 0
    exchange_out_count = 0

    for tx in data:
        try:
            value_usd = float(tx.get("value_usd", 0) or 0)
            inputs = tx.get("inputs", [])
            outputs = tx.get("outputs", [])

            # Whale tiers
            if value_usd >= 100000:
                whale_count_100k += 1
            if value_usd >= 1000000:
                whale_count_1m += 1
            if value_usd >= 10000000:
                whale_count_10m += 1

            total_whale_volume += value_usd

            # Detect exchange-related transactions
            all_addrs = []
            for inp in inputs:
                all_addrs.append(inp.get("recipient", "").lower())
            for out in outputs:
                all_addrs.append(out.get("recipient", "").lower())

            is_exchange = False
            matched_exchange = None
            for addr in all_addrs:
                for ex_name, keywords in EXCHANGE_TAGS.items():
                    for kw in keywords:
                        if kw in addr:
                            is_exchange = True
                            matched_exchange = ex_name
                            break
                    if is_exchange:
                        break
                if is_exchange:
                    break

            # Heuristic: if value > $100K, likely whale
            direction = "unknown"
            if is_exchange:
                # Check if first input looks like it's FROM exchange (withdrawal)
                # Simple heuristic: large tx with exchange tag = exchange-related
                direction = "exchange_related"

            whale_txs.append({
                "value_usd": round(value_usd, 2),
                "value_doge": round(float(tx.get("value", 0) or 0), 0),
                "is_exchange": is_exchange,
                "exchange": matched_exchange,
                "direction": direction,
                "time": tx.get("time", ""),
            })
        except Exception:
            continue

    # Build summary
    return {
        "whale_tx_count_100k": whale_count_100k,
        "whale_tx_count_1m": whale_count_1m,
        "whale_tx_count_10m": whale_count_10m,
        "total_whale_volume_usd": round(total_whale_volume, 2),
        "avg_whale_tx_value_usd": round(total_whale_volume / len(whale_txs), 2) if whale_txs else 0,
        "top_transactions": whale_txs[:10],
        "exchange_related_count": sum(1 for t in whale_txs if t["is_exchange"]),
        "sample_size": len(whale_txs),
    }


def analyze_whales(whale_data, price_data):
    """Generate whale-specific analysis."""
    if not whale_data:
        return {
            "status": "no_data",
            "summary": "巨鲸数据暂不可用",
            "activity_level": "unknown",
        }

    count_1m = whale_data["whale_tx_count_1m"]
    count_100k = whale_data["whale_tx_count_100k"]
    total_vol = whale_data["total_whale_volume_usd"]
    avg_val = whale_data["avg_whale_tx_value_usd"]
    exchange_count = whale_data["exchange_related_count"]
    top_txs = whale_data["top_transactions"]

    # Determine activity level
    if count_1m >= 5:
        activity = "high"
        activity_cn = "高度活跃 🔥"
    elif count_1m >= 2:
        activity = "medium"
        activity_cn = "温和活跃"
    else:
        activity = "low"
        activity_cn = "低迷"

    # Analyze direction
    summaries = []
    if count_100k >= 10:
        summaries.append(f"24h内≥10万$大额转账{count_100k}笔")
    if count_1m >= 3:
        summaries.append(f"百万级巨鲸交易{count_1m}笔")
    if count_1m == 0:
        summaries.append("无百万级以上转账，巨鲸按兵不动")
    if exchange_count >= 3:
        summaries.append(f"其中{exchange_count}笔与交易所相关")

    if avg_val > 5000000:
        summaries.append("平均单笔金额超$500万，大资金在动")
    elif avg_val > 1000000:
        summaries.append("平均单笔$100万+，中等体量资金活跃")

    # Top tx info
    if top_txs:
        largest = top_txs[0]
        summaries.insert(0, f"最大单笔：${largest['value_usd']:,.0f}")

    return {
        "status": "ok",
        "activity_level": activity_cn,
        "summary": "；".join(summaries),
        "whale_tx_count_100k": count_100k,
        "whale_tx_count_1m": count_1m,
        "whale_tx_count_10m": whale_data["whale_tx_count_10m"],
        "total_whale_volume_usd": total_vol,
        "avg_whale_tx_value_usd": avg_val,
        "exchange_related_count": exchange_count,
        "largest_tx_usd": round(top_txs[0]["value_usd"], 2) if top_txs else None,
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

    whale_data = fetch_whale_transactions()
    if whale_data:
        print(f"  Whale: {whale_data['whale_tx_count_100k']} tx>$100K | "
              f"{whale_data['whale_tx_count_1m']} tx>$1M | "
              f"largest: ${whale_data['avg_whale_tx_value_usd']:,.0f}")
    else:
        print("  Whale: data unavailable")

    # Analyze
    whale_analysis = analyze_whales(whale_data, price_data)
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
