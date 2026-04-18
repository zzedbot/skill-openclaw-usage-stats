#!/usr/bin/env python3
"""
OpenClaw Usage Stats - Data Collector

从文件系统读取 OpenClaw agent 会话数据，生成统计 JSON。
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import re


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


def parse_jsonl_file(file_path: Path) -> list:
    """解析 JSONL 文件，提取消息数据"""
    messages = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"⚠️  读取文件失败 {file_path}: {e}")
    return messages


def extract_session_stats(file_path: Path, agent_name: str) -> dict:
    """从单个会话文件提取统计信息"""
    entries = parse_jsonl_file(file_path)
    
    if not entries:
        return None
    
    # 过滤掉 deleted/reset 的会话
    if '.deleted' in str(file_path) or '.reset' in str(file_path):
        return None
    
    # 提取时间戳和 token 信息
    timestamps = []
    total_tokens = 0
    assistant_calls = 0
    
    for entry in entries:
        entry_type = entry.get('type', '')
        timestamp = entry.get('timestamp', 0)
        
        # 解析时间戳
        ts = None
        if timestamp:
            try:
                # 处理 ISO 格式或数字格式
                if isinstance(timestamp, str) and 'T' in timestamp:
                    # ISO 格式：2026-04-14T02:35:34.338Z
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    ts = dt.timestamp()
                else:
                    ts = float(timestamp)
                    ts = ts / 1000 if ts > 1e12 else ts
            except (ValueError, TypeError):
                continue
        
        if ts:
            timestamps.append(ts)
        
        # 统计 assistant 消息
        if entry_type == 'message':
            message = entry.get('message', {})
            role = message.get('role', '')
            
            if role == 'assistant':
                assistant_calls += 1
                
                # 尝试从 message 中提取 usage
                msg_content = message.get('content', [])
                if isinstance(msg_content, list):
                    for item in msg_content:
                        if isinstance(item, dict):
                            usage = item.get('usage', {})
                            if usage:
                                total_tokens += usage.get('totalTokens', 0) or \
                                              (usage.get('input', 0) + usage.get('output', 0))
    
    if not timestamps:
        return None
    
    # 计算会话持续时间
    start_time = min(timestamps)
    end_time = max(timestamps)
    duration_minutes = (end_time - start_time) / 60
    
    return {
        'agent': agent_name,
        'session_file': str(file_path),
        'calls': assistant_calls,
        'tokens': total_tokens,
        'start_time': start_time,
        'end_time': end_time,
        'duration_minutes': duration_minutes,
        'date': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d')
    }


def collect_agent_data(days: int = 1, start_date: str = None, end_date: str = None) -> dict:
    """
    收集指定时间范围内的 agent 数据
    
    Args:
        days: 统计天数
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    """
    
    # 计算时间范围
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
    
    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()
    
    print(f"📊 收集数据范围：{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
    
    # 按 agent 聚合数据
    agent_stats = defaultdict(lambda: {
        'calls': 0,
        'tokens': 0,
        'sessions': 0,
        'duration_minutes': 0
    })
    
    daily_stats = defaultdict(lambda: {'calls': 0, 'tokens': 0})
    
    total_sessions = 0
    total_calls = 0
    total_tokens = 0
    
    # 自动获取目标 agent 列表
    target_agents = get_target_agents()
    
    # 遍历所有目标 agent
    for agent_name in target_agents:
        agent_dir = AGENTS_BASE_PATH / agent_name / 'sessions'
        
        if not agent_dir.exists():
            print(f"⚠️  Agent 目录不存在：{agent_dir}")
            continue
        
        # 查找所有 JSONL 文件（包括 deleted/reset，它们是历史数据的一部分）
        jsonl_files = list(agent_dir.glob('*.jsonl*'))
        
        for file_path in jsonl_files:
            stats = extract_session_stats(file_path, agent_name)
            
            if stats and start_ts <= stats['start_time'] <= end_ts:
                agent_stats[agent_name]['calls'] += stats['calls']
                agent_stats[agent_name]['tokens'] += stats['tokens']
                agent_stats[agent_name]['sessions'] += 1
                agent_stats[agent_name]['duration_minutes'] += stats['duration_minutes']
                
                daily_stats[stats['date']]['calls'] += stats['calls']
                daily_stats[stats['date']]['tokens'] += stats['tokens']
                
                total_sessions += 1
                total_calls += stats['calls']
                total_tokens += stats['tokens']
    
    # 构建结果
    agents_list = []
    for agent_name in target_agents:
        stats = agent_stats[agent_name]
        if stats['calls'] > 0:
            agents_list.append({
                'name': agent_name,
                'calls': stats['calls'],
                'tokens': stats['tokens'],
                'sessions': stats['sessions'],
                'avg_tokens': stats['tokens'] // stats['calls'] if stats['calls'] > 0 else 0,
                'duration_minutes': int(stats['duration_minutes'])
            })
    
    # 按调用次数排序
    agents_list.sort(key=lambda x: x['calls'], reverse=True)
    
    # 构建每日趋势
    daily_trend = []
    for date in sorted(daily_stats.keys()):
        daily_trend.append({
            'date': date,
            'calls': daily_stats[date]['calls'],
            'tokens': daily_stats[date]['tokens']
        })
    
    result = {
        'total_sessions': total_sessions,
        'total_calls': total_calls,
        'total_tokens': total_tokens,
        'date_range': f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}",
        'days': days,
        'agents': agents_list,
        'daily_trend': daily_trend,
        'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='收集 OpenClaw agent 使用数据')
    parser.add_argument('--days', type=int, default=1, help='统计天数')
    parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--output', required=True, help='输出 JSON 文件路径')
    
    args = parser.parse_args()
    
    # 收集数据
    data = collect_agent_data(
        days=args.days,
        start_date=args.start,
        end_date=args.end
    )
    
    # 输出 JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存到：{output_path}")
    print(f"📊 总会话数：{data['total_sessions']}")
    print(f"📊 总调用次数：{data['total_calls']}")
    print(f"📊 总 Token 用量：{data['total_tokens']:,}")
    print(f"\n📈 Agent 排名:")
    for i, agent in enumerate(data['agents'][:5], 1):
        print(f"   {i}. {agent['name']}: {agent['calls']} 次调用，{agent['tokens']:,} tokens")


if __name__ == '__main__':
    main()
