import React, { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert,
} from "react-native";
import * as Clipboard from "expo-clipboard";
import { Ionicons } from "@expo/vector-icons";

export default function SettingsScreen({ pushToken }) {
  const [copied, setCopied] = useState(false);

  const handleCopyToken = () => {
    if (pushToken) {
      Clipboard.setStringAsync(pushToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      Alert.alert("已复制", "Push Token 已复制到剪贴板。\n\n请前往 GitHub 仓库 → Settings → Secrets → 添加 EXPO_PUSH_TOKEN。");
    }
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
    >
      {/* Header */}
      <View style={styles.header}>
        <Ionicons name="settings" size={48} color="#f5a623" />
        <Text style={styles.headerTitle}>设置</Text>
      </View>

      {/* Push Notification Setup */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🔔 推送通知</Text>

        {pushToken ? (
          <>
            <View style={styles.statusRow}>
              <View style={styles.statusDot} />
              <Text style={styles.statusText}>已注册</Text>
            </View>

            <Text style={styles.tokenLabel}>你的 Expo Push Token:</Text>
            <View style={styles.tokenBox}>
              <Text style={styles.tokenText} numberOfLines={3}>
                {pushToken}
              </Text>
            </View>

            <TouchableOpacity
              style={styles.copyButton}
              onPress={handleCopyToken}
            >
              <Ionicons
                name={copied ? "checkmark-circle" : "copy-outline"}
                size={18}
                color="#1a1a2e"
              />
              <Text style={styles.copyButtonText}>
                {copied ? "已复制" : "复制 Token"}
              </Text>
            </TouchableOpacity>

            <View style={styles.instructionsBox}>
              <Text style={styles.instructionsTitle}>📋 如何启用推送通知：</Text>
              <Text style={styles.instructionsText}>
                1. 点击上方「复制 Token」{"\n"}
                2. 打开你的 GitHub 仓库{"\n"}
                3. 进入 Settings → Secrets and variables → Actions{"\n"}
                4. 新建 Secret: 名称填 EXPO_PUSH_TOKEN{"\n"}
                5. 粘贴刚才复制的 Token{"\n"}
                6. 保存，下次运行时会自动推送
              </Text>
            </View>
          </>
        ) : (
          <View style={styles.noTokenBox}>
            <Ionicons name="warning-outline" size={32} color="#888" />
            <Text style={styles.noTokenText}>
              推送通知仅在真机上可用{"\n"}
              请在真机上运行此 App
            </Text>
          </View>
        )}
      </View>

      {/* Data Source Info */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📡 数据来源</Text>
        <View style={styles.sourceRow}>
          <Text style={styles.sourceLabel}>价格数据</Text>
          <Text style={styles.sourceValue}>CoinGecko API (免费)</Text>
        </View>
        <View style={styles.sourceRow}>
          <Text style={styles.sourceLabel}>链上数据</Text>
          <Text style={styles.sourceValue}>Blockchair API (免费)</Text>
        </View>
        <View style={styles.sourceRow}>
          <Text style={styles.sourceLabel}>更新频率</Text>
          <Text style={styles.sourceValue}>每天 9:00 / 21:00 (北京时间)</Text>
        </View>
        <View style={styles.sourceRow}>
          <Text style={styles.sourceLabel}>运行平台</Text>
          <Text style={styles.sourceValue}>GitHub Actions</Text>
        </View>
      </View>

      {/* About */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>ℹ️ 关于</Text>
        <Text style={styles.aboutText}>
          DOGE Monitor 是一个个人使用的 Dogecoin 链上数据监测工具。
          通过 GitHub Actions 定时抓取数据，推送到手机 APP。
        </Text>
        <Text style={styles.disclaimer}>
          ⚠️ 数据仅供参考，不构成投资建议。加密货币波动剧烈，请理性投资。
        </Text>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>DOGE Monitor v1.0.0</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f0f23",
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  header: {
    alignItems: "center",
    paddingVertical: 20,
  },
  headerTitle: {
    color: "#f5a623",
    fontSize: 24,
    fontWeight: "800",
    marginTop: 8,
  },

  // Card
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

  // Status
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
    gap: 8,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#4caf50",
  },
  statusText: {
    color: "#4caf50",
    fontSize: 14,
    fontWeight: "600",
  },

  // Token display
  tokenLabel: {
    color: "#888",
    fontSize: 13,
    marginBottom: 8,
  },
  tokenBox: {
    backgroundColor: "#0f0f23",
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: "#2a2a4a",
    marginBottom: 12,
  },
  tokenText: {
    color: "#e0e0e0",
    fontSize: 12,
    fontFamily: "monospace",
    lineHeight: 18,
  },
  copyButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#f5a623",
    borderRadius: 10,
    paddingVertical: 12,
    gap: 8,
    marginBottom: 16,
  },
  copyButtonText: {
    color: "#1a1a2e",
    fontSize: 15,
    fontWeight: "700",
  },

  // Instructions
  instructionsBox: {
    backgroundColor: "rgba(66,133,244,0.1)",
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "rgba(66,133,244,0.2)",
  },
  instructionsTitle: {
    color: "#64b5f6",
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 8,
  },
  instructionsText: {
    color: "#bbb",
    fontSize: 13,
    lineHeight: 22,
  },

  // No token
  noTokenBox: {
    alignItems: "center",
    paddingVertical: 20,
    gap: 12,
  },
  noTokenText: {
    color: "#888",
    fontSize: 14,
    textAlign: "center",
    lineHeight: 22,
  },

  // Sources
  sourceRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.05)",
  },
  sourceLabel: {
    color: "#888",
    fontSize: 14,
  },
  sourceValue: {
    color: "#e0e0e0",
    fontSize: 14,
    fontWeight: "500",
  },

  // About
  aboutText: {
    color: "#bbb",
    fontSize: 14,
    lineHeight: 22,
    marginBottom: 12,
  },
  disclaimer: {
    color: "#f5a623",
    fontSize: 13,
    lineHeight: 20,
  },

  // Footer
  footer: {
    alignItems: "center",
    paddingVertical: 20,
  },
  footerText: {
    color: "#555",
    fontSize: 12,
  },
});
