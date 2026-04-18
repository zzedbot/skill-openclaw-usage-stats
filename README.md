# OpenClaw Usage Stats 技能文档

## 快速开始

### 1. 统计数据

```bash
# 统计本周数据
python3 scripts/estimate_tokens.py --days $(($(date +%u))) --output data.json
```

### 2. 合并词汇数据 ⚠️

**重要**：`estimate_tokens.py` 不会自动收集词汇数据，必须手动合并！

```bash
# 方式 1：使用 Python 脚本合并
python3 -c "
import json
with open('data.json', 'r') as f:
    data = json.load(f)
with open('word_frequency_by_day.json', 'r') as f:
    word_freq = json.load(f)
data['word_frequency_by_day'] = word_freq
with open('data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
"

# 方式 2：使用文本报告生成器（自动合并）
python3 scripts/generate_text_report.py --data data.json --output report.txt
```

### 3. 生成报告

```bash
# HTML 可视化报告
python3 scripts/generate_report.py --data data.json --output report.html --version v2

# 文本报告（适合群聊推送）
python3 scripts/generate_text_report.py --data data.json --output report.txt

# Markdown 报告
python3 scripts/generate_text_report.py --data data.json --format markdown --output report.md
```

### 4. 推送到群聊（可选）

```bash
# 配置推送
cp conf/push.conf.example conf/push.conf
# 编辑 conf/push.conf，填入 yzjtoken

# 生成并推送
python3 scripts/generate_text_report.py --data data.json --push
```

## 定时任务

### OpenClaw Cron（推荐）

```bash
# 查看定时任务
openclaw cron list

# 手动触发
openclaw cron run <job-id>

# 查看历史
openclaw cron runs --id <job-id>
```

### 定时任务流程

```
每天 17:30
    ↓
1. 统计本周数据（estimate_tokens.py）
    ↓
2. 合并词汇数据 ⚠️
    ↓
3. 生成文本报告（generate_text_report.py）
    ↓
4. 推送到云之家群聊
    ↓
5. 记录日志到 /tmp/openclaw_daily_push.log
```

## 常见问题

### Q: 为什么高频词汇没有显示？

**A**: 因为 `estimate_tokens.py` 不会自动收集词汇数据！

**解决方案**：
1. 确保 `word_frequency_by_day.json` 文件存在
2. 在生成报告前合并词汇数据（见步骤 2）
3. 或者直接使用 `generate_text_report.py`（会自动合并）

### Q: 如何查看本周数据？

**A**: 使用 `--days $(($(date +%u)))` 参数：
```bash
# 今天是周四，收集 4 天数据（本周一到今天）
python3 scripts/estimate_tokens.py --days $(($(date +%u))) --output data.json
```

### Q: 推送失败怎么办？

**A**: 检查以下几点：
1. `conf/push.conf` 中 `PUSH_URL` 是否正确
2. `PUSH_ENABLED` 是否设为 `true`
3. 查看日志：`tail -20 /tmp/openclaw_daily_push.log`

## 文件结构

```
openclaw-usage-stats/
├── scripts/
│   ├── estimate_tokens.py       # 数据统计
│   ├── generate_report.py       # HTML 报告生成
│   ├── generate_text_report.py  # 文本报告生成（自动合并词汇）
│   ├── daily_push.sh            # 定时推送脚本
│   └── quick-report.py          # 一键部署
├── conf/
│   ├── push.conf                # 推送配置
│   └── push.conf.example        # 配置示例
├── assets/
│   ├── libs/                    # 本地 JS 库
│   └── report_template_v2.html  # HTML 模板
├── openclaw-usage-stats-workspace/
│   ├── latest/                  # 最新数据
│   │   ├── estimated_tokens.json
│   │   ├── report.txt
│   │   └── report.md
│   └── word_frequency_by_day.json  # 词汇数据
└── SKILL.md                     # 技能说明
```

## 数据说明

### 统计维度

- **agent × 天**: 每天的调用次数和 Token 用量
- **agent × 小时**: 每小时调用分布
- **agent × 天 × 小时**: 三维统计（用于热力图）
- **agent × 天 × 词汇**: 每天的热门词汇 Top 10

### 时间范围计算

```bash
# 本周：本周一到今天
DAY_OF_WEEK=$(date +%u)  # 1=周一，7=周日
DAYS=$((DAY_OF_WEEK))    # 从本周一到今天

# 上周：上周一到上周日
# 上月：上月 1 日到上月末
```

## 更新日志

- 2026-04-16: 添加词汇数据合并说明 ⚠️
- 2026-04-16: 添加 OpenClaw Cron 定时任务配置
- 2026-04-16: 添加推送功能
- 2026-04-15: 添加文本报告生成
- 2026-04-14: 初始版本
