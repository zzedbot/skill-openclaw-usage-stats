#!/usr/bin/env python3
"""
OpenClaw Usage Stats - Report Generator

生成可视化的 HTML 报告，展示 agent 使用情况统计。
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path


def generate_html_report(data: dict, output_path: str, title: str = "Agent 使用报告", version: str = "v1"):
    """生成 HTML 报告"""
    
    # 优先使用数据中的真实小时分布
    hourly_data = data.get('hourly_distribution', [0] * 24)
    
    if version == "v2":
        return generate_html_report_v2(data, output_path, title, hourly_data)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        h1 {{
            color: white;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
        }}
        
        .card h3 {{
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }}
        
        .card .unit {{
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .chart-container h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.3em;
        }}
        
        .chart-wrapper {{
            position: relative;
            height: 300px;
        }}
        
        .table-container {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow-x: auto;
        }}
        
        .table-container h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.3em;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 15px;
            border-bottom: 1px solid #eee;
            color: #333;
        }}
        
        tr:hover {{
            background: #f8f9ff;
        }}
        
        .rank {{
            display: inline-block;
            width: 30px;
            height: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 30px;
            font-weight: bold;
        }}
        
        .rank.gold {{ background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); }}
        .rank.silver {{ background: linear-gradient(135deg, #C0C0C0 0%, #808080 100%); }}
        .rank.bronze {{ background: linear-gradient(135deg, #CD7F32 0%, #8B4513 100%); }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            opacity: 0.8;
        }}
        
        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            
            h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {title}</h1>
        
        <div class="summary-cards">
            <div class="card">
                <h3>总会话数</h3>
                <div class="value">{data.get('total_sessions', 0)}</div>
                <div class="unit">个会话</div>
            </div>
            <div class="card">
                <h3>总调用次数</h3>
                <div class="value">{data.get('total_calls', 0)}</div>
                <div class="unit">次调用</div>
            </div>
            <div class="card">
                <h3>总 Token 用量</h3>
                <div class="value">{format_number(data.get('total_tokens', 0))}</div>
                <div class="unit">tokens</div>
            </div>
            <div class="card">
                <h3>时间范围</h3>
                <div class="value" style="font-size: 1.5em;">{data.get('date_range', 'N/A')}</div>
                <div class="unit">{data.get('days', 0)} 天</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <h2>🏆 Agent 调用次数排名</h2>
                <div class="chart-wrapper">
                    <canvas id="callsChart"></canvas>
                </div>
            </div>
            <div class="chart-container">
                <h2>💾 Agent Token 用量对比</h2>
                <div class="chart-wrapper">
                    <canvas id="tokensChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="chart-container" style="margin-bottom: 40px;">
            <h2>📈 每日调用趋势</h2>
            <div class="chart-wrapper">
                <canvas id="trendChart"></canvas>
            </div>
        </div>
        
        <div class="table-container">
            <h2>📋 详细统计</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>Agent</th>
                        <th>调用次数</th>
                        <th>Token 用量</th>
                        <th>平均 Token/次</th>
                        <th>占比</th>
                    </tr>
                </thead>
                <tbody>
                    {generate_table_rows(data.get('agents', []))}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>OpenClaw Usage Stats Report</p>
        </div>
    </div>
    
    <script>
        const agentNames = {json.dumps([a['name'] for a in data.get('agents', [])])};
        const callCounts = {json.dumps([a['calls'] for a in data.get('agents', [])])};
        const tokenCounts = {json.dumps([a['tokens'] for a in data.get('agents', [])])};
        const dailyData = {json.dumps(data.get('daily_trend', []))};
        
        // 调用次数图表
        new Chart(document.getElementById('callsChart'), {{
            type: 'bar',
            data: {{
                labels: agentNames,
                datasets: [{{
                    label: '调用次数',
                    data: callCounts,
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(0,0,0,0.05)' }}
                    }},
                    x: {{
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});
        
        // Token 用量图表
        new Chart(document.getElementById('tokensChart'), {{
            type: 'doughnut',
            data: {{
                labels: agentNames,
                datasets: [{{
                    data: tokenCounts,
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(247, 37, 133, 0.8)',
                        'rgba(255, 159, 67, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(54, 162, 235, 0.8)'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'right' }}
                }}
            }}
        }});
        
        // 趋势图表
        new Chart(document.getElementById('trendChart'), {{
            type: 'line',
            data: {{
                labels: dailyData.map(d => d.date),
                datasets: [{{
                    label: '每日调用次数',
                    data: dailyData.map(d => d.calls),
                    borderColor: 'rgba(102, 126, 234, 1)',
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(0,0,0,0.05)' }}
                    }},
                    x: {{
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    # 写入文件
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding='utf-8')
    
    # 复制本地 JS 库到输出目录
    libs_src = Path(__file__).parent.parent / "assets" / "libs"
    libs_dst = output_file.parent / "libs"
    if libs_src.exists():
        import shutil
        libs_dst.mkdir(parents=True, exist_ok=True)
        for f in libs_src.iterdir():
            if f.is_file():
                shutil.copy2(f, libs_dst / f.name)
    
    return str(output_file)


def generate_html_report_v2(data: dict, output_path: str, title: str, hourly_data: list = None):
    """生成 v2 版本 HTML 报告"""
    
    # 读取模板
    template_path = Path(__file__).parent.parent / "assets" / "report_template_v2.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 使用真实的小时数据（如果有）
    if hourly_data is None:
        hourly_data = data.get('hourly_distribution', [0] * 24)
    
    # 替换占位符
    html = template
    html = html.replace('{{title}}', title)
    html = html.replace('{{total_sessions}}', str(data.get('total_sessions', 0)))
    html = html.replace('{{total_calls}}', str(data.get('total_calls', 0)))
    html = html.replace('{{total_tokens_formatted}}', format_number(data.get('total_tokens', 0)))
    html = html.replace('{{days}}', str(data.get('days', 0)))
    html = html.replace('{{date_range}}', data.get('date_range', 'N/A'))
    html = html.replace('{{generated_at}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # JSON 数据
    import json
    html = html.replace('{{agents_json}}', json.dumps(data.get('agents', []), ensure_ascii=False))
    html = html.replace('{{daily_trend_json}}', json.dumps(data.get('daily_trend', []), ensure_ascii=False))
    html = html.replace('{{hourly_data_json}}', json.dumps(hourly_data, ensure_ascii=False))
    
    # agent_daily_breakdown
    adb = data.get('agent_daily_breakdown', {})
    html = html.replace('{{agent_daily_breakdown_json}}', json.dumps(adb, ensure_ascii=False))
    
    # agent_hourly_breakdown
    ahb = data.get('agent_hourly_breakdown', {})
    html = html.replace('{{agent_hourly_breakdown_json}}', json.dumps(ahb, ensure_ascii=False))
    
    # agent_day_hourly_breakdown
    adhb = data.get('agent_day_hourly_breakdown', {})
    html = html.replace('{{agent_day_hourly_breakdown_json}}', json.dumps(adhb, ensure_ascii=False))
    
    # word_frequency
    wf = data.get('word_frequency', {})
    html = html.replace('{{word_frequency_json}}', json.dumps(wf, ensure_ascii=False))
    
    # word_frequency_by_day
    wfbd = data.get('word_frequency_by_day', {})
    html = html.replace('{{word_frequency_by_day_json}}', json.dumps(wfbd, ensure_ascii=False))
    
    # 生成表格行
    html = html.replace('{{table_rows}}', generate_table_rows_v2(data.get('agents', [])))
    
    # 写入文件
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding='utf-8')
    
    # 复制本地 JS 库到输出目录
    libs_src = Path(__file__).parent.parent / "assets" / "libs"
    libs_dst = output_file.parent / "libs"
    if libs_src.exists():
        import shutil
        libs_dst.mkdir(parents=True, exist_ok=True)
        for f in libs_src.iterdir():
            if f.is_file():
                shutil.copy2(f, libs_dst / f.name)
    
    return str(output_file)


def generate_table_rows_v2(agents: list) -> str:
    """生成 v2 版本表格行"""
    rows = []
    total_calls = sum(a.get('calls', 0) for a in agents)
    
    colors = ['#2D5BFF', '#00C9A7', '#FF6B6B', '#FFB800', '#8B5CF6', '#EC4899', '#14B8A6']
    
    for i, agent in enumerate(agents, 1):
        name = agent.get('name', 'Unknown')
        calls = agent.get('calls', 0)
        tokens = agent.get('tokens', 0)
        avg_tokens = tokens // calls if calls > 0 else 0
        percentage = (calls / total_calls * 100) if total_calls > 0 else 0
        size_kb = agent.get('total_size_kb', 0)
        
        rank_class = "gold" if i == 1 else "silver" if i == 2 else "bronze" if i == 3 else "default"
        color = colors[(i - 1) % len(colors)]
        
        row = f"""<tr>
            <td><span class="rank {rank_class}">{i}</span></td>
            <td>
                <div class="agent-cell">
                    <div class="agent-avatar" style="background: {color}">{name[0].upper()}</div>
                    <strong>{name}</strong>
                </div>
            </td>
            <td>{calls:,}</td>
            <td>{format_number(tokens)}</td>
            <td>{format_number(avg_tokens)}</td>
            <td>{size_kb} KB</td>
            <td>{percentage:.1f}%</td>
        </tr>"""
        rows.append(row)
    
    return "\n".join(rows)


def format_number(num: int) -> str:
    """格式化大数字"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def generate_table_rows(agents: list) -> str:
    """生成表格行"""
    rows = []
    total_calls = sum(a.get('calls', 0) for a in agents)
    
    for i, agent in enumerate(agents, 1):
        name = agent.get('name', 'Unknown')
        calls = agent.get('calls', 0)
        tokens = agent.get('tokens', 0)
        avg_tokens = tokens // calls if calls > 0 else 0
        percentage = (calls / total_calls * 100) if total_calls > 0 else 0
        
        rank_class = ""
        if i == 1:
            rank_class = "gold"
        elif i == 2:
            rank_class = "silver"
        elif i == 3:
            rank_class = "bronze"
        
        row = f"""<tr>
            <td><span class="rank {rank_class}">{i}</span></td>
            <td><strong>{name}</strong></td>
            <td>{calls:,}</td>
            <td>{format_number(tokens)}</td>
            <td>{format_number(avg_tokens)}</td>
            <td>{percentage:.1f}%</td>
        </tr>"""
        rows.append(row)
    
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description='生成 OpenClaw 使用统计报告')
    parser.add_argument('--data', required=True, help='JSON 数据文件路径')
    parser.add_argument('--output', required=True, help='输出 HTML 文件路径')
    parser.add_argument('--title', default='Agent 使用报告', help='报告标题')
    parser.add_argument('--version', default='v2', choices=['v1', 'v2'], help='报告模板版本')
    
    args = parser.parse_args()
    
    # 读取数据
    with open(args.data, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 生成报告
    output_path = generate_html_report(data, args.output, args.title, args.version)
    print(f"报告已生成：{output_path}")


if __name__ == '__main__':
    main()
