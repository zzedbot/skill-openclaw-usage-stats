#!/usr/bin/env python3
"""
OpenClaw Usage Stats - Deploy Script

将生成的报告部署到 Nginx 服务目录，通过 HTTPS 对外提供访问。
"""

import argparse
import shutil
import os
from pathlib import Path
from datetime import datetime


def deploy_report(source_html: str, dest_name: str, title: str = None):
    """部署单个报告文件"""
    
    dest_dir = Path("/var/www/openclaw-reports")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    dest_file = dest_dir / dest_name
    shutil.copy2(source_html, dest_file)
    
    # 设置权限
    os.chmod(dest_file, 0o644)
    
    print(f"✅ 已部署：{dest_name}")
    print(f"   访问 URL: https://yunzhijiachannel.kingdee.space/reports/{dest_name}")
    
    return str(dest_file)


def deploy_all_from_iteration(iteration_path: str):
    """从迭代目录部署所有报告"""
    
    iteration_dir = Path(iteration_path)
    if not iteration_dir.exists():
        print(f"❌ 迭代目录不存在：{iteration_path}")
        return
    
    # 映射关系
    deployments = [
        ("eval-1-stat-today/output/report.html", "today.html", "今日报告"),
        ("eval-2-7day-trend/output/report.html", "7days.html", "7 天趋势"),
        ("eval-3-date-range/output/report.html", "date-range.html", "日期范围报告"),
        ("eval-4-quick-stats/output/report.html", "yesterday.html", "昨日统计"),
        ("eval-5-compare/output/report.html", "compare.html", "对比报告"),
        ("eval-viewer.html", "index.html", "评估查看器"),
    ]
    
    print(f"📦 开始部署迭代报告：{iteration_path}\n")
    
    for source, dest, desc in deployments:
        source_file = iteration_dir / source
        if source_file.exists():
            deploy_report(str(source_file), dest, desc)
        else:
            print(f"⚠️  文件不存在：{source_file}")
    
    print(f"\n✅ 部署完成！")
    print(f"\n📊 访问地址:")
    print(f"   首页：https://yunzhijiachannel.kingdee.space/reports/")
    print(f"   今日报告：https://yunzhijiachannel.kingdee.space/reports/today.html")
    print(f"   7 天趋势：https://yunzhijiachannel.kingdee.space/reports/7days.html")
    print(f"   日期范围：https://yunzhijiachannel.kingdee.space/reports/date-range.html")
    print(f"   昨日统计：https://yunzhijiachannel.kingdee.space/reports/yesterday.html")
    print(f"   对比报告：https://yunzhijiachannel.kingdee.space/reports/compare.html")


def main():
    parser = argparse.ArgumentParser(description='部署 OpenClaw 使用报告到 Nginx')
    parser.add_argument('--source', required=True, help='源 HTML 文件路径或迭代目录')
    parser.add_argument('--dest', help='目标文件名（单个文件时使用）')
    parser.add_argument('--title', help='报告标题')
    parser.add_argument('--iteration', action='store_true', help='从迭代目录部署所有报告')
    
    args = parser.parse_args()
    
    if args.iteration:
        deploy_all_from_iteration(args.source)
    else:
        if not args.dest:
            print("❌ 单个文件部署时需要指定 --dest 参数")
            return
        deploy_report(args.source, args.dest, args.title)


if __name__ == '__main__':
    main()
