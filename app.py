import json
from datetime import datetime
from pathlib import Path

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
from auth import logout_button, require_login
from theme import CATEGORICAL, PAGE_CSS, apply_plotly_theme, style_growth_column

st.set_page_config(page_title="MVH Report", layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)

MANAGER_COL = "Account Manager Email"
PERIOD_LABELS = ["Yesterday", "Commercial Month (19th–18th)", "Calendar Month"]
PERIOD_SLUGS = {
    "Yesterday": "yesterday",
    "Commercial Month (19th–18th)": "commercial",
    "Calendar Month": "calendar",
}

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
METADATA_PATH = UPLOAD_DIR / "metadata.json"


def _load_metadata():
    if METADATA_PATH.exists():
        return json.loads(METADATA_PATH.read_text())
    return {}


def _save_metadata(metadata):
    METADATA_PATH.write_text(json.dumps(metadata))


@st.cache_data
def load_file(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    return df


@st.cache_data
def load_file_from_path(path_str, _mtime):
    path = Path(path_str)
    if path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    return df


def full_table_height(df, max_height=600):
    return min(int((len(df) + 1) * 35 + 3), max_height)


def render_styled_table(df):
    formats = build_column_formats(df)
    styled = df.style.format(formats)
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
        "Calendar month = 1st through end of month. Yesterday = a single-day export. "
        "Uploads are kept until you clear them, so you won't need to re-upload after a "
        "refresh or switching modes."
    )
    metadata = _load_metadata()
    columns = st.columns(3)

    periods = {}
    for col, label in zip(columns, PERIOD_LABELS):
        slug = PERIOD_SLUGS[label]
        with col:
            upload_version = st.session_state.get(f"{slug}_version", 0)
            uploaded = st.file_uploader(
                label, type=["csv", "xlsx", "xls"], key=f"{slug}_{upload_version}"
            )

            if uploaded is not None:
                for old in UPLOAD_DIR.glob(f"{slug}.*"):
                    old.unlink()
                target = UPLOAD_DIR / f"{slug}{Path(uploaded.name).suffix}"
                target.write_bytes(uploaded.getvalue())
                metadata[label] = {
                    "filename": uploaded.name,
                    "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                _save_metadata(metadata)

            existing = list(UPLOAD_DIR.glob(f"{slug}.*"))
            if existing:
                info = metadata.get(label, {})
                st.caption(
                    f"📄 {info.get('filename', existing[0].name)} — "
                    f"last updated {info.get('uploaded_at', 'unknown')}"
                )
                if st.button("Clear", key=f"clear_{slug}"):
                    for f in existing:
                        f.unlink()
                    metadata.pop(label, None)
                    _save_metadata(metadata)
                    st.session_state[f"{slug}_version"] = upload_version + 1
                    st.rerun()

                d = load_file_from_path(str(existing[0]), existing[0].stat().st_mtime)
                if is_raw_mvh_report(d):
                    d = apply_mvh_transform(d)
                periods[label] = d
            else:
                st.caption("No file uploaded yet.")

    return periods, metadata


def load_periods_readonly():
    """Reads whatever period files are already persisted, without showing
    upload controls — used by the restricted per-manager view.
    """
    metadata = _load_metadata()
    periods = {}
    for label in PERIOD_LABELS:
        slug = PERIOD_SLUGS[label]
        existing = list(UPLOAD_DIR.glob(f"{slug}.*"))
        if not existing:
            continue
        d = load_file_from_path(str(existing[0]), existing[0].stat().st_mtime)
        if is_raw_mvh_report(d):
            d = apply_mvh_transform(d)
        periods[label] = d
    return periods, metadata


def manager_view(user):
    st.title(f"MVH Report — {user['name']}")

    periods, metadata = load_periods_readonly()
    period_tab_labels = [label for label in PERIOD_LABELS if label in periods]

    if not period_tab_labels:
        st.info("No data has been uploaded yet. Check back once the admin uploads the latest exports.")
        return

    manager_email = user.get("manager_email")
    tabs = st.tabs(period_tab_labels)
    for label, tab in zip(period_tab_labels, tabs):
        with tab:
            info = metadata.get(label)
            if info:
                st.caption(f"🕒 Last updated {info['uploaded_at']}")
            d = periods[label]
            if MANAGER_COL not in d.columns:
                st.warning(f"No '{MANAGER_COL}' column in this file.")
                continue
            sub = d[d[MANAGER_COL].astype(str).str.strip() == manager_email]
            if sub.empty:
                st.caption("No data for you in this period.")
                continue
            sub = sub.copy()
            sub[MANAGER_COL] = sub[MANAGER_COL].map(display_manager_name)
            render_styled_table(sub)


def mvh_report_page():
    st.title("MVH Report")

    mode = st.radio(
        "Mode",
        ["Account manager report", "Totals & averages", "General explorer"],
        horizontal=True,
        key="mvh_mode",
    )

    if mode in ("Account manager report", "Totals & averages"):
        periods, metadata = load_periods()

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
                    info = metadata.get(label)
                    if info:
                        st.caption(f"🕒 Last updated {info['uploaded_at']}")
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
                        is_total = d[MANAGER_COL].astype(str).str.strip().str.lower() == "total"
                        sub = pd.concat([d[is_total], d[~is_total]])
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
                    info = metadata.get(label)
                    if info:
                        st.caption(f"🕒 Last updated {info['uploaded_at']}")
                    d_all = periods[label]
                    if MANAGER_COL not in d_all.columns:
                        st.warning(f"No '{MANAGER_COL}' column in this file.")
                        continue
                    is_total = d_all[MANAGER_COL].astype(str).str.strip().str.lower() == "total"
                    grand_total_row = d_all[is_total]
                    d = d_all[~is_total]
                    totals, averages = compute_group_aggregates(d, MANAGER_COL)
                    if not grand_total_row.empty:
                        # use the source file's own Grand Total row verbatim so
                        # this matches the original Excel macro output exactly
                        totals.loc["All"] = grand_total_row.iloc[0].reindex(totals.columns)
                    totals = totals.reindex(["All"] + [i for i in totals.index if i != "All"])
                    averages = averages.reindex(
                        ["All"] + [i for i in averages.index if i != "All"]
                    )
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
    st.caption(
        "Search stores by name (Dimension), select one or more, and see a combined "
        "total. Uses whichever period files are uploaded on the MVH Report page."
    )

    periods, metadata = load_periods_readonly()
    period_tab_labels = [label for label in PERIOD_LABELS if label in periods]

    if not period_tab_labels:
        st.info("No data has been uploaded yet. Upload period files from the MVH Report page first.")
        return

    tabs = st.tabs(period_tab_labels)
    for label, tab in zip(period_tab_labels, tabs):
        with tab:
            info = metadata.get(label)
            if info:
                st.caption(f"🕒 Last updated {info['uploaded_at']}")

            d = periods[label]
            if "Dimension" not in d.columns:
                st.warning("No 'Dimension' column in this file.")
                continue

            is_grand_total = d["Dimension"].astype(str).str.strip().str.lower() == "grand total"
            grand_total_row = d[is_grand_total]
            d_no_total = d[~is_grand_total]
            all_dimensions = sorted(d_no_total["Dimension"].dropna().astype(str).str.strip().unique())

            search = st.text_input("Search stores", key=f"dim_search_{label}")
            options = (
                [dim for dim in all_dimensions if search.lower() in dim.lower()]
                if search
                else all_dimensions
            )

            selected = st.multiselect("Select stores", options, key=f"dim_select_{label}")

            view = st.radio(
                "Show", ["Selected only", "All stores"], horizontal=True, key=f"dim_view_{label}"
            )

            if view == "Selected only":
                if not selected:
                    st.caption("Select one or more stores above to see their data.")
                    continue
                display_sub = d_no_total[d_no_total["Dimension"].astype(str).str.strip().isin(selected)]

                if display_sub.empty:
                    st.caption("No matching stores.")
                    continue

                render_styled_table(display_sub)

                st.markdown("**Summary total**")
                totals, _ = compute_group_aggregates(display_sub, "Dimension")
                summary_row = totals.loc[["All"]].rename(
                    index={"All": f"Total ({len(display_sub)} stores)"}
                )
                summary_row = summary_row.reset_index().rename(columns={"index": "Dimension"})
                render_styled_table(summary_row)
            else:
                display_sub = pd.concat([grand_total_row, d_no_total])
                if display_sub.empty:
                    st.caption("No matching stores.")
                    continue
                # the Grand Total row (top of the table above) is already the
                # source file's own total, so no separate summary is needed here
                render_styled_table(display_sub)


def main():
    user = require_login()

    with st.sidebar:
        st.caption(f"Signed in as **{user['name']}**")
        logout_button()

    if user.get("role") == "admin":
        manager_names = sorted(MANAGER_EMAIL_BY_NAME)
        with st.sidebar:
            st.markdown("### 👀 View as")
            view_as = st.selectbox(
                "Preview a manager's view",
                ["Admin (full access)"] + manager_names,
                key="admin_view_as",
                label_visibility="collapsed",
            )

        if view_as != "Admin (full access)":
            with st.sidebar:
                st.info(f"Previewing as **{view_as}**")
            manager_view(
                {
                    "name": view_as,
                    "role": "manager",
                    "manager_email": MANAGER_EMAIL_BY_NAME.get(view_as),
                }
            )
            return

        with st.sidebar:
            st.markdown("### 📈 Reporting")

        pg = st.navigation(
            [
                st.Page(mvh_report_page, title="MVH Report", icon="📊", default=True),
                st.Page(store_statistics_page, title="Store Statistics", icon="🏬"),
            ]
        )
        pg.run()
    else:
        manager_view(user)


if __name__ == "__main__":
    main()
