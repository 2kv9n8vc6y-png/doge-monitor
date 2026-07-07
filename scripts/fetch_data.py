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


def fetch_whale_transactions(price_usd):
    """
    Fetch large DOGE transactions from 3xpl.com (Blockchair v3, free tier).
    Falls back to BlockCypher if 3xpl is unavailable.
    Combines mempool large tx + on-chain stats to estimate whale activity.
    """
    whale_txs = []
    seen_hashes = set()

    # ── Source 1: 3xpl.com (Blockchair v3) ─────────────────
    try:
        url = "https://api.3xpl.com/dogecoin/transaction"
        params = {
            "sort": "value",
            "order": "desc",
            "limit": 25,
            "from": "last_day",
        }
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            for tx in data:
                try:
                    value_doge = float(tx.get("value", 0))
                    value_usd = value_doge * price_usd
                    if value_usd < 10000:
                        continue
                    whale_txs.append({
                        "value_usd": round(value_usd, 2),
                        "value_doge": round(value_doge, 0),
                        "time": tx.get("time", ""),
                        "source": "3xpl",
                    })
                except Exception:
                    continue
    except Exception as e:
        print(f"  Warning: 3xpl fetch failed: {e}")

    # ── Source 2: BlockCypher (mempool) ────────────────────
    try:
        url = "https://api.blockcypher.com/v1/doge/main/txs"
        resp = requests.get(url, params={"limit": 50}, timeout=20)
        resp.raise_for_status()
        txs = resp.json()
        for tx in txs:
            try:
                value_doge = float(tx.get("total", 0)) / 1e8
                value_usd = value_doge * price_usd
                if value_usd < 50000:
                    continue
                tx_hash = tx.get("hash", "")
                if tx_hash in seen_hashes:
                    continue
                seen_hashes.add(tx_hash)
                whale_txs.append({
                    "value_usd": round(value_usd, 2),
                    "value_doge": round(value_doge, 0),
                    "time": tx.get("received", ""),
                    "source": "mempool",
                })
            except Exception:
                continue
    except Exception as e:
        print(f"  Warning: BlockCypher fetch failed: {e}")

    if not whale_txs:
        return None

    # Sort by value
    whale_txs.sort(key=lambda t: t["value_usd"], reverse=True)

    total_whale_volume = sum(t["value_usd"] for t in whale_txs)
    whale_count_100k = sum(1 for t in whale_txs if t["value_usd"] >= 100000)
    whale_count_1m = sum(1 for t in whale_txs if t["value_usd"] >= 1000000)
    whale_count_10m = sum(1 for t in whale_txs if t["value_usd"] >= 10000000)
    mempool_count = sum(1 for t in whale_txs if t.get("source") == "mempool")
    confirmed_count = sum(1 for t in whale_txs if t.get("source") == "3xpl")

    return {
        "whale_tx_count_100k": whale_count_100k,
        "whale_tx_count_1m": whale_count_1m,
        "whale_tx_count_10m": whale_count_10m,
        "total_whale_volume_usd": round(total_whale_volume, 2),
        "avg_whale_tx_value_usd": round(total_whale_volume / len(whale_txs), 2),
        "largest_tx_usd": round(whale_txs[0]["value_usd"], 2) if whale_txs else None,
        "top_transactions": whale_txs[:10],
        "sample_size": len(whale_txs),
        "mempool_whale_count": mempool_count,
        "confirmed_whale_count": confirmed_count,
    }


def analyze_whales(whale_data, price_data, chain_data):
    """Generate whale-specific analysis combining on-chain stats + big tx data."""
    if not whale_data:
        # Fallback: infer whale activity from available chain data
        largest_tx = chain_data.get("largest_transaction_24h_usd", 0)
        tx_count = chain_data.get("transactions_24h", 0)
        fee_total = chain_data.get("fee_24h_usd", 0)

        summaries = []
        if largest_tx and largest_tx > 1000000:
            summaries.append(f"24h最大转账${largest_tx:,.0f}")
            activity = "链上有大额转账记录"
        elif largest_tx and largest_tx > 100000:
            summaries.append(f"24h最大转账${largest_tx:,.0f}")
            activity = "中等活跃"
        else:
            activity = "暂无大额数据"

        if tx_count > 40000:
            summaries.append(f"日交易{tx_count}笔，链上活跃")
        if fee_total and fee_total > 10000:
            summaries.append(f"手续费${fee_total:,.0f}，网络需求偏高")

        return {
            "status": "partial",
            "activity_level": activity if summaries else "数据不足",
            "summary": "；".join(summaries) if summaries else "巨鲸数据暂不可用，请参考链上数据",
            "whale_tx_count_100k": 0,
            "whale_tx_count_1m": 0,
            "whale_tx_count_10m": 0,
            "total_whale_volume_usd": 0,
            "avg_whale_tx_value_usd": 0,
            "largest_tx_usd": largest_tx,
        }

    count_1m = whale_data["whale_tx_count_1m"]
    count_100k = whale_data["whale_tx_count_100k"]
    count_10m = whale_data["whale_tx_count_10m"]
    total_vol = whale_data["total_whale_volume_usd"]
    avg_val = whale_data["avg_whale_tx_value_usd"]
    mempool_whales = whale_data.get("mempool_whale_count", 0)

    # Activity level
    if count_1m >= 5:
        activity_cn = "高度活跃 🔥"
    elif count_1m >= 2:
        activity_cn = "温和活跃"
    elif count_100k >= 5:
        activity_cn = "有动作"
    else:
        activity_cn = "低迷"

    summaries = []
    if whale_data.get("largest_tx_usd"):
        summaries.append(f"最大单笔${whale_data['largest_tx_usd']:,.0f}")
    if count_10m >= 1:
        summaries.append(f"千万级巨鲸转账{count_10m}笔 💣")
    if count_1m >= 3:
        summaries.append(f"百万级以上{count_1m}笔，大资金活跃")
    elif count_1m >= 1:
        summaries.append(f"百万级{count_1m}笔")
    if count_100k >= 10:
        summaries.append(f"≥$10万转账{count_100k}笔")
    if mempool_whales >= 3:
        summaries.append(f"mempool中{mempool_whales}笔大单待确认")
    if avg_val > 1000000:
        summaries.append(f"平均单笔${avg_val:,.0f}")

    return {
        "status": "ok",
        "activity_level": activity_cn,
        "summary": "；".join(summaries),
        "whale_tx_count_100k": count_100k,
        "whale_tx_count_1m": count_1m,
        "whale_tx_count_10m": count_10m,
        "total_whale_volume_usd": total_vol,
        "avg_whale_tx_value_usd": avg_val,
        "largest_tx_usd": whale_data.get("largest_tx_usd"),
        "mempool_whale_count": mempool_whales,
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

    whale_data = fetch_whale_transactions(price_data.get("price_usd", 0.07))
    if whale_data:
        print(f"  Whale: {whale_data['whale_tx_count_100k']} tx>$100K | "
              f"{whale_data['whale_tx_count_1m']} tx>$1M | "
              f"largest: ${whale_data['avg_whale_tx_value_usd']:,.0f}")
    else:
        print("  Whale: data unavailable")

    # Analyze
    whale_analysis = analyze_whales(whale_data, price_data, chain_data)
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
