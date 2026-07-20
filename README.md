# 如意学伴（Ruyi Study Buddy）

> 基于 Hermes Agent 的三角色智能学习管家  
> 北京科技大学 2026 生产实习 · 人工智能方向

## 一句话描述

打开 Hermes，告诉它你的考试目标和每天可用时间，它自动帮你制定学习计划、按艾宾浩斯遗忘曲线插入复习、答疑时用费曼讲解法、每天微信早晚推送提醒。**所有代码由 Hermes Agent 生成，组员零手写。**

## 产品形态

```
你打开 Hermes → 加载 SKILL.md → Hermes 变成学习管家
```

不是一个独立 App，Hermes **本身就是产品**。

## 三角色系统

| 角色 | 触发方式 | 行为 |
|------|----------|------|
| 🎯 规划师 | "制定计划" / "调整计划" | 调用 ebbinghaus 工具生成周计划 + 约束校验 |
| 🧠 答疑导师 | 问知识点 | 费曼讲解 + 反提问检验 + 错题提醒 |
| ❤️ 督学伙伴 | "完成了XX" / 定时推送 | 更新进度 + 鼓励 + 难度调整建议 |

## 项目结构

```
Ruyi_study_buddy/
├── README.md                    # 本文件
├── SKILL.md                     # 🎯 核心：三角色 Skill 定义（Hermes 加载）
├── tools/                       # 3 个轻量 Python 工具（Hermes 注册调用）
│   ├── ebbinghaus.py            #   艾宾浩斯复习日期计算器
│   ├── constraint_checker.py    #   计划约束校验器
│   └── mistake_retriever.py     #   错题检索器
├── docs/                        # 文档
│   ├── 设计方案.md              #   完整设计方案
│   └── 测试报告.md              #   测试报告模板
├── outputs/                     # 导出示例
└── assets/                      # 截图等素材
```

## 快速开始

### 1. 加载 Skill

在 Hermes 中把 `SKILL.md` 注册为 Skill，或直接让 Hermes 读取：

```
hermes chat -f SKILL.md
```

### 2. 注册工具

```bash
# 将三个 Python 工具注册到 Hermes
hermes tools register tools/ebbinghaus.py
hermes tools register tools/constraint_checker.py
hermes tools register tools/mistake_retriever.py
```

### 3. 配置微信推送

```bash
# 配置企业微信 Webhook（一次性）
hermes gateway setup wecom --webhook-url "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"

# 创建定时推送任务
hermes cron create --schedule "0 8 * * *" --prompt "生成今日学习早报推送到微信"
hermes cron create --schedule "0 22 * * *" --prompt "生成今日学习晚报送微信"
```

### 4. 开始使用

直接在 Hermes 里说话：

- "下周五考数据结构，每天能学4小时，帮我制定计划"
- "红黑树怎么旋转？"
- "已完成数据结构第3章"
- "本周总结"

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 引擎 | Hermes Agent + DeepSeek v4-flash |
| 角色定义 | SKILL.md（Markdown） |
| 计算工具 | Python 3（ebbinghaus / constraint / mistake） |
| 数据存储 | Hermes 内置 Memory（本地 JSON） |
| 定时推送 | Hermes Cron + Gateway（企业微信 Webhook） |
| 导出 | Hermes 直接生成 PDF / MD / JSON |

## 四人分工

| 角色 | 核心任务 |
|------|----------|
| Skill 架构师 | SKILL.md 编写调优 + Cron 配置 |
| 工具与测试工程师 | 3 个 Python 工具生成 + 微信推送 + 测试 |
| 数据工程师 | Memory 结构设计 + 导出示例 + 数据图表 |
| 文档工程师 | 仓库维护 + 实验报告 + 视频录制 |

## 隐私

- 学习数据 100% 本地存储（`~/.hermes/`）
- 不上传任何第三方
- API Key 存 `.env`，已加入 `.gitignore`
