#!/usr/bin/env python3
"""
OpenClaw Usage Stats - Token 估算器

根据 JSONL 文件大小粗略估算 token 用量
（当 API 不返回真实 token 数据时使用）
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

# 目标 agent 列表（自动获取）
AGENTS_BASE_PATH = Path("/root/.openclaw/agents")
EXCLUDED_AGENTS = {"main"}  # 排除的 agent 列表


def get_target_agents():
    """自动获取目标 agent 列表（排除 main）"""
    if not AGENTS_BASE_PATH.exists():
        print(f"⚠️  Agent 目录不存在：{AGENTS_BASE_PATH}")
        return []
    
    all_agents = [d.name for d in AGENTS_BASE_PATH.iterdir() if d.is_dir()]
    target_agents = [a for a in all_agents if a not in EXCLUDED_AGENTS]
    
    print(f"📋 发现 {len(all_agents)} 个 agent，排除 {len(EXCLUDED_AGENTS)} 个，统计 {len(target_agents)} 个")
    print(f"   排除：{', '.join(EXCLUDED_AGENTS)}")
    print(f"   统计：{', '.join(sorted(target_agents))}")
    
    return sorted(target_agents)

# 中文停用词
STOP_WORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '他', '她', '它', '们', '什么', '这个', '那个', '怎么',
    '为什么', '哪里', '谁', '多少', '吗', '吧', '呢', '啊', '哦', '嗯', '哈',
    'the', 'and', 'is', 'in', 'at', 'of', 'to', 'for', 'with', 'on',
    'a', 'an', 'this', 'that', 'it', 'you', 'he', 'she', 'we', 'they',
    'not', 'but', 'or', 'as', 'if', 'when', 'where', 'what', 'which', 'who',
    'from', 'by', 'about', 'into', 'through', 'during', 'before', 'after',
    'sender', 'metadata', 'json', 'label', 'id', 'type', 'true', 'false',
    'null', 'string', 'number', 'array', 'object', 'key', 'value',
    'untrusted', 'conversation', 'info', 'message', 'user', 'new', 'old',
    'set', 'get', 'put', 'post', 'delete', 'create', 'update', 'read', 'write',
    'error', 'warn', 'debug', 'log', 'print', 'test', 'check',
}

# 估算系数
CHAR_RATIO = 0.35      # 内容字符占文件大小的比例
CHARS_PER_TOKEN = 2.0  # 中文场景：1 token ≈ 2 字符


def get_file_date(file_path):
    """从 JSONL 内容第一条记录提取日期"""
    try:
        with open(file_path, 'r') as f:
            first_line = f.readline()
            if first_line:
                entry = json.loads(first_line)
                ts = entry.get('timestamp', '')
                if isinstance(ts, str) and 'T' in ts:
                    mtime = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    mtime = mtime.astimezone(timezone.utc).replace(tzinfo=None)
                    return mtime.strftime('%Y-%m-%d')
    except:
        pass
    return None


def extract_user_text(file_path):
    """从 JSONL 文件中提取用户发送的文本内容"""
    text_parts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'message':
                        msg = entry.get('message', {})
                        if msg.get('role') == 'user':
                            content = msg.get('content', [])
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict):
                                        text = item.get('text', '')
                                        if text:
                                            text_parts.append(text)
                except:
                    continue
    except:
        pass
    return ' '.join(text_parts)


def tokenize(text):
    """简单的中文分词（按字符和英文单词）"""
    # 提取中文词汇（2-6 个字符的连续中文字符）
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
    # 提取英文单词（4+ 字母）
    english_words = re.findall(r'[a-zA-Z]{4,}', text)
    return chinese_words + english_words


def collect_estimated_data(days=None, start_date=None, end_date=None, date_range=None):
    """
    收集指定时间范围内的估算数据
    
    Args:
        days: 统计天数
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        date_range: 预设时间范围 (today/week/month/lastWeek/lastMonth)
    """
    from datetime import timezone
    
    # 计算时间范围
    if date_range:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if date_range == 'today':
            start_dt = today
            end_dt = today + timedelta(days=1)
        elif date_range == 'week':
            days_since_monday = today.weekday()
            start_dt = today - timedelta(days=days_since_monday)
            end_dt = today + timedelta(days=1)
        elif date_range == 'month':
            start_dt = today.replace(day=1)
            end_dt = today + timedelta(days=1)
        elif date_range == 'lastWeek':
            days_since_monday = today.weekday()
            this_monday = today - timedelta(days=days_since_monday)
            last_monday = this_monday - timedelta(days=7)
            start_dt = last_monday
            end_dt = this_monday
        elif date_range == 'lastMonth':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            start_dt = first_day_last_month
            end_dt = first_day_this_month
    elif start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    elif days:
        end_dt = (datetime.now() if not end_date else datetime.strptime(end_date, '%Y-%m-%d')) + timedelta(days=1)
        start_dt = end_dt - timedelta(days=days)
    else:
        # 默认本周
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_since_monday = today.weekday()
        start_dt = today - timedelta(days=days_since_monday)
        end_dt = today + timedelta(days=1)
    
    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()
    
    print(f"📊 估算数据范围：{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
    print(f"⚠️  使用粗略估算：token ≈ 文件大小 × {CHAR_RATIO} ÷ {CHARS_PER_TOKEN}")
    
    # 按 agent 聚合
    agent_stats = defaultdict(lambda: {
        'calls': 0,
        'estimated_tokens': 0,
        'sessions': 0,
        'total_size_bytes': 0
    })
    
    daily_stats = defaultdict(lambda: {'calls': 0, 'estimated_tokens': 0})
    hourly_stats = [0] * 24  # 24 小时分布
    agent_day_stats = defaultdict(lambda: {'calls': 0, 'tokens': 0})  # per-agent per-day
    agent_hourly_stats = defaultdict(lambda: [0] * 24)  # agent_name -> [24 hours]
    agent_day_hourly_stats = defaultdict(lambda: [0] * 24)  # 'agent|date' -> [24 hours]
    agent_day_word_freq = defaultdict(lambda: Counter())  # 'agent|date' -> Counter
    
    total_sessions = 0
    total_estimated_tokens = 0
    total_size = 0
    
    # 自动获取目标 agent 列表
    target_agents = get_target_agents()
    
    for agent_name in target_agents:
        agent_dir = AGENTS_BASE_PATH / agent_name / 'sessions'
        
        if not agent_dir.exists():
            continue
        
        # 收集所有包含 .jsonl 的文件（包括 reset 和 deleted）
        jsonl_files = list(agent_dir.iterdir())
        
        for f in jsonl_files:
            if '.jsonl' not in f.name:
                continue
            
            # 统计文件
            file_size = f.stat().st_size
            estimated_tokens = int(file_size * CHAR_RATIO / CHARS_PER_TOKEN)
            
            # 逐条解析消息，按实际日期归因（修复跨天会话问题）
            file_assistant_calls = 0
            file_has_data_in_range = False
            daily_calls = defaultdict(int)  # date -> calls
            hourly_distribution = [0] * 24
            
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    for line in fh:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            if entry.get('type') == 'message':
                                msg = entry.get('message', {})
                                if msg.get('role') == 'assistant':
                                    file_assistant_calls += 1
                                    # 提取时间戳并转换为北京时间
                                    ts = entry.get('timestamp', '')
                                    if isinstance(ts, str) and 'T' in ts:
                                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                        dt_beijing = dt + timedelta(hours=8)
                                        date_str = dt_beijing.strftime('%Y-%m-%d')
                                        hour = dt_beijing.hour
                                        
                                        # 检查是否在时间范围内
                                        if start_ts <= dt_beijing.timestamp() < end_ts:
                                            file_has_data_in_range = True
                                            daily_calls[date_str] += 1
                                            hourly_distribution[hour] += 1
                        except:
                            continue
            except:
                pass
            
            # 如果没有 assistant 调用或没有数据在时间范围内，跳过此文件
            if file_assistant_calls == 0 or not file_has_data_in_range:
                continue
            
            # 累加数据
            agent_stats[agent_name]['calls'] += file_assistant_calls
            agent_stats[agent_name]['estimated_tokens'] += estimated_tokens
            agent_stats[agent_name]['sessions'] += 1
            agent_stats[agent_name]['total_size_bytes'] += file_size
            
            # 按实际消息日期归因（支持跨天文件）
            for date_str, calls in daily_calls.items():
                # 按比例分配 token（简化：按调用次数比例）
                date_tokens = int(estimated_tokens * calls / file_assistant_calls) if file_assistant_calls > 0 else 0
                daily_stats[date_str]['calls'] += calls
                daily_stats[date_str]['estimated_tokens'] += date_tokens
                
                # agent + 日期聚合
                agent_day_key = f"{agent_name}|{date_str}"
                agent_day_stats[agent_day_key]['calls'] += calls
                agent_day_stats[agent_day_key]['tokens'] += date_tokens
            
            # 累加小时分布
            for hour in range(24):
                hourly_stats[hour] += hourly_distribution[hour]
                agent_hourly_stats[agent_name][hour] += hourly_distribution[hour]
            
            # 填充 agent_day_hourly_stats（热力图需要）
            # 注意：由于我们按日期聚合了调用，这里需要估算每小时的分布
            # 简化处理：将文件的 hourly_distribution 按日期平均分配
            num_dates = len(daily_calls) if daily_calls else 1
            for date_str in daily_calls.keys():
                date_key = f"{agent_name}|{date_str}"
                for hour in range(24):
                    # 按该日期调用数占总调用数的比例分配
                    proportion = daily_calls[date_str] / file_assistant_calls if file_assistant_calls > 0 else 0
                    agent_day_hourly_stats[date_key][hour] += int(hourly_distribution[hour] * proportion)
            
            # 词汇统计（按文件）
            text = extract_user_text(f)
            words = [w.lower() for w in tokenize(text) if w.lower() not in STOP_WORDS]
            for date_str in daily_calls.keys():
                date_key = f"{agent_name}|{date_str}"
                for w in words:
                    agent_day_word_freq[date_key][w] += 1
            
            total_sessions += 1
            total_estimated_tokens += estimated_tokens
            total_size += file_size
    
    # 构建 agents 列表
    agents_list = []
    for agent_name in target_agents:
        stats = agent_stats[agent_name]
        if stats['calls'] > 0:
            agents_list.append({
                'name': agent_name,
                'calls': stats['calls'],
                'tokens': stats['estimated_tokens'],
                'sessions': stats['sessions'],
                'avg_tokens': stats['estimated_tokens'] // stats['calls'] if stats['calls'] > 0 else 0,
                'total_size_kb': round(stats['total_size_bytes'] / 1024, 1),
                'estimation_method': 'file_size'
            })
    
    # 按调用次数排序
    agents_list.sort(key=lambda x: x['calls'], reverse=True)
    
    # 构建每日趋势（包含所有日期，即使调用为 0）
    daily_trend = []
    current = start_dt
    while current < end_dt:
        date_str = current.strftime('%Y-%m-%d')
        daily_trend.append({
            'date': date_str,
            'calls': daily_stats[date_str]['calls'],
            'tokens': daily_stats[date_str]['estimated_tokens']
        })
        current += timedelta(days=1)
    
    # 构建 word_frequency_by_day
    word_frequency_by_day = {}
    for key, counter in agent_day_hourly_stats.items():
        word_freq = agent_day_word_freq.get(key, Counter())
        if word_freq:
            word_frequency_by_day[key] = [{'word': w, 'count': c} for w, c in word_freq.most_common(10)]
    
    return {
        'total_sessions': total_sessions,
        'total_calls': sum(a['calls'] for a in agents_list),
        'total_tokens': total_estimated_tokens,
        'total_size_kb': round(total_size / 1024, 1),
        'total_size_mb': round(total_size / 1024 / 1024, 2),
        'date_range': f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}",
        'days': (end_dt - start_dt).days,
        'agents': agents_list,
        'daily_trend': daily_trend,
        'hourly_distribution': hourly_stats,
        'agent_daily_breakdown': {k: v for k, v in agent_day_stats.items()},
        'agent_hourly_breakdown': {k: list(v) for k, v in agent_hourly_stats.items()},
        'agent_day_hourly_breakdown': {k: list(v) for k, v in agent_day_hourly_stats.items()},
        'word_frequency_by_day': word_frequency_by_day,
        'estimation_info': {
            'method': 'file_size_based',
            'formula': f'tokens ≈ file_size × {CHAR_RATIO} ÷ {CHARS_PER_TOKEN}',
            'accuracy': 'rough_estimate',
            'note': '基于 JSONL 文件大小的粗略估算，实际值可能有±30% 偏差'
        },
        'word_frequency': {},
        'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='根据文件大小估算 token 用量')
    parser.add_argument('--days', type=int, default=None, help='统计天数（从结束日期往前推）')
    parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)，默认今天')
    parser.add_argument('--range', choices=['today', 'week', 'month', 'lastWeek', 'lastMonth'], help='预设时间范围')
    parser.add_argument('--output', required=True, help='输出 JSON 文件路径')
    
    args = parser.parse_args()
    
    # 收集数据
    data = collect_estimated_data(
        days=args.days,
        start_date=args.start,
        end_date=args.end,
        date_range=args.range
    )
    
    # 输出
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据已保存到：{output_path}")
    
    # 显示摘要
    print(f"\n📊 统计摘要:")
    print(f"   总会话数：{data['total_sessions']}")
    print(f"   估算总 token: {data['total_tokens']:,}")
    print(f"   总文件大小：{data['total_size_mb']} MB")
    print(f"\n🏆 Top Agents:")
    for i, agent in enumerate(data['agents'][:5], 1):
        print(f"   {i}. {agent['name']}: {agent['calls']} 次，估算 {agent['tokens']:,} tokens ({agent['total_size_kb']} KB)")
    
    print(f"\n⚠️  注意：这是粗略估算，实际值可能有±30% 偏差")


if __name__ == '__main__':
    main()
