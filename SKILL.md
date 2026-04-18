---
name: openclaw-usage-stats
description: 统计 OpenClaw 中所有 agent 的使用情况并生成可视化报告。当用户提到查看 agent 使用情况、生成使用报告、统计调用、查看使用趋势、agent 使用分析、使用统计、调用次数、token 用量等场景时触发此技能。支持自定义时间范围和历史趋势对比。
---

# OpenClaw Usage Stats - Agent 使用情况统计

这个技能用于统计 OpenClaw 中所有 agent 的使用情况，生成可视化的 HTML 报告。

## 何时使用

当用户想要：
- 查看 agent 的使用情况
- 生成使用报告
- 统计调用次数或 token 用量
- 分析 agent 使用趋势
- 对比不同时间段的使用情况

## 目标 Agent

**自动获取 agent 列表**：
- 技能会自动扫描 `/root/.openclaw/agents/` 目录
- 获取所有可用的 agent 名称
- 无需手动维护 agent 列表

**排除 `main` agent**：
- `main` 是 OpenClaw 核心 agent，处理所有用户交互和系统任务
- 其调用量远超其他 agent，会扭曲使用统计的对比分析
- 默认统计除 `main` 之外的所有 agent

**示例**：
- 如果 `/root/.openclaw/agents/` 包含：`main`, `agent1`, `agent2`, `agent3`
- 则统计：`agent1`, `agent2`, `agent3`（排除 main）

如需修改排除规则，编辑 `scripts/collect_data.py` 或 `scripts/estimate_tokens.py` 中的 `EXCLUDED_AGENTS` 变量。

## 工作流程

### 1. 确定时间范围

首先确认用户想要统计的时间范围：
- 如果用户指定了日期范围，使用该范围
- 如果用户说"今天"，使用当天 00:00 到当前时间
- 如果用户说"昨天"，使用前一天的 00:00 到 23:59
- 如果用户说"本周"，使用本周一到当前时间
- 如果用户说"上周"，使用上周一到上周日
- 如果用户说"本月"，使用本月 1 日到当前时间
- 默认：如果用户没有指定，询问用户想要统计的时间范围

### 2. 获取会话列表

有两种方式获取会话数据：

**方式 A：从文件系统读取（推荐，更准确）**

直接读取 `/root/.openclaw/agents/{agent_name}/sessions/` 目录下的 `.jsonl` 文件：

```bash
# 列出所有 agent 目录
ls /root/.openclaw/agents/

# 获取某个 agent 的会话文件
ls /root/.openclaw/agents/{agent_name}/sessions/*.jsonl
```

**方式 B：使用 sessions_list 工具**

使用 `sessions_list` 工具获取会话列表。根据需要设置过滤参数：
- `activeMinutes`: 根据时间范围计算（例如：24 小时 = 1440 分钟）
- `limit`: 设置合理的上限（默认 100，可根据需要调整）
- `messageLimit`: 每个会话获取的最后消息数（默认 1）

### 3. 获取会话详情

**从 JSONL 文件提取数据：**

解析 JSONL 文件，提取以下信息：
- agent 名称（从目录名自动获取）
- 消息时间戳
- token 使用量（usage.totalTokens）
- 会话开始/结束时间

**使用 sessions_history（可选）：**

对每个会话使用 `sessions_history` 获取详细信息：
- `sessionKey`: 从 sessions_list 获取
- `limit`: 获取的消息数量（根据需求设置）
- `includeTools`: 设为 `true` 以获取工具调用信息

### 4. 聚合统计数据

按 agent 聚合以下指标：
- **调用次数**: 该 agent 被调用的总次数
- **总 token 用量**: 输入 + 输出 token 总和
- **平均 token 用量**: 每次调用的平均 token 数
- **会话持续时间**: 从第一次到最后一次调用的时间差
- **时间分布**: 按小时/天统计调用分布

### 5. 生成 HTML 报告

使用 `assets/report_template.html` 模板生成可视化报告，包含：
- 总体统计摘要卡片
- 各 agent 调用次数柱状图
- Token 用量对比图
- 时间趋势折线图
- 详细数据表格

### 6. 输出报告

将生成的 HTML 报告保存并告知用户文件位置，或直接展示关键统计数据。

## 数据提取指南

### 从 sessions_list 获取

```json
{
  "sessionKey": "唯一标识",
  "label": "会话标签",
  "lastMessage": {
    "timestamp": "时间戳",
    "role": "user/assistant"
  }
}
```

### 从 sessions_history 获取

```json
{
  "messages": [
    {
      "role": "user/assistant",
      "timestamp": "时间戳",
      "content": "消息内容",
      "toolCalls": [...]
    }
  ]
}
```

### 从 session_status 获取（可选）

如果需要更详细的 token 和成本信息，可以对每个会话调用 `session_status`。

## 输出格式

### HTML 报告结构

报告应包含以下部分：

1. **摘要卡片**
   - 总会话数
   - 总调用次数
   - 总 token 用量
   - 时间范围

2. **Agent 排名**
   - 按调用次数排序
   - 按 token 用量排序

3. **趋势图表**
   - 每日调用趋势
   - 每小时分布热力图

4. **详细表格**
   - 每个 agent 的详细统计

## 脚本工具

### 数据收集

**从文件系统收集真实调用数据**：
```bash
python3 scripts/collect_data.py \
  --days 62 \
  --output data.json
```

**估算 Token 用量（当 API 不返回真实数据时）**：
```bash
python3 scripts/estimate_tokens.py \
  --days 62 \
  --output estimated_tokens.json
```

估算原理：
- 分析 JSONL 文件大小与内容字符数的关系
- 公式：`token ≈ 文件大小 × 0.35 ÷ 2.0`
- 准确度：粗略估算，±30% 偏差

### 📋 数据收集范围要求

**为确保前端报告的时间范围筛选器正常工作，建议收集至少 62 天的完整历史数据。**

| 参数 | 说明 | 适用场景 |
|------|------|---------|
| `--days 62` | 收集 62 天完整数据 | **推荐**：支持前端本周/上周/本月/上月筛选 |
| `--range week` | 仅收集本周一到今天 | 临时统计，前端筛选受限 |
| `--range month` | 仅收集本月 1 日到今天 | 临时统计，前端筛选受限 |
| `--start/--end` | 自定义日期范围 | 特定时间段分析 |

**为什么需要 62 天？**
- 前端报告提供"本周/上周/本月/上月"四种预设筛选
- 如果只收集本周数据，"上周"和"上月"筛选将无数据可显示
- 62 天 ≈ 2 个月，可覆盖所有预设时间范围

**定时任务配置**：
- 使用 `daily_push.sh` 脚本，每日自动收集 62 天数据
- 或配置 OpenClaw cron 每天执行一次

### 生成报告

```bash
python scripts/generate_report.py \
  --data <json_data_file> \
  --output <output_html_path> \
  --title "Agent 使用报告 - <日期范围>"
```

### 一键部署

```bash
python3 scripts/quick-report.py --days 7 --deploy
```

### 生成文本报告

```bash
# 纯文本格式（适合微信/钉钉/飞书群聊）
python3 scripts/generate_text_report.py \
  --data estimated_tokens.json \
  --output report.txt

# Markdown 格式（适合支持 Markdown 的平台）
python3 scripts/generate_text_report.py \
  --data estimated_tokens.json \
  --format markdown \
  --output report.md
```

### 📱 推送到群聊

**默认推送本周数据**：
- 使用 `daily_push.sh` 脚本每日自动推送
- 脚本会生成两份数据：
  - **62 天完整数据** → 用于前端 HTML 报告（支持所有时间范围筛选）
  - **本周数据** → 用于推送消息（显示"本周"统计）
- 推送消息标题自动显示为"**本周**"（本周一到今天）

**自动时间范围标签**：
- 脚本会自动检测数据对应的时间范围
- 显示为"本周"、"本月"、"上周"、"上月"或"过去 X 天"
- 日期范围与前端报表保持一致（按前端 JS 逻辑计算）

**手动指定时间范围标签**：
```bash
# 强制显示为特定标签
python3 scripts/generate_text_report.py \
  --data estimated_tokens.json \
  --label "本周" \
  --push
```

**推送消息包含完整报告链接**：
- 每条推送消息末尾会自动添加完整 HTML 报告的链接
- 链接地址：`https://yunzhijiachannel.kingdee.space/reports/`
- 用户可以点击链接查看详细的可视化图表（热力图、趋势图、词汇图等）

**示例输出**：
```
📊 *OpenClaw Agent 使用情况报告*
_本周 (2026-04-13 ~ 2026-04-16)_

*【总体统计】*
• 总会话数：21
• 总调用次数：619
• 总 Token 用量：824.3K

*【Agent 排名】*
🥇 *agent1*: 185 次调用，143.9K
🥈 *agent2*: 183 次调用，281.9K
...
```

## 部署配置

报告默认生成在本地文件系统，可通过 Nginx 对外提供 HTTPS 访问：

- **Nginx 配置**: `/etc/nginx/sites-available/yunzhijiachannel.kingdee.space`
- **报告目录**: `/var/www/openclaw-reports/`
- **访问 URL**: `https://yunzhijiachannel.kingdee.space/reports/`

### 推送配置

推送相关的敏感信息存放在 `conf/push.conf` 配置文件中：

```ini
# 云之家 webhook 地址
PUSH_URL="https://www.yunzhijia.com/gateway/robot/webhook/send?yzjtype=0&yzjtoken=xxx"
PUSH_ENABLED=true

# 完整 HTML 报告地址（推送消息末尾会添加此链接）
REPORT_URL="https://yunzhijiachannel.kingdee.space/reports/"

# 推送标签（显示在推送消息开头）
PUSH_LABEL="OpenClaw Usage Report"
```

**配置说明**：
- `PUSH_URL`: 云之家 webhook 地址（包含 token，请妥善保管）
- `PUSH_ENABLED`: 是否启用推送（`true`/`false`）
- `REPORT_URL`: 完整 HTML 报告地址，推送消息末尾会添加此链接
- `PUSH_LABEL`: 推送消息的标签/标题

**安全建议**：
- 将 `conf/push.conf` 加入 `.gitignore`，避免 token 泄露
- 使用 `conf/push.conf.example` 模板文件（不含真实 token）进行版本控制

部署步骤：
1. 将生成的 HTML 报告复制到 `/var/www/openclaw-reports/`
2. 确保文件权限正确：`chmod 644 /var/www/openclaw-reports/*.html`
3. 重载 Nginx: `systemctl reload nginx`

## 注意事项

### 📁 文件过滤策略

**包含 reset 和 deleted 文件**：

脚本会处理所有 `.jsonl*` 文件，包括：
- `.jsonl` - 正常会话文件
- `.jsonl.reset.*` - 已重置的会话（包含历史数据）
- `.jsonl.deleted.*` - 已删除的会话（包含历史数据）

原因：reset 和 deleted 文件包含真实的用户交互历史，是完整使用统计的一部分。

### ⚠️ 重要：词汇数据需要手动合并

**问题**：`estimate_tokens.py` **不会自动收集词汇数据**，只统计调用次数和 Token 用量。

**解决方案**：生成报告前必须手动合并词汇数据：

```python
import json

# 读取主数据
with open('estimated_tokens.json', 'r') as f:
    data = json.load(f)

# 读取词汇数据
with open('word_frequency_by_day.json', 'r') as f:
    word_freq = json.load(f)

# 合并数据
data['word_frequency_by_day'] = word_freq

# 保存
with open('estimated_tokens.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

**或者使用文本报告生成器自动合并**：
```bash
python3 scripts/generate_text_report.py   --data estimated_tokens.json   --output report.txt
# 该脚本会自动检测并合并词汇数据
```

**定时任务已包含合并步骤**：
- `daily_push.sh` 脚本会在统计后自动合并词汇数据
- OpenClaw Cron 任务会自动执行完整流程

### 其他注意事项

- 大量会话时注意 API 调用频率，避免触发限流
- 时间范围过大时建议分批次处理
- 敏感数据（如 token 用量、成本）可能需要权限验证
- HTML 报告中的图表使用 Chart.js

## 示例输出

```
📊 Agent 使用报告 (2026-04-14)

总会话数：156
总调用次数：342
总 Token 用量：1,234,567

Top Agents:
1. main - 120 次调用 (456,789 tokens)
2. subagent - 89 次调用 (345,678 tokens)
3. acp - 67 次调用 (234,567 tokens)

报告已保存至：/path/to/report.html
```
