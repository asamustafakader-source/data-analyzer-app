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

PERCENT_COLUMNS = ["MV%", "MVH%", "HL% Cost on Store", "Net HL % GMV", "toters+ cost %", "C.O. %"]


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

    return df[FINAL_COLUMN_ORDER]
