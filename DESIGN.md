# 🎨 新版设计说明

## 设计改进

### 1. 配色方案
- ❌ **移除渐变**：不再使用渐变配色
- ✅ **纯色块**：采用精心选择的纯色配色
  - Primary: `#2D5BFF` (亮蓝)
  - Secondary: `#00C9A7` (青绿)
  - Accent: `#FF6B6B` (珊瑚红)
  - 中性灰阶：`#F8F9FA` ~ `#212529`

### 2. 字体选择
- **标题字体**：IBM Plex Sans (现代、专业)
- **代码字体**：JetBrains Mono (技术感)
- 避免使用通用字体 (Arial, Inter, Roboto)

### 3. 新增功能

#### Agent 过滤器
- 下拉选择器，可按单个 agent 筛选
- 支持"全部 Agent"选项
- 实时筛选（开发中）

#### 时间范围过滤器
- 日期选择器：开始日期 ~ 结束日期
- 默认显示过去 7 天
- 支持自定义时间范围

#### 会话个数统计
- 新增独立卡片显示总会话数
- 带趋势指示器
- 视觉突出

#### 每日对话时间分布热力图
- 24 小时热力图展示
- 颜色级别：0-7 级
- 悬停显示具体数值
- 直观展示活跃时段

### 4. 视觉细节

#### 卡片设计
- 精致圆角：`10px` ~ `16px`
- 多层阴影：`shadow-md` / `shadow-lg`
- 悬停动画：上浮 4px + 阴影加深
- 入场动画：依次淡入上浮

#### 表格优化
- Agent 头像：彩色圆形 + 首字母
- 排名徽章：金银铜配色
- 悬停高亮：浅灰背景
- 更好的留白和间距

#### 图表美化
- 纯色配色，无渐变
- 圆角柱状图：`borderRadius: 6`
- 平滑曲线：`tension: 0.4`
- 自定义网格颜色

### 5. 响应式设计
- 移动端适配
- 卡片单列布局
- 过滤器自动换行
- 横向滚动支持

## 技术实现

### 文件结构
```
~/.openclaw/skills/openclaw-usage-stats/
├── assets/
│   └── report_template_v2.html    # 新版模板
├── scripts/
│   ├── generate_report.py         # 支持 v1/v2 版本
│   ├── estimate_tokens.py         # Token 估算
│   └── collect_data.py            # 数据收集
└── openclaw-usage-stats-workspace/
    └── iteration-2/
        └── estimated_tokens.json  # 估算数据
```

### 使用方法

```bash
# 生成 v2 版本报告
python3 scripts/generate_report.py \
  --data estimated_tokens.json \
  --output report.html \
  --title "Agent 使用报告" \
  --version v2

# 一键生成并部署
python3 scripts/quick-report.py --days 7 --deploy
```

### 待开发功能

1. **过滤器实际功能**
   - 前端筛选逻辑
   - 动态更新图表
   - URL 参数支持

2. **真实小时数据**
   - 从 JSONL 解析时间戳
   - 统计每小时调用数
   - 按天分组热力图

3. **交互增强**
   - 点击图例筛选
   - 数据导出 CSV
   - 打印优化样式

4. **性能优化**
   - 大数据量分页
   - 图表懒加载
   - 缓存优化

## 设计原则

1. **Intentionality**: 每个设计选择都有明确目的
2. **Cohesion**: 色彩、字体、间距保持一致性
3. **Delight**: 微动画和交互细节带来惊喜
4. **Accessibility**: 足够的对比度和清晰的层次
5. **Performance**: 纯 CSS 动画，最小化 JS

## 对比

| 特性 | 旧版 | 新版 |
|------|------|------|
| 配色 | 渐变紫色 | 纯色块 |
| 字体 | 系统字体 | IBM Plex Sans |
| 阴影 | 单一阴影 | 多层阴影系统 |
| 圆角 | 统一 15px | 分级 6-24px |
| 过滤器 | 无 | ✓ |
| 热力图 | 无 | ✓ |
| 会话统计 | 无 | ✓ |
| 动画 | 基础 | 精心编排 |

---

**访问**: https://yunzhijiachannel.kingdee.space/reports/
