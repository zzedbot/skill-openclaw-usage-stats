#!/bin/bash
# OpenClaw Usage Stats - 每日定时推送脚本（本周数据）
# 流程：统计数据 → 等待完成 → 生成报告 → 推送到群聊

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/../openclaw-usage-stats-workspace"
CONF_DIR="$SCRIPT_DIR/../conf"

# 日志文件
LOG_FILE="/tmp/openclaw_daily_push.log"

echo "" >> "$LOG_FILE"
echo "=== OpenClaw 每日推送 $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"

# 收集 62 天完整数据（支持前端本周/上周/本月/上月筛选）
DAYS_TO_COLLECT=62

echo "今天：$(date '+%Y-%m-%d')" >> "$LOG_FILE"
echo "统计范围：${DAYS_TO_COLLECT} 天完整数据（支持本周/上周/本月/上月筛选）" >> "$LOG_FILE"

# 确保数据目录存在
mkdir -p "$DATA_DIR/latest"

# ============================================
# 步骤 1: 统计最新数据（62 天完整数据，用于前端报告）
# ============================================
echo "" >> "$LOG_FILE"
echo "【步骤 1/4】统计 62 天完整数据（前端报告）..." >> "$LOG_FILE"

python3 "$SCRIPT_DIR/estimate_tokens.py" \
  --days ${DAYS_TO_COLLECT} \
  --output "$DATA_DIR/latest/estimated_tokens.json" \
  >> "$LOG_FILE" 2>&1

STATS_EXIT_CODE=$?

if [ $STATS_EXIT_CODE -ne 0 ]; then
  echo "❌ 数据统计失败 (退出码：$STATS_EXIT_CODE)" >> "$LOG_FILE"
  exit 1
fi

echo "✅ 62 天数据统计完成" >> "$LOG_FILE"

# ============================================
# 步骤 2: 统计本周数据（用于推送消息）
# ============================================
echo "" >> "$LOG_FILE"
echo "【步骤 2/4】统计本周数据（推送消息）..." >> "$LOG_FILE"

python3 "$SCRIPT_DIR/estimate_tokens.py" \
  --range week \
  --output "$DATA_DIR/latest/weekly_report.json" \
  >> "$LOG_FILE" 2>&1

WEEKLY_EXIT_CODE=$?

if [ $WEEKLY_EXIT_CODE -ne 0 ]; then
  echo "❌ 本周数据统计失败 (退出码：$WEEKLY_EXIT_CODE)" >> "$LOG_FILE"
  exit 1
fi

echo "✅ 本周数据统计完成" >> "$LOG_FILE"

# ============================================
# 步骤 3: 生成 HTML 报告（使用 62 天数据）
# ============================================
echo "" >> "$LOG_FILE"
echo "【步骤 3/4】生成 HTML 报告..." >> "$LOG_FILE"

python3 "$SCRIPT_DIR/generate_report.py" \
  --data "$DATA_DIR/latest/estimated_tokens.json" \
  --output "$DATA_DIR/latest/report.html" \
  --title "Agent 使用报告" \
  --version v2 \
  >> "$LOG_FILE" 2>&1

REPORT_EXIT_CODE=$?

if [ $REPORT_EXIT_CODE -ne 0 ]; then
  echo "❌ 报告生成失败 (退出码：$REPORT_EXIT_CODE)" >> "$LOG_FILE"
  exit 1
fi

# 部署到 Nginx
cp "$DATA_DIR/latest/report.html" /var/www/openclaw-reports/index.html
chmod 644 /var/www/openclaw-reports/index.html

echo "✅ HTML 报告已生成并部署" >> "$LOG_FILE"

# ============================================
# 步骤 4: 生成推送报告并推送（使用本周数据）
# ============================================
echo "" >> "$LOG_FILE"
echo "【步骤 4/4】生成推送报告并推送..." >> "$LOG_FILE"

python3 "$SCRIPT_DIR/generate_text_report.py" \
  --data "$DATA_DIR/latest/weekly_report.json" \
  --push \
  --config "$CONF_DIR/push.conf" \
  >> "$LOG_FILE" 2>&1

PUSH_EXIT_CODE=$?

if [ $PUSH_EXIT_CODE -eq 0 ]; then
  echo "✅ 推送成功" >> "$LOG_FILE"
  echo "========================================" >> "$LOG_FILE"
  exit 0
else
  echo "❌ 推送失败 (退出码：$PUSH_EXIT_CODE)" >> "$LOG_FILE"
  echo "========================================" >> "$LOG_FILE"
  exit 1
fi
