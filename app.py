import pandas as pd
import plotly.express as px
import streamlit as st

from mvh_transform import (
    GROWTH_COLUMN,
    MANAGER_EMAIL_BY_NAME,
    apply_mvh_transform,
    build_column_formats,
    compute_group_aggregates,
    display_manager_name,
    is_raw_mvh_report,
    write_excel_with_formats,
)
from theme import CATEGORICAL, PAGE_CSS, apply_plotly_theme, blue_colormap, style_growth_column

st.set_page_config(page_title="MVH Report", layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)

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


def full_table_height(df):
    return int((len(df) + 1) * 35 + 3)


def render_styled_table(df):
    formats = build_column_formats(df)
    gradient_cols = [c for c in formats if c != GROWTH_COLUMN]
    styled = df.style.format(formats).background_gradient(
        cmap=blue_colormap(), subset=gradient_cols
    )
    if GROWTH_COLUMN in df.columns:
        styled = style_growth_column(styled, GROWTH_COLUMN)
    st.dataframe(styled, use_container_width=True, height=full_table_height(df))


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


def load_periods():
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
    return periods


def mvh_report_page():
    st.title("MVH Report")

    mode = st.radio(
        "Mode",
        ["Account manager report", "Totals & averages", "General explorer"],
        horizontal=True,
    )

    if mode in ("Account manager report", "Totals & averages"):
        periods = load_periods()

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

        display_names = sorted({display_manager_name(m) for m in managers})

        if mode == "Account manager report":
            period_tab_labels = [label for label in PERIOD_LABELS if label in periods]
            period_tabs = st.tabs(period_tab_labels)
            for label, tab in zip(period_tab_labels, period_tabs):
                with tab:
                    d = periods[label]
                    if MANAGER_COL not in d.columns:
                        st.warning(f"No '{MANAGER_COL}' column in this file.")
                        continue

                    selection = st.segmented_control(
                        "Account manager",
                        ["All"] + display_names,
                        default="All",
                        key=f"manager_toggle_{label}",
                    )
                    selection = selection or "All"

                    if selection == "All":
                        sub = d[d[MANAGER_COL].astype(str).str.strip().str.lower() != "total"]
                    else:
                        email = MANAGER_EMAIL_BY_NAME.get(selection, selection)
                        sub = d[d[MANAGER_COL].astype(str).str.strip() == email]

                    if sub.empty:
                        st.caption("No data for this manager/period.")
                        continue

                    sub = sub.copy()
                    sub[MANAGER_COL] = sub[MANAGER_COL].map(display_manager_name)
                    render_styled_table(sub)

        else:  # Totals & averages
            period_tab_labels = [label for label in PERIOD_LABELS if label in periods]
            period_tabs = st.tabs(period_tab_labels)
            for label, tab in zip(period_tab_labels, period_tabs):
                with tab:
                    d = periods[label]
                    if MANAGER_COL not in d.columns:
                        st.warning(f"No '{MANAGER_COL}' column in this file.")
                        continue
                    d = d[d[MANAGER_COL].astype(str).str.strip().str.lower() != "total"]
                    totals, averages = compute_group_aggregates(d, MANAGER_COL)
                    totals.index = [
                        display_manager_name(i) if i != "All" else i for i in totals.index
                    ]
                    averages.index = [
                        display_manager_name(i) if i != "All" else i for i in averages.index
                    ]

                    st.markdown("**Totals by account manager**")
                    render_styled_table(
                        totals.reset_index().rename(columns={"index": MANAGER_COL})
                    )

                    st.markdown("**Averages by account manager**")
                    render_styled_table(
                        averages.reset_index().rename(columns={"index": MANAGER_COL})
                    )

    else:  # General explorer
        uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])

        if not uploaded:
            st.info("Upload a file to get started.")
            st.stop()

        df = load_file(uploaded)

        if is_raw_mvh_report(df):
            st.subheader("MVH transform")
            apply_transform = st.checkbox(
                "This looks like the raw Tableau MVH export — apply the MVH transform",
                value=True,
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
        summary = filtered.describe(include="all").transpose()
        st.dataframe(summary, use_container_width=True, height=full_table_height(summary))

        missing = filtered.isna().sum()
        missing = missing[missing > 0]
        if not missing.empty:
            st.subheader("Missing values")
            missing_df = missing.rename("missing_count")
            st.dataframe(
                missing_df, use_container_width=True, height=full_table_height(missing_df)
            )

        render_chart_builder(filtered)

        st.download_button(
            "Download filtered data as CSV",
            filtered.to_csv(index=False).encode("utf-8"),
            "filtered_data.csv",
            "text/csv",
        )


def store_statistics_page():
    st.title("Store Statistics")
    st.info("Coming soon — tell me what you'd like to see on this page.")


with st.sidebar:
    st.markdown("### 📈 Reporting")

pg = st.navigation(
    [
        st.Page(mvh_report_page, title="MVH Report", icon="📊", default=True),
        st.Page(store_statistics_page, title="Store Statistics", icon="🏬"),
    ]
)
pg.run()
