# 🐕 DOGE Monitor

Dogecoin 链上数据自动监测工具。GitHub Actions 每 12 小时自动抓取数据，推送到手机 APP。

## 架构

```
GitHub Actions (定时) → Python 脚本 → CoinGecko + Blockchair API
                                    ↓
                              public/latest.json
                                    ↓
                          Expo App ← 读取 JSON
                                    ↓
                          Expo Push 通知 → 手机
```

## 快速开始

### 1. 部署到 GitHub

```bash
# 替换成你的 GitHub 用户名
export GITHUB_USER="YOUR_USERNAME"

# 创建 GitHub 仓库
gh repo create doge-monitor --public --push --source .

# 启用 GitHub Pages (Settings → Pages → Source: main branch, /docs → 或直接用 raw URL)
```

### 2. 修改报告 URL

编辑 `app/app.json`，把 `YOUR_USERNAME` 替换成你的 GitHub 用户名：

```json
"extra": {
  "reportUrl": "https://raw.githubusercontent.com/你的用户名/doge-monitor/main/public/latest.json"
}
```

编辑 `app/src/screens/ReportScreen.js`，同样替换 `YOUR_USERNAME`。

### 3. 运行手机 App

```bash
cd app
npm install
npx expo start
```

手机安装 **Expo Go**，扫码即可运行。

### 4. 启用推送通知（可选）

1. 在真机上打开 App，进入「设置」标签
2. 复制 Expo Push Token
3. 在 GitHub 仓库 → Settings → Secrets and variables → Actions → 新建 Secret：
   - Name: `EXPO_PUSH_TOKEN`
   - Value: 粘贴刚才复制的 Token
4. 下次 GitHub Actions 运行时自动推送

## 项目结构

```
doge-monitor/
├── .github/workflows/
│   └── fetch-and-notify.yml    # 定时任务配置
├── scripts/
│   ├── fetch_data.py           # 数据抓取脚本
│   ├── send_push.py            # 推送通知脚本
│   └── requirements.txt
├── public/
│   └── latest.json             # 最新报告（自动生成）
├── reports/                    # 历史报告（自动生成）
├── push_tokens.json            # Push Token 列表
├── app/                        # Expo React Native App
│   ├── App.js
│   ├── app.json
│   ├── package.json
│   └── src/screens/
│       ├── ReportScreen.js
│       └── SettingsScreen.js
└── README.md
```

## 数据来源

| 数据 | 来源 | 限制 |
|------|------|------|
| 价格、市值、成交量 | [CoinGecko API](https://www.coingecko.com/en/api) | 免费，每分钟 10-30 次 |
| 链上交易、算力 | [Blockchair API](https://blockchair.com/api) | 免费，每天 ~2k 次 |

## 免责声明

⚠️ 本工具仅供个人学习参考，**不构成任何投资建议**。加密货币波动剧烈，请理性投资，风险自担。
