"""kaiwu 功能实测脚本"""
import sys, os, json, time
os.environ['LOGURU_LEVEL'] = 'ERROR'
from loguru import logger
logger.disable('kaiwu')

print('=' * 60)
print('kaiwu 功能实测 — 模拟真实编码场景')
print('=' * 60)

# === 测试 1: 错误诊断三层匹配 ===
print('\n### 测试 1: 错误诊断三层匹配')
from kaiwu.storage.error_kb import ErrorKB
kb = ErrorKB()

errors = [
    ('UnicodeDecodeError', 'Traceback:\nUnicodeDecodeError: gbk codec cant decode byte 0xef'),
    ('ModuleNotFoundError', 'Traceback:\nModuleNotFoundError: No module named PIL'),
    ('ConnectionRefused', 'Traceback:\nConnectionRefusedError: [Errno 111] Connection refused'),
    ('npm ERESOLVE', 'npm ERR! ERESOLVE unable to resolve dependency tree'),
    ('PermissionError', 'Traceback:\nPermissionError: [Errno 13] Permission denied'),
]

local_hits = 0
for name, err in errors:
    start = time.perf_counter()
    result = kb.find_solution(err)
    elapsed = (time.perf_counter() - start) * 1000
    hit = bool(result and result.get('solution'))
    if hit:
        local_hits += 1
    print(f"  {name:30s} -> {'HIT' if hit else 'MISS':4s} ({elapsed:.2f}ms)")
print(f"  Local hit rate: {local_hits}/{len(errors)} ({local_hits/len(errors)*100:.0f}%)")

# === 测试 2: 任务分类器 ===
print('\n### 测试 2: 任务分类器')
from kaiwu.task_classifier import classify_task

test_tasks = [
    ('simple_algo', 'write a binary search function'),
    ('frontend', 'React + Tailwind user dashboard'),
    ('deploy', 'deploy FastAPI to nginx with HTTPS'),
    ('database', 'design MySQL schema for e-commerce'),
    ('wechat_pay', 'implement wechat pay JSAPI callback'),
    ('encoding_fix', 'fix Windows Python GBK encoding issue'),
    ('api_dev', 'FastAPI RESTful auth with JWT'),
    ('scraping', 'scrape douban top250 into SQLite'),
    ('urgent_fix', 'production 502 nginx upstream timeout'),
]

for label, task in test_tasks:
    v = classify_task(task)
    inject = []
    if v.inject_knowledge: inject.append('KB')
    if v.inject_experience: inject.append('EXP')
    if v.call_llm: inject.append('LLM')
    inject_str = '+'.join(inject) if inject else 'none'
    print(f"  [{v.level:7s}] {label:15s} | inject: {inject_str}")

# === 测试 3: 场景检测 ===
print('\n### 测试 3: 场景检测 (19 scenes)')
from kaiwu.scene import get_scene

scene_tasks = [
    'Vue3 + Element Plus admin panel',
    'wechat mini program payment',
    'Python data analysis CSV processing',
    'D3.js realtime data visualization',
    'Shell script MySQL backup automation',
    'pytest unit tests for API endpoints',
]

for task in scene_tasks:
    r = get_scene(task)
    scenes = r.get('scenes', [])
    if scenes:
        names = [f"{s['key']}({s.get('score',0)})" for s in scenes[:3]]
        print(f"  {task:42s} -> {' | '.join(names)}")
    else:
        print(f"  {task:42s} -> no match")

# === 测试 4: 知识库按需注入 ===
print('\n### 测试 4: 知识库按需注入')
from kaiwu.task_classifier import should_inject_knowledge

kb_names = ['china_kb', 'python_compat', 'deps_pitfalls', 'tool_priming']
inject_tasks = [
    'deploy to Aliyun ECS with nginx reverse proxy',
    'fix Python 3.12 asyncio compatibility issue',
    'resolve npm ERESOLVE dependency conflict',
    'build custom MCP tool with FastMCP',
]

for task in inject_tasks:
    injected = [kb for kb in kb_names if should_inject_knowledge(task, kb)]
    print(f"  {task:50s} -> {injected if injected else 'none'}")

# === 测试 5: 主模型识别 ===
print('\n### 测试 5: 主模型能力识别')
from kaiwu.config import infer_host_level

models = {
    'strong': ['claude-opus-4-6', 'claude-sonnet-4-6', 'gpt-4o', 'gpt-4-turbo', 'deepseek-r1', 'gemini-2-pro'],
    'medium': ['deepseek-chat', 'qwen-72b', 'llama-70b'],
    'weak': ['claude-haiku-4-5', 'gpt-3.5-turbo', 'o4-mini', 'qwen-7b', 'gemini-flash'],
}

correct = 0
total = 0
for expected, model_list in models.items():
    for m in model_list:
        actual = infer_host_level(host_model=m)
        ok = actual == expected
        if ok: correct += 1
        total += 1
        mark = 'OK' if ok else f'WRONG(got {actual})'
        print(f"  {m:25s} -> {actual:7s} {mark}")
print(f"  Accuracy: {correct}/{total} ({correct/total*100:.0f}%)")

# === 测试 6: DeepSeek 规划 ===
print('\n### 测试 6: DeepSeek 规划 (API call)')
try:
    from kaiwu.planner import get_plan
    task = 'FastAPI user registration with JWT auth and bcrypt password hashing'
    start = time.perf_counter()
    result = get_plan(task, '', session_id='', project_name='test')
    elapsed = time.perf_counter() - start
    steps = result.get('steps', [])
    traps = result.get('trap_warnings', [])
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Steps: {len(steps)}")
    for s in steps[:3]:
        print(f"    {s.get('seq', '?')}. {s.get('action', '')[:60]}")
    if len(steps) > 3:
        print(f"    ... total {len(steps)} steps")
    print(f"  Trap warnings: {len(traps)}")
    for t in traps[:2]:
        print(f"    ! {t[:70]}")
    print(f"  Edge cases: {len(result.get('edge_cases', []))}")
    print(f"  Verify steps: {len(result.get('verify', []))}")
except Exception as e:
    print(f"  SKIP (API error: {e})")

# === 测试 7: DeepSeek 错误诊断 ===
print('\n### 测试 7: DeepSeek 错误诊断 (API call)')
try:
    from kaiwu.lessons import get_lessons
    error = 'Traceback:\n  File "/app/main.py", line 45\nValueError: Invalid salt'
    start = time.perf_counter()
    result = get_lessons(error, '', session_id='', project_name='test')
    elapsed = time.perf_counter() - start
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Root cause: {result.get('root_cause', '')[:80]}")
    print(f"  Fix: {result.get('fix_suggestion', '')[:80]}")
    print(f"  Confidence: {result.get('confidence', 0)}")
    print(f"  Source: {result.get('source', '')}")
except Exception as e:
    print(f"  SKIP (API error: {e})")

print('\n' + '=' * 60)
print('Done')
