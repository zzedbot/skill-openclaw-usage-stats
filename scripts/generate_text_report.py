#!/usr/bin/env python3
"""
OpenClaw Usage Stats - Text Report Generator

将可视化报告转换成文本格式，适合推送到群聊中。
"""

import json
import re
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta


def get_frontend_date_range(date_range: str, days: int) -> tuple:
    """计算前端报表的日期范围（与前端 JS 逻辑一致）"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 前端 JS: const dayOfWeek = now.getDay() || 7; (1=周一，7=周日)
    # Python weekday(): 0=周一，6=周日
    # 转换：js_day = (py_weekday + 1) % 7，如果结果=0 则改为 7
    js_day = (today.weekday() + 1) % 7
    if js_day == 0:
        js_day = 7
    
    # 前端本周计算：startDate = today - (dayOfWeek - 1) days
    start_days = js_day - 1
    this_monday = today - timedelta(days=start_days)
    
    # 前端本月计算
    first_day_this_month = today.replace(day=1)
    
    # 判断当前数据属于哪个范围，返回前端计算的日期范围
    parts = date_range.split(' ~ ')
    if len(parts) != 2:
        return date_range, days
    
    start_date = datetime.strptime(parts[0], '%Y-%m-%d')
    end_date = datetime.strptime(parts[1], '%Y-%m-%d')
    
    # 检查是否是本周
    is_end_near_today = abs((end_date - today).days) <= 1
    is_start_near_monday = abs((start_date - this_monday).days) <= 3
    
    if is_end_near_today and is_start_near_monday:
        # 返回前端计算的本周范围
        return f"{this_monday.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')}", days
    
    # 检查是否是本月
    if start_date.date() == first_day_this_month.date():
        return f"{first_day_this_month.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')}", days
    
    # 其他情况返回原始范围
    return date_range, days


def get_time_range_label(date_range: str, days: int) -> str:
    """根据日期范围和天数自动判断时间范围标签"""
    # 解析日期范围
    parts = date_range.split(' ~ ')
    if len(parts) != 2:
        return f'过去{days}天'
    
    start_date = datetime.strptime(parts[0], '%Y-%m-%d')
    end_date = datetime.strptime(parts[1], '%Y-%m-%d')
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 检查是否是本周（本周一到今天）- 与前端报表逻辑一致
    # 前端逻辑：startDate = today - (dayOfWeek - 1) days, endDate = today
    # Python weekday(): 0=周一，6=周日
    # JS getDay(): 0=周日，1=周一，6=周六
    
    days_since_monday = today.weekday()  # 0=周一，6=周日
    this_monday = today - timedelta(days=days_since_monday)
    
    # 前端计算的本周开始日期
    expected_start = this_monday
    
    # 放宽判断：数据覆盖本周一到今天即可（允许前后各 3 天误差）
    # 因为 estimate_tokens.py --days 7 可能包含上周末
    is_end_near_today = abs((end_date - today).days) <= 1
    is_start_near_monday = abs((start_date - expected_start).days) <= 3
    
    if is_end_near_today and is_start_near_monday:
        return '本周'
    
    # 检查是否是本月（本月 1 日到今天或本月内）
    first_day_this_month = today.replace(day=1)
    if start_date.date() == first_day_this_month.date():
        return '本月'
    
    # 检查是否是上周
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    if start_date.date() == last_monday.date() and end_date.date() == last_sunday.date():
        return '上周'
    
    # 检查是否是上月
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    if start_date.date() == first_day_last_month.date() and end_date.date() == last_day_last_month.date():
        return '上月'
    
    # 默认返回过去 X 天
    return f'过去{days}天'


def generate_text_report(data: dict, time_range_label: str = "最近", report_url: str = None) -> str:
    """
    生成文本格式的报告
    
    Args:
        data: 统计数据字典
        time_range_label: 时间范围标签（如"本周"、"本月"等）
        report_url: 完整 HTML 报告地址（可选，默认使用配置文件中的地址）
    
    Returns:
        格式化的文本报告
    """
    lines = []
    if report_url is None:
        report_url = 'https://yunzhijiachannel.kingdee.space/reports/'
    
    # 标题
    lines.append("📊 *OpenClaw Agent 使用情况报告*")
    lines.append(f"_{time_range_label} ({data['date_range']})_")
    lines.append("")
    
    # 总体统计
    lines.append("*【总体统计】*")
    lines.append(f"• 总会话数：{data['total_sessions']}")
    lines.append(f"• 总调用次数：{data['total_calls']:,}")
    lines.append(f"• 总 Token 用量：{format_tokens(data['total_tokens'])}")
    lines.append(f"• 统计天数：{data['days']} 天")
    lines.append("")
    
    # Agent 排名（显示所有 agent）
    lines.append("*【Agent 排名】*")
    medals = ['🥇', '🥈', '🥉']
    for i, agent in enumerate(data['agents'], 1):
        if i <= 3:
            medal = medals[i-1]
        else:
            medal = f"{i}️⃣"
        lines.append(f"{medal} *{agent['name']}*: {agent['calls']:,} 次调用，{format_tokens(agent['tokens'])}")
    lines.append("")
    
    # 每日趋势（只显示有调用的日期）
    active_days = [d for d in data['daily_trend'] if d['calls'] > 0]
    if active_days:
        lines.append("*【每日趋势】*")
        for day in active_days[-7:]:  # 最近 7 天有调用的日期
            lines.append(f"• {day['date']}: {day['calls']:,} 次")
        lines.append("")
    
    # 小时分布（如果有数据）
    if 'hourly_distribution' in data and any(h > 0 for h in data['hourly_distribution']):
        hourly = data['hourly_distribution']
        peak_hour = hourly.index(max(hourly))
        lines.append("*【活跃时段】*")
        lines.append(f"• 高峰时段：{peak_hour:02d}:00 ({hourly[peak_hour]} 次调用)")
        
        # 显示前 3 个高峰时段
        top_hours = sorted(enumerate(hourly), key=lambda x: -x[1])[:3]
        for hour, count in top_hours:
            lines.append(f"  {hour:02d}:00 - {count} 次")
        lines.append("")
    
    # 高频词汇（如果有数据）
    if 'word_frequency_by_day' in data and data['word_frequency_by_day']:
        # 聚合所有词汇
        all_words = {}
        for v in data['word_frequency_by_day'].values():
            for item in v:
                w = item['word']
                all_words[w] = all_words.get(w, 0) + item['count']
        
        if all_words:
            lines.append("*【高频词汇 Top 10】*")
            top_words = sorted(all_words.items(), key=lambda x: -x[1])[:10]
            for i, (word, count) in enumerate(top_words, 1):
                lines.append(f"{i}. {word}: {count} 次")
            lines.append("")
    
    # 页脚
    lines.append("---")
    lines.append(f"_生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
    lines.append("_数据基于 JSONL 文件大小估算 (±30% 偏差)_")
    lines.append("")
    lines.append(f"📊 *查看完整报告*: {report_url}")
    
    return '\n'.join(lines)


def format_tokens(num: int) -> str:
    """格式化 Token 数字"""
    if num >= 1000000:
        return f"{num / 1000000:.2f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}K"
    else:
        return f"{num}"


def generate_markdown_report(data: dict, time_range_label: str = "最近", report_url: str = None) -> str:
    """
    生成 Markdown 格式的报告（适合支持 Markdown 的聊天平台）
    
    Args:
        data: 统计数据字典
        time_range_label: 时间范围标签（如"本周"、"本月"等）
        report_url: 完整 HTML 报告地址（可选，默认使用配置文件中的地址）
    """
    lines = []
    if report_url is None:
        report_url = 'https://yunzhijiachannel.kingdee.space/reports/'
    
    # 标题
    lines.append("# 📊 OpenClaw Agent 使用情况报告")
    lines.append(f"\n*{time_range_label}* ({data['date_range']})\n")
    
    # 总体统计
    lines.append("## 📈 总体统计\n")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总会话数 | {data['total_sessions']} |")
    lines.append(f"| 总调用次数 | {data['total_calls']:,} |")
    lines.append(f"| 总 Token 用量 | {format_tokens(data['total_tokens'])} |")
    lines.append(f"| 统计天数 | {data['days']} 天 |")
    lines.append("")
    
    # Agent 排名（显示所有 agent）
    lines.append("## 🏆 Agent 排名\n")
    lines.append("| 排名 | Agent | 调用次数 | Token 用量 |")
    lines.append("|------|-------|----------|-----------|")
    for i, agent in enumerate(data['agents'], 1):
        if i <= 3:
            medal = ['🥇', '🥈', '🥉'][i-1]
        else:
            medal = f"{i}️⃣"
        lines.append(f"| {medal} | {agent['name']} | {agent['calls']:,} | {format_tokens(agent['tokens'])} |")
    lines.append("")
    
    # 每日趋势
    active_days = [d for d in data['daily_trend'] if d['calls'] > 0]
    if active_days:
        lines.append("## 📅 每日趋势\n")
        for day in active_days[-14:]:
            emoji = "📈" if day['calls'] > 50 else "📊"
            lines.append(f"{emoji} **{day['date']}**: {day['calls']:,} 次调用")
        lines.append("")
    
    # 高频词汇
    if 'word_frequency_by_day' in data and data['word_frequency_by_day']:
        all_words = {}
        for v in data['word_frequency_by_day'].values():
            for item in v:
                w = item['word']
                all_words[w] = all_words.get(w, 0) + item['count']
        
        if all_words:
            lines.append("## 💬 高频词汇 Top 10\n")
            top_words = sorted(all_words.items(), key=lambda x: -x[1])[:10]
            for i, (word, count) in enumerate(top_words, 1):
                lines.append(f"{i}. **{word}**: {count} 次")
            lines.append("")
    
    # 页脚
    lines.append("---")
    lines.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  ")
    lines.append("*数据基于 JSONL 文件大小估算 (±30% 偏差)*  ")
    lines.append("")
    lines.append(f"📊 **[查看完整报告]({report_url})**")
    
    return '\n'.join(lines)


def load_push_config(config_path: str = None) -> dict:
    """加载推送配置"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "conf" / "push.conf"
    
    config = {
        'PUSH_URL': '',
        'PUSH_ENABLED': False,
        'PUSH_SCHEDULE': '',
        'PUSH_LABEL': 'OpenClaw Usage Report',
        'REPORT_URL': 'https://yunzhijiachannel.kingdee.space/reports/'
    }
    
    if not Path(config_path).exists():
        print(f"⚠️  配置文件不存在：{config_path}")
        return config
    
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == 'PUSH_ENABLED':
                    config[key] = value.lower() == 'true'
                else:
                    config[key] = value
    
    return config


def push_to_yunzhijia(content: str, config: dict) -> bool:
    """推送消息到云之家"""
    if not config.get('PUSH_ENABLED') or not config.get('PUSH_URL'):
        print("⚠️  推送未启用或 URL 未配置")
        return False
    
    # 构建请求数据
    # 云之家 webhook 接收 JSON 格式：{"content": "消息内容"}
    data = json.dumps({'content': content}).encode('utf-8')
    
    try:
        req = urllib.request.Request(
            config['PUSH_URL'],
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = response.read().decode('utf-8')
            
            # 检查响应
            if response.status == 200:
                try:
                    resp_json = json.loads(result)
                    if resp_json.get('code') == 200 or resp_json.get('success'):
                        print(f"✅ 推送成功！")
                        return True
                    else:
                        print(f"❌ 推送失败：{result}")
                        return False
                except json.JSONDecodeError:
                    print(f"✅ 推送成功（响应：{result[:100]}）")
                    return True
            else:
                print(f"❌ 推送失败，HTTP 状态码：{response.status}")
                return False
    
    except urllib.error.HTTPError as e:
        print(f"❌ 推送失败，HTTP 错误：{e.code} {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"❌ 推送失败，网络错误：{e.reason}")
        return False
    except Exception as e:
        print(f"❌ 推送失败，未知错误：{e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='生成文本格式的 Agent 使用报告')
    parser.add_argument('--data', required=True, help='JSON 数据文件路径')
    parser.add_argument('--output', help='输出文件路径（可选）')
    parser.add_argument('--format', choices=['text', 'markdown'], default='text', help='输出格式')
    parser.add_argument('--label', default=None, help='时间范围标签（可选，自动检测）')
    parser.add_argument('--push', action='store_true', help='推送到云之家群聊')
    parser.add_argument('--config', help='推送配置文件路径（可选）')
    
    args = parser.parse_args()
    
    # 读取数据
    with open(args.data, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 自动检测时间范围标签
    if args.label is None:
        args.label = get_time_range_label(data['date_range'], data['days'])
    
    # 使用前端计算的日期范围
    frontend_range, _ = get_frontend_date_range(data['date_range'], data['days'])
    data['date_range'] = frontend_range
    
    # 加载配置（获取报告地址）
    config = load_push_config(args.config)
    report_url = config.get('REPORT_URL', 'https://yunzhijiachannel.kingdee.space/reports/')
    
    # 生成报告
    if args.format == 'markdown':
        report = generate_markdown_report(data, args.label, report_url)
    else:
        report = generate_text_report(data, args.label, report_url)
    
    # 输出
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 报告已保存到：{output_path}")
    else:
        print(report)
    
    # 推送（config 已在上面加载）
    if args.push:
        print(f"\n📱 正在推送到云之家...")
        
        # 添加推送标签
        push_content = f"*{config['PUSH_LABEL']}*\n\n" + report
        push_to_yunzhijia(push_content, config)


if __name__ == '__main__':
    main()
