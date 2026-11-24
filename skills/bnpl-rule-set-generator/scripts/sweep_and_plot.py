"""BNPL 参数扫描 + 四图对比（探索模式入口）。

设计（方案 A）：
- 对 max_depth ∈ depth_list 各跑一次 bnbl.run_once，max_intercept 固定为
  用户给定拦截率区间的上限。
- 每份 rule_set 明细的“累计列”本身就是一条从小到大的完整曲线，据此画图：
    * 图1：全样本 FPD7 压降率 vs check 累计拦截率
    * 图2：OOT FPD7 压降率  vs check 累计拦截率
    * 图3：累计召回 FPD7 金额占比 vs check 累计拦截率
    * 图4：最优规则集规则数量 vs check 累计拦截率
- 图1/2/3 的每个节点标注“较前一节点在纵轴上增加的百分点”（+N）。
- 每条曲线代表一个 max_depth 取值。

关键约定：
- depth_list 与拦截率区间（min,max,step）均为**必填、无默认、缺失即报错**。
- 复用 bnbl.run_once 作为唯一计算后端，不在本脚本重造任何建模/贪心逻辑，
  保证与生成模式口径一致。
"""

import argparse
import json
import os
from types import SimpleNamespace
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")  # 无显示环境
import matplotlib.pyplot as plt  # noqa: E402

import bnbl  # noqa: E402  同目录 import，复用 run_once


# rule_set.csv / run_once 返回 DataFrame 中用于画图的列名（与 bnbl.py 输出严格对齐）。
COL_INTERCEPT = "check表累计拦截率"
COL_DROP_ALL = "累计压降率"            # 全样本累计压降率（保留，兼容旧口径）
COL_DROP_TRAIN = "train累计压降率"     # 图1改用：train 累计压降率
COL_DROP_OOT = "oot累计压降率"
COL_RECALL_AMT = "累计召回FPD7金额占比"

# 多条 depth 曲线的固定配色（缺省时用 matplotlib 默认色循环兜底）。
_DEPTH_COLORS = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "BNPL max_depth × max_intercept 参数扫描与四图对比。对每个 max_depth "
            "跑一次 bnbl.run_once（max_intercept 取拦截率区间上限），据累计曲线画图。"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ---- 透传给 bnbl 的数据参数（与 bnbl.py 同名同义）----
    p.add_argument("--df-path", default="")
    p.add_argument("--check-path", default="")
    p.add_argument("--df-query", default="")
    p.add_argument("--check-query", default="")
    p.add_argument("--control-col", default="")
    p.add_argument("--control-value", default="")
    p.add_argument("--control-min-rows", type=int, default=5000)
    p.add_argument("--features", default="")
    p.add_argument("--exclude-cols", default="")
    p.add_argument("--date-col", default="")
    p.add_argument("--label-col", default="")
    p.add_argument("--amount-col", default="fpd7_ovd_num")
    p.add_argument("--principal-col", default="fpd7_principal_den")
    p.add_argument("--oot-start-date", default="")
    p.add_argument("--lift-threshold-train", type=float, default=None)
    p.add_argument("--lift-threshold-oot", type=float, default=None)
    p.add_argument("--fixed-feature-list", default="")
    p.add_argument("--xgboost-path", default=bnbl._DEFAULT_XGBOOST_PATH)

    # ---- 扫描专属参数（必填、无默认、缺失即报错）----
    p.add_argument(
        "--depth-list",
        default="",
        help="要对比的 max_depth 列表，逗号分隔，例如 '3,4,5'。必填，需用户显式提供。",
    )
    p.add_argument(
        "--intercept-range",
        default="",
        help=(
            "拦截率区间 'min,max,step'，例如 '0.10,0.20,0.02'。曲线画到 max 为止，"
            "各分割点作为横轴参考刻度。必填，需用户显式提供。"
        ),
    )

    # ---- 输出目录 ----
    p.add_argument(
        "--out-dir",
        default="",
        help="图与中间 rule_set/rule_pool CSV 的输出目录。必填，需用户显式提供。",
    )

    return p.parse_args()


def _validate_sweep_args(a: argparse.Namespace) -> None:
    """探索模式必填项校验：depth_list / intercept_range / out_dir 缺失即报错。"""
    if not a.depth_list:
        raise ValueError("--depth-list 为必填参数，请显式提供要对比的 max_depth 列表，例如 '3,4,5'。")
    if not a.intercept_range:
        raise ValueError(
            "--intercept-range 为必填参数，请显式提供拦截率区间 'min,max,step'，例如 '0.10,0.20,0.02'。"
        )
    if not a.out_dir:
        raise ValueError("--out-dir 为必填参数，请显式提供图与中间文件的输出目录。")
    # 透传给 bnbl 的必填项也在这里前置校验，避免跑到第一个 depth 才报错。
    if not a.df_path:
        raise ValueError("--df-path 为必填参数。")
    if not a.check_path:
        raise ValueError("--check-path 为必填参数。")
    if not a.date_col:
        raise ValueError("--date-col 为必填参数。")
    if not a.label_col:
        raise ValueError("--label-col 为必填参数。")
    if not a.oot_start_date:
        raise ValueError("--oot-start-date 为必填参数。")
    if a.lift_threshold_train is None:
        raise ValueError("--lift-threshold-train 为必填参数。")
    if a.lift_threshold_oot is None:
        raise ValueError("--lift-threshold-oot 为必填参数。")


def parse_depth_list(raw: str) -> List[int]:
    depths = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not depths:
        raise ValueError("--depth-list 解析后为空，请检查格式，例如 '3,4,5'。")
    return depths


def parse_intercept_range(raw: str):
    """解析 'min,max,step' -> (lo, hi, marks)。

    marks 为 [lo, lo+step, ..., hi]（含端点），作为横轴参考刻度；
    hi 同时作为本次扫描 max_intercept 的取值（方案 A：一次跑到上限）。
    """
    parts = [float(x.strip()) for x in raw.split(",") if x.strip()]
    if len(parts) != 3:
        raise ValueError("--intercept-range 必须是 'min,max,step' 三个值，例如 '0.10,0.20,0.02'。")
    lo, hi, step = parts
    if not (0 < lo < hi <= 1.0):
        raise ValueError("--intercept-range 需满足 0 < min < max <= 1（用小数表示，如 0.10 表示 10%）。")
    if step <= 0:
        raise ValueError("--intercept-range 的 step 必须为正数。")
    marks = []
    v = lo
    # 用整数步进避免浮点累加误差。
    n = int(round((hi - lo) / step))
    for i in range(n + 1):
        marks.append(round(lo + i * step, 10))
    if marks[-1] < hi - 1e-9:
        marks.append(hi)
    return lo, hi, marks


def build_params(a: argparse.Namespace, depth: int, max_intercept: float, out_dir: str) -> SimpleNamespace:
    """为单个 depth 组装 bnbl.run_once 需要的参数对象（等价于一份 argparse.Namespace）。"""
    rule_pool = os.path.join(out_dir, f"rule_pool_depth{depth}.csv")
    rule_set = os.path.join(out_dir, f"rule_set_depth{depth}.csv")
    return SimpleNamespace(
        df_path=a.df_path,
        check_path=a.check_path,
        df_query=a.df_query,
        check_query=a.check_query,
        control_col=a.control_col,
        control_value=a.control_value,
        control_min_rows=a.control_min_rows,
        features=a.features,
        exclude_cols=a.exclude_cols,
        date_col=a.date_col,
        label_col=a.label_col,
        amount_col=a.amount_col,
        principal_col=a.principal_col,
        oot_start_date=a.oot_start_date,
        lift_threshold_train=a.lift_threshold_train,
        lift_threshold_oot=a.lift_threshold_oot,
        max_intercept=max_intercept,  # 固定为区间上限
        fixed_feature_list=a.fixed_feature_list,
        max_depth=depth,  # 每轮变化的量
        xgboost_path=a.xgboost_path,
        rule_pool_path=rule_pool,
        rule_set_path=rule_set,
    )


def run_all_depths(a: argparse.Namespace, depths: List[int], max_intercept: float):
    """对每个 depth 调 bnbl.run_once，返回 {depth: rule_set_df}。

    单个 depth 抛异常不中断整体扫描；空规则池 run_once 返回空 DataFrame，画图端跳过。
    """
    results: Dict[int, "object"] = {}
    for d in depths:
        params = build_params(a, d, max_intercept, a.out_dir)
        print(f"\n===== 扫描 max_depth={d}, max_intercept={max_intercept} =====")
        try:
            results[d] = bnbl.run_once(params)
        except Exception as exc:  # noqa: BLE001 - 记录并跳过，保证其它 depth 继续
            print(f"[WARN] max_depth={d} 运行失败，跳过该曲线：{type(exc).__name__}: {exc}")
            results[d] = None
    return results


def _color_for(depth: int, depths: List[int]) -> str:
    idx = depths.index(depth) if depth in depths else 0
    return _DEPTH_COLORS[idx % len(_DEPTH_COLORS)]


def _pct(series):
    return (series.astype(float) * 100.0).to_numpy()


def _plot_curve_with_delta(ax, results, depths, ycol, title, ylabel, marks):
    """画一张带 +N 逐点百分点标注的对比图（图1/2/3）。"""
    for depth in depths:
        df = results.get(depth)
        if df is None or getattr(df, "empty", True) or ycol not in df.columns:
            continue
        df = df.sort_values(COL_INTERCEPT)
        x = _pct(df[COL_INTERCEPT])
        y = _pct(df[ycol])
        color = _color_for(depth, depths)
        ax.plot(x, y, marker="o", label=f"max_depth={depth}", color=color)
        # 逐点标注：较前一节点在纵轴上增加的百分点。
        for i in range(1, len(y)):
            ax.annotate(
                f"+{y[i] - y[i - 1]:.1f}",
                (x[i], y[i]),
                fontsize=7,
                textcoords="offset points",
                xytext=(0, 6),
                color=color,
            )
    for m in marks:
        ax.axvline(m * 100.0, ls="--", lw=0.5, color="grey", alpha=0.4)
    ax.set_title(title)
    ax.set_xlabel("Actual Intercept Rate (%)")
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(alpha=0.3)


def _plot_rule_count(ax, results, depths, marks):
    """图4：最优规则集规则数量（累计行号）vs check 累计拦截率。"""
    for depth in depths:
        df = results.get(depth)
        if df is None or getattr(df, "empty", True) or COL_INTERCEPT not in df.columns:
            continue
        df = df.sort_values(COL_INTERCEPT)
        x = _pct(df[COL_INTERCEPT])
        n = list(range(1, len(df) + 1))  # 累计规则数
        ax.plot(x, n, marker="o", label=f"max_depth={depth}", color=_color_for(depth, depths))
    for m in marks:
        ax.axvline(m * 100.0, ls="--", lw=0.5, color="grey", alpha=0.4)
    ax.set_title("Rule Count vs Intercept Rate")
    ax.set_xlabel("Actual Intercept Rate (%)")
    ax.set_ylabel("Number of Rules in Selected Set")
    ax.legend()
    ax.grid(alpha=0.3)


# ==========================================================================
# 推荐 (max_depth, max_intercept) 组合
# --------------------------------------------------------------------------
# Step 1（最优层数 D）：
#   - 每个 depth 取其“区间内 OOT 压降率峰值点”作为该 depth 的代表点，
#     衡量两个维度：region_peak_oot（越高越好）与 total_rules（越少越好）。
#   - 强支配：若存在某点在两个维度上都不劣于其它所有点、且至少一个维度严格更优，
#     则该点所属 depth 即为 D。
#   - 否则退化：a = 各 depth region_peak_oot 的最大值；在满足
#     region_peak_oot >= a*0.95 的 depth 中取层数最低者为 D。
# Step 2（最优拦截率）：
#   - 在 D 曲线、拦截率限定在 [lo, hi] 的子序列上，计算相邻点局部斜率
#     = Δ(OOT 压降率) / Δ(拦截率)，取所有局部斜率的均值 s_avg。
#   - 从区间内峰值点（右端 ≈ hi）向左考察：若某段局部斜率 < s_avg 则继续左移，
#     停在“第一段局部斜率 >= s_avg”的右端点。
#   - 子区间内不足 2 个点时退化为峰值点，并在推荐说明里标注。
# ==========================================================================


def _region_subframe(df, lo, hi):
    """取 df 中拦截率落在 [lo, hi]（含端点，带浮点容差）的子序列，按拦截率升序。"""
    if df is None or getattr(df, "empty", True) or COL_INTERCEPT not in df.columns:
        return None
    sub = df.sort_values(COL_INTERCEPT)
    x = sub[COL_INTERCEPT].astype(float)
    mask = (x >= lo - 1e-9) & (x <= hi + 1e-9)
    sub = sub[mask]
    if sub.empty:
        return None
    return sub


def _depth_region_peak(df, lo, hi):
    """返回该 depth 在区间内的 OOT 压降率峰值点信息 dict，无有效点返回 None。"""
    sub = _region_subframe(df, lo, hi)
    if sub is None or COL_DROP_OOT not in sub.columns:
        return None
    idx = sub[COL_DROP_OOT].astype(float).idxmax()
    row = sub.loc[idx]
    return {
        "intercept": float(row[COL_INTERCEPT]),
        "oot_drop": float(row[COL_DROP_OOT]),
        "total_rules": int(len(df)),  # 该 depth 最终规则集规则总数
    }


def select_optimal_depth(results, depths, lo, hi):
    """Step 1：确定最优 max_depth D，返回 (D, peaks, reason)。

    peaks: {depth: region_peak_dict}，仅含有有效区间峰值点的 depth。
    reason: 'dominance' 或 'a95'，用于日志与推荐说明。
    """
    peaks = {}
    for d in depths:
        info = _depth_region_peak(results.get(d), lo, hi)
        if info is not None:
            peaks[d] = info
    if not peaks:
        return None, {}, "none"

    # 强支配：oot_drop 越大越好、total_rules 越小越好。
    def dominates(p, q):
        not_worse = (p["oot_drop"] >= q["oot_drop"]) and (p["total_rules"] <= q["total_rules"])
        strictly = (p["oot_drop"] > q["oot_drop"]) or (p["total_rules"] < q["total_rules"])
        return not_worse and strictly

    dominant = []
    for d in peaks:
        if all(not dominates(peaks[o], peaks[d]) for o in peaks if o != d):
            dominant.append(d)
    # “在所有支配方向都最优”的点：不被任何其它点支配，且支配（或并列）所有其它点。
    for d in peaks:
        if all(
            (peaks[d]["oot_drop"] >= peaks[o]["oot_drop"] and peaks[d]["total_rules"] <= peaks[o]["total_rules"])
            for o in peaks
        ) and any(
            (peaks[d]["oot_drop"] > peaks[o]["oot_drop"] or peaks[d]["total_rules"] < peaks[o]["total_rules"])
            for o in peaks if o != d
        ):
            return d, peaks, "dominance"

    # 退化：a = 最大 region_peak_oot；满足 >= a*0.95 的 depth 中取最低层数。
    a = max(p["oot_drop"] for p in peaks.values())
    eligible = [d for d in peaks if peaks[d]["oot_drop"] >= a * 0.95]
    D = min(eligible)
    return D, peaks, "a95"


def select_optimal_intercept(df, lo, hi):
    """Step 2：在 D 曲线区间内做“局部斜率 vs 均值”的向左搜索。

    返回 (intercept, oot_drop, degraded)。degraded=True 表示区间内不足 2 点，
    退化为峰值点。
    """
    sub = _region_subframe(df, lo, hi)
    if sub is None:
        return None, None, True
    x = sub[COL_INTERCEPT].astype(float).to_numpy()
    y = sub[COL_DROP_OOT].astype(float).to_numpy()

    # 区间内峰值点索引（OOT 压降率最大）。
    peak_i = int(y.argmax())

    if len(x) < 2:
        return float(x[peak_i]), float(y[peak_i]), True

    # 相邻点局部斜率：slope[i] 表示 (i-1 -> i) 段，Δ(oot压降率)/Δ(拦截率)。
    slopes = {}
    for i in range(1, len(x)):
        dx = x[i] - x[i - 1]
        slopes[i] = (y[i] - y[i - 1]) / dx if dx > 1e-12 else 0.0
    s_avg = sum(slopes.values()) / len(slopes)

    # 从峰值点向左：看进入当前点的那一段(seg=cur)的斜率。
    cur = peak_i
    while cur >= 1:
        seg_slope = slopes[cur]  # (cur-1 -> cur) 段
        if seg_slope < s_avg:
            cur -= 1  # 该段增益偏低，继续左移
        else:
            break  # 第一段斜率 >= 均值，停在其右端点
    return float(x[cur]), float(y[cur]), False


def build_recommendation(results, depths, lo, hi):
    """组装推荐结果 dict；无有效点返回 None。"""
    D, peaks, reason = select_optimal_depth(results, depths, lo, hi)
    if D is None:
        return None
    inter, oot, degraded = select_optimal_intercept(results.get(D), lo, hi)
    if inter is None:
        return None
    a = max(p["oot_drop"] for p in peaks.values()) if peaks else None
    return {
        "max_depth": int(D),
        "max_intercept": round(float(inter), 6),
        "oot_drop_at_point": round(float(oot), 6),
        "depth_reason": reason,          # dominance | a95
        "a_best_oot_drop": round(float(a), 6) if a is not None else None,
        "region_peak_oot_of_D": round(float(peaks[D]["oot_drop"]), 6),
        "total_rules_of_D": int(peaks[D]["total_rules"]),
        "intercept_degraded": bool(degraded),
        "intercept_range": [round(lo, 6), round(hi, 6)],
        "per_depth_region_peak": {
            int(d): {
                "region_peak_oot_drop": round(peaks[d]["oot_drop"], 6),
                "peak_intercept": round(peaks[d]["intercept"], 6),
                "total_rules": int(peaks[d]["total_rules"]),
            }
            for d in peaks
        },
    }


def _mark_recommendation(ax, rec, ycol):
    """在指定坐标轴上高亮推荐点（若该轴的纵轴列与推荐点口径一致才标注）。"""
    if rec is None:
        return
    # 推荐点纵坐标只有 OOT 压降率是精确已知的；其它图仅在 x 轴画竖线定位。
    xr = rec["max_intercept"] * 100.0
    if ycol == COL_DROP_OOT:
        yr = rec["oot_drop_at_point"] * 100.0
        ax.scatter([xr], [yr], s=180, facecolors="none", edgecolors="red",
                   linewidths=2.0, zorder=6, label="Recommended")
        ax.annotate(
            f"REC d={rec['max_depth']} @ {xr:.1f}%",
            (xr, yr), fontsize=8, fontweight="bold", color="red",
            textcoords="offset points", xytext=(6, -12), zorder=6,
        )
    ax.axvline(xr, ls="-", lw=1.2, color="red", alpha=0.6, zorder=5)


def make_plots(results, depths, out_dir, marks, rec=None):
    # 图1/2/3 放一张三联图（与附件一致）。
    fig, axes = plt.subplots(1, 3, figsize=(21, 6))
    _plot_curve_with_delta(
        axes[0], results, depths, COL_DROP_TRAIN,
        "Train FPD7 Drop Rate", "Train FPD7 Drop Rate (%)", marks,
    )
    _plot_curve_with_delta(
        axes[1], results, depths, COL_DROP_OOT,
        "OOT FPD7 Drop Rate", "OOT FPD7 Drop Rate (%)", marks,
    )
    _plot_curve_with_delta(
        axes[2], results, depths, COL_RECALL_AMT,
        "Bad Debt (FPD7 Amount) Recall", "FPD7 Amount Recall (%)", marks,
    )
    # 在三联图上高亮推荐点/推荐拦截率。
    _mark_recommendation(axes[0], rec, COL_DROP_TRAIN)
    _mark_recommendation(axes[1], rec, COL_DROP_OOT)
    _mark_recommendation(axes[2], rec, COL_RECALL_AMT)
    for ax in axes:
        ax.legend()
    fig.suptitle(
        "BNPL Post-Loan Rules: max_depth sweep | Greedy Selection "
        "(annotation = per-point gap in pp; red = recommended)",
        fontsize=14,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    p1 = os.path.join(out_dir, "compare_drop_recall.png")
    fig.savefig(p1, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 图4 单独出。
    fig2, ax = plt.subplots(figsize=(8, 6))
    _plot_rule_count(ax, results, depths, marks)
    _mark_recommendation(ax, rec, "__rule_count__")  # 只画竖线定位推荐拦截率
    ax.legend()
    fig2.tight_layout()
    p2 = os.path.join(out_dir, "compare_rule_count.png")
    fig2.savefig(p2, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    return p1, p2


def _build_figure_table(results, depths, ycol, value_name):
    """方案甲：如实呈现。每个 depth 的每个规则节点一行，不做刻度对齐。

    列：max_depth、累计规则数、check累计拦截率(%)、<value_name>。
    ycol 为 None 时表示“规则数”图（y = 累计规则数，无额外压降/召回列）。
    """
    import pandas as pd

    rows = []
    for depth in depths:
        df = results.get(depth)
        if df is None or getattr(df, "empty", True) or COL_INTERCEPT not in df.columns:
            continue
        sub = df.sort_values(COL_INTERCEPT)
        x = sub[COL_INTERCEPT].astype(float).to_numpy()
        n_cum = list(range(1, len(sub) + 1))  # 累计规则数（与图4一致）
        if ycol is None:
            for i in range(len(sub)):
                rows.append({
                    "max_depth": depth,
                    "累计规则数": n_cum[i],
                    "check累计拦截率(%)": round(x[i] * 100.0, 4),
                    value_name: n_cum[i],
                })
        else:
            if ycol not in sub.columns:
                continue
            y = sub[ycol].astype(float).to_numpy()
            for i in range(len(sub)):
                rows.append({
                    "max_depth": depth,
                    "累计规则数": n_cum[i],
                    "check累计拦截率(%)": round(x[i] * 100.0, 4),
                    value_name: round(y[i] * 100.0, 4),
                })
    return pd.DataFrame(rows)


def export_tables(results, depths, out_dir):
    """把四张图对应的数据表写入一个 xlsx（每图一个 sheet，方案甲）。

    优先输出 .xlsx（多 sheet）；若缺 openpyxl 引擎则降级为 4 个独立 CSV。
    返回写出的文件路径列表。
    """
    import pandas as pd

    tables = {
        "train压降率": _build_figure_table(results, depths, COL_DROP_TRAIN, "train累计压降率(%)"),
        "oot压降率": _build_figure_table(results, depths, COL_DROP_OOT, "oot累计压降率(%)"),
        "召回FPD7金额占比": _build_figure_table(results, depths, COL_RECALL_AMT, "累计召回FPD7金额占比(%)"),
        "规则数": _build_figure_table(results, depths, None, "累计规则数"),
    }
    xlsx_path = os.path.join(out_dir, "compare_tables.xlsx")
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            for sheet, tdf in tables.items():
                # sheet 名 <=31 字符且不含非法字符，这里名称均合规。
                tdf.to_excel(writer, sheet_name=sheet, index=False)
        print("四图数据表（xlsx，多 sheet）:", xlsx_path)
        return [xlsx_path]
    except Exception as exc:  # noqa: BLE001 - 缺 openpyxl 等，降级为多 CSV
        print(f"[WARN] 写 xlsx 失败（{type(exc).__name__}: {exc}），降级为多个 CSV。")
        paths = []
        name_map = {
            "train压降率": "table_train_drop.csv",
            "oot压降率": "table_oot_drop.csv",
            "召回FPD7金额占比": "table_recall_amt.csv",
            "规则数": "table_rule_count.csv",
        }
        for sheet, tdf in tables.items():
            p = os.path.join(out_dir, name_map[sheet])
            tdf.to_csv(p, index=False, encoding="utf-8-sig")
            paths.append(p)
        print("四图数据表（降级为多 CSV）:", paths)
        return paths


def main() -> None:
    a = parse_args()
    _validate_sweep_args(a)
    depths = parse_depth_list(a.depth_list)
    lo, hi, marks = parse_intercept_range(a.intercept_range)
    os.makedirs(a.out_dir, exist_ok=True)

    print(f"扫描 max_depth={depths}，拦截率区间=[{lo}, {hi}]，参考刻度={marks}")
    results = run_all_depths(a, depths, max_intercept=hi)

    if all(v is None or getattr(v, "empty", True) for v in results.values()):
        raise RuntimeError(
            "所有 depth 的规则集均为空或运行失败，无法画图。请检查数据、lift 阈值或拦截率区间。"
        )

    # 先算推荐组合，供画图高亮与落盘。
    rec = build_recommendation(results, depths, lo, hi)

    p1, p2 = make_plots(results, depths, a.out_dir, marks, rec=rec)
    print("对比曲线（压降/召回三联图）:", p1)
    print("规则数对比图:", p2)

    # 四张图对应的数据表，落盘为一个多 sheet 的 xlsx（缺 openpyxl 时降级为多 CSV）。
    table_paths = export_tables(results, depths, a.out_dir)
    print("四图数据表文件:", table_paths)

    # 结构化产物清单，供助手解析 stdout 后在会话中展示（仅 sweep 模式产出）。
    print("[ARTIFACT] figure_triptych " + os.path.abspath(p1))
    print("[ARTIFACT] figure_rule_count " + os.path.abspath(p2))
    for tp in table_paths:
        kind = "tables_xlsx" if tp.lower().endswith(".xlsx") else "tables_csv"
        print("[ARTIFACT] " + kind + " " + os.path.abspath(tp))

    for d in depths:
        df = results.get(d)
        n = 0 if df is None or getattr(df, "empty", True) else len(df)
        print(f"  max_depth={d}: 最终规则集规则数={n}")

    # 推荐结果落盘 + 打印。
    if rec is not None:
        rec_path = os.path.join(a.out_dir, "recommendation.json")
        with open(rec_path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        reason_txt = (
            "在所有支配方向都最优（规则数最少且 OOT 压降率最高）"
            if rec["depth_reason"] == "dominance"
            else f"退化规则：a={rec['a_best_oot_drop']:.4%}，取满足最优 OOT 压降率>=a*0.95 的最低层数"
        )
        print("\n===== 推荐组合 =====")
        print(f"  推荐 max_depth   = {rec['max_depth']}（{reason_txt}）")
        print(f"  推荐 max_intercept = {rec['max_intercept']:.4%}"
              + ("（区间内不足2点，退化为峰值点）" if rec["intercept_degraded"] else ""))
        print(f"  该点 OOT 压降率   = {rec['oot_drop_at_point']:.4%}")
        print(f"  D 层规则总数      = {rec['total_rules_of_D']}")
        print(f"  推荐结果已保存至   : {rec_path}")
    else:
        print("\n[WARN] 无法在给定区间内确定推荐组合（所有 depth 区间内均无有效点）。")


if __name__ == "__main__":
    main()
