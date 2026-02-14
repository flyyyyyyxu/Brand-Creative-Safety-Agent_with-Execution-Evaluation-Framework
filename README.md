Brand Creative Safety Agent（Allbirds）

这是一个面向 广告创意安全（Creative Safety）与品牌风险（Brand Risk） 的 Agent 实践项目。

你将通过 部署 OpenClaw（Web/Tool Agent 框架），让 Agent 自动从公开网页获取与品牌相关的舆论信号，并将结果结构化输出；同时用一套可量化的执行评估框架（成功率 / 失败类型 / 成本 / 延迟等）来验证与优化 Agent 的稳定性。

重要： 本 README 以“零代码基础也能一步一步推进”为原则。你可以把每一步的输出（日志/报错/文件内容）粘贴给 ChatGPT/Codex，让 AI 帮你继续推进。

⸻

0. 你要做的是什么（产品定义）

0.1 项目目标

目标一句话：
	•	为品牌（默认 Allbirds）构建一个“舆情/创意安全监控 Agent”，自动收集多来源风险信号，并输出可评估、可对比、可复盘的数据。

你最终会交付：
	1.	一个可运行的 Agent：给定任务集（queries）自动搜索 → 打开网页 → 提取信息 → 情绪/风险分析 → 输出结构化结果
	2.	一套评估框架（Eval Harness）：能统计成功率、失败类型、平均步数、延迟、成本等
	3.	三组策略实验 A/B/C 的对比结果（可写进简历、可面试讲述）

0.2 为什么这个选题适合投 Axon
	•	Axon/广告系统非常重视 品牌安全（广告展示环境/创意风险/舆论反噬）
	•	你在此项目中展示的能力是：
	•	把“舆论/风险”抽象成可量化的信号与指标
	•	让 Agent 在真实网页环境下稳定执行（这很像平台/infra 的可靠性工作）
	•	用 A/B 实验方法验证策略（更像 PM 的工作方式）

⸻

1. 产出长什么样（输入 / 输出示例）

1.1 输入是什么

输入由 datasets/tasks.json 定义：
	•	brand：Allbirds
	•	tasks：12 条固定任务（例如 “Allbirds scam / complaint / greenwashing …”）
	•	strategies：A/B/C 三种策略
	•	run_defaults：超时、最大步数、失败时截图等

你也会有一个域名白名单 datasets/allowlist.txt（用于策略 B/C）。

1.2 输出是什么

每次运行会生成一条“run record”，并追加写入 artifacts/runs.jsonl（每行一个 JSON）。

输出字段由 eval/schema.json 约束（这一步非常关键，它保证你后面能做统计与对比）。

输出示例（简化版）

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

你现在仓库里的 v0 版本可能会先输出 success=false + failure_type=not_implemented。
这是正常的：我们先把“数据管道与 schema”锁住，再接 OpenClaw 实现真正的浏览与提取。

⸻

2. 技术方案（可行性验证：逻辑闭环）

这里是最关键的“可行性验证”。我们把系统拆成 3 层，并说明每层为什么可行、怎么验证。

2.1 三层架构
	1.	Execution Layer（执行层）：OpenClaw 驱动浏览器/工具执行
	•	可行性：OpenClaw 的核心价值就是“规划→工具调用→网页交互”。
	•	验证方式：能在云服务器上完成一次“搜索→打开→提取”的最小流程，并输出 1 条 record。
	2.	Evaluation Layer（评估层）：统一 schema + 指标统计
	•	可行性：只要所有 run 都输出到 runs.jsonl 且遵守 schema，就能稳定统计指标。
	•	验证方式：跑 10 次（同一任务），能计算成功率、失败类型分布、平均耗时。
	3.	Product Layer（产品层）：风险评分与策略优化
	•	可行性：风险评分本质是对结构化信号的聚合（负面比例+关键词权重+时间衰减）。
	•	验证方式：同一品牌多来源数据能输出不同 risk_score；策略 B/C 能降低误点、提升 relevance。

2.2 为什么不容易被“反爬”卡死

我们避免重爬大平台（TikTok/Instagram）。
策略是：
	•	优先抓取 公开网页（新闻、论坛、评测、博客）
	•	使用 域名白名单 避免进入广告/登录墙
	•	每次 run 限制步数与访问页数（成本可控、风险可控）

2.3 策略 A/B/C 的真实意义（你会做的实验）
	•	A：free_planning
	•	覆盖广，但误点多、广告跳转多、稳定性差
	•	B：allowlist_only
	•	限制只访问 allowlist.txt 里的域名
	•	预期：误点/广告跳转显著下降，成功率上升，成本下降
	•	C：allowlist + 语义校验
	•	在 B 的基础上要求页面 title 必须包含 “Allbirds”
	•	预期：relevance 更高，但可能因为过滤太严导致 no_result 增加（这是典型 tradeoff）

这三种策略的对比，就是你面试里最能讲清楚的“产品化实验”。

⸻

3. 环境与部署（OpenClaw on Ubuntu 22.04）

你当前云服务器：阿里云 ECS Ubuntu 22.04 / 4 vCPU / 8GiB / 40GiB。

3.1 推荐工作流（避免混乱）
	•	本地：用 Codex/AI 辅助写代码 → git commit/push
	•	云端：只做 git pull + 运行 + 保存 artifacts
	•	.env（模型 key 等）只放云端，不提交 GitHub

3.2 依赖（最低要求）
	•	Python 3.10+
	•	Node 20+
	•	OpenClaw（后续接入）
	•	浏览器自动化依赖（Playwright + Chromium 或系统 Chromium）

你已经完成服务器的基础安装与仓库 clone。

⸻

4. 如何一步一步运行（从 0 到 1）

4.1 第一步：确认任务集与 schema（已在仓库中）
	•	datasets/tasks.json：Allbirds 12 条任务
	•	eval/schema.json：run record 的 JSON Schema

你可以用：

cat datasets/tasks.json
cat eval/schema.json

4.2 第二步：跑通 v0（只验证日志管道）

在云端仓库根目录执行：

python3 agent/agent.py --task_id T1 --strategy_id A --timeout 90 --max_steps 8

预期：
	•	生成 artifacts/runs.jsonl
	•	追加写入 1 条 record

检查：

ls -la artifacts
tail -n 1 artifacts/runs.jsonl

如果失败：把报错复制给 ChatGPT（我们会逐步修）。

4.3 第三步：接入 OpenClaw（v1：真正的网页执行）

这一部分需要你逐步把 agent/agent.py 的 TODO 替换为 OpenClaw 调用。

v1 的最小目标：
	•	输入 query
	•	通过 OpenClaw 搜索并打开 1 个结果
	•	提取 title + url + snippet
	•	写入 sources[]
	•	success=true

你不需要一次把情绪/关键词/风险评分都做好。
先实现“可用数据抓取”最重要。

4.4 第四步：评估与统计（v2）

v2 的最小目标：
	•	写一个 eval 脚本（后续由 AI 生成）
	•	读取 runs.jsonl
	•	输出：成功率、失败类型分布、平均耗时、平均 token

4.5 第五步：实验 A/B/C（v3）

v3 的最小目标：
	•	用 tasks.json 里的 repeat_per_strategy（默认 3 次）跑批
	•	比较策略 A/B/C 的：
	•	success rate
	•	irrelevant_click 占比
	•	avg steps
	•	token cost

⸻

5. 风险评分（v4：产品化输出）

风险评分公式（可解释、可面试）：
	•	negative_ratio：负面样本占比
	•	keyword_weight：风险关键词加权（scam/lawsuit/refund/greenwashing…）
	•	recentness_factor：时间衰减（越近越高）

示例：

Risk Score = 0.4*negative_ratio + 0.3*keyword_weight + 0.3*recentness_factor

分级：
	•	0–0.3：low
	•	0.3–0.6：moderate
	•	0.6–1.0：high

⸻

6. 常见问题（你没有代码基础也能推进）

Q1：我不懂代码，怎么推进？

A：按 README 的顺序执行命令；每一步把输出/报错贴给 AI，让 AI 生成下一步需要的代码或修复命令。

Q2：我怕网站反爬？

A：我们主要依靠公开网页 + allowlist + 步数限制；失败会被 taxonomy 记录下来，本身就是实验数据。

Q3：我怎么把它讲成面试故事？

A：核心是：
	•	业务问题：品牌创意安全
	•	方法：Agent 自动采集 + 评估框架
	•	实验：A/B/C 策略对比
	•	结果：成功率提升、误点下降、成本下降

⸻

7. 下一步你要做什么（非常明确）
	1.	在云端跑 v0：
	•	python3 agent/agent.py --task_id T1 --strategy_id A ...
	2.	把 tail -n 1 artifacts/runs.jsonl 输出贴给 AI
	3.	我们开始 v1：接入 OpenClaw 的最小搜索/打开/提取流程