#!/usr/bin/env python3
"""
OpenClaw Usage Stats - 一键生成并部署报告

收集真实数据 -> 生成报告 -> 部署到 Nginx
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).parent
WORKSPACE = SCRIPTS_DIR.parent / "openclaw-usage-stats-workspace"
REPORTS_DIR = Path("/var/www/openclaw-reports")


def run_command(cmd: str, description: str):
    """运行命令并显示进度"""
    print(f"🔄 {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ {description}失败:")
        print(result.stderr)
        return False
    print(f"✅ {description}完成")
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='一键生成并部署 Agent 使用报告')
    parser.add_argument('--days', type=int, default=7, help='统计天数')
    parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--deploy', action='store_true', help='部署到 Nginx')
    parser.add_argument('--title', help='报告标题')
    
    args = parser.parse_args()
    
    # 创建工作区
    iteration_name = datetime.now().strftime("iteration-%Y%m%d-%H%M")
    workspace = WORKSPACE / iteration_name
    workspace.mkdir(parents=True, exist_ok=True)
    
    print(f"📊 OpenClaw Agent 使用报告生成器")
    print(f"工作区：{workspace}\n")
    
    # 步骤 1: 收集数据
    data_file = workspace / "data.json"
    time_range = f"{args.start} ~ {args.end}" if args.start and args.end else f"过去{args.days}天"
    
    cmd = f"python3 {SCRIPTS_DIR}/collect_data.py"
    if args.start and args.end:
        cmd += f" --start {args.start} --end {args.end}"
    else:
        cmd += f" --days {args.days}"
    cmd += f" --output {data_file}"
    
    if not run_command(cmd, f"收集数据 ({time_range})"):
        return 1
    
    # 步骤 2: 生成报告
    report_file = workspace / "report.html"
    title = args.title or f"Agent 使用报告 - {time_range}"
    
    cmd = f"python3 {SCRIPTS_DIR}/generate_report.py --data {data_file} --output {report_file} --title '{title}' --version v2"
    if not run_command(cmd, "生成 HTML 报告"):
        return 1
    
    # 步骤 3: 部署
    if args.deploy:
        if not run_command(f"cp {report_file} {REPORTS_DIR}/index.html", "部署到 Nginx"):
            return 1
        
        print(f"\n✅ 部署完成！")
        print(f"\n📊 访问地址:")
        print(f"   https://yunzhijiachannel.kingdee.space/reports/")
        print(f"\n💡 提示：报告已保存到 {report_file}")
    else:
        print(f"\n✅ 报告生成完成！")
        print(f"   本地路径：{report_file}")
        print(f"\n💡 使用 --deploy 参数可自动部署到 Nginx")
    
    # 显示统计摘要
    import json
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n📈 统计摘要:")
    print(f"   总会话数：{data['total_sessions']}")
    print(f"   总调用次数：{data['total_calls']}")
    print(f"   时间范围：{data['date_range']}")
    print(f"\n🏆 Top 3 Agents:")
    for i, agent in enumerate(data['agents'][:3], 1):
        print(f"   {i}. {agent['name']}: {agent['calls']} 次调用")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
