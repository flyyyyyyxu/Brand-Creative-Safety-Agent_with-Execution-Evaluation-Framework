# Brand Creative Safety Agent（Allbirds）- 增强版开发指南

> **重要原则**：本 README 以"零代码基础也能一步一步推进"为原则。每一步的输出（日志/报错/文件内容）都可以粘贴给 ChatGPT/Claude，让 AI 帮你继续推进。

---

## 目录
- [0. 项目定义](#0-项目定义)
- [1. 输入输出示例](#1-输入输出示例)
- [2. 技术方案与风险缓解](#2-技术方案与风险缓解)
- [3. 环境与部署](#3-环境与部署)
- [4. 分阶段验证步骤（最重要）](#4-分阶段验证步骤最重要)
- [5. 风险评分公式](#5-风险评分公式)
- [6. 故障排查](#6-故障排查)

---

## 0. 项目定义

### 0.1 项目目标（一句话）

为品牌（默认 Allbirds）构建一个"舆情/创意安全监控 Agent"，自动收集多来源风险信号，并输出可评估、可对比、可复盘的数据。

### 0.2 最终交付物

1. **一个可运行的 Agent**：给定任务集（queries）自动搜索 → 打开网页 → 提取信息 → 情绪/风险分析 → 输出结构化结果
2. **一套评估框架（Eval Harness）**：能统计成功率、失败类型、平均步数、延迟、成本等
3. **三组策略实验 A/B/C 的对比结果**（可写进简历、可面试讲述）

### 0.3 为什么这个选题适合投 Axon

- Axon/广告系统非常重视**品牌安全**（广告展示环境/创意风险/舆论反噬）
- 你在此项目中展示的能力是：
  - 把"舆论/风险"抽象成可量化的信号与指标
  - 让 Agent 在真实网页环境下稳定执行（这很像平台/infra 的可靠性工作）
  - 用 A/B 实验方法验证策略（更像 PM 的工作方式）

---

## 1. 输入输出示例

### 1.1 输入是什么

输入由 `datasets/tasks.json` 定义：
- **brand**：Allbirds
- **tasks**：12 条固定任务（例如 "Allbirds scam / complaint / greenwashing …"）
- **strategies**：A/B/C 三种策略
- **run_defaults**：超时、最大步数、失败时截图等

你也会有一个域名白名单 `datasets/allowlist.txt`（用于策略 B/C）。

### 1.2 输出是什么

每次运行会生成一条"run record"，并追加写入 `artifacts/runs.jsonl`（每行一个 JSON）。

输出字段由 `eval/schema.json` 约束（这一步非常关键，它保证你后面能做统计与对比）。

**输出示例（简化版）**：

```json
{
  "run_id": "...",
  "timestamp_utc": "2026-02-14T18:00:00Z",
  "brand": "Allbirds",
  "task_id": "T2",
  "strategy_id": "B",
  "query": "Allbirds complaint",
  "success": true,
  "failure_type": null,
  "step_count": 6,
  "latency_ms": 12850,
  "token_cost_estimate": 520,
  "sources": [
    {
      "source_type": "forum",
      "title": "Allbirds quality issues?",
      "url": "https://...",
      "snippet": "..."
    }
  ],
  "analysis": {
    "summary": "用户集中抱怨尺码、耐久度...",
    "sentiment": {"label": "negative", "score": -0.6},
    "risk_keywords": ["quality", "refund", "misleading"],
    "relevance_score": 0.92
  },
  "risk": {
    "negative_ratio": 0.67,
    "keyword_weight": 0.55,
    "recentness_factor": 0.73,
    "risk_score": 0.64,
    "risk_level": "high"
  },
  "debug": {"notes": "...", "screenshot_path": null, "trace_path": null}
}
```

---

## 2. 技术方案与风险缓解

### 2.1 三层架构

1. **Execution Layer（执行层）**：OpenClaw 驱动浏览器/工具执行
2. **Evaluation Layer（评估层）**：统一 schema + 指标统计
3. **Product Layer（产品层）**：风险评分与策略优化

### 2.2 关键风险点与缓解方案

#### ⚠️ **风险点 1：OpenClaw 稳定性问题（最大风险）**

**问题描述**：
Web Agent 在真实环境中失败率通常很高（30-50%）。OpenClaw 可能因为以下原因失败：
- 页面加载超时
- 搜索结果格式变化
- 广告/弹窗干扰
- 网页结构不符合预期

**缓解方案（3 个层次）**：

##### **层次 1：降低期望值（接受失败是正常的）**
```
成功率目标：
- 阶段 1（最小验证）：>30%
- 阶段 2（稳定性优化）：>60%
- 阶段 3（生产就绪）：>80%
```

把"Agent 本身的失败"也作为实验数据记录：
```json
"failure_type": "agent_timeout",  // Agent 超时
"failure_type": "parse_error",     // 无法解析页面结构
"failure_type": "no_results",      // 搜索无结果
"failure_type": "blocked_by_captcha" // 被验证码拦截
```

##### **层次 2：设置严格的超时与重试机制**

在 `datasets/tasks.json` 中设置：
```json
"run_defaults": {
  "timeout_seconds": 90,        // 单次 run 总超时
  "max_steps": 8,               // 最大步数（防止无限循环）
  "step_timeout_seconds": 15,   // 单步超时
  "retry_on_failure": false,    // 阶段 1 不重试，保持数据真实性
  "screenshot_on_failure": true // 失败时截图，便于调试
}
```

**建议成本预算（MiniMax 100 prompts/5h）**：
```
预估单次 run 消耗：2-4 prompts
12 tasks × 3 strategies × 3 repeats = 108 runs
总消耗：216-432 prompts（分批跑，每批 30-50 runs）

保险策略：
- 先跑 1 个 task × 3 strategies = 9 runs，验证成本
- 如果单次超过 5 prompts，需要降低 max_steps
```

##### **层次 3：Plan B - 降级为半自动方案**

如果 OpenClaw 成功率 <30%，启动备选方案：

**备选方案 A：手动爬虫 + Claude 分析**
```python
# 用 Playwright 手动抓取数据
import asyncio
from playwright.async_api import async_playwright

async def fallback_scrape(query):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"https://www.google.com/search?q={query}")
        # 提取前 3 个结果
        results = await page.query_selector_all(".g")
        # 手动解析...
```

然后用 Claude API 做情绪分析和风险评分（这部分一定能跑通）。

**备选方案 B：聚焦单一数据源**
```
只爬 Reddit 的 r/Allbirds 或公开论坛
用 PRAW (Python Reddit API Wrapper) 直接获取数据
避开 Web Agent 的复杂性
```

**如何判断是否需要降级**：
```bash
# 阶段 1 结束后运行评估脚本（后续会创建）
python eval/analyze.py artifacts/runs.jsonl

# 如果输出显示：
# Success rate: 12% (策略 A)
# Failure types: agent_timeout (60%), parse_error (28%)

# → 启动备选方案
```

---

#### ⚠️ **风险点 2：反爬与网页变化**

**问题描述**：
即使是公开网页，也可能遇到：
- Cloudflare 验证
- 动态加载（需要等待 JS 执行）
- 页面结构频繁变化
- 登录墙（Reddit/Twitter）

**缓解方案**：

##### **优先选择结构稳定的站点**

编辑 `datasets/allowlist.txt`，优先包含：
```
# 新闻媒体（结构稳定，无登录墙）
nytimes.com
theguardian.com
forbes.com
businessinsider.com

# 消费者评测（公开访问）
trustpilot.com
consumeraffairs.com
bbb.org

# 可持续性相关（Allbirds 主打环保）
greenbiz.com
sustainablebrands.com

# 论坛（需要控制访问频率）
reddit.com/r/Allbirds  # 仅此子版块
quora.com

# 避免的站点（高风险）
# instagram.com    - 需要登录
# tiktok.com       - 需要登录
# twitter.com/x.com - 需要登录
# facebook.com     - 需要登录
```

##### **Reddit 专用配置（你已有经验）**

在 Agent 代码中增加 Reddit 特殊处理：
```python
# agent/agent.py 中的配置
RATE_LIMIT_CONFIG = {
    "reddit.com": {
        "min_interval_seconds": 5,  # 最小间隔 5 秒
        "max_requests_per_minute": 10
    },
    "default": {
        "min_interval_seconds": 2
    }
}
```

##### **增加 failure_type 分类**

在 schema 中补充：
```json
"failure_type": {
  "enum": [
    null,
    "not_implemented",
    "agent_timeout",
    "parse_error",
    "no_results",
    "blocked_by_captcha",     // 被验证码拦截
    "page_load_timeout",      // 页面加载超时
    "login_required",         // 需要登录
    "irrelevant_content"      // 内容不相关（策略 C 会用）
  ]
}
```

---

#### ⚠️ **风险点 3：成本控制**

**问题描述**：
MiniMax 100 prompts/5h 的限制，需要精确控制每次 run 的消耗。

**缓解方案**：

##### **单次 run 成本估算**
```
假设 OpenClaw 每步消耗 1 prompt：
- 搜索：1 prompt
- 打开页面：1 prompt
- 提取信息：1 prompt
- 情绪分析：1 prompt
总计：4 prompts/run（理想情况）

实际可能：
- 有重试：6-8 prompts/run
- 页面复杂：10+ prompts/run
```

##### **在代码中硬编码限制**

```python
# agent/agent.py
MAX_PROMPTS_PER_RUN = 10  # 硬上限，防止单次 run 失控
prompt_counter = 0

def call_openclaw_step():
    global prompt_counter
    if prompt_counter >= MAX_PROMPTS_PER_RUN:
        raise Exception("Exceeded max prompts per run")
    prompt_counter += 1
    # ... OpenClaw 调用 ...
```

##### **分批执行策略**

```bash
# 不要一次跑完 108 runs

# 批次 1：单任务多策略（验证成本）
python agent/batch_runner.py --task_ids T1 --all_strategies --repeat 3
# 预估：9 runs × 6 prompts = 54 prompts

# 批次 2：如果成本可控，扩大到 3 个任务
python agent/batch_runner.py --task_ids T1,T2,T3 --all_strategies --repeat 3
# 预估：27 runs × 6 prompts = 162 prompts

# 批次 3：全量（如果前面都顺利）
python agent/batch_runner.py --all_tasks --all_strategies --repeat 3
```

##### **监控实时消耗**

在每次 run 后输出：
```bash
# 在 batch_runner.py 中加入
print(f"Completed {run_count}/{total_runs} | Estimated prompts used: {prompt_counter}")
print(f"Remaining quota: ~{100 - prompt_counter} prompts")
```

---

#### ⚠️ **风险点 4："零代码基础"的现实性**

**问题描述**：
README 说"零代码基础也能推进"，但实际上需要：
- 理解 Python 环境配置
- 调试 OpenClaw 的安装和浏览器依赖
- 处理 JSON Schema 验证错误

**缓解方案**：

##### **提供完整的依赖安装脚本**

创建 `scripts/setup.sh`（见下文"自动化脚本"部分）

##### **对每个错误类型提供 troubleshooting 文档**

见下文"故障排查"部分

##### **使用"错误 → AI 辅助"工作流**

```
你的工作流：
1. 执行命令（如 python agent/agent.py ...）
2. 遇到报错
3. 复制整段报错信息
4. 粘贴给 ChatGPT/Claude，说："帮我修复这个错误"
5. 执行 AI 给出的修复命令
6. 继续

关键：不要自己猜，直接问 AI
```

---

### 2.3 策略 A/B/C 的真实意义（你会做的实验）

- **A：free_planning**
  - 覆盖广，但误点多、广告跳转多、稳定性差
  
- **B：allowlist_only**
  - 限制只访问 `allowlist.txt` 里的域名
  - 预期：误点/广告跳转显著下降，成功率上升，成本下降
  
- **C：allowlist + 语义校验**
  - 在 B 的基础上要求页面 title 必须包含 "Allbirds"
  - 预期：relevance 更高，但可能因为过滤太严导致 no_result 增加（这是典型 tradeoff）

这三种策略的对比，就是你面试里最能讲清楚的"产品化实验"。

---

## 3. 环境与部署

### 3.1 当前云服务器配置

- **平台**：阿里云 ECS
- **系统**：Ubuntu 22.04
- **配置**：4 vCPU / 8GiB / 40GiB

### 3.2 推荐工作流（避免混乱）

- **本地**：用 Codex/AI 辅助写代码 → git commit/push
- **云端**：只做 git pull + 运行 + 保存 artifacts
- **.env**（模型 key 等）只放云端，不提交 GitHub

### 3.3 依赖（最低要求）

- Python 3.10+
- Node 20+
- OpenClaw（后续接入）
- 浏览器自动化依赖（Playwright + Chromium 或系统 Chromium）

---

## 4. 分阶段验证步骤（最重要）

### 📍 **阶段 0：环境验证（预计 30 分钟）**

**目标**：确认服务器环境可用，依赖安装正确。

#### 步骤 0.1：检查基础环境

```bash
# 在云端服务器执行
python3 --version  # 应该 >= 3.10
node --version     # 应该 >= 20
git --version

# 确认仓库已 clone
cd ~/brand-safety-agent  # 或你的仓库路径
git status
```

#### 步骤 0.2：运行自动安装脚本

```bash
# 创建并运行安装脚本（见下文"自动化脚本"部分）
bash scripts/setup.sh
```

**预期输出**：
```
✓ Python dependencies installed
✓ Node.js dependencies installed
✓ Playwright browsers installed
✓ Environment ready
```

**如果失败**：
- 复制整段报错信息
- 粘贴给 ChatGPT/Claude，说："帮我修复这个错误"
- 执行 AI 给出的修复命令

#### 步骤 0.3：验证任务集与 schema

```bash
# 确认这些文件存在
ls -la datasets/tasks.json
ls -la datasets/allowlist.txt
ls -la eval/schema.json

# 查看内容
cat datasets/tasks.json | head -20
cat eval/schema.json | head -30
```

**预期**：能看到 JSON 内容，没有报错。

---

### 📍 **阶段 1：最小可行验证（预计 2-4 小时）**

**目标**：证明 OpenClaw 能完成 1 次完整流程（搜索 → 打开 → 提取）。

#### 核心成功标准

```
✓ 能启动 OpenClaw
✓ 能完成搜索（Google/Bing）
✓ 能打开 1 个搜索结果
✓ 能提取 title + URL + snippet
✓ 能写入 artifacts/runs.jsonl
✓ success=true

允许失败的部分：
- 情绪分析可以先用假数据
- 风险评分可以先用假数据
- 不需要做 allowlist 过滤
```

#### 步骤 1.1：跑通 v0（只验证日志管道）

```bash
# 在云端仓库根目录执行
python3 agent/agent.py --task_id T1 --strategy_id A --timeout 90 --max_steps 8
```

**预期输出**：
```
[INFO] Starting run: task=T1, strategy=A
[INFO] Writing to artifacts/runs.jsonl
[INFO] Run completed: success=false, failure_type=not_implemented
```

**验证结果**：
```bash
# 检查输出文件
ls -la artifacts/
tail -n 1 artifacts/runs.jsonl | python3 -m json.tool
```

**应该看到**：
```json
{
  "run_id": "...",
  "success": false,
  "failure_type": "not_implemented",
  ...
}
```

**如果失败**：见"故障排查"部分。

#### 步骤 1.2：接入 OpenClaw 最小实现

**目标**：把 `agent/agent.py` 中的 TODO 替换为 OpenClaw 调用。

**最小实现伪代码**：
```python
# agent/agent.py (v1 最小版本)

def run_agent_v1(query, strategy):
    # 1. 初始化 OpenClaw
    agent = OpenClaw(...)
    
    # 2. 搜索
    search_results = agent.search(query)
    
    # 3. 打开第 1 个结果
    page_content = agent.open_url(search_results[0]['url'])
    
    # 4. 提取信息
    source = {
        "source_type": "unknown",  # 先不分类
        "title": page_content.title,
        "url": search_results[0]['url'],
        "snippet": page_content.snippet[:200]
    }
    
    # 5. 假数据填充分析部分
    analysis = {
        "summary": "TODO",
        "sentiment": {"label": "neutral", "score": 0.0},
        "risk_keywords": [],
        "relevance_score": 0.5
    }
    
    # 6. 返回结果
    return {
        "success": True,
        "failure_type": None,
        "sources": [source],
        "analysis": analysis,
        ...
    }
```

**验证命令**：
```bash
python3 agent/agent.py --task_id T1 --strategy_id A --timeout 90 --max_steps 8
```

**预期输出**：
```
[INFO] Starting run: task=T1, strategy=A
[INFO] OpenClaw initialized
[INFO] Searching for: Allbirds scam
[INFO] Found 10 results
[INFO] Opening: https://...
[INFO] Extracted: title="...", url="..."
[INFO] Writing to artifacts/runs.jsonl
[INFO] Run completed: success=true
```

**验证结果**：
```bash
tail -n 1 artifacts/runs.jsonl | python3 -m json.tool
```

**应该看到**：
```json
{
  "success": true,
  "sources": [
    {
      "title": "...",
      "url": "https://...",
      "snippet": "..."
    }
  ]
}
```

#### 阶段 1 成功标准

```
✓ 至少 1 次 run 达到 success=true
✓ sources[] 中有真实数据（不是假数据）
✓ 能稳定复现（跑 3 次，至少 1 次成功）
```

**如果成功率 <30%**：
- 检查是否被反爬拦截（看 debug.screenshot_path）
- 考虑更换搜索引擎（Google → DuckDuckGo）
- 考虑启动备选方案（见"风险点 1"）

---

### 📍 **阶段 2：稳定性验证（预计 1-2 天）**

**目标**：证明评估框架有效，能统计成功率和失败类型。

#### 步骤 2.1：批量运行单任务

```bash
# 运行 10 次（同一任务，策略 A）
for i in {1..10}; do
  python3 agent/agent.py --task_id T1 --strategy_id A --timeout 90 --max_steps 8
  sleep 5  # 避免触发 rate limit
done
```

#### 步骤 2.2：运行评估脚本

```bash
# 创建评估脚本（见下文"自动化脚本"部分）
python3 eval/analyze.py artifacts/runs.jsonl --strategy A
```

**预期输出**：
```
=== Evaluation Report (Strategy A) ===
Total runs: 10
Success rate: 60% (6/10)
Failure types:
  - agent_timeout: 30% (3/10)
  - parse_error: 10% (1/10)
Average steps (successful): 5.2
Average latency: 8234 ms
Estimated token cost: 4800
```

#### 阶段 2 成功标准

```
✓ 成功率 > 60%
✓ 能统计失败类型分布
✓ 平均耗时 < 15 秒
✓ Token 成本 < 800/run
```

**如果成功率 <60%**：
- 分析 failure_type 分布
- 优化超时设置
- 考虑引入重试机制

---

### 📍 **阶段 3：策略对比（预计 2-3 天）**

**目标**：证明 A/B/C 有显著差异。

#### 步骤 3.1：实现策略 B（allowlist_only）

```python
# agent/agent.py

def apply_strategy_b(search_results, allowlist):
    """只保留 allowlist 中的域名"""
    filtered = []
    for result in search_results:
        domain = extract_domain(result['url'])
        if domain in allowlist:
            filtered.append(result)
    return filtered
```

#### 步骤 3.2：实现策略 C（allowlist + 语义校验）

```python
def apply_strategy_c(search_results, allowlist, brand_name):
    """allowlist + title 必须包含品牌名"""
    filtered = []
    for result in search_results:
        domain = extract_domain(result['url'])
        if domain in allowlist and brand_name.lower() in result['title'].lower():
            filtered.append(result)
    return filtered
```

#### 步骤 3.3：批量运行对比

```bash
# 创建批量运行脚本（见下文"自动化脚本"部分）
python3 agent/batch_runner.py --task_ids T1,T2,T3 --all_strategies --repeat 5
```

**预期输出**：
```
Running 45 total runs (3 tasks × 3 strategies × 5 repeats)
[1/45] T1 | Strategy A | Run 1/5 ... success
[2/45] T1 | Strategy A | Run 2/5 ... failed (agent_timeout)
...
[45/45] T3 | Strategy C | Run 5/5 ... success

Summary:
Strategy A: 60% success (27/45), avg_steps=6.2, avg_cost=650
Strategy B: 80% success (36/45), avg_steps=4.8, avg_cost=480
Strategy C: 70% success (31.5/45), avg_steps=4.1, avg_cost=420
```

#### 步骤 3.4：对比分析

```bash
python3 eval/compare_strategies.py artifacts/runs.jsonl
```

**预期输出**：
```
=== Strategy Comparison ===

Metric              | A (free)  | B (allowlist) | C (allowlist+semantic)
--------------------|-----------|---------------|----------------------
Success rate        | 60%       | 80% (+33%)    | 70% (+17%)
Irrelevant clicks   | 45%       | 15% (-67%)    | 5% (-89%)
Avg steps           | 6.2       | 4.8 (-23%)    | 4.1 (-34%)
Avg latency (ms)    | 9500      | 7200 (-24%)   | 6500 (-32%)
Token cost/run      | 650       | 480 (-26%)    | 420 (-35%)
No results rate     | 5%        | 10% (+100%)   | 20% (+300%)

Recommendation: Strategy B (allowlist_only) 最优
- 成功率提升 33%
- 误点下降 67%
- 成本下降 26%
- No results 增加可接受（仅 10%）
```

#### 阶段 3 成功标准

```
✓ 策略 B 成功率 > 策略 A
✓ 策略 B 误点率 < 策略 A
✓ 策略 C relevance_score > 策略 A/B
✓ 能清晰看到 tradeoff（C 的 no_results 更高）
```

---

### 📍 **阶段 4：产品化输出（预计 1-2 天）**

**目标**：实现完整的风险评分和情绪分析。

#### 步骤 4.1：实现情绪分析

```python
# agent/sentiment.py

def analyze_sentiment(text):
    """使用 Claude API 做情绪分析"""
    prompt = f"""
    分析以下文本的情绪倾向（针对品牌 Allbirds）：
    
    文本：{text}
    
    输出 JSON：
    {{
      "label": "positive|neutral|negative",
      "score": -1.0 到 1.0,
      "confidence": 0.0 到 1.0
    }}
    """
    # 调用 Claude API...
```

#### 步骤 4.2：实现风险评分

见下文"风险评分公式"部分。

#### 步骤 4.3：生成最终报告

```bash
python3 eval/generate_report.py artifacts/runs.jsonl --output artifacts/final_report.md
```

**预期输出**：
```markdown
# Brand Safety Report - Allbirds

## Executive Summary
- Total runs: 108
- Overall success rate: 73%
- High risk signals: 15/108 (14%)
- Recommended action: Monitor "greenwashing" queries closely

## Risk Breakdown by Topic
| Query Type     | Avg Risk Score | High Risk Count |
|----------------|----------------|-----------------|
| scam           | 0.65 (high)    | 8               |
| greenwashing   | 0.58 (moderate)| 5               |
| complaint      | 0.45 (moderate)| 2               |
...
```

---

## 5. 风险评分公式

### 5.1 公式定义

```
Risk Score = 0.4 × negative_ratio + 0.3 × keyword_weight + 0.3 × recentness_factor
```

**参数说明**：

1. **negative_ratio**（负面比例）
   ```
   负面样本数 / 总样本数
   例：10 条评论中有 7 条负面 → 0.7
   ```

2. **keyword_weight**（关键词权重）
   ```
   风险关键词加权得分
   
   关键词权重表：
   - scam, fraud, lawsuit: 1.0（最高风险）
   - greenwashing, misleading, false advertising: 0.8
   - complaint, refund, poor quality: 0.6
   - disappointed, not recommended: 0.4
   
   计算：命中关键词的最高权重
   ```

3. **recentness_factor**（时间衰减）
   ```
   越近的内容权重越高
   
   时间衰减函数：
   - 30 天内：1.0
   - 30-90 天：0.7
   - 90-180 天：0.5
   - 180 天+：0.3
   ```

### 5.2 风险等级分类

```
Risk Score     | Risk Level
---------------|------------
0.0 - 0.3      | low
0.3 - 0.6      | moderate
0.6 - 1.0      | high
```

### 5.3 实现示例

```python
# agent/risk_scoring.py

def calculate_risk_score(sources, analysis):
    # 1. 计算 negative_ratio
    negative_count = sum(1 for s in sources if analysis['sentiment']['score'] < -0.2)
    negative_ratio = negative_count / len(sources) if sources else 0
    
    # 2. 计算 keyword_weight
    risk_keywords = {
        "scam": 1.0, "fraud": 1.0, "lawsuit": 1.0,
        "greenwashing": 0.8, "misleading": 0.8,
        "complaint": 0.6, "refund": 0.6
    }
    max_weight = 0
    for keyword in analysis['risk_keywords']:
        max_weight = max(max_weight, risk_keywords.get(keyword, 0))
    keyword_weight = max_weight
    
    # 3. 计算 recentness_factor
    # （假设 sources 中有 publish_date 字段）
    avg_age_days = calculate_avg_age(sources)
    if avg_age_days <= 30:
        recentness_factor = 1.0
    elif avg_age_days <= 90:
        recentness_factor = 0.7
    elif avg_age_days <= 180:
        recentness_factor = 0.5
    else:
        recentness_factor = 0.3
    
    # 4. 综合计算
    risk_score = (
        0.4 * negative_ratio +
        0.3 * keyword_weight +
        0.3 * recentness_factor
    )
    
    # 5. 分级
    if risk_score < 0.3:
        risk_level = "low"
    elif risk_score < 0.6:
        risk_level = "moderate"
    else:
        risk_level = "high"
    
    return {
        "negative_ratio": negative_ratio,
        "keyword_weight": keyword_weight,
        "recentness_factor": recentness_factor,
        "risk_score": risk_score,
        "risk_level": risk_level
    }
```

---

## 6. 故障排查

见独立文档 `docs/TROUBLESHOOTING.md`（将在下一个文件中创建）

---

## 7. 自动化脚本

### 7.1 环境安装脚本（scripts/setup.sh）

```bash
#!/bin/bash
set -e

echo "=== Installing Python dependencies ==="
pip3 install --user playwright anthropic jsonschema

echo "=== Installing Playwright browsers ==="
python3 -m playwright install chromium

echo "=== Installing Node.js dependencies (if using docx-js) ==="
# npm install -g docx  # 如果需要生成 Word 报告

echo "=== Creating directories ==="
mkdir -p artifacts
mkdir -p logs

echo "✓ Setup complete"
```

### 7.2 批量运行脚本（agent/batch_runner.py）

```python
#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

def main():
    # 读取 tasks.json
    with open("datasets/tasks.json") as f:
        config = json.load(f)
    
    tasks = config["tasks"]
    strategies = config["strategies"]
    repeat = config.get("repeat_per_strategy", 3)
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task_ids", help="Comma-separated task IDs (e.g., T1,T2,T3)")
    parser.add_argument("--all_tasks", action="store_true")
    parser.add_argument("--all_strategies", action="store_true")
    parser.add_argument("--repeat", type=int, default=repeat)
    args = parser.parse_args()
    
    # 选择任务
    if args.all_tasks:
        selected_tasks = tasks
    elif args.task_ids:
        task_ids = args.task_ids.split(",")
        selected_tasks = [t for t in tasks if t["task_id"] in task_ids]
    else:
        print("Error: specify --all_tasks or --task_ids")
        sys.exit(1)
    
    # 选择策略
    if args.all_strategies:
        selected_strategies = list(strategies.keys())
    else:
        selected_strategies = ["A"]  # 默认只跑 A
    
    total_runs = len(selected_tasks) * len(selected_strategies) * args.repeat
    print(f"Running {total_runs} total runs")
    
    run_count = 0
    for task in selected_tasks:
        for strategy_id in selected_strategies:
            for i in range(args.repeat):
                run_count += 1
                print(f"\n[{run_count}/{total_runs}] {task['task_id']} | Strategy {strategy_id} | Run {i+1}/{args.repeat}")
                
                cmd = [
                    "python3", "agent/agent.py",
                    "--task_id", task["task_id"],
                    "--strategy_id", strategy_id,
                    "--timeout", "90",
                    "--max_steps", "8"
                ]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        print("... success")
                    else:
                        print(f"... failed: {result.stderr[:100]}")
                except subprocess.TimeoutExpired:
                    print("... timeout")

if __name__ == "__main__":
    main()
```

### 7.3 评估脚本（eval/analyze.py）

```python
#!/usr/bin/env python3
import json
import sys
from collections import defaultdict
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 eval/analyze.py <runs.jsonl> [--strategy A]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # 读取所有 runs
    runs = []
    with open(filepath) as f:
        for line in f:
            runs.append(json.loads(line))
    
    # 过滤策略
    if "--strategy" in sys.argv:
        strategy_id = sys.argv[sys.argv.index("--strategy") + 1]
        runs = [r for r in runs if r["strategy_id"] == strategy_id]
    
    # 统计
    total = len(runs)
    success_count = sum(1 for r in runs if r["success"])
    
    failure_types = defaultdict(int)
    for r in runs:
        if not r["success"]:
            failure_types[r["failure_type"]] += 1
    
    successful_runs = [r for r in runs if r["success"]]
    avg_steps = sum(r["step_count"] for r in successful_runs) / len(successful_runs) if successful_runs else 0
    avg_latency = sum(r["latency_ms"] for r in successful_runs) / len(successful_runs) if successful_runs else 0
    avg_cost = sum(r["token_cost_estimate"] for r in successful_runs) / len(successful_runs) if successful_runs else 0
    
    # 输出报告
    print(f"=== Evaluation Report ===")
    print(f"Total runs: {total}")
    print(f"Success rate: {success_count/total*100:.1f}% ({success_count}/{total})")
    print(f"\nFailure types:")
    for ftype, count in sorted(failure_types.items(), key=lambda x: -x[1]):
        print(f"  - {ftype}: {count/total*100:.1f}% ({count}/{total})")
    print(f"\nAverage metrics (successful runs only):")
    print(f"  Steps: {avg_steps:.1f}")
    print(f"  Latency: {avg_latency:.0f} ms")
    print(f"  Token cost: {avg_cost:.0f}")

if __name__ == "__main__":
    main()
```

---

## 8. 面试故事模板

### 如何讲述这个项目（3 分钟版本）

**背景**：
"我做了一个品牌创意安全监控的项目，针对 Allbirds 这个环保鞋履品牌。背景是广告系统需要避免品牌广告出现在不安全的内容旁边，比如负面舆论、虚假宣传指控等。"

**方法**：
"我用 Web Agent（OpenClaw）自动从公开网页抓取品牌相关的舆论信号，包括新闻、论坛、评测等。然后用一套评估框架来验证 Agent 的稳定性，记录成功率、失败类型、成本等指标。"

**实验**：
"我设计了三种策略：A 是自由搜索，B 是只访问白名单域名，C 是白名单+语义校验。通过 A/B 实验发现，策略 B 的成功率提升了 33%，误点下降了 67%，成本降低了 26%。策略 C 的相关性更高，但 no_results 增加了 300%，是个典型的 precision-recall tradeoff。"

**结果**：
"最终我交付了一个可复现的评估框架和风险评分系统。风险评分基于负面比例、关键词权重和时间衰减，公式是可解释的，适合产品化。"

**技能点**：
- 量化评估（成功率、失败分类、成本）
- 实验设计（A/B/C 对比）
- 产品化思维（风险评分公式）
- 可靠性工程（处理 Agent 失败）

---

## 9. 下一步行动（非常明确）

1. **在云端跑阶段 0**：
   ```bash
   bash scripts/setup.sh
   ```

2. **在云端跑阶段 1（v0）**：
   ```bash
   python3 agent/agent.py --task_id T1 --strategy_id A --timeout 90 --max_steps 8
   ```

3. **把输出贴给 AI**：
   ```bash
   tail -n 1 artifacts/runs.jsonl
   ```
   然后说："我跑通了 v0，接下来如何接入 OpenClaw？"

4. **继续推进阶段 1（v1）**：
   - 实现最小搜索/打开/提取流程
   - 目标：success=true

---

## 附录

### A. 项目文件结构

```
brand-safety-agent/
├── agent/
│   ├── agent.py              # 主 Agent 逻辑
│   ├── batch_runner.py       # 批量运行脚本
│   ├── sentiment.py          # 情绪分析
│   └── risk_scoring.py       # 风险评分
├── datasets/
│   ├── tasks.json            # 任务定义
│   └── allowlist.txt         # 域名白名单
├── eval/
│   ├── schema.json           # 输出 schema
│   ├── analyze.py            # 单策略评估
│   └── compare_strategies.py # 策略对比
├── artifacts/
│   └── runs.jsonl            # 输出数据（追加写入）
├── scripts/
│   └── setup.sh              # 环境安装脚本
├── docs/
│   └── TROUBLESHOOTING.md    # 故障排查文档
└── README.md                 # 本文件
```

### B. 关键文件示例

#### datasets/tasks.json
```json
{
  "brand": "Allbirds",
  "tasks": [
    {"task_id": "T1", "query": "Allbirds scam", "topic": "fraud"},
    {"task_id": "T2", "query": "Allbirds complaint", "topic": "quality"},
    {"task_id": "T3", "query": "Allbirds greenwashing", "topic": "sustainability"}
  ],
  "strategies": {
    "A": {"name": "free_planning", "use_allowlist": false, "semantic_check": false},
    "B": {"name": "allowlist_only", "use_allowlist": true, "semantic_check": false},
    "C": {"name": "allowlist_semantic", "use_allowlist": true, "semantic_check": true}
  },
  "run_defaults": {
    "timeout_seconds": 90,
    "max_steps": 8,
    "screenshot_on_failure": true
  },
  "repeat_per_strategy": 3
}
```

#### datasets/allowlist.txt
```
# 新闻媒体
nytimes.com
theguardian.com
forbes.com
businessinsider.com

# 消费者评测
trustpilot.com
consumeraffairs.com

# 论坛（控制频率）
reddit.com

# 可持续性
greenbiz.com
sustainablebrands.com
```

---

**最后提醒**：
- 按阶段推进，不要跳步
- 每个阶段的失败都是有价值的数据
- 遇到问题就问 AI，不要自己猜
- 成功率 60% 已经足够写进简历

Good luck! 🚀