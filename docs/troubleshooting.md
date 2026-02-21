# 故障排查文档（TROUBLESHOOTING）

本文档涵盖所有可能遇到的错误类型和解决方案。每个错误都提供：
- **错误现象**：你会看到什么
- **原因分析**：为什么会出现
- **解决方案**：如何修复（含命令）
- **如何验证**：确认修复成功

---

## 目录

1. [环境安装问题](#1-环境安装问题)
2. [OpenClaw 相关问题](#2-openclaw-相关问题)
3. [运行时错误](#3-运行时错误)
4. [数据验证错误](#4-数据验证错误)
5. [成本超支问题](#5-成本超支问题)
6. [通用调试技巧](#6-通用调试技巧)

---

## 1. 环境安装问题

### 1.1 Python 版本过低

**错误现象**：
```bash
$ python3 --version
Python 3.8.10

$ python3 agent/agent.py ...
SyntaxError: invalid syntax (match case 不支持)
```

**原因分析**：
代码使用了 Python 3.10+ 的特性（如 match-case 语法）。

**解决方案**：

```bash
# 方案 A：安装 Python 3.10（推荐）
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev

# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 验证
python --version  # 应该是 3.10.x

# 方案 B：降级代码（不推荐，但可应急）
# 把 match-case 改成 if-elif-else
```

**如何验证**：
```bash
python --version
# 应该输出 Python 3.10.x 或更高
```

---

### 1.2 pip install 失败

**错误现象**：
```bash
$ pip3 install playwright
ERROR: Could not find a version that satisfies the requirement playwright
```

**原因分析**：
- pip 版本过低
- 或者网络问题（无法访问 PyPI）

**解决方案**：

```bash
# 方案 A：升级 pip
python3 -m pip install --upgrade pip

# 方案 B：使用国内镜像（如果在中国）
pip3 install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方案 C：手动下载 wheel 文件
# 去 https://pypi.org/project/playwright/#files 下载
# 然后 pip install playwright-xxx.whl
```

**如何验证**：
```bash
python3 -c "import playwright; print(playwright.__version__)"
# 应该输出版本号，如 1.40.0
```

---

### 1.3 Playwright 浏览器安装失败

**错误现象**：
```bash
$ python3 -m playwright install chromium
Downloading Chromium...
ERROR: Failed to download, timeout
```

**原因分析**：
- 网络问题（Playwright 下载浏览器很慢）
- 或者磁盘空间不足

**解决方案**：

```bash
# 方案 A：检查磁盘空间
df -h
# 如果 / 分区不足，清理：
sudo apt clean
sudo apt autoremove

# 方案 B：使用系统 Chromium（不推荐，但可应急）
sudo apt install chromium-browser

# 方案 C：手动设置环境变量（跳过 Playwright 自带浏览器）
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
pip3 install playwright

# 然后在代码中使用系统浏览器
# browser = playwright.chromium.launch(executable_path="/usr/bin/chromium-browser")

# 方案 D：增加超时时间并重试
PLAYWRIGHT_DOWNLOAD_TIMEOUT=300000 python3 -m playwright install chromium
```

**如何验证**：
```bash
python3 -m playwright install --help
# 应该能看到帮助信息

# 或者运行简单测试
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com')
    print(page.title())
    browser.close()
"
# 应该输出 "Example Domain"
```

---

### 1.4 Node.js 版本过低（如果使用 docx-js）

**错误现象**：
```bash
$ node --version
v14.x.x

$ npm install -g docx
ERROR: Requires Node.js >= 18
```

**原因分析**：
docx-js 需要 Node.js 18+。

**解决方案**：

```bash
# 使用 nvm 安装新版本
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20

# 验证
node --version  # 应该是 v20.x.x
```

**如何验证**：
```bash
npm install -g docx
docx --version
```

---

## 2. OpenClaw 相关问题

### 2.1 OpenClaw 未安装或导入失败

**错误现象**：
```bash
$ python3 agent/agent.py ...
ModuleNotFoundError: No module named 'openclaw'
```

**原因分析**：
OpenClaw 未安装或安装路径不在 Python PATH 中。

**解决方案**：

```bash
# 方案 A：检查 OpenClaw 是否安装
pip3 list | grep -i claw
# 如果没有，需要安装（具体安装方式取决于 OpenClaw 的发布形式）

# 方案 B：如果 OpenClaw 是本地目录
export PYTHONPATH="${PYTHONPATH}:/path/to/openclaw"

# 方案 C：临时方案 - 在代码中添加路径
# 在 agent.py 开头加入：
import sys
sys.path.insert(0, '/path/to/openclaw')
```

**如何验证**：
```bash
python3 -c "import openclaw; print(openclaw.__version__)"
# 或者如果没有 __version__：
python3 -c "import openclaw; print('OK')"
```

---

### 2.2 OpenClaw 初始化失败

**错误现象**：
```bash
$ python3 agent/agent.py ...
[ERROR] OpenClaw initialization failed: API key not found
```

**原因分析**：
OpenClaw 需要 API key（MiniMax 或其他），但未正确配置。

**解决方案**：

```bash
# 方案 A：创建 .env 文件
cat > .env << 'EOF'
MINIMAX_API_KEY=your_key_here
OPENAI_API_KEY=backup_key_here
EOF

# 在代码中加载
# from dotenv import load_dotenv
# load_dotenv()

# 方案 B：直接设置环境变量
export MINIMAX_API_KEY="your_key_here"

# 方案 C：在代码中硬编码（仅用于测试，不要提交到 GitHub）
# agent = OpenClaw(api_key="your_key_here")
```

**如何验证**：
```bash
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('API key:', os.getenv('MINIMAX_API_KEY')[:10] + '...')
"
# 应该输出 API key 的前 10 个字符
```

---

### 2.3 OpenClaw 搜索超时

**错误现象**：
```bash
[ERROR] Run failed: failure_type=agent_timeout
[DEBUG] Last step: search, elapsed=45s
```

**原因分析**：
- 网络慢
- 搜索引擎响应慢
- OpenClaw 内部超时设置太短

**解决方案**：

```python
# 方案 A：增加超时时间
agent = OpenClaw(
    timeout=120,  # 从 60 增加到 120 秒
    step_timeout=30  # 单步超时
)

# 方案 B：更换搜索引擎
# 如果用的是 Google，试试 DuckDuckGo
agent.search_engine = "duckduckgo"

# 方案 C：减少搜索结果数量
results = agent.search(query, max_results=3)  # 从 10 减少到 3
```

**如何验证**：
```bash
# 运行单个任务并观察日志
python3 agent/agent.py --task_id T1 --strategy_id A --timeout 120 --max_steps 8 --verbose
# 查看每一步的耗时
```

---

### 2.4 OpenClaw 被反爬拦截

**错误现象**：
```bash
[ERROR] Run failed: failure_type=blocked_by_captcha
[DEBUG] Page title: "Please verify you are human"
```

**原因分析**：
被 Cloudflare 或其他反爬机制拦截。

**解决方案**：

```python
# 方案 A：使用 stealth 模式
agent = OpenClaw(
    stealth=True,  # 启用反检测
    headless=True  # 保持无头模式
)

# 方案 B：增加随机延迟
import random
import time
time.sleep(random.uniform(2, 5))  # 在每次请求之间

# 方案 C：更换域名（使用 allowlist）
# 避开需要验证的站点，只访问白名单
```

**如何验证**：
```bash
# 检查失败类型分布
python3 eval/analyze.py artifacts/runs.jsonl | grep blocked_by_captcha
# 如果比例 >30%，说明反爬严重
```

---

## 3. 运行时错误

### 3.1 JSONDecodeError

**错误现象**：
```bash
$ python3 agent/agent.py ...
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**原因分析**：
- `tasks.json` 或其他 JSON 文件格式错误
- 或者 OpenClaw 返回的不是有效 JSON

**解决方案**：

```bash
# 方案 A：验证 JSON 文件
python3 -m json.tool datasets/tasks.json
# 如果报错，说明 JSON 格式有问题，检查：
# - 是否有多余的逗号
# - 是否有未闭合的引号/括号

# 方案 B：添加异常处理
try:
    data = json.loads(response_text)
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {response_text[:200]}")
    raise

# 方案 C：检查 OpenClaw 输出
# 如果是 OpenClaw 返回的问题，检查其 response 格式
```

**如何验证**：
```bash
# 验证所有 JSON 文件
for file in datasets/*.json eval/*.json; do
    echo "Checking $file..."
    python3 -m json.tool "$file" > /dev/null && echo "✓ OK" || echo "✗ FAILED"
done
```

---

### 3.2 KeyError: 'task_id'

**错误现象**：
```bash
$ python3 agent/agent.py --task_id T99 ...
KeyError: 'T99'
```

**原因分析**：
指定的 task_id 不存在于 `tasks.json` 中。

**解决方案**：

```bash
# 方案 A：检查可用的 task_id
python3 -c "
import json
with open('datasets/tasks.json') as f:
    tasks = json.load(f)['tasks']
for task in tasks:
    print(task['task_id'], '-', task['query'])
"

# 方案 B：修复命令
python3 agent/agent.py --task_id T1 --strategy_id A ...
# 确保 task_id 在 T1-T12 范围内（取决于你的 tasks.json）
```

**如何验证**：
```bash
# 跑一个已知存在的 task_id
python3 agent/agent.py --task_id T1 --strategy_id A --timeout 90 --max_steps 8
```

---

### 3.3 FileNotFoundError: 'artifacts/runs.jsonl'

**错误现象**：
```bash
$ python3 eval/analyze.py artifacts/runs.jsonl
FileNotFoundError: [Errno 2] No such file or directory: 'artifacts/runs.jsonl'
```

**原因分析**：
- `artifacts/` 目录不存在
- 或者还没有运行过任何 task（runs.jsonl 未创建）

**解决方案**：

```bash
# 方案 A：创建目录
mkdir -p artifacts

# 方案 B：运行至少一次 task
python3 agent/agent.py --task_id T1 --strategy_id A --timeout 90 --max_steps 8

# 方案 C：创建空文件（仅用于测试）
touch artifacts/runs.jsonl
```

**如何验证**：
```bash
ls -la artifacts/runs.jsonl
# 应该能看到文件，即使大小为 0
```

---

### 3.4 内存溢出（OOM）

**错误现象**：
```bash
$ python3 agent/batch_runner.py --all_tasks ...
Killed
# 或者
MemoryError
```

**原因分析**：
- 批量运行太多任务
- 或者 OpenClaw 内存泄漏
- 云服务器内存不足（8GB 可能不够）

**解决方案**：

```bash
# 方案 A：分批运行（最推荐）
# 每次只跑 10-20 个任务
python3 agent/batch_runner.py --task_ids T1,T2,T3 --all_strategies --repeat 3

# 方案 B：监控内存使用
htop  # 实时监控
# 或者
free -h  # 查看可用内存

# 方案 C：增加 swap（临时方案）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 方案 D：在代码中显式释放内存
import gc
gc.collect()  # 在每次 run 后调用
```

**如何验证**：
```bash
# 运行时监控内存
watch -n 1 free -h
# 同时在另一个终端运行 batch_runner
```

---

## 4. 数据验证错误

### 4.1 Schema 验证失败

**错误现象**：
```bash
$ python3 agent/agent.py ...
[ERROR] Schema validation failed: 'success' is a required property
```

**原因分析**：
输出的 JSON 不符合 `eval/schema.json` 定义的 schema。

**解决方案**：

```python
# 方案 A：使用 jsonschema 验证
import jsonschema
with open("eval/schema.json") as f:
    schema = json.load(f)

try:
    jsonschema.validate(output, schema)
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
    print(f"Failed value: {e.instance}")
    # 修复 output...

# 方案 B：检查必需字段
required_fields = ["run_id", "timestamp_utc", "brand", "task_id", 
                   "strategy_id", "query", "success"]
for field in required_fields:
    if field not in output:
        print(f"Missing required field: {field}")

# 方案 C：使用默认值填充
output.setdefault("success", False)
output.setdefault("failure_type", "unknown")
```

**如何验证**：
```bash
# 手动验证一条 record
tail -n 1 artifacts/runs.jsonl > /tmp/test_record.json
python3 -c "
import json
import jsonschema
with open('/tmp/test_record.json') as f:
    record = json.load(f)
with open('eval/schema.json') as f:
    schema = json.load(f)
jsonschema.validate(record, schema)
print('✓ Valid')
"
```

---

### 4.2 timestamp 格式错误

**错误现象**：
```bash
[ERROR] Invalid timestamp: 2026-02-14 18:00:00
Expected: 2026-02-14T18:00:00Z
```

**原因分析**：
timestamp 必须是 ISO 8601 格式（带 T 和 Z）。

**解决方案**：

```python
# 正确的生成方式
from datetime import datetime, timezone

timestamp_utc = datetime.now(timezone.utc).isoformat()
# 输出：2026-02-14T18:00:00.123456+00:00

# 或者简化版
timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
# 输出：2026-02-14T18:00:00Z
```

**如何验证**：
```bash
python3 -c "
from datetime import datetime, timezone
print(datetime.now(timezone.utc).isoformat())
"
# 应该输出类似：2026-02-14T18:00:00.123456+00:00
```

---

## 5. 成本超支问题

### 5.1 单次 run 消耗过多 prompts

**错误现象**：
```bash
[WARNING] Run consumed 15 prompts (expected <10)
[WARNING] Approaching rate limit: 85/100 prompts used
```

**原因分析**：
- max_steps 设置过高
- OpenClaw 内部有重试逻辑
- 页面太复杂，需要多次交互

**解决方案**：

```python
# 方案 A：降低 max_steps
python3 agent/agent.py --task_id T1 --strategy_id A --max_steps 5  # 从 8 降到 5

# 方案 B：在代码中硬编码 prompt 上限
MAX_PROMPTS_PER_RUN = 8
if prompt_counter >= MAX_PROMPTS_PER_RUN:
    return {
        "success": False,
        "failure_type": "max_prompts_exceeded",
        ...
    }

# 方案 C：禁用 OpenClaw 的自动重试
agent = OpenClaw(auto_retry=False)
```

**如何验证**：
```bash
# 运行 10 次并统计平均消耗
for i in {1..10}; do
    python3 agent/agent.py --task_id T1 --strategy_id A --max_steps 5
done

python3 eval/analyze.py artifacts/runs.jsonl --strategy A | grep "Token cost"
# 应该看到：Avg token cost: 400-600
```

---

### 5.2 达到 MiniMax 速率限制

**错误现象**：
```bash
[ERROR] Rate limit exceeded: 100 prompts in 5 hours
[ERROR] Next reset: 2026-02-14T23:00:00Z
```

**原因分析**：
MiniMax 100 prompts/5h 的限制被触发。

**解决方案**：

```bash
# 方案 A：等待重置（最简单）
# 记录重置时间，5 小时后再跑

# 方案 B：使用备用 API（如果有）
export OPENAI_API_KEY="backup_key"
# 修改代码，当 MiniMax 失败时切换到 OpenAI

# 方案 C：分散时间跑
# 不要一次跑 100 个，分成 5 批，每批等待 1 小时

# 方案 D：减少每次运行的 repeat
# 从 repeat=5 降到 repeat=3
python3 agent/batch_runner.py --task_ids T1,T2 --all_strategies --repeat 3
```

**如何验证**：
```bash
# 监控实时消耗
python3 -c "
import json
with open('artifacts/runs.jsonl') as f:
    runs = [json.loads(line) for line in f]
total_cost = sum(r.get('token_cost_estimate', 0) for r in runs)
print(f'Total prompts used (approx): {total_cost // 100}')
print(f'Remaining quota: ~{100 - total_cost // 100}')
"
```

---

## 6. 通用调试技巧

### 6.1 启用详细日志

```bash
# 在 agent.py 中添加
import logging
logging.basicConfig(level=logging.DEBUG)

# 或者运行时指定
python3 agent/agent.py --task_id T1 --strategy_id A --verbose
```

### 6.2 保存失败时的截图

```python
# 在 run 失败时
if not success and screenshot_on_failure:
    screenshot_path = f"artifacts/screenshots/{run_id}.png"
    agent.save_screenshot(screenshot_path)
    debug["screenshot_path"] = screenshot_path
```

### 6.3 使用交互式调试

```bash
# 安装 ipdb
pip3 install ipdb

# 在代码中插入断点
import ipdb; ipdb.set_trace()

# 或者运行时进入
python3 -m pdb agent/agent.py --task_id T1 ...
```

### 6.4 检查 runs.jsonl 的最后几条

```bash
# 查看最后 5 条 run
tail -n 5 artifacts/runs.jsonl | while read line; do
    echo "$line" | python3 -m json.tool | head -20
    echo "---"
done
```

### 6.5 统计失败模式

```bash
# 快速统计失败类型
cat artifacts/runs.jsonl | \
python3 -c "
import json
import sys
from collections import Counter
failure_types = []
for line in sys.stdin:
    record = json.loads(line)
    if not record['success']:
        failure_types.append(record.get('failure_type', 'unknown'))
print(Counter(failure_types))
"
```

---

## 7. 求助流程（当所有方法都失败时）

### 7.1 准备诊断信息

```bash
# 1. 收集系统信息
uname -a > /tmp/debug_info.txt
python3 --version >> /tmp/debug_info.txt
pip3 list >> /tmp/debug_info.txt

# 2. 收集错误日志
tail -n 50 logs/agent.log >> /tmp/debug_info.txt

# 3. 收集最后一次运行的输出
tail -n 1 artifacts/runs.jsonl >> /tmp/debug_info.txt
```

### 7.2 粘贴给 AI

```
# 复制整个文件内容
cat /tmp/debug_info.txt

# 然后粘贴给 ChatGPT/Claude，并说明：
"我在运行 Brand Safety Agent 时遇到了以下错误：
[粘贴错误信息]

系统信息和日志：
[粘贴 debug_info.txt 内容]

请帮我诊断问题并提供解决方案。"
```

### 7.3 提供最小复现步骤

```bash
# 尽量简化到最小可复现步骤
# 例如：
python3 -c "
import openclaw
agent = openclaw.OpenClaw()
result = agent.search('test query')
print(result)
"
```

---

## 8. 常见问题速查表

| 错误关键词 | 可能原因 | 快速修复 |
|-----------|---------|---------|
| `ModuleNotFoundError` | 依赖未安装 | `pip3 install <module>` |
| `JSONDecodeError` | JSON 格式错误 | `python3 -m json.tool <file>` |
| `KeyError` | 字段缺失 | 检查 schema 和实际输出 |
| `TimeoutError` | 超时 | 增加 `--timeout` 参数 |
| `MemoryError` | 内存不足 | 分批运行，减少 repeat |
| `Rate limit` | API 限额 | 等待重置或使用备用 key |
| `blocked_by_captcha` | 反爬拦截 | 使用 allowlist，避开验证站点 |
| `ValidationError` | Schema 不匹配 | 检查必需字段，验证格式 |

---

## 9. 预防性检查清单

在每次运行前，执行以下检查：

```bash
# ✓ 环境检查
python3 --version  # >= 3.10
node --version     # >= 20 (如果用 docx-js)
pip3 list | grep playwright  # 已安装

# ✓ 文件检查
ls datasets/tasks.json
ls datasets/allowlist.txt
ls eval/schema.json

# ✓ 磁盘空间检查
df -h  # / 分区至少有 5GB 空闲

# ✓ API key 检查
echo $MINIMAX_API_KEY | head -c 10  # 应该有值

# ✓ 配额检查
# 估算本次运行会用多少 prompts
# 确保不超过剩余配额
```

---

**最后提醒**：
- 90% 的问题都能通过"复制报错 → 粘贴给 AI"解决
- 不要花超过 30 分钟自己猜
- 每次修复后记得提交代码（git commit）
- 保持 artifacts/ 目录的备份

Good luck! 🛠️