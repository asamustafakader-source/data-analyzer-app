import pandas as pd

# Validated categorical palette (fixed order — never cycle/reassign per filter)
CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

SURFACE = "#fcfcfb"
PAGE_PLANE = "#f9f9f7"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"


# Excel's classic green/yellow/red conditional-formatting triplets
GOOD_FILL = "background-color: #C6EFCE; color: #006100"
WARN_FILL = "background-color: #FFEB9C; color: #9C6500"
BAD_FILL = "background-color: #FFC7CE; color: #9C0006"


def _growth_cell_style(value):
    if pd.isna(value):
        return ""
    if value > 0:
        return GOOD_FILL
    if value < 0:
        return BAD_FILL
    return WARN_FILL


def style_growth_column(styler, column):
    """Green/yellow/red fill for a signed rate column — green if
    positive, yellow if zero, red if negative.
    """
    return styler.map(_growth_cell_style, subset=[column])


def apply_plotly_theme(fig):
    fig.update_layout(
        template="plotly_white",
        colorway=CATEGORICAL,
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font_color=PRIMARY_INK,
        font_family="system-ui, -apple-system, 'Segoe UI', sans-serif",
        legend_title_text="",
        margin=dict(t=40, l=10, r=10, b=10),
    )
    fig.update_xaxes(gridcolor=GRIDLINE, linecolor=BASELINE, zeroline=False)
    fig.update_yaxes(gridcolor=GRIDLINE, linecolor=BASELINE, zeroline=False)
    fig.update_traces(marker_line_width=0, selector=dict(type="bar"))
    fig.update_traces(line_width=2, marker_size=9, selector=dict(type="scatter"))
    return fig


PAGE_CSS = f"""
<style>
:root {{
  --surface: {SURFACE};
  --page-plane: {PAGE_PLANE};
  --ink: {PRIMARY_INK};
  --ink-secondary: {SECONDARY_INK};
  --accent: {CATEGORICAL[0]};
  --accent-wash: rgba(42,120,214,0.12);
  --border: rgba(11,11,11,0.08);
  --shadow: 0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.04);
  --shadow-hover: 0 6px 16px rgba(42,120,214,0.20);
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --surface: #1c1c1e;
    --page-plane: #0d0d0d;
    --ink: #ffffff;
    --ink-secondary: #c3c2b7;
    --accent: #3987e5;
    --accent-wash: rgba(57,135,229,0.18);
    --border: rgba(255,255,255,0.10);
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 2px 8px rgba(0,0,0,0.25);
    --shadow-hover: 0 6px 18px rgba(57,135,229,0.35);
  }}
}}

html, body, [class*="css"] {{
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI",
    system-ui, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}}

h1 {{ font-weight: 700 !important; letter-spacing: -0.02em; }}
h2, h3 {{ font-weight: 650 !important; letter-spacing: -0.01em; }}

/* ---------- Buttons ---------- */
.stApp button[kind] {{
  border-radius: 980px !important;
  padding: 0.5rem 1.25rem !important;
  font-weight: 590 !important;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--ink) !important;
  box-shadow: var(--shadow);
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}}
.stApp button[kind="primary"] {{
  background: var(--accent) !important;
  color: #ffffff !important;
  border: none !important;
}}
.stApp button[kind]:hover {{
  transform: translateY(-1px);
  box-shadow: var(--shadow-hover);
}}
.stApp button[kind="secondary"]:hover {{
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}}
.stApp button[kind]:active {{
  transform: translateY(0);
}}

/* ---------- Text / number inputs ---------- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {{
  border-radius: 12px !important;
  border: 1px solid var(--border) !important;
  box-shadow: none !important;
  padding: 0.55rem 0.85rem !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-wash) !important;
}}

/* ---------- Select / multiselect (BaseWeb) ---------- */
[data-baseweb="select"] > div {{
  border-radius: 12px !important;
  border-color: var(--border) !important;
  box-shadow: none !important;
}}
[data-baseweb="tag"] {{
  border-radius: 8px !important;
  background: var(--accent-wash) !important;
}}

/* ---------- Segmented control ---------- */
[data-testid="stSegmentedControl"] label {{
  border-radius: 980px !important;
}}

/* ---------- Tabs: pill style instead of underline ---------- */
[data-baseweb="tab-list"] {{
  gap: 4px;
  background: var(--page-plane);
  padding: 4px;
  border-radius: 14px;
  border-bottom: none !important;
  width: fit-content;
}}
[data-baseweb="tab"] {{
  border-radius: 10px !important;
  padding: 0.45rem 1.1rem !important;
  transition: background 0.15s ease;
}}
[data-baseweb="tab"][aria-selected="true"] {{
  background: var(--surface) !important;
  box-shadow: var(--shadow);
}}
[data-baseweb="tab-highlight"] {{
  display: none;
}}

/* ---------- Expander / cards ---------- */
[data-testid="stExpander"] {{
  border-radius: 14px !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow);
  overflow: hidden;
}}

/* ---------- File uploader ---------- */
[data-testid="stFileUploaderDropzone"] {{
  border-radius: 14px !important;
  border: 1.5px dashed var(--border) !important;
  background: var(--page-plane) !important;
}}

/* ---------- DataFrame ---------- */
[data-testid="stDataFrame"] {{
  border-radius: 14px !important;
  overflow: hidden;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow);
}}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {{
  border-right: 1px solid var(--border);
}}

/* ---------- Metric tiles ---------- */
[data-testid="stMetric"] {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.9rem 1rem;
  box-shadow: var(--shadow);
}}

/* ---------- Alerts (info/warning/error/success) ---------- */
[data-testid="stAlert"] {{
  border-radius: 14px !important;
  border: none !important;
}}
</style>
"""
