import pandas as pd
import plotly.express as px
import streamlit as st

from mvh_transform import (
    apply_mvh_transform,
    build_column_formats,
    is_raw_mvh_report,
    write_excel_with_formats,
)

st.set_page_config(page_title="Data Analyzer", layout="wide")
st.title("Data Analyzer")


@st.cache_data
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)


uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])

if not uploaded:
    st.info("Upload a file to get started.")
    st.stop()

df = load_file(uploaded)

if is_raw_mvh_report(df):
    st.subheader("MVH transform")
    apply_transform = st.checkbox(
        "This looks like the raw Tableau MVH export — apply the MVH transform", value=True
    )
    if apply_transform:
        df = apply_mvh_transform(df)
        st.download_button(
            "Download transformed Excel",
            write_excel_with_formats(df, sheet_name="MVH"),
            "MVH_transformed.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

st.subheader("Filters")
filtered = df.copy()
with st.expander("Filter rows", expanded=False):
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            lo, hi = float(df[col].min()), float(df[col].max())
            if lo < hi:
                sel = st.slider(col, lo, hi, (lo, hi))
                filtered = filtered[filtered[col].between(*sel)]
        elif df[col].nunique() <= 50:
            options = df[col].dropna().unique().tolist()
            sel = st.multiselect(col, options, default=options)
            filtered = filtered[filtered[col].isin(sel)]

st.subheader("Preview")
st.caption(f"{filtered.shape[0]} rows x {filtered.shape[1]} columns")
st.dataframe(filtered.style.format(build_column_formats(filtered)), use_container_width=True)

st.subheader("Summary statistics")
st.dataframe(filtered.describe(include="all").transpose(), use_container_width=True)

missing = filtered.isna().sum()
missing = missing[missing > 0]
if not missing.empty:
    st.subheader("Missing values")
    st.dataframe(missing.rename("missing_count"), use_container_width=True)

st.subheader("Chart builder")
all_cols = filtered.columns.tolist()
numeric_cols = [c for c in all_cols if pd.api.types.is_numeric_dtype(filtered[c])]

chart_type = st.selectbox(
    "Chart type", ["Scatter", "Line", "Bar", "Histogram", "Box", "Correlation heatmap"]
)

if chart_type == "Correlation heatmap":
    if len(numeric_cols) >= 2:
        corr = filtered[numeric_cols].corr(numeric_only=True)
        fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Need at least two numeric columns.")
elif chart_type == "Histogram":
    x = st.selectbox("Column", numeric_cols or all_cols)
    color = st.selectbox("Color by (optional)", ["None"] + all_cols)
    fig = px.histogram(filtered, x=x, color=None if color == "None" else color)
    st.plotly_chart(fig, use_container_width=True)
else:
    x = st.selectbox("X axis", all_cols)
    y = st.selectbox("Y axis", numeric_cols or all_cols)
    color = st.selectbox("Color by (optional)", ["None"] + all_cols)
    color_arg = None if color == "None" else color

    if chart_type == "Scatter":
        fig = px.scatter(filtered, x=x, y=y, color=color_arg)
    elif chart_type == "Line":
        fig = px.line(filtered, x=x, y=y, color=color_arg)
    elif chart_type == "Bar":
        fig = px.bar(filtered, x=x, y=y, color=color_arg)
    else:  # Box
        fig = px.box(filtered, x=x, y=y, color=color_arg)

    st.plotly_chart(fig, use_container_width=True)

st.download_button(
    "Download filtered data as CSV",
    filtered.to_csv(index=False).encode("utf-8"),
    "filtered_data.csv",
    "text/csv",
)
