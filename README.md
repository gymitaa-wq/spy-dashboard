# SPY Put Selling Dashboard

一个基于 Streamlit 的期权数据分析仪表板，支持 Google OAuth 登录认证。

## 功能特性

- 📊 **多标的支持**：SPY、QQQ、TSLA、IBIT 等标的的期权数据
- 🎯 **智能筛选**：自动寻找目标 Moneyness（0.85, 0.90, 0.92, 0.93, 0.95）最近的合约
- 📈 **关键指标**：年化收益率、Premium、Open Interest 等
- 🔐 **Google 登录**：使用 Google OAuth 2.0 进行安全认证
- 👥 **访问控制**：支持基于邮箱域名或特定邮箱的访问限制
- 💾 **数据导出**：支持 CSV 格式导出

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Google OAuth

#### 2.1 创建 Google Cloud 项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 **Google+ API** 和 **People API**

#### 2.2 创建 OAuth 2.0 客户端 ID

1. 进入 **APIs & Services** > **Credentials**
2. 点击 **Create Credentials** > **OAuth client ID**
3. 选择应用类型：**Web application**
4. 配置授权重定向 URI：
   - 本地开发：`http://localhost:8501`
   - 生产环境：`https://your-domain.com`
5. 保存 **Client ID** 和 **Client Secret**

#### 2.3 配置 Streamlit Secrets

创建 `.streamlit/secrets.toml` 文件（参考 `.streamlit/secrets.toml.example`）：

```toml
[google_oauth]
client_id = "your-client-id.apps.googleusercontent.com"
client_secret = "your-client-secret"
redirect_uri = "http://localhost:8501"

# 可选：限制访问域名
allowed_domains = []

# 可选：限制特定邮箱
allowed_emails = []
```

**注意**：`.streamlit/secrets.toml` 已添加到 `.gitignore`，不会被提交到 Git。

### 3. 运行应用

```bash
streamlit run dashboard.py
```

应用将在 `http://localhost:8501` 启动。

## 访问控制配置

### 允许所有 Google 账号

```toml
[google_oauth]
client_id = "..."
client_secret = "..."
redirect_uri = "http://localhost:8501"
allowed_domains = []
allowed_emails = []
```

### 限制特定域名

```toml
[google_oauth]
client_id = "..."
client_secret = "..."
redirect_uri = "http://localhost:8501"
allowed_domains = ["company.com", "example.com"]
allowed_emails = []
```

### 限制特定邮箱

```toml
[google_oauth]
client_id = "..."
client_secret = "..."
redirect_uri = "http://localhost:8501"
allowed_domains = []
allowed_emails = ["user1@gmail.com", "user2@company.com"]
```

## 项目结构

```
spy-dashboard/
├── dashboard.py              # 主应用文件
├── auth.py                   # Google OAuth 认证模块
├── requirements.txt          # Python 依赖
├── .streamlit/
│   └── secrets.toml.example # 配置模板
└── README.md                # 项目文档
```

## 技术栈

- **Streamlit**：Web 应用框架
- **yfinance**：Yahoo Finance 数据获取
- **pandas**：数据处理
- **google-auth-oauthlib**：Google OAuth 认证
- **google-api-python-client**：Google API 客户端

## 使用说明

### 1. 登录

首次访问时，点击 "使用 Google 账号登录" 按钮，授权应用访问您的 Google 账号信息。

### 2. 设置参数

在侧边栏设置：
- **Min DTE**：最小到期天数
- **Max DTE**：最大到期天数

### 3. 查看数据

切换不同标的的 Tab（SPY、QQQ、TSLA、IBIT），点击 "刷新数据" 按钮获取最新期权数据。

### 4. 导出数据

点击 "下载 CSV" 按钮导出当前标的的期权数据。

### 5. 登出

点击侧边栏底部的 "登出" 按钮退出登录。

## 安全注意事项

1. **不要提交 secrets.toml**：此文件包含敏感信息，已添加到 `.gitignore`
2. **使用 HTTPS**：生产环境务必使用 HTTPS
3. **定期更新依赖**：保持依赖包为最新版本
4. **限制访问权限**：根据需要配置 `allowed_domains` 或 `allowed_emails`

## 部署到生产环境

### Streamlit Cloud

1. 将代码推送到 GitHub
2. 在 [Streamlit Cloud](https://streamlit.io/cloud) 创建应用
3. 在 Streamlit Cloud 的 Secrets 管理中添加配置
4. 更新 Google OAuth 重定向 URI 为生产环境 URL

### 其他平台

确保在部署平台的环境变量或 secrets 管理中配置 Google OAuth 凭证。

## 常见问题

### Q: 登录后显示 "您没有访问权限"

A: 检查 `allowed_domains` 或 `allowed_emails` 配置，确保您的邮箱在允许列表中。

### Q: 登录后页面一直刷新

A: 检查 `redirect_uri` 是否与实际访问的 URL 一致（包括端口号）。

### Q: 无法获取期权数据

A: Yahoo Finance API 可能有访问限制，请稍后重试或检查网络连接。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请在 GitHub 上提交 Issue。
