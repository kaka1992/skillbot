"""BNPL XGBoost rule mining and greedy rule selection.

脚本流程：
1. 读取贷后表 df 和 check 表。
2. 在 df 上按时间切分 train / oot，并训练定制版 XGBoost。
3. 逐棵树提取叶子路径规则，按 train/oot lift 过滤形成规则池。
4. 在 check 表累计拦截率不超过上限的约束下，用贪心算法选择规则。
5. 输出规则池和最终规则集。
"""

import argparse
import os
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Set

import numpy as np
import pandas as pd
from pathlib import Path

# 以本脚本所在目录为基准解析随包分发的资源路径，
# 使 skill 发布到 market 后在任意用户环境均可定位，不依赖 /home/mira/files。
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 随包分发的定制版 XGBoost（python-package 形态，内含 xgboost/lib/libxgboost.so）。
_DEFAULT_XGBOOST_PATH = os.path.join(_SCRIPT_DIR, "xgboost_runtime")
# 默认输出目录：当前工作目录下的 outputs/，运行时自动创建。
_DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")

# ----------------------------------------------------------------------------
# 定制版 libxgboost.so 的运行时获取。
# 为了让 skill 包足够小以通过 market 审核，体积较大的 libxgboost.so 不随包分发，
# 而是首次运行时从远端下载到 xgboost_runtime/xgboost/lib/ 下（XGBoost 的
# find_lib_path 会自动从该目录加载），下载后本地缓存，后续运行不再重复下载。
# ----------------------------------------------------------------------------
_LIB_DIR = os.path.join(_DEFAULT_XGBOOST_PATH, "xgboost", "lib")
_LIB_PATH = os.path.join(_LIB_DIR, "libxgboost.so")
# 远端 .so 资源（tar.gz 内含单个 libxgboost.so，已 strip）。
_LIB_URL = (
    "https://lf0-fast-deliver-inner.bytedance.net"
    "/obj/eden-internal/121eh7uhmpfvhog/libxgboost_so.tar.gz"
)
# strip 后 libxgboost.so 的 md5，用于校验缓存与下载完整性。
_LIB_MD5 = "bb69352d45a6a6b84372ee44d4b9ccac"


def _file_md5(path: str) -> str:
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_libxgboost() -> None:
    """确保定制版 libxgboost.so 就位；缺失或损坏时从远端下载并解压到 lib 目录。"""
    if os.path.isfile(_LIB_PATH) and _file_md5(_LIB_PATH) == _LIB_MD5:
        return  # 已缓存且校验通过

    import tarfile
    import tempfile
    import urllib.request

    os.makedirs(_LIB_DIR, exist_ok=True)
    print("首次运行：正在下载定制版 libxgboost.so（约 3.4MB，仅下载一次）...")
    with tempfile.TemporaryDirectory() as tmp:
        tgz = os.path.join(tmp, "libxgboost_so.tar.gz")
        try:
            urllib.request.urlretrieve(_LIB_URL, tgz)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"下载 libxgboost.so 失败：{exc}。请检查网络，或手动将 libxgboost.so "
                f"放到 {_LIB_PATH}"
            ) from exc
        with tarfile.open(tgz, "r:gz") as tar:
            member = next((m for m in tar.getmembers()
                           if m.name.endswith("libxgboost.so")), None)
            if member is None:
                raise RuntimeError("下载的压缩包内未找到 libxgboost.so")
            member.name = "libxgboost.so"
            tar.extract(member, _LIB_DIR)

    if not os.path.isfile(_LIB_PATH) or _file_md5(_LIB_PATH) != _LIB_MD5:
        raise RuntimeError(
            f"libxgboost.so 下载后校验失败（md5 不匹配），请删除 {_LIB_PATH} 后重试。"
        )
    print(f"libxgboost.so 就位：{_LIB_PATH}")


def read_input_table(file_path: str) -> pd.DataFrame:
    """按文件后缀读取 csv/parquet。"""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path)
    if suffix == ".parquet":
        return pd.read_parquet(file_path)
    raise ValueError(f"暂不支持的文件格式: {file_path}，仅支持 .csv 和 .parquet")


def resolve_control_query(df, control_col, control_value="", min_rows=5000):
    """分析 control 列分布，返回追加到 df_query 的 control 过滤子句。

    规则（与用户确认一致）：
    - 只保留 control 组。
    - control_value 显式给出时用它；否则按比例自动判定：control 约占 10%，
      取“样本量更少的取值”为 control。
    - 无论分布是否异常，都做分布分析并打印各取值占比 + 判定出的 control 值。
    - 非纯 0/1 时判断是否为二元标签（恰好 2 个非空取值）：是则继续按少数派/指定值判定，
      否则报错（无法界定 control 组）。

    返回 (clause, control_value_used)：clause 形如 "control_col == 1"，可直接 AND 追加。
    """
    if control_col not in df.columns:
        raise ValueError(f"--control-col 指定的列 '{control_col}' 不在 df 中。")

    s = df[control_col]
    n_total = len(s)
    n_na = int(s.isna().sum())
    counts = s.value_counts(dropna=True)
    uniques = list(counts.index)

    # 强制分布分析日志（无论是否异常都打印）。
    print(f"\n===== control 组分布分析（列: {control_col}）=====")
    print(f"  总行数={n_total}，缺失={n_na}，非空取值数={len(uniques)}")
    for v in uniques:
        c = int(counts[v])
        print(f"    取值 {v!r}: {c} 行 ({safe_divide(c, n_total):.2%})")

    is_binary_01 = set(uniques) <= {0, 1} and len(uniques) >= 1
    if not is_binary_01:
        if len(uniques) != 2:
            raise ValueError(
                f"control 列 '{control_col}' 非 0/1 且非二元标签（发现 {len(uniques)} 个非空取值: "
                f"{uniques}），无法界定 control 组。请检查数据或改用 --control-value 显式指定。"
            )
        print(f"  [注意] 该列不是标准 0/1，但为二元标签（取值 {uniques}），按二元处理。")

    # 判定 control 取值。
    if control_value != "":
        # 用户显式指定：尽量转成与列一致的类型（数值列转数值）。
        cv_parsed = control_value
        try:
            if pd.api.types.is_numeric_dtype(s):
                cv_parsed = float(control_value)
                if cv_parsed.is_integer():
                    cv_parsed = int(cv_parsed)
        except (ValueError, TypeError):
            cv_parsed = control_value
        if cv_parsed not in set(uniques):
            raise ValueError(
                f"--control-value={control_value!r} 不在 control 列的取值 {uniques} 中。"
            )
        control_used = cv_parsed
        print(f"  按用户显式指定 control_value={control_used!r} 判定 control 组。")
    else:
        # 自动：样本量最少的取值为 control（control 约占 10%）。
        control_used = counts.idxmin()
        print(f"  自动判定：样本量最少的取值 {control_used!r} 为 control 组"
              f"（占比约 {safe_divide(int(counts.min()), n_total):.2%}）。")

    # 组装 query 子句：字符串取值加引号，数值直接拼。
    if isinstance(control_used, str):
        clause = f"`{control_col}` == {control_used!r}"
    else:
        clause = f"`{control_col}` == {control_used}"
    print(f"  追加到 df_query 的 control 过滤子句: {clause}")

    # 软告警：control 组行数过少（切 train/OOT 之前的总量）。
    control_rows = int(counts.get(control_used, 0))
    if control_rows < min_rows:
        print(
            f"  [告警] control 组仅 {control_rows} 行，少于阈值 {min_rows}，数据量可能过少，"
            f"仅用 control 组建模可能不稳定。"
        )
    print("=========================================")
    return clause, control_used

LEVEL_COLS = [
    "first_level_feature",
    "second_level_feature",
    "third_level_feature",
    "fourth_level_feature",
    "fifth_level_feature",
    "sixth_level_feature",
]

IV_BINS = 10
NUM_BOOST_ROUND = 60
EARLY_STOPPING_ROUNDS = 30
LEARNING_RATE = 0.01
SUBSAMPLE = 0.8
COLSAMPLE_BYTREE = 0.8
REG_ALPHA = 0.5
REG_LAMBDA = 10.0
MIN_CHILD_WEIGHT = 50.0
SEED = 42
VERBOSITY = 0
VERBOSE_EVAL = 10


def parse_csv_arg(value: Optional[str]) -> List[str]:
    """把逗号分隔参数解析成 list；空字符串/None 返回空 list。"""
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# 用户显式传入 features 时缺失值的填充值。
FEATURE_MISSING_FILL_VALUE = -9999.0


def cast_features_to_float_fill_missing(
    df: pd.DataFrame,
    check: pd.DataFrame,
    features: Sequence[str],
    fill_value: float = FEATURE_MISSING_FILL_VALUE,
) -> None:
    """把 df 和 check 两张表的 features 列统一转成 float，缺失值用 fill_value 填充。

    仅在用户显式传入 features 时调用。就地修改传入的 df / check。
    非数值内容用 pd.to_numeric(errors="coerce") 转成 NaN，再和原缺失值一起
    统一填成 fill_value（默认 -9999），保证进入建模的特征全部为 float。
    """
    for frame_name, frame in (("df", df), ("check", check)):
        for col in features:
            if col not in frame.columns:
                # 列缺失由 validate_input_data 负责报错，这里防御式跳过。
                continue
            frame[col] = pd.to_numeric(frame[col], errors="coerce").astype("float64")
            frame[col] = frame[col].fillna(fill_value)
    print(
        f"已将用户指定的 {len(features)} 个 features 列在 df/check 上转为 float，"
        f"缺失值用 {fill_value} 填充。"
    )


def parse_args() -> argparse.Namespace:
    """解析所有输入变量。"""
    parser = argparse.ArgumentParser(
        description=(
            "在贷后 df 上训练定制 XGBoost，提取树路径规则形成规则池，"
            "再按 train/oot lift 和 check 表拦截率约束筛选最终规则。"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # 输入数据与筛选逻辑
    parser.add_argument(
        "--df-path",
        default="",
        help="贷后样本表 parquet 路径；该表需要包含标签列、金额列、时间列和训练特征。",
    )
    parser.add_argument(
        "--check-path",
        default="",
        help="check 表 parquet 路径；用于计算规则在待拦截样本上的命中率/拦截率。",
    )
    parser.add_argument(
        "--df-query",
        default="",
        help="读取 df 后执行的 pandas query 过滤条件；传空字符串表示不过滤。",
    )
    parser.add_argument(
        "--check-query",
        default="",
        help="读取 check 表后执行的 pandas query 过滤条件；传空字符串表示不过滤。",
    )
    parser.add_argument(
        "--control-col",
        default="",
        help=(
            "可选：区分 control 组的特征列名（取值一般为 0/1）。非空时会分析该列分布，"
            "自动把 control 组取值以 AND 追加到 df_query（只保留 control 组）。"
        ),
    )
    parser.add_argument(
        "--control-value",
        default="",
        help=(
            "可选：显式指定哪个取值代表 control 组。留空时按比例自动判定"
            "（control 约占 10%%，取样本量更少的取值为 control）。"
        ),
    )
    parser.add_argument(
        "--control-min-rows",
        type=int,
        default=5000,
        help=(
            "control 组行数（切 train/OOT 之前的 df 总量）低于该阈值时打印告警，"
            "提示数据量过少。默认 5000。仅在指定 --control-col 时生效。"
        ),
    )

    # 字段配置
    parser.add_argument(
        "--features",
        default="",
        help=(
            "模型使用的特征列，逗号分隔。传空字符串时自动从 df/check 共同列中筛选"
            "数值型特征，并排除标签、金额、时间和 --exclude-cols 中的列。"
        ),
    )
    parser.add_argument(
        "--exclude-cols",
        default="",
        help="自动生成 features 时需要排除的列名，逗号分隔。",
    )
    parser.add_argument(
        "--date-col",
        default="",
        help="时间字段名；用于转 datetime，并按 --oot-start-date 切分 train 和 oot。",
    )
    parser.add_argument(
        "--label-col",
        default="",
        help="二分类标签字段名；1 表示坏样本/FPD7。",
    )
    parser.add_argument(
        "--amount-col",
        default="fpd7_ovd_num",
        help="FPD7 逾期金额字段名；用于计算 FPD7 金额、金额率和贪心召回收益。",
    )
    parser.add_argument(
        "--principal-col",
        default="fpd7_principal_den",
        help="本金/放款金额分母字段名；用于计算 FPD7 金额率。",
    )
    parser.add_argument(
        "--oot-start-date",
        default="",
        help="OOT 开始日期；date_col 小于该日期为训练集，大于等于该日期为 OOT。",
    )

    # 规则筛选和贪心约束
    parser.add_argument(
        "--lift-threshold-train",
        type=float,
        default=None,
        help="规则池筛选阈值：规则在训练集上的 FPD7 金额率 lift 必须大于该值。必填，需用户显式提供。",
    )
    parser.add_argument(
        "--lift-threshold-oot",
        type=float,
        default=None,
        help="规则池筛选阈值：规则在 OOT 上的 FPD7 金额率 lift 必须大于该值。必填，需用户显式提供。",
    )
    parser.add_argument(
        "--max-intercept",
        type=float,
        default=None,
        help="最终规则集在 check 表上的累计拦截率上限，例如 0.1 表示不超过 10%%。必填，需用户显式提供。",
    )

    # 定制 XGBoost 固定层特征和训练参数
    parser.add_argument(
        "--fixed-feature-list",
        default="",
        help=(
            "定制 XGBoost 的固定分裂特征列表，逗号分隔，最多 6 个。"
            "形式如'bnpl_trade_model_v2,max_loan_hist_overdue_days'"
            "输入的顺序不是最终规则中出现的顺序"
            "因为代码会按 IV 从高到低排序后映射为 first_level_feature 到 sixth_level_feature。"
        ),
    )
    parser.add_argument("--max-depth", type=int, default=5, help="XGBoost 单棵树最大深度。")

    # 修正的xgboost的路径
    parser.add_argument(
        "--xgboost-path",
        default=_DEFAULT_XGBOOST_PATH,
        help="修正后的xgboost导入的路径（默认使用随 skill 分发的 xgboost_runtime）"
    )

    # 输出路径（必填，需由用户显式提供）
    parser.add_argument(
        "--rule-pool-path",
        default="",
        help="规则池输出 CSV 路径，保存经过 train/oot lift 过滤后的候选规则。必填，需用户显式提供。",
    )
    parser.add_argument(
        "--rule-set-path",
        default="",
        help="最终规则集输出 CSV 路径，保存贪心选中的规则及逐步累计指标。必填，需用户显式提供。",
    )

    return parser.parse_args()

#输入校验
def validate_input_data(
    df: pd.DataFrame,
    check: pd.DataFrame,
    features: Sequence[str],
    args: argparse.Namespace,
) -> None:
    if df.empty:
        raise ValueError("df 为空：读取并应用 --df-query 后没有数据，请检查 df-path 或 df-query。")

    if check.empty:
        raise ValueError("check 为空：读取并应用 --check-query 后没有数据，请检查 check-path 或 check-query。")

    required_df_cols = {args.date_col, args.label_col, args.amount_col, args.principal_col}
    missing_df_cols = [col for col in required_df_cols if col not in df.columns]
    if missing_df_cols:
        raise ValueError(f"df 缺少必要字段: {missing_df_cols}")

    if not features:
        raise ValueError("features 为空：请通过 --features 指定特征，或检查 df/check 是否有共同数值型特征。")

    missing_feature_cols_in_df = [col for col in features if col not in df.columns]
    if missing_feature_cols_in_df:
        raise ValueError(f"df 缺少特征列: {missing_feature_cols_in_df}")

    missing_feature_cols_in_check = [col for col in features if col not in check.columns]
    if missing_feature_cols_in_check:
        raise ValueError(f"check 缺少特征列: {missing_feature_cols_in_check}")

#切分后的校验
def validate_split_data(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    check: pd.DataFrame,
    features: Sequence[str],
    args: argparse.Namespace,
) -> None:
    if train_df.empty:
        raise ValueError("train_df 为空：按 --oot-start-date 切分后训练集没有数据，请检查日期列或 oot-start-date。")

    if test_df.empty:
        raise ValueError("test_df 为空：按 --oot-start-date 切分后 OOT 没有数据，请检查日期列或 oot-start-date。")

    if check.empty:
        raise ValueError("check 为空：无法计算拦截率。")

    all_nan_features = [col for col in features if train_df[col].notna().sum() == 0]
    if all_nan_features:
        raise ValueError(f"训练集存在全为空的特征列: {all_nan_features}")

    if train_df[args.label_col].nunique(dropna=True) < 2:
        raise ValueError(f"训练集标签列 {args.label_col} 只有一个取值，无法进行有效二分类训练。")


def safe_divide(num: float, den: float) -> float:
    if den == 0:
        return np.nan
    return num / den


def calc_fpd7_amt_rate(data: pd.DataFrame, label_col: str, amount_col: str, principal_col: str) -> float:
    if len(data) == 0:
        return np.nan
    return safe_divide(
        data.loc[data[label_col] == 1, amount_col].sum(),
        data[principal_col].sum(),
    )


def calc_iv(df: pd.DataFrame, feature: str, target: str, bins: int = 10, eps: float = 1e-6) -> float:
    """计算单个特征关于 target 的 IV 值。target=1 表示 bad/event。"""
    tmp = df[[feature, target]].copy()

    if pd.api.types.is_numeric_dtype(tmp[feature]):
        try:
            tmp["_bin"] = pd.qcut(tmp[feature], q=bins, duplicates="drop")
        except ValueError:
            tmp["_bin"] = tmp[feature]
    else:
        tmp["_bin"] = tmp[feature].astype("object")

    tmp["_bin"] = tmp["_bin"].astype("object").where(tmp["_bin"].notna(), "MISSING")
    stat = tmp.groupby("_bin", dropna=False)[target].agg(["count", "sum"])
    stat["bad"] = stat["sum"]
    stat["good"] = stat["count"] - stat["bad"]

    total_bad = stat["bad"].sum()
    total_good = stat["good"].sum()
    stat["bad_rate"] = (stat["bad"] + eps) / (total_bad + eps)
    stat["good_rate"] = (stat["good"] + eps) / (total_good + eps)
    stat["woe"] = np.log(stat["bad_rate"] / stat["good_rate"])
    stat["iv"] = (stat["bad_rate"] - stat["good_rate"]) * stat["woe"]
    return stat["iv"].sum()


def infer_features(
    df: pd.DataFrame,
    check: pd.DataFrame,
    label_col: str,
    amount_col: str,
    principal_col: str,
    date_col: str,
    exclude_cols: Sequence[str],
) -> List[str]:
    """自动筛选 df/check 共同存在的数值型特征。"""
    excluded = set(exclude_cols) | {label_col, amount_col, principal_col, date_col}
    features = []
    for col in df.columns:
        if col in excluded or col not in check.columns:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            features.append(col)
    return features


def get_level_features_by_iv(
    df: pd.DataFrame,
    fixed_feature_list: Sequence[str],
    raw_features: Sequence[str],
    target: str,
    bins: int,
) -> Dict[str, int]:
    """按 IV 对固定特征排序，并返回定制 XGBoost 需要的 level feature index。"""
    if len(fixed_feature_list) > 6:
        raise ValueError("fixed_feature_list 最多支持 6 个特征")

    missing_features = [feature for feature in fixed_feature_list if feature not in raw_features]
    if missing_features:
        raise ValueError(f"fixed_feature_list 中存在不在 features 里的特征: {missing_features}")

    raw_feature_index_map = {feature: idx for idx, feature in enumerate(raw_features)}
    feature_iv_list = []
    for feature in fixed_feature_list:
        iv = calc_iv(df, feature, target, bins=bins)
        feature_iv_list.append((feature, iv))

    feature_iv_list = sorted(feature_iv_list, key=lambda x: x[1], reverse=True)
    sorted_feature_indices = [raw_feature_index_map[feature] for feature, _ in feature_iv_list]
    sorted_feature_indices = sorted_feature_indices[:6]
    sorted_feature_indices += [-1] * (6 - len(sorted_feature_indices))
    return dict(zip(LEVEL_COLS, sorted_feature_indices))


def parse_tree(tree_str: str) -> Dict[int, Dict[str, Optional[float]]]:
    lines = tree_str.strip().replace("\t", "").split("\n")
    nodes = {}

    for line in lines:
        if line.strip() == "":
            continue

        parts = line.split("[")
        node_id = int(parts[0].split(":")[0])
        condition = None
        yes = None
        no = None
        missing = None
        leaf_value = None

        if len(parts) > 1:
            condition_part = parts[1].split("]")
            condition = condition_part[0]
            outcome = condition_part[1].strip().split(",")
            yes = int(outcome[0].split("=")[1])
            no = int(outcome[1].split("=")[1])
            missing = int(outcome[2].split("=")[1])
        else:
            leaf_value = float(parts[0].split("=")[1])

        nodes[node_id] = {
            "condition": condition,
            "yes": yes,
            "no": no,
            "missing": missing,
            "leaf_value": leaf_value,
        }

    return nodes


def traverse_tree(
    node_id: int,
    path: List[str],
    nodes: Dict[int, Dict[str, Optional[float]]],
    feature_columns_dict: Dict[str, str],
) -> List[str]:
    node = nodes[node_id]

    if node["condition"] is not None:
        feature, threshold = str(node["condition"]).split("<")
        feature_name = feature_columns_dict[feature]

        path.append(f"({feature_name}<{threshold})")
        results = traverse_tree(int(node["yes"]), path.copy(), nodes, feature_columns_dict)
        path.pop()

        path.append(f"({feature_name}>={threshold})")
        results += traverse_tree(int(node["no"]), path.copy(), nodes, feature_columns_dict)
        path.pop()

        return results

    return [" & ".join(path)]


def query_dt_rules(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_oot: pd.DataFrame,
    y_oot: pd.Series,
    parsed_rules: Iterable[str],
    train_fpd7_amount_rate: float,
    test_fpd7_amount_rate: float,
    label_col: str,
    amount_col: str,
    principal_col: str,
) -> pd.DataFrame:
    """计算每条规则在 train 和 oot 上的命中、坏率和 FPD7 金额率 lift。"""
    rules = []

    def calc_rule_metrics(
        x: pd.DataFrame,
        y: pd.Series,
        select_index: pd.Index,
        fpd7_amt_rate_0: float,
        prefix: str,
    ) -> Dict[str, float]:
        if len(select_index) <= 0:
            return {
                f"{prefix}上命中的好样本数": 0,
                f"{prefix}上命中的坏样本数": 0,
                f"{prefix}上的命中数": 0,
                f"{prefix}上的坏率": 0,
                f"{prefix}上的LIFT值": 0,
            }

        y_select = y.loc[select_index]
        hit_count = len(y_select)
        bad_count = y_select.sum()
        good_count = hit_count - bad_count
        bad_rate = y_select.mean()
        select_df = x.loc[select_index]
        rule_fpd7_amt_rate = calc_fpd7_amt_rate(select_df, label_col, amount_col, principal_col)
        lift = 0 if fpd7_amt_rate_0 == 0 else rule_fpd7_amt_rate / fpd7_amt_rate_0

        return {
            f"{prefix}上命中的好样本数": good_count,
            f"{prefix}上命中的坏样本数": bad_count,
            f"{prefix}上的命中数": hit_count,
            f"{prefix}上的坏率": bad_rate,
            f"{prefix}上的LIFT值": lift,
        }

    if isinstance(parsed_rules, pd.DataFrame):
        parsed_rules = parsed_rules["组合策略"].unique()

    for rule in parsed_rules:
        try:
            select_index_train = x_train.query(rule).index
            select_index_oot = x_oot.query(rule).index
        except Exception as exc:  # noqa: BLE001 - 打印坏规则后跳过
            print("=" * 100)
            print(rule)
            print(type(exc))
            print(exc)
            continue

        df_rule = {"组合策略": rule}
        df_rule.update(
            calc_rule_metrics(
                x=x_train,
                y=y_train,
                select_index=select_index_train,
                fpd7_amt_rate_0=train_fpd7_amount_rate,
                prefix="训练集",
            )
        )
        df_rule.update(
            calc_rule_metrics(
                x=x_oot,
                y=y_oot,
                select_index=select_index_oot,
                fpd7_amt_rate_0=test_fpd7_amount_rate,
                prefix="oot",
            )
        )
        rules.append(df_rule)

    return pd.DataFrame(rules)


def get_rule_hit_on_data(rule, data: pd.DataFrame) -> Set[int]:
    """根据 pandas query 字符串或 callable 规则计算命中 index。"""
    if callable(rule):
        hit_mask = rule(data)
        if isinstance(hit_mask, pd.Series):
            return set(data.index[hit_mask])
        return set(hit_mask)
    return set(data.query(rule).index)


def make_rule_hit_index(rule: str, data: pd.DataFrame) -> np.ndarray:
    """返回规则命中的行号数组。

    main() 中会把 df/check reset_index(drop=True)，因此 query 返回的 index 就是
    可直接用于 numpy 向量的 0-based 行号。使用 numpy 数组可以避免贪心循环里
    频繁构造 set/list 和反复 pandas loc/query。
    """
    return data.query(rule).index.to_numpy(dtype=np.int64, copy=True)


def greedy_select_rules(
    rule_dict: Dict[int, Dict[str, object]],
    bad_amount_values: np.ndarray,
    n_df: int,
    n_pre: int,
    max_intercept_rate: float,
) -> "tuple[List[int], bool]":
    """在 check 拦截率约束下，用向量化增量计算做贪心选规则。

    目标函数与原实现一致：每轮选择 ROI 最大的规则，其中
        ROI = 新增召回 FPD7 金额 / check 表新增拦截量
    且加入后累计拦截率不超过 max_intercept_rate。

    提前停止：如果某一轮所能选到的最优规则 ROI == 0（即再选任何剩余规则都只会
    增加 check 拦截量、却召回不到任何新的 FPD7 坏账金额），则不再选入该规则，
    直接停止，以当前已选规则集作为最终规则集。

    返回 (selected_rules, early_stopped)：
    - selected_rules：贪心选中的规则 id 列表；
    - early_stopped：是否因为最优 ROI 归零而提前停止（区别于“达到拦截率上限”
      或“没有可增拦截的规则”这两种正常结束）。

    相比原实现，核心优化是：
    1. 规则命中样本提前保存为 numpy 行号数组；
    2. 覆盖状态用 bool mask 表示；
    3. 新增坏金额直接对 bad_amount_values[hit_x] 按未覆盖 mask 求和；
    4. 不在内层循环里执行 df.loc(...).query(...).sum()。
    """
    covered_x_mask = np.zeros(n_df, dtype=bool)
    covered_pre_mask = np.zeros(n_pre, dtype=bool)
    selected_rules: List[int] = []
    selected_rule_set: Set[int] = set()
    early_stopped = False

    while True:
        best_rule = None
        best_score = -1.0
        current_intercept_count = int(covered_pre_mask.sum())
        if safe_divide(current_intercept_count, n_pre) >= max_intercept_rate:
            break

        for rid, info in rule_dict.items():
            if rid in selected_rule_set:
                continue

            hit_pre = info["hit_pre_idx"]
            new_pre_mask = ~covered_pre_mask[hit_pre]
            new_intercept = int(new_pre_mask.sum())
            if new_intercept == 0:
                continue

            future_rate = safe_divide(current_intercept_count + new_intercept, n_pre)
            if future_rate > max_intercept_rate:
                continue

            hit_x = info["hit_x_idx"]
            new_x_mask = ~covered_x_mask[hit_x]
            new_bad_amt = bad_amount_values[hit_x][new_x_mask].sum()
            score = new_bad_amt / new_intercept
            if score > best_score:
                best_score = score
                best_rule = rid

        if best_rule is None:
            break

        # 提前停止：本轮最优规则的 ROI 已经归零，说明再往下选只增拦截、不增召回，
        # 直接以当前规则集收尾（不选入该 ROI=0 的规则）。
        if best_score <= 0:
            early_stopped = True
            print(
                f"提前停止：当前剩余规则的最优 ROI 已为 0，"
                f"停止选规则，当前 check 拦截率={covered_pre_mask.mean():.4%}"
            )
            break

        selected_rules.append(best_rule)
        selected_rule_set.add(best_rule)
        covered_x_mask[rule_dict[best_rule]["hit_x_idx"]] = True
        covered_pre_mask[rule_dict[best_rule]["hit_pre_idx"]] = True
        print(f"add rule_{best_rule}, intercept={covered_pre_mask.mean():.4%}")

    return selected_rules, early_stopped


def ensure_parent_dir(file_path: str) -> None:
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

def run_once(args) -> pd.DataFrame:
    """执行一次完整的规则挖掘 + 贪心选规则流程，并返回最终规则集明细 DataFrame。

    ``args`` 可以是 ``argparse.Namespace``（CLI 入口），也可以是任意具有相同
    属性名的对象（如扫描脚本用 ``SimpleNamespace`` 组装）。行为与旧 ``main()``
    完全一致：写出 rule_pool / rule_set 两个 CSV，并额外把 rule_set 明细返回，
    供 sweep 等上层复用。规则池为空时返回空 DataFrame。
    """
    # rule-pool-path / rule-set-path 为必填，需用户显式提供；缺失即报错，避免写到空路径。
    if not args.rule_pool_path:
        raise ValueError("--rule-pool-path 为必填参数，请显式提供规则池输出 CSV 路径。")
    if not args.rule_set_path:
        raise ValueError("--rule-set-path 为必填参数，请显式提供最终规则集输出 CSV 路径。")

    # lift-threshold-train / lift-threshold-oot 为必填，需用户显式提供；缺失即报错，不使用隐式默认。
    if args.lift_threshold_train is None:
        raise ValueError("--lift-threshold-train 为必填参数，请显式提供训练集 lift 阈值。")
    if args.lift_threshold_oot is None:
        raise ValueError("--lift-threshold-oot 为必填参数，请显式提供 OOT lift 阈值。")

    # max-intercept 为必填，需用户显式提供；缺失即报错，不使用隐式默认。
    if args.max_intercept is None:
        raise ValueError("--max-intercept 为必填参数，请显式提供 check 表累计拦截率上限。")

    features = parse_csv_arg(args.features)
    exclude_cols = parse_csv_arg(args.exclude_cols)
    fixed_feature_list = parse_csv_arg(args.fixed_feature_list)

    # 记录 features 是否为用户显式传入（区别于后续自动推断）。
    features_user_provided = bool(features)

    # 分别读取贷后表和 check 表数据，并根据 query 参数筛选。
    df = read_input_table(args.df_path)
    check = read_input_table(args.check_path)

    # 可选：若指定了 control 列，分析其分布并把 control 组过滤条件 AND 追加到 df_query。
    control_col = getattr(args, "control_col", "") or ""
    control_value = getattr(args, "control_value", "") or ""
    control_min_rows = getattr(args, "control_min_rows", 5000) or 5000
    effective_df_query = args.df_query
    if control_col:
        control_clause, _ = resolve_control_query(
            df, control_col, control_value, min_rows=control_min_rows
        )
        if effective_df_query:
            effective_df_query = f"({effective_df_query}) and ({control_clause})"
        else:
            effective_df_query = control_clause
        print(f"最终生效的 df_query: {effective_df_query}")

    if effective_df_query:
        df = df.query(effective_df_query)
    if args.check_query:
        check = check.query(args.check_query)

    # 后续命中结果会转成 numpy 行号数组；统一重置 index，避免原始非连续
    # index 被误当作位置下标使用。
    df = df.reset_index(drop=True)
    check = check.reset_index(drop=True)



    # 未显式传入 features 时，自动使用 df/check 共同存在的数值型特征。
    if not features:
        features = infer_features(
            df=df,
            check=check,
            label_col=args.label_col,
            amount_col=args.amount_col,
            principal_col=args.principal_col,
            date_col=args.date_col,
            exclude_cols=exclude_cols,
        )
    validate_input_data(
        df=df,
        check=check,
        features=features,
        args=args,
    )

    # 用户显式传入 features 时：在读取 df/check 后、进入建模前，先把这些
    # features 列在两张表上统一转为 float，并把缺失值填成 -9999。
    # features 为自动推断时不做该处理（推断只选取已有数值型列）。
    if features_user_provided:
        cast_features_to_float_fill_missing(df=df, check=check, features=features)

    #对时间标签进行转换
    if args.date_col not in df.columns:
        raise ValueError(f"df 中不存在日期字段: {args.date_col}")
    df[args.date_col] = pd.to_datetime(df[args.date_col], errors="coerce")
    if df[args.date_col].notna().sum() == 0:
        raise ValueError(f"日期列 {args.date_col} 转 datetime 后全部为 NaT，请检查日期格式。")    


    fixed_fea_result = get_level_features_by_iv(
        df=df,
        fixed_feature_list=fixed_feature_list,
        raw_features=features,
        target=args.label_col,
        bins=IV_BINS,
    )

    # 划分训练集和 OOT。
    oot_start_date = pd.to_datetime(args.oot_start_date)
    train_df = df[df[args.date_col] < oot_start_date].reset_index(drop=True)
    test_df = df[df[args.date_col] >= oot_start_date].reset_index(drop=True)
    validate_split_data(
        train_df=train_df,
        test_df=test_df,
        check=check,
        features=features,
        args=args,
    )
    train_black_rate = train_df[args.label_col].mean()
    test_black_rate = test_df[args.label_col].mean()
    print(f"训练集黑样本浓度: {train_black_rate:.6f} ({train_black_rate * 100:.2f}%)")
    print(f"测试集黑样本浓度: {test_black_rate:.6f} ({test_black_rate * 100:.2f}%)")

    train_fpd7_amount_rate = calc_fpd7_amt_rate(train_df, args.label_col, args.amount_col, args.principal_col)
    test_fpd7_amount_rate = calc_fpd7_amt_rate(test_df, args.label_col, args.amount_col, args.principal_col)
    print(f"训练集 FPD7金额率: {train_fpd7_amount_rate:.6f}")
    print(f"测试集 FPD7金额率: {test_fpd7_amount_rate:.6f}")

    # 导入定制版 xgboost。
    # 默认 runtime 下的 libxgboost.so 不随包分发，首次运行时按需下载到本地缓存。
    if args.xgboost_path == _DEFAULT_XGBOOST_PATH:
        ensure_libxgboost()
    if args.xgboost_path not in sys.path:
        sys.path.insert(0, args.xgboost_path)
    import xgboost as xgb  # pylint: disable=import-outside-toplevel

    dtrain = xgb.DMatrix(train_df[features], label=train_df[args.label_col], feature_names=features)
    dtest = xgb.DMatrix(test_df[features], label=test_df[args.label_col], feature_names=features)

    params = {
        "first_level_feature": fixed_fea_result["first_level_feature"],
        "second_level_feature": fixed_fea_result["second_level_feature"],
        "third_level_feature": fixed_fea_result["third_level_feature"],
        "fourth_level_feature": fixed_fea_result["fourth_level_feature"],
        "fifth_level_feature": fixed_fea_result["fifth_level_feature"],
        "sixth_level_feature": fixed_fea_result["sixth_level_feature"],
        "max_depth": args.max_depth,
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "learning_rate": LEARNING_RATE,
        "subsample": SUBSAMPLE,
        "colsample_bytree": COLSAMPLE_BYTREE,
        "reg_alpha": REG_ALPHA,
        "reg_lambda": REG_LAMBDA,
        "min_child_weight": MIN_CHILD_WEIGHT,
        "seed": SEED,
        "verbosity": VERBOSITY,
    }

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=NUM_BOOST_ROUND,
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        verbose_eval=VERBOSE_EVAL,
    )

    fscore = model.get_fscore()
    importance_df = pd.DataFrame(list(fscore.items()), columns=["feature", "fscore"]).sort_values(
        "fscore", ascending=False
    )
    print(importance_df)

    tree_model = model.get_dump(dump_format="text")
    feature_columns_dict = {col: col for col in features}

    parsed_rules_all = pd.DataFrame()
    for tree_idx, tree in enumerate(tree_model):
        print(f"第 {tree_idx} 棵树")
        nodes = parse_tree(tree)
        if nodes[0]["condition"] is None:
            print(f"tree {tree_idx} is leaf-only, skip")
            continue

        result_rules = traverse_tree(0, [], nodes, feature_columns_dict)
        parsed_rules_des = query_dt_rules(
            train_df,
            train_df[args.label_col],
            test_df,
            test_df[args.label_col],
            result_rules,
            train_fpd7_amount_rate=train_fpd7_amount_rate,
            test_fpd7_amount_rate=test_fpd7_amount_rate,
            label_col=args.label_col,
            amount_col=args.amount_col,
            principal_col=args.principal_col,
        )
        parsed_rules_des = parsed_rules_des[parsed_rules_des["训练集上的LIFT值"] > args.lift_threshold_train]
        parsed_rules_new = parsed_rules_des[parsed_rules_des["oot上的LIFT值"] > args.lift_threshold_oot]
        parsed_rules_all = pd.concat([parsed_rules_all, parsed_rules_new], ignore_index=True)
        print("总规则数:", parsed_rules_all.shape[0])
    ensure_parent_dir(args.rule_pool_path)
    ensure_parent_dir(args.rule_set_path)
    parsed_rules_all = parsed_rules_all.drop_duplicates(subset=["组合策略"])
    parsed_rules_all.to_csv(args.rule_pool_path, index=False)
    print("规则池提取完成")
    print("规则池中的规则数量:", parsed_rules_all.shape[0])
    if parsed_rules_all.empty:
        print("规则池为空：没有满足 train/oot lift 阈值的规则。")
        empty_rule_set = pd.DataFrame(columns=["rule_id", "规则内容"])
        empty_rule_set.to_csv(args.rule_set_path, index=False)
        print("已输出空的最终规则集文件:", args.rule_set_path)
        return empty_rule_set
    df_rules = pd.read_csv(args.rule_pool_path)
    rule_dict = {}
    for i, rule in enumerate(df_rules["组合策略"], start=1):
        hit_x_idx = make_rule_hit_index(rule, df)
        hit_pre_idx = make_rule_hit_index(rule, check)
        rule_dict[i] = {
            "rule": rule,
            "hit_x_idx": hit_x_idx,
            "hit_pre_idx": hit_pre_idx,
            # 保留 set 形态，供后续结果明细统计复用。
            "hit_x": set(hit_x_idx),
            "hit_pre": set(hit_pre_idx),
        }

    total_bad_amt = df.loc[df[args.label_col] == 1, args.amount_col].sum()
    n_pre = len(check)
    bad_amount_values = np.where(
        df[args.label_col].to_numpy() == 1,
        df[args.amount_col].fillna(0).to_numpy(dtype=float),
        0.0,
    )

    # 用“新增召回金额 / check 表新增拦截量”作为贪心分数。
    selected_rules, early_stopped = greedy_select_rules(
        rule_dict=rule_dict,
        bad_amount_values=bad_amount_values,
        n_df=len(df),
        n_pre=n_pre,
        max_intercept_rate=args.max_intercept,
    )

    covered_x: Set[int] = set()
    covered_pre: Set[int] = set()
    for rid in selected_rules:
        covered_x |= rule_dict[rid]["hit_x"]
        covered_pre |= rule_dict[rid]["hit_pre"]

    final_intercept_rate = safe_divide(len(covered_pre), len(check))
    if early_stopped:
        print(
            f"[提前停止] 剩余规则最优 ROI 归零，已提前结束规则集生成；"
            f"最终规则集共 {len(selected_rules)} 条规则，"
            f"此时 check 累计拦截率={final_intercept_rate:.4%}"
            f"（未达到 max_intercept 上限 {args.max_intercept:.4%}）。"
        )

    final_hit = list(covered_x)
    captured_bad_amt = df.loc[final_hit].query(f"{args.label_col}==1")[args.amount_col].sum()
    print("selected rules:")
    print(selected_rules)
    print("intercept rate:")
    print(len(covered_pre) / len(check))
    print("captured bad amount:")
    print(captured_bad_amt)
    print("captured bad amount recall:")
    print(safe_divide(captured_bad_amt, total_bad_amt))

    R0 = calc_fpd7_amt_rate(df, args.label_col, args.amount_col, args.principal_col)
    remain_df = df.loc[~df.index.isin(final_hit)]
    R = calc_fpd7_amt_rate(remain_df, args.label_col, args.amount_col, args.principal_col)
    print(f"原始的fpd7金额率是{R0}")
    print(f"现在的fpd7金额率是{R}")
    print(f"fpd7压降率是{(R0 - R) / R0}")

    test_R0 = calc_fpd7_amt_rate(test_df, args.label_col, args.amount_col, args.principal_col)
    train_R0 = calc_fpd7_amt_rate(train_df, args.label_col, args.amount_col, args.principal_col)
    result = []
    cum_df_hit: Set[int] = set()
    cum_train_df_hit: Set[int] = set()
    cum_test_df_hit: Set[int] = set()
    cum_pre_hit: Set[int] = set()

    for rid in selected_rules:
        rule = rule_dict[rid]["rule"]
        hit_df = set(rule_dict[rid]["hit_x"])
        hit_pre = set(rule_dict[rid]["hit_pre"])
        hit_train_df = get_rule_hit_on_data(rule, train_df)
        hit_test_df = get_rule_hit_on_data(rule, test_df)

        rule_bad_cnt = df.loc[list(hit_df), args.label_col].eq(1).sum()
        train_rule_bad_cnt = train_df.loc[list(hit_train_df), args.label_col].eq(1).sum()
        test_rule_bad_cnt = test_df.loc[list(hit_test_df), args.label_col].eq(1).sum()
        rule_intercept_rate = safe_divide(len(hit_pre), len(check))

        hit_df_data = df.loc[list(hit_df)]
        rule_fpd7_amt_rate = calc_fpd7_amt_rate(hit_df_data, args.label_col, args.amount_col, args.principal_col)
        train_hit_df_data = train_df.loc[list(hit_train_df)]
        train_rule_fpd7_amt_rate = calc_fpd7_amt_rate(
            train_hit_df_data, args.label_col, args.amount_col, args.principal_col
        )
        test_hit_df_data = test_df.loc[list(hit_test_df)]
        test_rule_fpd7_amt_rate = calc_fpd7_amt_rate(
            test_hit_df_data, args.label_col, args.amount_col, args.principal_col
        )

        remain_df = df.loc[~df.index.isin(hit_df)]
        after_rule_fpd7_amt_rate = calc_fpd7_amt_rate(remain_df, args.label_col, args.amount_col, args.principal_col)
        train_remain_df = train_df.loc[~train_df.index.isin(hit_train_df)]
        train_after_rule_fpd7_amt_rate = calc_fpd7_amt_rate(
            train_remain_df, args.label_col, args.amount_col, args.principal_col
        )
        test_remain_df = test_df.loc[~test_df.index.isin(hit_test_df)]
        test_after_rule_fpd7_amt_rate = calc_fpd7_amt_rate(
            test_remain_df, args.label_col, args.amount_col, args.principal_col
        )

        cum_df_hit |= hit_df
        cum_train_df_hit |= hit_train_df
        cum_test_df_hit |= hit_test_df
        cum_pre_hit |= hit_pre

        cum_hit_df = df.loc[list(cum_df_hit)]
        cum_hit_fpd7_amt_rate = calc_fpd7_amt_rate(cum_hit_df, args.label_col, args.amount_col, args.principal_col)
        train_cum_hit_df = train_df.loc[list(cum_train_df_hit)]
        train_cum_hit_fpd7_amt_rate = calc_fpd7_amt_rate(
            train_cum_hit_df, args.label_col, args.amount_col, args.principal_col
        )
        test_cum_hit_df = test_df.loc[list(cum_test_df_hit)]
        test_cum_hit_fpd7_amt_rate = calc_fpd7_amt_rate(
            test_cum_hit_df, args.label_col, args.amount_col, args.principal_col
        )

        remain_df = df.loc[~df.index.isin(cum_df_hit)]
        cum_after_fpd7_amt_rate = calc_fpd7_amt_rate(remain_df, args.label_col, args.amount_col, args.principal_col)
        train_remain_df = train_df.loc[~train_df.index.isin(cum_train_df_hit)]
        train_cum_after_fpd7_amt_rate = calc_fpd7_amt_rate(
            train_remain_df, args.label_col, args.amount_col, args.principal_col
        )
        test_remain_df = test_df.loc[~test_df.index.isin(cum_test_df_hit)]
        test_cum_after_fpd7_amt_rate = calc_fpd7_amt_rate(
            test_remain_df, args.label_col, args.amount_col, args.principal_col
        )

        drop_rate = safe_divide(R0 - cum_after_fpd7_amt_rate, R0)
        train_drop_rate = safe_divide(train_R0 - train_cum_after_fpd7_amt_rate, train_R0)
        test_drop_rate = safe_divide(test_R0 - test_cum_after_fpd7_amt_rate, test_R0)
        intercept_rate = safe_divide(len(cum_pre_hit), len(check))

        cum_captured_bad_amt = df.loc[list(cum_df_hit)].query(f"{args.label_col}==1")[args.amount_col].sum()
        cum_bad_amt_recall = safe_divide(cum_captured_bad_amt, total_bad_amt)

        result.append(
            {
                "rule_id": rid,
                "规则内容": rule,
                "当前规则命中总量": len(hit_df),
                "当前规则命中黑样本数量": rule_bad_cnt,
                "当前规则命中 FPD7 金额率": rule_fpd7_amt_rate,
                "拦截当前规则后的 FPD7 金额率": after_rule_fpd7_amt_rate,
                "累计规则命中的 FPD7 金额率": cum_hit_fpd7_amt_rate,
                "累计规则拦截后的 FPD7 金额率": cum_after_fpd7_amt_rate,
                "累计压降率": drop_rate,
                "累计召回FPD7金额": cum_captured_bad_amt,
                "累计召回FPD7金额占比": cum_bad_amt_recall,
                "当前规则在train上命中总量": len(hit_train_df),
                "当前规则在train上命中黑样本数量": train_rule_bad_cnt,
                "当前规则在train上命中 FPD7 金额率": train_rule_fpd7_amt_rate,
                "当前规则在train上拦截后的 FPD7 金额率": train_after_rule_fpd7_amt_rate,
                "累计规则在train上命中的 FPD7 金额率": train_cum_hit_fpd7_amt_rate,
                "累计规则在train上拦截后的 FPD7 金额率": train_cum_after_fpd7_amt_rate,
                "train累计压降率": train_drop_rate,
                "当前规则在check表拦截率": rule_intercept_rate,
                "check表累计拦截率": intercept_rate,
                "当前规则在oot上命中总量": len(hit_test_df),
                "当前规则在oot上命中黑样本数量": test_rule_bad_cnt,
                "当前规则在oot上命中 FPD7 金额率": test_rule_fpd7_amt_rate,
                "当前规则在oot上拦截后的 FPD7 金额率": test_after_rule_fpd7_amt_rate,
                "累计规则在oot上命中的 FPD7 金额率": test_cum_hit_fpd7_amt_rate,
                "累计规则在oot上拦截后的 FPD7 金额率": test_cum_after_fpd7_amt_rate,
                "oot累计压降率": test_drop_rate,
            }
        )

    result_df = pd.DataFrame(result)
    result_df.to_csv(args.rule_set_path, index=False)
    print("最终规则集输出完成:", args.rule_set_path)
    return result_df


def main() -> None:
    """CLI 入口（生成模式）：解析命令行参数后调用 run_once，行为与重构前一致。"""
    args = parse_args()
    run_once(args)


if __name__ == "__main__":
    main()
