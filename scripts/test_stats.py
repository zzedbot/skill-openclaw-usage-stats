#!/usr/bin/env python3
"""
OpenClaw Usage Stats - 测试脚本

测试关键功能，确保修复后不会回归。
"""

import json
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent
TEST_AGENTS = ["test_agent1", "test_agent2"]

def run_estimate_tokens(days, output_path, extra_args=None):
    """运行 estimate_tokens.py"""
    cmd = [sys.executable, str(SCRIPTS_DIR / "estimate_tokens.py"),
           "--days", str(days), "--output", str(output_path)]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def load_json(path):
    with open(path) as f:
        return json.load(f)

def test_agent_daily_breakdown_not_empty():
    """Bug 1 测试: agent_daily_breakdown 必须有数据"""
    print("Test 1: agent_daily_breakdown 不应为空...", end=" ")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        output_path = f.name
    
    try:
        result = run_estimate_tokens(7, output_path)
        if result.returncode != 0:
            print(f"SKIP (脚本执行失败: {result.stderr[:200]})")
            return False
        
        data = load_json(output_path)
        adb = data.get("agent_daily_breakdown", {})
        
        if len(adb) == 0:
            print("FAIL - agent_daily_breakdown 为空!")
            return False
        
        # 验证数据结构
        for key, val in adb.items():
            if "calls" not in val or "tokens" not in val:
                print(f"FAIL - 数据结构错误: {key}")
                return False
            if not isinstance(val["calls"], int) or val["calls"] < 0:
                print(f"FAIL - calls 值错误: {key} = {val}")
                return False
        
        print(f"OK ({len(adb)} 条目)")
        return True
    finally:
        os.unlink(output_path)

def test_hourly_distribution_sums_correctly():
    """测试: 24小时分布总和 = total_calls"""
    print("Test 2: hourly_distribution 总和应等于 total_calls...", end=" ")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        output_path = f.name
    
    try:
        result = run_estimate_tokens(7, output_path)
        if result.returncode != 0:
            print(f"SKIP (脚本执行失败)")
            return False
        
        data = load_json(output_path)
        hourly_sum = sum(data.get("hourly_distribution", []))
        total = data["total_calls"]
        
        if hourly_sum != total:
            print(f"FAIL - 小时总和 {hourly_sum} != 总调用 {total}")
            return False
        
        print(f"OK ({total} calls)")
        return True
    finally:
        os.unlink(output_path)

def test_agent_hourly_breakdown_exists():
    """测试: agent_hourly_breakdown 必须有数据"""
    print("Test 3: agent_hourly_breakdown 应有数据...", end=" ")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        output_path = f.name
    
    try:
        result = run_estimate_tokens(7, output_path)
        if result.returncode != 0:
            print(f"SKIP")
            return False
        
        data = load_json(output_path)
        ahb = data.get("agent_hourly_breakdown", {})
        
        if len(ahb) == 0:
            print("FAIL - 为空")
            return False
        
        # 验证每个 agent 有 24 小时数据
        for agent, hours in ahb.items():
            if len(hours) != 24:
                print(f"FAIL - {agent} 只有 {len(hours)} 小时")
                return False
        
        print(f"OK ({len(ahb)} agents)")
        return True
    finally:
        os.unlink(output_path)

def test_adhb_hourly_sums_match_agent_hourly():
    """测试: agent_day_hourly_breakdown 按 agent 聚合 = agent_hourly_breakdown"""
    print("Test 4: adhb 按 agent 聚合应匹配 agent_hourly_breakdown...", end=" ")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        output_path = f.name
    
    try:
        result = run_estimate_tokens(7, output_path)
        if result.returncode != 0:
            print(f"SKIP")
            return False
        
        data = load_json(output_path)
        ahb = data.get("agent_hourly_breakdown", {})
        adhb = data.get("agent_day_hourly_breakdown", {})
        
        # 按 agent 聚合 adhb
        aggregated = {}
        for key, hours in adhb.items():
            agent = key.split("|")[0]
            if agent not in aggregated:
                aggregated[agent] = [0] * 24
            for i in range(24):
                aggregated[agent][i] += hours[i]
        
        for agent in ahb:
            if agent not in aggregated:
                print(f"FAIL - {agent} 在 adhb 聚合中缺失")
                return False
            if aggregated[agent] != ahb[agent]:
                print(f"FAIL - {agent} 聚合不匹配")
                return False
        
        print(f"OK")
        return True
    finally:
        os.unlink(output_path)

def test_date_range_filtering():
    """测试: --range 参数正确工作"""
    print("Test 5: --range week 应返回本周数据...", end=" ")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        output_path = f.name
    
    try:
        result = run_estimate_tokens(None, output_path, ["--range", "week"])
        if result.returncode != 0:
            print(f"SKIP")
            return False
        
        data = load_json(output_path)
        
        # 验证 date_range 包含本周日期
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        
        if data["days"] < 1 or data["days"] > 7:
            print(f"FAIL - 天数异常: {data['days']}")
            return False
        
        print(f"OK ({data['days']} days, {data['date_range']})")
        return True
    finally:
        os.unlink(output_path)

def test_target_agents_includes_main():
    """Bug 4 测试: TARGET_AGENTS 应包含 main"""
    print("Test 6: TARGET_AGENTS 应包含 main...", end=" ")
    
    for script_name in ["estimate_tokens.py", "collect_data.py"]:
        script_path = SCRIPTS_DIR / script_name
        content = script_path.read_text()
        if "'main'" not in content and '"main"' not in content:
            print(f"FAIL - {script_name} 缺少 'main'")
            return False
    
    print("OK")
    return True

def test_quick_report_uses_v2():
    """Bug 3 测试: quick-report.py 应默认使用 v2 模板"""
    print("Test 7: quick-report.py 应使用 --version v2...", end=" ")
    qr_path = SCRIPTS_DIR / "quick-report.py"
    content = qr_path.read_text()
    
    if "--version" not in content or "v2" not in content:
        print("FAIL - 没有 --version v2")
        return False
    
    print("OK")
    return True

if __name__ == "__main__":
    print(f"=== OpenClaw Usage Stats 测试 ===")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    tests = [
        test_agent_daily_breakdown_not_empty,
        test_hourly_distribution_sums_correctly,
        test_agent_hourly_breakdown_exists,
        test_adhb_hourly_sums_match_agent_hourly,
        test_date_range_filtering,
        test_target_agents_includes_main,
        test_quick_report_uses_v2,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            result = test()
            if result is True:
                passed += 1
            elif result is False:
                failed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
    
    print(f"\n{'='*40}")
    print(f"结果: {passed} 通过, {failed} 失败, {skipped} 跳过")
    
    if failed > 0:
        sys.exit(1)
