import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  ActivityIndicator,
  Dimensions,
} from "react-native";

const SCREEN_WIDTH = Dimensions.get("window").width;

// Default URL — replace YOUR_USERNAME with your GitHub username
const DEFAULT_REPORT_URL =
  "https://raw.githubusercontent.com/2kv9n8vc6y-png/doge-monitor/master/public/latest.json";

export default function ReportScreen({ notification, onClearNotification }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchReport = useCallback(async () => {
    try {
      const resp = await fetch(DEFAULT_REPORT_URL, {
        headers: { Accept: "application/json" },
        cache: "no-cache",
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setReport(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Clear notification when user views the report
  useEffect(() => {
    if (notification && onClearNotification) {
      onClearNotification();
    }
  }, [notification]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchReport();
  }, [fetchReport]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#f5a623" />
        <Text style={styles.loadingText}>加载 DOGE 数据...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorIcon}>🐕‍🦺</Text>
        <Text style={styles.errorText}>数据加载失败</Text>
        <Text style={styles.errorDetail}>{error}</Text>
        <Text style={styles.errorHint}>下拉刷新重试</Text>
      </View>
    );
  }

  const { price, chain, analysis } = report;
  const change = price?.change_24h_pct || 0;
  const isUp = change >= 0;
  const emoji = report.type === "morning" ? "☀️" : "🌙";
  const label = report.type === "morning" ? "DOGE 早报" : "DOGE 晚报";

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#f5a623"
          colors={["#f5a623"]}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerEmoji}>🐕</Text>
        <Text style={styles.headerTitle}>{label}</Text>
        <Text style={styles.headerDate}>
          {new Date(report.timestamp).toLocaleString("zh-CN")}
        </Text>
      </View>

      {/* Price Card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>💰 价格</Text>
        <View style={styles.priceRow}>
          <Text style={styles.priceValue}>
            ${price?.price_usd?.toFixed(5) || "N/A"}
          </Text>
          <View
            style={[
              styles.changeBadge,
              { backgroundColor: isUp ? "#1b5e20" : "#b71c1c" },
            ]}
          >
            <Text style={styles.changeText}>
              {isUp ? "+" : ""}
              {change?.toFixed(2)}%
            </Text>
          </View>
        </View>

        {/* Price grid */}
        <View style={styles.grid}>
          <MetricBox label="24h高" value={`$${price?.high_24h_usd?.toFixed(5) || "-"}`} />
          <MetricBox label="24h低" value={`$${price?.low_24h_usd?.toFixed(5) || "-"}`} />
          <MetricBox label="7日" value={`${price?.change_7d_pct?.toFixed(1) || "-"}%`} color={price?.change_7d_pct >= 0 ? "#4caf50" : "#f44336"} />
          <MetricBox label="30日" value={`${price?.change_30d_pct?.toFixed(1) || "-"}%`} color={price?.change_30d_pct >= 0 ? "#4caf50" : "#f44336"} />
        </View>

        <View style={styles.grid}>
          <MetricBox label="市值" value={formatLargeNum(price?.market_cap_usd)} />
          <MetricBox label="排名" value={`#${price?.market_cap_rank || "-"}`} />
          <MetricBox label="24h成交量" value={formatLargeNum(price?.volume_24h_usd)} />
          <MetricBox label="流通量" value={`${(price?.circulating_supply / 1e9)?.toFixed(1) || "-"}B`} />
        </View>
      </View>

      {/* On-Chain Card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>⛓️ 链上数据</Text>
        <View style={styles.grid}>
          <MetricBox label="24h交易数" value={chain?.transactions_24h?.toLocaleString() || "-"} />
          <MetricBox label="24h手续费" value={`$${chain?.fee_24h_usd?.toFixed(0) || "-"}`} />
          <MetricBox label="算力" value={chain?.hashrate_24h || "-"} />
          <MetricBox label="Mempool" value={chain?.mempool_transactions?.toLocaleString() || "-"} />
        </View>
        <View style={styles.grid}>
          <MetricBox label="平均手续费" value={`$${chain?.average_transaction_fee_24h_usd?.toFixed(4) || "-"}`} />
          <MetricBox label="最大单笔转账" value={formatLargeNum(chain?.largest_transaction_24h_usd)} />
          <MetricBox label="节点数" value={chain?.nodes?.toLocaleString() || "-"} />
          <MetricBox label="24h输出数" value={chain?.outputs_24h?.toLocaleString() || "-"} />
        </View>
      </View>

      {/* Analysis Card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🧠 分析</Text>

        <View style={styles.phaseBox}>
          <Text style={styles.phaseText}>{analysis?.phase}</Text>
        </View>

        <Text style={styles.summaryText}>{analysis?.summary}</Text>

        {/* Key levels */}
        <View style={styles.levelsContainer}>
          <View style={[styles.levelBox, styles.supportBox]}>
            <Text style={styles.levelLabel}>🟢 支撑位</Text>
            <Text style={styles.levelValue}>${analysis?.support?.toFixed(5)}</Text>
          </View>
          <View style={[styles.levelBox, styles.resistanceBox]}>
            <Text style={styles.levelLabel}>🔴 阻力位</Text>
            <Text style={styles.levelValue}>${analysis?.resistance?.toFixed(5)}</Text>
          </View>
        </View>

        <View style={styles.levelsContainer}>
          <View style={[styles.levelBox, styles.supportBox]}>
            <Text style={styles.levelLabel}>🟢 强支撑</Text>
            <Text style={styles.levelValue}>${analysis?.major_support?.toFixed(5)}</Text>
          </View>
          <View style={[styles.levelBox, styles.resistanceBox]}>
            <Text style={styles.levelLabel}>🔴 强阻力</Text>
            <Text style={styles.levelValue}>${analysis?.major_resistance?.toFixed(5)}</Text>
          </View>
        </View>

        {/* Indicators */}
        <View style={styles.indicatorsRow}>
          <IndicatorPill label="换手率" value={`${analysis?.key_indicators?.vol_mcap_ratio}%`} />
          <IndicatorPill label="链上TX" value={analysis?.key_indicators?.transactions_24h?.toLocaleString()} />
          <IndicatorPill label="Mempool" value={analysis?.key_indicators?.mempool_txs?.toLocaleString()} />
        </View>
      </View>

      {/* Historical context */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📜 历史对比</Text>
        <View style={styles.grid}>
          <MetricBox label="ATH" value={`$${price?.ath_usd?.toFixed(4) || "-"}`} />
          <MetricBox label="距ATH" value={`${price?.ath_usd ? ((price.price_usd / price.ath_usd - 1) * 100).toFixed(0) : "-"}%`} color="#f44336" />
          <MetricBox label="ATL" value={`$${price?.atl_usd?.toFixed(6) || "-"}`} />
          <MetricBox label="距ATL" value={`${price?.atl_usd ? ((price.price_usd / price.atl_usd - 1) * 100).toFixed(0) : "-"}%`} color="#4caf50" />
        </View>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          数据来源: CoinGecko + Blockchair{"\n"}
          自动更新 · 仅供参考 · 不构成投资建议
        </Text>
      </View>
    </ScrollView>
  );
}

// ── Sub-components ────────────────────────────────────

function MetricBox({ label, value, color }) {
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

function IndicatorPill({ label, value }) {
  return (
    <View style={styles.pill}>
      <Text style={styles.pillLabel}>{label}</Text>
      <Text style={styles.pillValue}>{value}</Text>
    </View>
  );
}

function formatLargeNum(num) {
  if (!num) return "-";
  if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
  if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
  if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
  return `$${num.toFixed(2)}`;
}

// ── Styles ────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f0f23",
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#0f0f23",
    padding: 24,
  },
  loadingText: {
    color: "#888",
    marginTop: 12,
    fontSize: 16,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  errorText: {
    color: "#f44336",
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 8,
  },
  errorDetail: {
    color: "#888",
    fontSize: 14,
    textAlign: "center",
  },
  errorHint: {
    color: "#f5a623",
    marginTop: 16,
    fontSize: 14,
  },

  // Header
  header: {
    alignItems: "center",
    paddingVertical: 20,
  },
  headerEmoji: {
    fontSize: 48,
  },
  headerTitle: {
    color: "#f5a623",
    fontSize: 24,
    fontWeight: "800",
    marginTop: 8,
  },
  headerDate: {
    color: "#888",
    fontSize: 13,
    marginTop: 4,
  },

  // Cards
  card: {
    backgroundColor: "#1a1a2e",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#2a2a4a",
  },
  cardTitle: {
    color: "#f5a623",
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 12,
  },

  // Price
  priceRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
  },
  priceValue: {
    color: "#fff",
    fontSize: 36,
    fontWeight: "800",
    flex: 1,
  },
  changeBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  changeText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },

  // Grid
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginBottom: 4,
  },
  metricBox: {
    width: (SCREEN_WIDTH - 64) / 4,
    paddingVertical: 8,
    alignItems: "center",
  },
  metricLabel: {
    color: "#888",
    fontSize: 11,
    marginBottom: 4,
  },
  metricValue: {
    color: "#e0e0e0",
    fontSize: 14,
    fontWeight: "600",
  },

  // Phase
  phaseBox: {
    backgroundColor: "rgba(245,166,35,0.15)",
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "rgba(245,166,35,0.3)",
  },
  phaseText: {
    color: "#f5a623",
    fontSize: 16,
    fontWeight: "700",
    textAlign: "center",
  },
  summaryText: {
    color: "#ccc",
    fontSize: 14,
    lineHeight: 22,
    marginBottom: 16,
  },

  // Levels
  levelsContainer: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 8,
  },
  levelBox: {
    flex: 1,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
  },
  supportBox: {
    backgroundColor: "rgba(76,175,80,0.1)",
    borderWidth: 1,
    borderColor: "rgba(76,175,80,0.2)",
  },
  resistanceBox: {
    backgroundColor: "rgba(244,67,54,0.1)",
    borderWidth: 1,
    borderColor: "rgba(244,67,54,0.2)",
  },
  levelLabel: {
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 4,
    color: "#ccc",
  },
  levelValue: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "800",
  },

  // Indicators
  indicatorsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 8,
  },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 6,
  },
  pillLabel: {
    color: "#888",
    fontSize: 12,
  },
  pillValue: {
    color: "#e0e0e0",
    fontSize: 13,
    fontWeight: "600",
  },

  // Footer
  footer: {
    alignItems: "center",
    paddingVertical: 20,
  },
  footerText: {
    color: "#555",
    fontSize: 12,
    textAlign: "center",
    lineHeight: 18,
  },
});
