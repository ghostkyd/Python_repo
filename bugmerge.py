#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
表格合并工具（固定文件路径，仅需指定 Sheet 名称）
比较旧表格 a 和新表格 b，生成合并结果表格 c。

规则：
1. a 中有但 b 中没有的记录 → 标记“状态”列为“已迁出”。
2. 两表共有记录 → 以 b 中的数据为准。
3. b 中有但 a 中没有的记录 → “迁入日期”列填入当天日期。 

文件路径固定（请根据实际修改下方常量）：
- FILE_A: 旧表格文件路径（Excel 或 CSV）
- FILE_B: 新表格文件路径
- OUTPUT_FILE: 输出文件路径
"""

import pandas as pd
from datetime import datetime
import sys
import os

# ==================== 固定文件路径配置 ====================
FILE_A = r"/Users/stanleysun/Documents/Python_repo/DataFile/RTC系统问题汇总--每天更新_2026.xlsx"      # 表格 a 的路径（支持 .xlsx, .csv）
FILE_B = r"/Users/stanleysun/Documents/Python_repo/DataFile/b.xlsx"      # 表格 b 的路径
OUTPUT_FILE = r"/Users/stanleysun/Documents/Python_repo/DataFile/合并结果.xlsx" # 输出文件路径

# 固定列头（按顺序）
COLUMNS = [
    "关键字",
    "概要",
    "优先级",
    "状态",
    "平台/车型/车型年 PVM",
    "经办人",
    "创建日期",
    "已更新",
    "迁入日期",
    "迁出状态"
]

# 关键列名
KEY_COL = "关键字"
STATUS_COL = "迁出状态"
INBOUND_COL = "迁入日期"
DATE_FORMAT = "%Y年%m月%d日"

# ========================================================

def normalize_columns(df):
    """去除列名首尾空格，并强制按固定列头对齐（缺失列补空）"""
    df.columns = df.columns.str.strip()
    # 确保所有固定列都存在，缺失的添加空列
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    # 只保留固定列，顺序也按固定列头
    df = df[COLUMNS]
    return df

def load_excel_sheet(file_path, sheet_spec, file_desc):
    if not os.path.exists(file_path):
        print(f"错误：文件不存在 - {file_path}")
        sys.exit(1)

    try:
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
    except Exception as e:
        print(f"无法读取 Excel 文件 {file_path}: {e}")
        sys.exit(1)

    if isinstance(sheet_spec, int):
        if sheet_spec < 0 or sheet_spec >= len(sheet_names):
            print(f"错误：{file_desc} 的 Sheet 索引 {sheet_spec} 超出范围 (共 {len(sheet_names)} 个 Sheet)")
            sys.exit(1)
        sheet_name = sheet_names[sheet_spec]
    else:
        if sheet_spec not in sheet_names:
            print(f"错误：{file_desc} 中未找到 Sheet '{sheet_spec}'。可用 Sheet: {sheet_names}")
            sys.exit(1)
        sheet_name = sheet_spec

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        return normalize_columns(df)
    except Exception as e:
        print(f"读取 {file_desc} 的 Sheet '{sheet_name}' 失败: {e}")
        sys.exit(1)

def load_csv(file_path, file_desc):
    if not os.path.exists(file_path):
        print(f"错误：文件不存在 - {file_path}")
        sys.exit(1)
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_path, encoding='gbk')
        except Exception as e:
            print(f"读取 CSV 文件 {file_path} 失败: {e}")
            sys.exit(1)
    return normalize_columns(df)

def load_file(file_path, sheet_spec, file_desc):
    if file_path.lower().endswith('.csv'):
        if sheet_spec is not None:
            print(f"警告：{file_desc} 是 CSV 文件，忽略 Sheet 参数 '{sheet_spec}'")
        return load_csv(file_path, file_desc)
    else:
        return load_excel_sheet(file_path, sheet_spec, file_desc)

def merge_tables(sheet_a_name):
    print(f"正在处理表格 a 的 Sheet: {sheet_a_name}")

    df_a = load_file(FILE_A, sheet_a_name, "表格 A")
    df_b = load_file(FILE_B, 0, "表格 B")   # 表格 b 使用第一个 Sheet

    # 检查关键列是否存在（理论上 normalize 已保证存在，但再确认一次）
    if KEY_COL not in df_a.columns:
        print(f"错误：表格 A 中缺少关键列 '{KEY_COL}'")
        sys.exit(1)
    if KEY_COL not in df_b.columns:
        print(f"错误：表格 B 中缺少关键列 '{KEY_COL}'")
        sys.exit(1)

    # 关键列唯一性
    if df_a[KEY_COL].duplicated().any():
        print(f"错误：{FILE_A} 中关键字列存在重复值")
        sys.exit(1)
    if df_b[KEY_COL].duplicated().any():
        print(f"错误：{FILE_B} 中关键字列存在重复值")
        sys.exit(1)

    keys_a = set(df_a[KEY_COL])
    keys_b = set(df_b[KEY_COL])
    a_only_keys = keys_a - keys_b
    b_only_keys = keys_b - keys_a

    # 结果以 b 为基础
    df_result = df_b.copy()

    # 对 b_only 记录填写迁入日期
    today_str = datetime.now().strftime(DATE_FORMAT)
    if INBOUND_COL in df_result.columns:
        df_result.loc[df_result[KEY_COL].isin(b_only_keys), INBOUND_COL] = today_str

    # 添加 a_only 记录，并将状态改为“已迁出”
    if a_only_keys:
        df_a_only = df_a[df_a[KEY_COL].isin(a_only_keys)].copy()
        if STATUS_COL in df_a_only.columns:
            df_a_only[STATUS_COL] = "已迁出"
        # 合并（两个 DataFrame 列结构已完全一致）
        df_result = pd.concat([df_result, df_a_only], ignore_index=True)

    # 确保列顺序与固定列头一致
    df_result = df_result[COLUMNS]

    # 输出
    try:
        if OUTPUT_FILE.lower().endswith('.csv'):
            df_result.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        else:
            df_result.to_excel(OUTPUT_FILE, index=False, engine='openpyxl')
        print(f"合并完成，结果已保存至: {OUTPUT_FILE}")
    except Exception as e:
        print(f"保存文件失败: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) > 1:
        sheet_a_name = sys.argv[1]
    else:
        sheet_a_name = input("请输入表格 a 中要处理的 Sheet 名称: ").strip()
        if not sheet_a_name:
            print("错误：Sheet 名称不能为空")
            sys.exit(1)
    merge_tables(sheet_a_name)

if __name__ == "__main__":
    main()