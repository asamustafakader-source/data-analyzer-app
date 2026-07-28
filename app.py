import pandas as pd
import plotly.express as px
import streamlit as st

from mvh_transform import (
    apply_mvh_transform,
    build_column_formats,
    is_raw_mvh_report,
    write_excel_with_formats,
)
from theme import CATEGORICAL, PAGE_CSS, apply_plotly_theme, blue_colormap

st.set_page_config(page_title="Data Analyzer", layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)
st.title("Data Analyzer")

MANAGER_COL = "Account Manager Email"
PERIOD_LABELS = ["Yesterday", "Commercial Month (19th–18th)", "Calendar Month"]


@st.cache_data
def load_file(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    return df


def render_styled_table(df):
    formats = build_column_formats(df)
    styled = df.style.format(formats).background_gradient(
        cmap=blue_colormap(), subset=list(formats.keys())
    )
    st.dataframe(styled, use_container_width=True)


def render_chart_builder(filtered):
    st.subheader("Chart builder")
    all_cols = filtered.columns.tolist()
    numeric_cols = [c for c in all_cols if pd.api.types.is_numeric_dtype(filtered[c])]

    chart_type = st.selectbox(
        "Chart type", ["Scatter", "Line", "Bar", "Histogram", "Box", "Correlation heatmap"]
    )

    if chart_type == "Correlation heatmap":
        if len(numeric_cols) >= 2:
            corr = filtered[numeric_cols].corr(numeric_only=True)
            fig = px.imshow(
                corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1
            )
            st.plotly_chart(apply_plotly_theme(fig), use_container_width=True)
        else:
            st.warning("Need at least two numeric columns.")
    elif chart_type == "Histogram":
        x = st.selectbox("Column", numeric_cols or all_cols)
        color = st.selectbox("Color by (optional)", ["None"] + all_cols)
        fig = px.histogram(
            filtered,
            x=x,
            color=None if color == "None" else color,
            color_discrete_sequence=CATEGORICAL,
        )
        st.plotly_chart(apply_plotly_theme(fig), use_container_width=True)
    else:
        x = st.selectbox("X axis", all_cols)
        y = st.selectbox("Y axis", all_cols)
        color = st.selectbox("Color by (optional)", ["None"] + all_cols)
        color_arg = None if color == "None" else color

        if chart_type == "Scatter":
            fig = px.scatter(
                filtered, x=x, y=y, color=color_arg, color_discrete_sequence=CATEGORICAL
            )
        elif chart_type == "Line":
            fig = px.line(
                filtered, x=x, y=y, color=color_arg, color_discrete_sequence=CATEGORICAL
            )
        elif chart_type == "Bar":
            fig = px.bar(
                filtered, x=x, y=y, color=color_arg, color_discrete_sequence=CATEGORICAL
            )
        else:  # Box
            fig = px.box(
                filtered, x=x, y=y, color=color_arg, color_discrete_sequence=CATEGORICAL
            )

        st.plotly_chart(apply_plotly_theme(fig), use_container_width=True)


mode = st.radio(
    "Mode", ["Account manager report", "General explorer"], horizontal=True
)

if mode == "Account manager report":
    st.subheader("Upload period exports")
    st.caption(
        "Commercial month = 19th of previous month through the 18th (inclusive). "
        "Calendar month = 1st through end of month. Yesterday = a single-day export."
    )
    col1, col2, col3 = st.columns(3)
    uploaders = {
        "Yesterday": col1.file_uploader("Yesterday", type=["csv", "xlsx", "xls"], key="yesterday"),
        "Commercial Month (19th–18th)": col2.file_uploader(
            "Commercial month", type=["csv", "xlsx", "xls"], key="commercial"
        ),
        "Calendar Month": col3.file_uploader(
            "Calendar month", type=["csv", "xlsx", "xls"], key="calendar"
        ),
    }

    periods = {}
    for label, file in uploaders.items():
        if file is None:
            continue
        d = load_file(file)
        if is_raw_mvh_report(d):
            d = apply_mvh_transform(d)
        periods[label] = d

    if not periods:
        st.info("Upload at least one period file to get started.")
        st.stop()

    managers = set()
    for d in periods.values():
        if MANAGER_COL in d.columns:
            vals = d[MANAGER_COL].dropna().astype(str).str.strip()
            managers.update(v for v in vals.unique() if v.lower() != "total")
    managers = sorted(managers)

    if not managers:
        st.warning(f"No '{MANAGER_COL}' column found in the uploaded file(s).")
        st.stop()

    tabs = st.tabs(managers)
    for manager, tab in zip(managers, tabs):
        with tab:
            for label in PERIOD_LABELS:
                if label not in periods:
                    continue
                d = periods[label]
                if MANAGER_COL not in d.columns:
                    continue
                sub = d[d[MANAGER_COL].astype(str).str.strip() == manager]
                st.markdown(f"**{label}**")
                if sub.empty:
                    st.caption("No data for this period.")
                    continue
                render_styled_table(sub)

else:
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
    render_styled_table(filtered)

    st.subheader("Summary statistics")
    st.dataframe(filtered.describe(include="all").transpose(), use_container_width=True)

    missing = filtered.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        st.subheader("Missing values")
        st.dataframe(missing.rename("missing_count"), use_container_width=True)

    render_chart_builder(filtered)

    st.download_button(
        "Download filtered data as CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        "filtered_data.csv",
        "text/csv",
    )
