"""
如意学伴仪表盘 — 本地 API 服务器
启动: python server.py  → http://localhost:8765
"""
import http.server, json, os, re, subprocess, sys, uuid, webbrowser
from pathlib import Path
from urllib.parse import urlparse

PORT = 8765
THIS_DIR = Path(__file__).parent
HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
KB_DIR = Path("D:/Ruyi_study_buddy/kb")
QUIZ_BANK_DIR = Path("D:/Ruyi_study_buddy/quiz_bank")
STATE_FILE = HERMES_HOME / "pomodoro_state.json"
SESSIONS_FILE = HERMES_HOME / "pomodoro_sessions.json"
PLAN_FILE = HERMES_HOME / "study_plan.json"
WEAK_FILE = HERMES_HOME / "weak_points.json"
POMODORO_TOOL = str(THIS_DIR.parent / "tools" / "pomodoro.py")
PUSH_TOOL = str(THIS_DIR.parent / "tools" / "push_wechat.py")

# ===== 知识库检索 =====
KB_SUBJECTS = {
    "01-数据结构.md": ["数据结构", "线性表", "栈", "队列", "二叉树", "图", "排序", "查找", "红黑树", "B树", "B+树", "散列", "哈希", "KMP", "并查集", "哈夫曼", "拓扑排序", "最短路径", "最小生成树", "深度优先", "广度优先", "DFS", "BFS", "链表", "数组", "堆", "AVL"],
    "02-操作系统.md": ["操作系统", "进程", "线程", "死锁", "PV操作", "信号量", "内存管理", "分页", "分段", "虚拟内存", "文件系统", "磁盘调度", "银行家算法", "页面置换", "FIFO", "LRU", "管程", "SPOOLing", "DMA", "系统调用", "临界区", "PCB", "FCB", "inode", "中断", "内核"],
    "03-计算机网络.md": ["计算机网络", "TCP", "UDP", "IP", "HTTP", "HTTPS", "DNS", "OSI", "网络层", "传输层", "路由器", "交换机", "三次握手", "四次挥手", "子网", "CIDR", "RIP", "OSPF", "BGP", "ARP", "CSMA/CD", "CRC", "SMTP", "FTP", "拥塞控制"],
    "04-计算机组成原理.md": ["计算机组成", "CPU", "存储器", "指令", "流水线", "补码", "反码", "浮点", "IEEE 754", "Cache", "DMA", "总线", "ALU", "寻址", "RISC", "CISC", "SRAM", "DRAM", "中断", "I/O"],
    "05-数据库系统.md": ["数据库", "SQL", "范式", "事务", "索引", "ACID", "BCNF", "关系代数", "并发控制", "封锁", "DDL", "DML", "DCL", "连接查询", "子查询", "B+树", "聚簇索引"],
    "06-编程语言基础.md": ["C语言", "C ", "Java", "Python", "指针", "面向对象", "集合", "多线程", "装饰器", "生成器", "JVM", "结构体", "动态内存", "类型系统", "编译", "解释", "OOP"],
    "07-算法思想.md": ["算法", "分治", "贪心", "动态规划", "DP", "回溯", "分支限界", "递归", "N皇后", "背包", "最长公共子序列", "归并排序", "快速排序", "哈夫曼编码", "旅行商"],
    "08-常见面试题.md": ["面试题", "面试", "高频", "考点", "面经", "408真题"],
    "09-学习路线图.md": ["学习路线", "考研", "复习计划", "阶段", "备考", "冲刺", "零基础"],
    "10-推荐资源清单.md": ["资源", "书籍", "课程", "推荐", "教材", "视频", "刷题平台", "B站", "慕课", "LeetCode", "牛客"],
}

def load_kb_context(question):
    """根据问题关键词匹配最相关的知识库文档，返回上下文文本"""
    if not KB_DIR.exists():
        return ""
    q = question.lower()
    scores = {}
    for fname, keywords in KB_SUBJECTS.items():
        score = sum(1 for kw in keywords if kw.lower() in q)
        if score > 0:
            scores[fname] = score
    if not scores:
        return ""  # 未匹配到任何知识库
    # 取得分最高的前2个文件
    top = sorted(scores, key=scores.get, reverse=True)[:2]
    parts = []
    for fname in top:
        fpath = KB_DIR / fname
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        # 截取前 1500 字，避免 token 过多
        if len(content) > 1500:
            content = content[:1500] + "\n\n... (内容已截断)"
        parts.append(content)
    if not parts:
        return ""
    context = "【知识库参考】以下是你必须参考的知识库文档内容，请严格基于此回答：\n\n"
    context += "\n\n---\n\n".join(parts)
    context += "\n\n【用户问题】"
    return context

# ===== 刷题系统 =====
SUBJECT_MAP = {
    "数据结构": "01-数据结构.md", "操作系统": "02-操作系统.md",
    "计算机网络": "03-计算机网络.md", "计算机组成原理": "04-计算机组成原理.md",
    "数据库系统": "05-数据库系统.md", "数据库": "05-数据库系统.md",
    "编程语言": "06-编程语言基础.md", "算法思想": "07-算法思想.md", "算法": "07-算法思想.md",
}
SUBJECT_NAMES = {v: k for k, v in SUBJECT_MAP.items()}

def clean_markdown(text):
    """去除KB文档中的Markdown格式符号，保留可读纯文本"""
    if not text:
        return ""
    # 去除标题标记：### 题型X：
    text = re.sub(r'###\s*题型\s*\d*\s*[：:]', '', text)
    # 去除加粗标记 **...** 但保留内容
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # 去除 inline code 标记 `...`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 去除水平分割线
    text = re.sub(r'\n-{3,}\n?', '\n', text)
    # 去除代码块标记 ```...```（保留内容）
    text = re.sub(r'```\w*\n?', '', text)
    # 去除大于引用标记
    text = re.sub(r'^> ?', '', text, flags=re.MULTILINE)
    # 去除多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 去除表格分隔行 |---|
    text = re.sub(r'\|[-\s|]+\|', '', text)
    # 去除特殊符号（保留中文标点、字母数字、换行）
    # text = re.sub(r'[★☆⬆⬇→]', '', text)  # 保留这些作为视觉提示
    return text.strip()

def load_quiz_bank(subject=None, qtype=None):
    """从本地缓存题库加载选择题"""
    if not QUIZ_BANK_DIR.exists():
        return []
    bank = []
    for f in sorted(QUIZ_BANK_DIR.glob("*.json")):
        try:
            qs = json.loads(f.read_text(encoding="utf-8"))
            subj_name = f.stem
            for q in qs:
                q["id"] = f"qz_{uuid.uuid4().hex[:8]}"
                q["subject"] = subj_name
                q["source"] = "cached"
                q["type"] = q.get("type", "choice")
                if subject and subj_name != subject:
                    continue
                if qtype and q.get("type") != qtype:
                    continue
                bank.append(q)
        except:
            pass
    return bank

def extract_quiz_problems(subject=None, topic=None, count=3, qtype=None):
    """搜题：缓存题库 > KB提取 > AI生成"""
    # 1. 优先查缓存题库
    cached = load_quiz_bank(subject=subject, qtype=qtype)
    if cached:
        import random
        random.shuffle(cached)
        return cached[:count]
    # 2. KB文档提取
    if not KB_DIR.exists():
        return []
    candidates = []
    if subject:
        fname = SUBJECT_MAP.get(subject)
        if fname:
            candidates = [fname]
    if not candidates:
        for fname in KB_SUBJECTS:
            if any(kw in (topic or "") for kw in KB_SUBJECTS[fname]):
                candidates.append(fname)
        if not candidates:
            candidates = sorted(KB_DIR.glob("0[1-7]*.md"))
            candidates = [f.name for f in candidates]
    problems = []
    for fname in candidates[:2]:
        fpath = KB_DIR / fname
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        m = re.search(r'##\s*三、常见题型.*?(?=\n##\s)', content, re.DOTALL)
        if not m:
            m = re.search(r'##\s*常见题型.*?(?=\n##\s)', content, re.DOTALL)
        if not m:
            m = re.search(r'##\s*三、常见题型.*', content, re.DOTALL)
        if not m:
            continue
        section = m.group()
        blocks = re.split(r'\n(?=###\s*题型)', section)
        subj = SUBJECT_NAMES.get(fname, fname.replace(".md", ""))
        for block in blocks[1:]:
            title_m = re.match(r'###\s*题型\s*\d*\s*[：:](.*)', block)
            title = title_m.group(1).strip() if title_m else "未命名题目"
            # 提取知识点标签（支持 **考点**：和 考点：两种格式）
            kp_matches = re.findall(r'(?:\*\*)?考点(?:\*\*)?[：:]\s*(.*?)(?:\n|$)', block)
            knowledge = kp_matches[0].strip() if kp_matches else topic or ""
            # 推断题目类型：有A/B/C/D选项的为选择题，否则为简答题
            has_options = bool(re.search(r'(?:^|\n)\s*[A-D][.、．)\s]', block, re.MULTILINE))
            qtype_detected = "choice" if has_options else "short"
            # 分离题干与解题思路/答案：切分点在"答案"、"解答"、"思路"、"解题思路"等标记处
            # 优先在"思路"处切（思路 ≠ 题目），其次在"答案"处切
            solution_markers = r'(?:\*\*)?(?:答案|解答|标准答案|正确答案|思路|解题思路|方法总结|关键点)(?:\*\*)?[^：:\n]{0,10}[：:]'
            split_parts = re.split(r'\n\s*' + solution_markers, block)
            question_only = split_parts[0].strip()
            # 提取所有被切掉的部分作为"答案/解析"（用于 AI 批改参考）
            answer_text = "\n".join(split_parts[1:]).strip() if len(split_parts) > 1 else ""
            # 清理题干中的Markdown格式符号（保留纯文本+换行+代码块）
            q_content = clean_markdown(question_only[:1000])
            answer_clean = clean_markdown(answer_text[:500])
            problems.append({
                "id": f"qz_{uuid.uuid4().hex[:8]}",
                "subject": subj,
                "topic": title,
                "type": qtype_detected,
                "knowledge_points": [kp.strip() for kp in knowledge.replace("、", ",").split(",") if kp.strip()],
                "content": q_content,
                "answer": answer_clean,
                "has_answer": bool(answer_clean),
                "source": "kb",
                "source_file": fname,
            })
    if not problems and (subject or topic):
        problems = ai_generate_problems(subject or topic, topic, min(count, 3), qtype)
    # 按类型过滤
    if qtype and qtype in ("choice", "short"):
        problems = [p for p in problems if p.get("type") == qtype]
        # 过滤后为空 → AI 生成指定题型
        if not problems and (subject or topic):
            problems = ai_generate_problems(subject or topic, topic, min(count, 3), qtype)
    return problems[:count]

def ai_generate_problems(subject, topic, count=3, qtype=None):
    """AI生成题目（KB无匹配时降级方案）"""
    type_hint = ""
    if qtype == "choice":
        type_hint = f'请生成{count}道**选择题**，每题4个选项（A/B/C/D），"type"字段填"choice"。'
    elif qtype == "short":
        type_hint = f'请生成{count}道**简答题**，"type"字段填"short"，options为空数组。'
    else:
        type_hint = f'请生成{count}道经典题目（选择题或简答题均可）。'
    prompt = f"""请为"{subject}"学科生成题目，知识点为"{topic}"。{type_hint}
返回JSON数组格式：[{{"type":"choice|short","content":"题目描述","options":["A...","B...","C...","D..."],"answer":"正确答案","knowledge_points":["知识点1","知识点2"]}}]
选择题："type":"choice"，options为四个选项数组。简答题："type":"short"，options为空数组[]。"""
    try:
        r = subprocess.run(["hermes", "chat", "-q", prompt, "-Q", "-m", "deepseek-v4-flash"],
                           capture_output=True, text=True, timeout=60)
        ans = r.stdout.strip()
        # 尝试提取JSON
        json_m = re.search(r'\[[\s\S]*\]', ans)
        if json_m:
            data = json.loads(json_m.group())
            result = []
            for item in data:
                result.append({
                    "id": f"qz_{uuid.uuid4().hex[:8]}",
                    "subject": subject,
                    "topic": item.get("knowledge_points", [topic])[0] if item.get("knowledge_points") else topic,
                    "knowledge_points": item.get("knowledge_points", [topic]),
                    "type": item.get("type", "short"),
                    "content": item.get("content", ""),
                    "options": item.get("options", []),
                    "answer": item.get("answer", ""),
                    "source": "ai_generated",
                })
            return result
        return []
    except:
        return []

def evaluate_answer(question, user_answer):
    """批改用户答案：选择题精确比对，简答题关键词匹配，秒出结果"""
    kps = question.get("knowledge_points", [])
    ref_answer = question.get("answer", "")
    q_type = question.get("type", "short")

    # 选择题：精确比对 + 题目自带解析
    if q_type == "choice":
        user_clean = user_answer.strip().upper().replace(" ", "")
        ref_clean = (ref_answer or "").strip().upper().replace(" ", "")
        correct = user_clean == ref_clean
        builtin_analysis = question.get("analysis", "")
        if correct:
            msg = f"正确！{builtin_analysis}" if builtin_analysis else "回答正确！"
        else:
            correct_option = ref_answer
            correct_text = ""
            for opt in question.get("options", []):
                if opt.strip().upper().startswith(correct_option.upper()):
                    correct_text = opt
                    break
            msg = f"错误。正确答案是 {correct_text or correct_option}。{builtin_analysis}" if builtin_analysis else f"错误。正确答案是 {correct_text or correct_option}"
        return {
            "correct": correct,
            "knowledge_points": kps,
            "analysis": msg,
            "correct_answer": ref_answer,
            "root_cause": "" if correct else "概念不清",
        }

    # 简答题：关键词匹配
    if not ref_answer or len(ref_answer) < 5:
        return {"correct": True, "knowledge_points": kps,
                "analysis": "暂无标准答案，已记录你的作答", "correct_answer": "", "root_cause": ""}

    # 提取关键词（中文按字切，英文按词切）
    import re as _re
    def extract_keywords(text):
        # 提取中文词和英文词
        cn = _re.findall(r'[\u4e00-\u9fff]{2,}', text)
        en = _re.findall(r'[a-zA-Z_]\w+', text.lower())
        return set(cn + en)

    user_kw = extract_keywords(user_answer)
    ref_kw = extract_keywords(ref_answer)
    if not ref_kw:
        return {"correct": True, "knowledge_points": kps,
                "analysis": "已记录你的作答", "correct_answer": ref_answer[:200], "root_cause": ""}

    overlap = len(user_kw & ref_kw)
    ratio = overlap / len(ref_kw)
    if ratio >= 0.4:
        return {"correct": True, "knowledge_points": kps,
                "analysis": f"回答基本正确（关键词匹配率 {int(ratio*100)}%），继续加油！",
                "correct_answer": ref_answer[:300], "root_cause": ""}
    elif ratio >= 0.15:
        return {"correct": False, "knowledge_points": kps,
                "analysis": f"部分正确但缺少关键要点（匹配率 {int(ratio*100)}%）。请对照标准答案补充。",
                "correct_answer": ref_answer[:300], "root_cause": "理解不透"}
    else:
        return {"correct": False, "knowledge_points": kps,
                "analysis": "回答与标准答案差距较大，建议复习该知识点后重试。",
                "correct_answer": ref_answer[:300], "root_cause": "概念不清"}

def call_push(mode, *args):
    try:
        r = subprocess.run([sys.executable, PUSH_TOOL, mode] + list(args),
                           capture_output=True, text=True, timeout=15)
        return json.loads(r.stdout)
    except Exception as e:
        return {"errcode": -1, "errmsg": str(e)}

def read_json(p, default=None):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except: return default if default is not None else {}

def write_json(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_streak():
    """从 sessions 计算连续打卡天数"""
    sessions = read_json(SESSIONS_FILE, [])
    if not sessions:
        return {"current": 0, "best": 0, "today_active": False, "dates": []}
    # 提取所有有学习记录的日期（去重）
    study_dates = sorted(set(s.get("date", "") for s in sessions if s.get("date")))
    if not study_dates:
        return {"current": 0, "best": 0, "today_active": False, "dates": []}
    
    from datetime import date, timedelta
    today = date.today().isoformat()
    today_active = today in study_dates
    
    # 计算当前连续天数（从今天或昨天开始向前追溯）
    current_streak = 0
    check_date = date.today()
    if not today_active:
        check_date -= timedelta(days=1)  # 允许昨天也算活跃
    
    while check_date.isoformat() in study_dates:
        current_streak += 1
        check_date -= timedelta(days=1)
    
    # 计算历史最佳连续天数
    best_streak = 0
    temp_streak = 0
    prev = None
    for d_str in study_dates:
        d = date.fromisoformat(d_str)
        if prev is None:
            temp_streak = 1
        else:
            diff = (d - prev).days
            if diff == 1:
                temp_streak += 1
            elif diff == 0:
                continue  # 同一日多条记录
            else:
                temp_streak = 1
        best_streak = max(best_streak, temp_streak)
        prev = d
    
    # 最近30天的活跃日期（用于热力图小方块）
    last_7 = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        last_7.append({"date": d, "active": d in study_dates, "day_of_week": date.fromisoformat(d).weekday()})
    
    return {"current": current_streak, "best": best_streak, "today_active": today_active, "dates": last_7}

def call_pomodoro(cmd, **kw):
    a = [sys.executable, POMODORO_TOOL, cmd]
    if cmd == "start":
        a.append(kw.get("subject", ""))
        if kw.get("topic"): a.append(kw["topic"])
    try:
        r = subprocess.run(a, capture_output=True, text=True, timeout=10)
        return json.loads(r.stdout)
    except Exception as e:
        return {"success": False, "message": str(e)}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(THIS_DIR), **kw)

    def _json(self, d, code=200):
        body = json.dumps(d, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path).path
        routes = {
            "/api/state": lambda: read_json(STATE_FILE, {"status": "idle"}),
            "/api/sessions": lambda: read_json(SESSIONS_FILE, []),
            "/api/plan": lambda: read_json(PLAN_FILE, {}),
            "/api/weak_points": lambda: read_json(WEAK_FILE, []),
            "/api/streak": lambda: compute_streak(),
        }
        if p in routes: self._json(routes[p]())
        else: super().do_GET()

    def do_POST(self):
        p = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8")) if length > 0 else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            try:
                body = json.loads(raw.decode("gbk", errors="replace")) if length > 0 else {}
            except:
                body = {}

        if p == "/api/pomodoro":
            cmd = body.get("command", "")
            result = call_pomodoro(cmd, subject=body.get("subject", ""), topic=body.get("topic", ""))
            
            # ── 微信推送 ──
            if result.get("success"):
                subj = result.get("subject", body.get("subject", ""))
                if cmd == "start":
                    count = len(read_json(SESSIONS_FILE, [])) + 1
                    call_push("pomo_start", subj, str(count))
                elif cmd == "stop":
                    s = result.get("session", {})
                    mins = s.get("duration_minutes", 0)
                    if mins >= 25:
                        call_push("pomo_end", "1", str(int(mins)), "1")
                    elif mins > 0:
                        call_push("pomo_interrupt", subj, str(int(mins)), "主动结束")
                    # ── 存储到 sessions ──
                    if s and mins > 0:
                        sess = read_json(SESSIONS_FILE, [])
                        sess.append(s)
                        write_json(SESSIONS_FILE, sess)
            
            self._json(result)

        elif p == "/api/plan/save":
            write_json(PLAN_FILE, body)
            self._json({"success": True})

        elif p == "/api/weak_points/save":
            write_json(WEAK_FILE, body)
            self._json({"success": True})

        elif p == "/api/weak_points/add":
            entry = body.get("entry", {})
            if entry:
                pts = read_json(WEAK_FILE, [])
                # 检查是否已存在相同科目+知识点
                existing = None
                for i, pt in enumerate(pts):
                    if pt.get("subject") == entry.get("subject") and pt.get("topic") == entry.get("topic"):
                        existing = i
                        break
                if existing is not None:
                    pts[existing]["error_count"] = pts[existing].get("error_count", 0) + 1
                    pts[existing]["last_error_date"] = entry.get("date", "")
                    if entry.get("mistake"): pts[existing]["last_mistake"] = entry["mistake"]
                    if entry.get("root_cause"): pts[existing]["root_cause"] = entry["root_cause"]
                else:
                    entry["error_count"] = 1
                    pts.append(entry)
                write_json(WEAK_FILE, pts)
                self._json({"success": True, "total": len(pts)})
            else:
                self._json({"error": "entry required"}, 400)

        elif p == "/api/reviews":
            from datetime import date, timedelta
            sdata = read_json(SESSIONS_FILE, [])
            reviews = []
            intervals = [1, 2, 4, 7, 15]
            td = date.today()
            for s in sdata:
                ld = s.get("date", "")
                if not ld or not s.get("subject"): continue
                try:
                    ld2 = date.fromisoformat(ld)
                    for iv in intervals:
                        rd = ld2 + timedelta(days=iv)
                        if td - timedelta(days=30) <= rd <= td + timedelta(days=30):
                            reviews.append({"date": rd.isoformat(), "subject": s["subject"], "topic": s.get("topic",""), "interval": iv, "status": "pending"})
                except: pass
            pdata = read_json(PLAN_FILE, {})
            for t in (pdata.get("tasks",[]) or []):
                if t.get("is_review"):
                    reviews.append({"date": t.get("date",""), "subject": t.get("subject",""), "topic": t.get("topic",""), "interval": 0, "status": t.get("status","pending")})
            self._json(reviews)

        elif p == "/api/upload":
            img_data = body.get("image", "")
            if img_data and img_data.startswith("data:image/"):
                import base64, uuid
                header, encoded = img_data.split(",", 1)
                ext = header.split(";")[0].split("/")[-1]
                ext = ext if ext in ("png","jpg","jpeg","gif","webp") else "png"
                fn = f"uploads/{uuid.uuid4().hex}.{ext}"
                fp = THIS_DIR / fn
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(base64.b64decode(encoded))
                self._json({"success": True, "path": fn})
            else:
                self._json({"error": "invalid image data"}, 400)

        elif p == "/api/push":
            result = call_push(body.get("type", "morning"),
                str(body.get("arg1", "")), str(body.get("arg2", "")), str(body.get("arg3", "")))
            self._json(result)

        elif p == "/api/chat":
            q = body.get("question", "")
            if not q:
                self._json({"error": "问题为空"}, 400); return
            # 加载知识库上下文
            kb_ctx = load_kb_context(q)
            if kb_ctx:
                full_q = kb_ctx + q
            else:
                full_q = q
            try:
                r = subprocess.run(["hermes", "chat", "-q", full_q, "-Q", "-m", "deepseek-v4-flash"],
                                   capture_output=True, text=True, timeout=120)
                ans = r.stdout.strip() or r.stderr.strip()
            except FileNotFoundError:
                self._json({"error": "Hermes CLI 未安装或不在 PATH 中。请在终端中安装 Hermes Agent，或者直接在聊天窗口提问。", "fallback": True}, 503); return
            except subprocess.TimeoutExpired:
                self._json({"error": "回答超时"}, 504); return
            except Exception as e:
                self._json({"error": str(e)}, 500); return
            try:
                ans = re.sub(r'\x1b\[[0-9;]*m', '', ans)
                ans = re.sub(r'^Query:.*?\n', '', ans)
                ans = re.sub(r'Initializing.*?\n', '', ans)
                ans = re.sub(r'[╭╰─│╮╯]{2,}.*?\n?', '', ans)
                ans = re.sub(r'Resume.*?\n', '', ans)
                ans = re.sub(r'Session:.*?\n', '', ans)
                ans = re.sub(r'Duration:.*?\n', '', ans)
                ans = re.sub(r'Messages:.*?\n?', '', ans)
                ans = re.sub(r'hermes --resume.*?\n?', '', ans)
                ans = re.sub(r'^\s*\d+\s*\(.*?\)\s*$', '', ans)
                ans = ans.strip()
                self._json({"answer": ans[:4000]})
            except subprocess.TimeoutExpired:
                self._json({"error": "回答超时"}, 504)
            except Exception as e:
                self._json({"error": str(e)}, 500)

        elif p == "/api/quiz/search":
            subject = body.get("subject", "")
            topic = body.get("topic", "")
            count = body.get("count", 3)
            qtype = body.get("type", "")  # "choice" | "short" | ""
            if not subject and not topic:
                self._json({"error": "subject或topic至少传一个"}, 400); return
            questions = extract_quiz_problems(subject=subject, topic=topic, count=count, qtype=qtype)
            self._json({"questions": questions, "total": len(questions)})

        elif p == "/api/quiz/submit":
            print(f"[SUBMIT] qid={body.get('question_id','?')[:20]} user_ans_len={len(body.get('user_answer',''))} q_len={len(str(body.get('question',{})))}", flush=True)
            qid = body.get("question_id", "")
            user_answer = body.get("user_answer", "")
            question = body.get("question", {})
            if not user_answer:
                self._json({"error": "答案不能为空"}, 400); return
            result = evaluate_answer(question, user_answer)
            # 错题自动入库
            if not result.get("correct", False):
                from datetime import date
                entry = {
                    "subject": question.get("subject", ""),
                    "topic": question.get("topic", ""),
                    "date": date.today().isoformat(),
                    "question_content": question.get("content", ""),
                    "wrong_answer": user_answer,
                    "correct_answer": result.get("correct_answer", ""),
                    "options_text": "\n".join(question.get("options", [])) if question.get("options") else "",
                    "root_cause": result.get("root_cause", ""),
                }
                pts = read_json(WEAK_FILE, [])
                entry["error_count"] = 1
                pts.append(entry)
                write_json(WEAK_FILE, pts)
                result["auto_mistake_added"] = True
            else:
                result["auto_mistake_added"] = False
            self._json(result)

        elif p == "/api/quiz/recommend":
            pts = read_json(WEAK_FILE, [])
            if not pts:
                self._json({"recommendations": [], "message": "暂无错题记录，先去学习吧！"})
            else:
                # 按error_count排序，推荐最薄弱知识点
                pts_sorted = sorted(pts, key=lambda x: x.get("error_count", 0), reverse=True)
                recs = []
                for pt in pts_sorted[:5]:
                    recs.append({
                        "subject": pt.get("subject", ""),
                        "topic": pt.get("topic", ""),
                        "error_count": pt.get("error_count", 0),
                        "root_cause": pt.get("root_cause", ""),
                    })
                self._json({"recommendations": recs})

        elif p == "/api/weak_points/delete":
            idx = body.get("index", -1)
            if idx < 0:
                self._json({"error": "index required"}, 400); return
            pts = read_json(WEAK_FILE, [])
            if 0 <= idx < len(pts):
                del pts[idx]
                write_json(WEAK_FILE, pts)
                self._json({"success": True, "total": len(pts)})
            else:
                self._json({"error": "index out of range"}, 400)

        else:
            self._json({"error": "not found"}, 404)

def main():
    print(f"如意学伴 http://localhost:{PORT}")
    srv = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    try: srv.serve_forever()
    except KeyboardInterrupt: srv.server_close()

if __name__ == "__main__":
    main()
