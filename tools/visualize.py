"""
如意学伴 · 学习数据可视化工具
生成答辩用的 6 张图表 PNG
用法：python visualize.py [data_bridge输出.json]
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from datetime import date, timedelta
import json, sys, os, subprocess

# ── 中文字体 ──────────────────────────────────────────
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'outputs')
os.makedirs(OUTPUT, exist_ok=True)

# ── 配色 ──────────────────────────────────────────────
DARK_BG  = '#0F1A3A'
GOLD     = '#D4A843'
BLUE     = '#3B82F6'
GREEN    = '#10B981'
RED      = '#EF4444'
ORANGE   = '#F59E0B'
PURPLE   = '#8B5CF6'
CYAN     = '#06B6D4'
WHITE    = '#F8FAFC'
CARD     = '#1E293B'
GRID     = '#334155'

plt.style.use('dark_background')

# ── 默认示例数据（无 data_bridge 输入时使用）──────────────
WEEKDAYS = ['周一','周二','周三','周四','周五','周六','周日']
completion = [1.0, 0.75, 1.0, 0.5, 0.75, 0.0, 0.0]   # 完成率
hours      = [4, 3, 4, 2, 3, 0, 0]                    # 实际学时
subjects  = {'数据结构': 8, '操作系统': 5, '计算机网络': 3, '组成原理': 2}
weak     = {'红黑树': 3, 'PV操作': 2, '进程调度': 2, 'IP协议': 1, '链表': 1}
pomo_completed = [4, 3, 5, 2, 4, 0, 0]
pomo_interrupted = [1, 0, 2, 1, 0, 0, 0]
pomo_subjects = {'数据结构': 8, '操作系统': 5, '计算机网络': 3, '组成原理': 2}

# ═══════════════════════════════════════════════════════
# 数据加载：可选传入 data_bridge 输出的 JSON
# ═══════════════════════════════════════════════════════
USE_REAL = False
_data_file = sys.argv[1] if len(sys.argv) > 1 else None
if _data_file and os.path.exists(_data_file):
    with open(_data_file, encoding='utf-8') as f:
        _real = json.load(f)
    USE_REAL = _real.get('_meta', {}).get('data_is_real', False)
    if USE_REAL:
        weeks = _real.get('week_labels', WEEKDAYS)
        completion = _real['completion']
        hours = _real['hours']
        subjects = _real.get('subjects', subjects)
        pomo_completed = _real.get('pomo_completed', pomo_completed)
        pomo_interrupted = _real.get('pomo_interrupted', pomo_interrupted)
        pomo_subjects = _real.get('pomo_subjects', pomo_subjects)
        weak = _real.get('weak', weak)
TAG = ' [真实数据]' if USE_REAL else ''

# =====================================================
# 图表 1：每日完成率 + 学习时长（柱状图 + 折线图）
# =====================================================
fig, ax1 = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor(DARK_BG)
ax1.set_facecolor(DARK_BG)

x = np.arange(len(WEEKDAYS))
bars = ax1.bar(x, hours, color=GOLD, alpha=0.85, width=0.55, label='学习时长 (h)',
               edgecolor=GOLD, linewidth=0.5)
ax1.set_ylabel('学习时长 (h)', color=GOLD, fontsize=11)
ax1.set_ylim(0, 5)
ax1.tick_params(axis='y', colors=GOLD)

ax2 = ax1.twinx()
line = ax2.plot(x, completion, color=CYAN, marker='o', linewidth=2.5, markersize=9,
                label='完成率', markerfacecolor=CYAN, markeredgecolor=WHITE)
for i, (v, h) in enumerate(zip(completion, hours)):
    if v > 0:
        ax2.annotate(f'{v:.0%}', (i, v+0.04), color=CYAN, fontsize=10, ha='center', fontweight='bold')
    if h > 0:
        ax1.annotate(f'{h}h', (i, h+0.1), color=GOLD, fontsize=9, ha='center')
ax2.set_ylabel('完成率', color=CYAN, fontsize=11)
ax2.set_ylim(0, 1.2)
ax2.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax2.set_yticklabels(['0%','25%','50%','75%','100%'])
ax2.tick_params(axis='y', colors=CYAN)

ax1.set_xticks(x)
ax1.set_xticklabels(WEEKDAYS, fontsize=11)
ax1.grid(axis='y', alpha=0.15, color=WHITE)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labels1+labels2, loc='upper right', fontsize=10)
ax1.set_title(f'本周学习完成率趋势{TAG}', color=WHITE, fontsize=15, fontweight='bold', pad=15)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT, '01_完成率趋势.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print('✅ 01_完成率趋势.png')

# =====================================================
# 图表 2：科目时间分配（饼图 + 柱状图）
# =====================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
fig.patch.set_facecolor(DARK_BG)

# 饼图
colors_pie = [GOLD, BLUE, GREEN, PURPLE]
wedges, texts, autotexts = ax1.pie(
    subjects.values(), labels=subjects.keys(), autopct='%1.1f%%',
    colors=colors_pie, startangle=90,
    textprops={'color': WHITE, 'fontsize': 10},
    pctdistance=0.6, wedgeprops={'edgecolor': DARK_BG, 'linewidth': 2}
)
for at in autotexts:
    at.set_fontweight('bold')
    at.set_fontsize(11)
ax1.set_title('科目时间占比', color=WHITE, fontsize=13, fontweight='bold')

# 柱状图
subj_names = list(subjects.keys())
subj_hours = list(subjects.values())
bars = ax2.barh(subj_names, subj_hours, color=colors_pie, height=0.55,
                edgecolor=WHITE, linewidth=0.3)
for bar, h in zip(bars, subj_hours):
    ax2.text(bar.get_width()+0.2, bar.get_y()+bar.get_height()/2,
             f'{h}h', va='center', color=WHITE, fontsize=11, fontweight='bold')
ax2.set_xlim(0, max(subj_hours)+2)
ax2.set_title('科目学习时长', color=WHITE, fontsize=13, fontweight='bold')
ax2.set_facecolor(DARK_BG)
ax2.grid(axis='x', alpha=0.15, color=WHITE)
ax2.tick_params(colors=WHITE, labelsize=11)
ax1.set_facecolor(DARK_BG)

fig.suptitle('本周科目时间分配', color=WHITE, fontsize=15, fontweight='bold', y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT, '02_科目分配.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print('✅ 02_科目分配.png')

# =====================================================
# 图表 3：艾宾浩斯复习日历
# =====================================================
fig, ax = plt.subplots(figsize=(10, 4))
fig.patch.set_facecolor(DARK_BG)
ax.set_facecolor(DARK_BG)

topics = ['链表', '栈和队列', '二叉树', '图', '排序算法']
learn_dates = [date(2026,7,20), date(2026,7,21), date(2026,7,22), date(2026,7,23), date(2026,7,24)]
ebbinghaus_intervals = [1, 2, 4, 7, 15]

for i, (topic, ld) in enumerate(zip(topics, learn_dates)):
    for j, interval in enumerate(ebbinghaus_intervals):
        rd = ld + timedelta(days=interval)
        day_num = (rd - date(2026,7,20)).days
        alpha = max(0.3, 1.0 - j*0.15)
        ax.scatter(day_num, i, s=140-15*j, color=GOLD, alpha=alpha, zorder=5-j,
                   edgecolors=WHITE if j==0 else 'none', linewidths=0.8)
        if j == 0:
            # 首次学习
            ax.scatter(day_num, i, s=200, color=BLUE, alpha=0.9, zorder=10,
                       edgecolors=WHITE, linewidths=1.5, marker='D', label='首次学习' if i==0 else '')

ax.set_yticks(range(len(topics)))
ax.set_yticklabels(topics, fontsize=11, color=WHITE)
ax.set_xticks(range(0, 22))
ax.set_xticklabels([(date(2026,7,20)+timedelta(days=d)).strftime('%m/%d') for d in range(0, 22)], rotation=45, fontsize=8, color=WHITE)
ax.set_xlim(-0.5, 21.5)
ax.grid(axis='x', alpha=0.1, color=WHITE)
ax.set_title('艾宾浩斯复习日历', color=WHITE, fontsize=15, fontweight='bold', pad=12)

# Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=BLUE, label='首次学习', alpha=0.9),
    Patch(facecolor=GOLD, label='复习节点', alpha=0.7),
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=10, facecolor=CARD)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT, '03_艾宾浩斯日历.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print('✅ 03_艾宾浩斯日历.png')

# =====================================================
# 图表 4：薄弱知识点排行
# =====================================================
fig, ax = plt.subplots(figsize=(8, 4.5))
fig.patch.set_facecolor(DARK_BG)
ax.set_facecolor(DARK_BG)

wp_sorted = sorted(weak.items(), key=lambda x: x[1], reverse=True)
names = [w[0] for w in wp_sorted]
counts = [w[1] for w in wp_sorted]
colors_bar = [RED if c >= 3 else ORANGE if c >= 2 else GOLD for c in counts]

bars = ax.barh(range(len(names)), counts, color=colors_bar, height=0.55,
               edgecolor=WHITE, linewidth=0.3)
for bar, c in zip(bars, counts):
    ax.text(bar.get_width()+0.1, bar.get_y()+bar.get_height()/2,
            f'{c}次', va='center', color=WHITE, fontsize=12, fontweight='bold')

ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=11, color=WHITE)
ax.set_xlim(0, max(counts)+1)
ax.invert_yaxis()
ax.grid(axis='x', alpha=0.1, color=WHITE)
ax.set_title('薄弱知识点排行', color=WHITE, fontsize=15, fontweight='bold', pad=12)

# 添加说明
ax.text(0.98, 0.02, '>=3次需重点突破  >=2次需关注  1次需留意',
        transform=ax.transAxes, fontsize=9, color='#94A3B8', ha='right')

fig.tight_layout()
fig.savefig(os.path.join(OUTPUT, '04_薄弱知识点.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print('✅ 04_薄弱知识点.png')

# =====================================================
# 图表 5：番茄钟统计（每日柱状图 + 科目饼图）
# =====================================================
# 示例数据
pomo_days = ['周一','周二','周三','周四','周五','周六','周日']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
fig.patch.set_facecolor(DARK_BG)

x = np.arange(len(pomo_days))
ax1.bar(x, pomo_completed, color=GREEN, alpha=0.85, width=0.55, label='完成', edgecolor=GREEN)
ax1.bar(x, pomo_interrupted, bottom=pomo_completed, color=RED, alpha=0.7, width=0.55, label='中断', edgecolor=RED)
ax1.set_xticks(x)
ax1.set_xticklabels(pomo_days, fontsize=10, color=WHITE)
ax1.set_ylabel('番茄数', color=WHITE, fontsize=11)
ax1.set_ylim(0, max(max(pomo_completed), max(pomo_interrupted), 1) + 2)
ax1.set_facecolor(DARK_BG)
ax1.grid(axis='y', alpha=0.1, color=WHITE)
ax1.tick_params(colors=WHITE)
ax1.legend(fontsize=9, facecolor=CARD, edgecolor='none')
ax1.set_title('每日番茄完成情况', color=WHITE, fontsize=13, fontweight='bold')

# Total label on bars
for i, (c, inter) in enumerate(zip(pomo_completed, pomo_interrupted)):
    if c+inter > 0:
        ax1.text(i, c+inter+0.15, str(c+inter), ha='center', color=WHITE, fontsize=9, fontweight='bold')

# 数据全为零时兜底
_pie_data = pomo_subjects if sum(pomo_subjects.values()) > 0 else {'暂无数据': 1}
colors_pie = [GOLD, BLUE, GREEN, PURPLE]
wedges, texts, autotexts = ax2.pie(
    _pie_data.values(), labels=_pie_data.keys(), autopct='%1.1f%%',
    colors=colors_pie, startangle=90,
    textprops={'color': WHITE, 'fontsize': 10},
    wedgeprops={'edgecolor': DARK_BG, 'linewidth': 2}
)
for at in autotexts:
    at.set_fontweight('bold')
ax2.set_title('各科番茄专注占比', color=WHITE, fontsize=13, fontweight='bold')
ax2.set_facecolor(DARK_BG)

fig.suptitle('番茄钟专注统计', color=WHITE, fontsize=15, fontweight='bold', y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT, '05_番茄统计.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print('✅ 05_番茄统计.png')

# =====================================================
# 图表 6：番茄勋章进度
# =====================================================
fig, ax = plt.subplots(figsize=(8, 3))
fig.patch.set_facecolor(DARK_BG)
ax.set_facecolor(DARK_BG)
ax.set_xlim(0, 8)
ax.set_ylim(0, 1)
ax.axis('off')

badges = [
    ('新手的第一个番茄', 1, '🌱'),
    ('专注达人', 4, '🍅'),
    ('番茄大师', 8, '🏆'),
    ('自律王者', 30, '👑'),
]
y_positions = [0.7, 0.5, 0.3, 0.1]
earned = 5  # example: user has 5 completed pomodoros today

for i, (name, threshold, emoji) in enumerate(badges):
    y = y_positions[i]
    earned_bool = earned >= threshold
    color = GOLD if earned_bool else GRID
    alpha = 1.0 if earned_bool else 0.4
    ax.barh(y, min(earned, threshold)/threshold, height=0.12, left=0.1,
            color=GOLD, alpha=alpha)
    ax.barh(y, 1, height=0.12, left=0.1, color=GRID, alpha=0.3, zorder=0)
    ax.text(0.05, y, emoji, fontsize=16, va='center', color=GOLD if earned_bool else GRID)
    ax.text(0.22, y+0.02, name, fontsize=11, color=GOLD if earned_bool else WHITE, fontweight='bold')
    ax.text(0.95, y+0.02, f'{threshold}个', fontsize=9, color=WHITE, ha='right', alpha=alpha)

ax.set_title('番茄勋章进度', color=WHITE, fontsize=15, fontweight='bold', pad=15)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT, '06_番茄勋章.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print('✅ 06_番茄勋章.png')

print(f'\n📁 全部图表已保存到: {OUTPUT}')
for f in sorted(os.listdir(OUTPUT)):
    if f.endswith('.png'):
        size = os.path.getsize(os.path.join(OUTPUT, f))
        print(f'  {f} ({size//1024} KB)')
