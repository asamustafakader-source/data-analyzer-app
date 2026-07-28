import io

import numpy as np
import pandas as pd

REQUIRED_RAW_COLUMNS = [
    "Dimension",
    "Account Manager Email",
    "Store ID",
    "Previous Period Items Total",
    "Items Total Amount",
    "Items Total Growth",
    "Average Cart",
    "Number of Arrived Orders",
    "Number of Canceled Orders",
    "Number of Canceled Orders After Approval",
    "Number of Canceled Orders Before Approval",
    "Avg. Time from Placed On to Canceled",
    "Lost Items Total",
    "Lost Items Total After Approval",
    "Lost Items Total Before Approval",
    "Total GMV",
    "Net Top Up Amount",
    "Merchant Discount Amount",
    "Store Credits Used",
    "Marketing Free Delivery",
    "Marketing Punch Card",
    "Number of Stores on MV",
    "% of Orders with MV",
    "% of All Orders Badly Rated",
]

DROPPED_COLUMNS = [
    "Average Service Charge",
    "Average Delivery Charge",
    "MV %",
    "Reward on Merchant",
    "Merchant Incentive Cashback",
    "% of Stores on MV",
    "MV Per Order",
    "Number of Stores with Orders",
    "Number of Brands with Orders",
]

FINAL_COLUMN_ORDER = [
    "Store ID",
    "Dimension",
    "Account Manager Email",
    "Previous Period Items Total",
    "Items Total Amount",
    "Items Total Growth",
    "Average Cart",
    "Number of Arrived Orders",
    "C.O. %",
    "Total GMV",
    "Total MV",
    "Total MVH",
    "MV%",
    "MVH%",
    "Net Top Up Amount",
    "HL% Cost on Store",
    "Net HL % GMV",
    "Merchant Discount Amount",
    "Store Credits Used",
    "Marketing Free Delivery",
    "Marketing Punch Card",
    "toters+ cost %",
    "Number of Stores on MV",
    "% of Orders with MV",
    "% of All Orders Badly Rated",
    "Number of Canceled Orders",
    "Number of Canceled Orders After Approval",
    "Number of Canceled Orders Before Approval",
    "Avg. Time from Placed On to Canceled",
    "Lost Items Total",
    "Lost Items Total After Approval",
    "Lost Items Total Before Approval",
]

PERCENT_COLUMNS = [
    "MV%",
    "MVH%",
    "HL% Cost on Store",
    "Net HL % GMV",
    "toters+ cost %",
    "C.O. %",
    "Items Total Growth",
]

GROWTH_COLUMN = "Items Total Growth"

MANAGER_DISPLAY_NAMES = {
    "hassan.fareed@totersapp.com": "Hassan",
    "lania.salar@totersapp.com": "Lania",
    "mustafa.hatam@totersapp.com": "Mustafa",
    "sivar.farhad@totersapp.com": "Sivar",
}

MANAGER_EMAIL_BY_NAME = {name: email for email, name in MANAGER_DISPLAY_NAMES.items()}


def display_manager_name(email) -> str:
    return MANAGER_DISPLAY_NAMES.get(str(email).strip(), str(email).strip())

# columns whose group "total" can be correctly recomputed as a ratio of summed
# base columns, rather than a naive sum/mean of the per-row percentage
RATIO_COLUMN_BASES = {
    "MV%": ("Total MV", "Items Total Amount"),
    "MVH%": ("Total MVH", "Items Total Amount"),
    "HL% Cost on Store": ("Net Top Up Amount", "Items Total Amount"),
    "Net HL % GMV": ("Net Top Up Amount", "Total GMV"),
    "toters+ cost %": ("Marketing Free Delivery", "Items Total Amount"),
}


def _safe_div(numerator, denominator):
    with np.errstate(divide="ignore", invalid="ignore"):
        result = numerator / denominator
    return result.replace([np.inf, -np.inf], 0).fillna(0)


def is_raw_mvh_report(df: pd.DataFrame) -> bool:
    cleaned_cols = {c.strip() for c in df.columns}
    return all(col in cleaned_cols for col in REQUIRED_RAW_COLUMNS)


def apply_mvh_transform(df: pd.DataFrame) -> pd.DataFrame:
    """Recreates the MVH_Dynamic Excel macro: drops raw cost/reach columns
    Tableau exports that aren't needed, and adds the derived MV/MVH/C.O. metrics.
    """
    df = df.rename(columns=lambda c: c.strip())
    df = df.drop(columns=[c for c in DROPPED_COLUMNS if c in df.columns])

    df["Total MV"] = (
        df["Merchant Discount Amount"]
        + df["Store Credits Used"]
        + df["Marketing Free Delivery"]
        + df["Marketing Punch Card"]
    )
    df["Total MVH"] = df["Total MV"] + df["Net Top Up Amount"]
    df["MV%"] = _safe_div(df["Total MV"], df["Items Total Amount"])
    df["MVH%"] = _safe_div(df["Total MVH"], df["Items Total Amount"])
    df["HL% Cost on Store"] = _safe_div(df["Net Top Up Amount"], df["Items Total Amount"])
    df["Net HL % GMV"] = _safe_div(df["Net Top Up Amount"], df["Total GMV"])
    df["toters+ cost %"] = _safe_div(df["Marketing Free Delivery"], df["Items Total Amount"])
    df["C.O. %"] = _safe_div(
        df["Number of Canceled Orders After Approval"],
        df["Number of Arrived Orders"] + df["Number of Canceled Orders After Approval"],
    )

    # this raw column mixes strings ("04:12:00") and datetimes (the Grand
    # Total row), which breaks Arrow serialization when rendering the table
    df["Avg. Time from Placed On to Canceled"] = df["Avg. Time from Placed On to Canceled"].astype(str)

    return df[FINAL_COLUMN_ORDER]


EXCEL_NUMBER_FORMATS = {
    "{:.2%}": "0.00%",
    "{:,.0f}": "#,##0",
    "{:,.2f}": "#,##0.00",
}


def build_column_formats(df: pd.DataFrame, exclude=("Store ID",)) -> dict:
    """Maps each numeric column to a display format: percent for known MV/MVH
    ratio columns, comma-separated otherwise (no decimals for whole numbers).
    """
    formats = {}
    for col in df.columns:
        if col in exclude:
            continue
        if col in PERCENT_COLUMNS or "%" in col:
            formats[col] = "{:.2%}"
        elif pd.api.types.is_numeric_dtype(df[col]):
            non_null = df[col].dropna()
            if not non_null.empty and (non_null % 1 == 0).all():
                formats[col] = "{:,.0f}"
            else:
                formats[col] = "{:,.2f}"
    return formats


def compute_group_aggregates(df: pd.DataFrame, group_col: str):
    """Returns (totals, averages) tables indexed by group_col, with an
    appended "All" row. Ratio/percent columns are recomputed from summed base
    columns where the underlying formula is known (correct "blended" rate),
    rather than summing the percentages themselves; other percent columns
    fall back to the mean in both tables.
    """
    numeric_cols = [
        c
        for c in df.columns
        if c != "Store ID" and pd.api.types.is_numeric_dtype(df[c])
    ]
    grouped = df.groupby(group_col, dropna=False)[numeric_cols]

    totals = grouped.sum(numeric_only=True)
    averages = grouped.mean(numeric_only=True)
    totals.loc["All"] = df[numeric_cols].sum(numeric_only=True)
    averages.loc["All"] = df[numeric_cols].mean(numeric_only=True)

    if GROWTH_COLUMN in totals.columns and {"Items Total Amount", "Previous Period Items Total"}.issubset(
        totals.columns
    ):
        totals[GROWTH_COLUMN] = _safe_div(
            totals["Items Total Amount"] - totals["Previous Period Items Total"],
            totals["Previous Period Items Total"],
        )

    if "C.O. %" in totals.columns and {
        "Number of Canceled Orders After Approval",
        "Number of Arrived Orders",
    }.issubset(totals.columns):
        num = totals["Number of Canceled Orders After Approval"]
        totals["C.O. %"] = _safe_div(num, totals["Number of Arrived Orders"] + num)

    for col, (numerator_col, denom_col) in RATIO_COLUMN_BASES.items():
        if col in totals.columns and {numerator_col, denom_col}.issubset(totals.columns):
            totals[col] = _safe_div(totals[numerator_col], totals[denom_col])

    # any other percent-shaped column has no known recompute formula here —
    # summing percentages is meaningless, so fall back to the mean
    handled = set(RATIO_COLUMN_BASES) | {GROWTH_COLUMN, "C.O. %"}
    for col in totals.columns:
        if (col in PERCENT_COLUMNS or "%" in col) and col not in handled:
            totals[col] = averages[col]

    return totals, averages


def write_excel_with_formats(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    formats = build_column_formats(df)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        for col_name, py_fmt in formats.items():
            excel_fmt = EXCEL_NUMBER_FORMATS[py_fmt]
            col_idx = df.columns.get_loc(col_name) + 1
            for row in range(2, len(df) + 2):
                worksheet.cell(row=row, column=col_idx).number_format = excel_fmt
    return buf.getvalue()
