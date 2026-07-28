from matplotlib.colors import LinearSegmentedColormap

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

# Sequential single-hue ramp (blue), light -> dark
SEQUENTIAL_BLUE = [
    "#cde2fb",
    "#9ec5f4",
    "#6da7ec",
    "#3987e5",
    "#2a78d6",
    "#1c5cab",
    "#104281",
    "#0d366b",
]

SURFACE = "#fcfcfb"
PAGE_PLANE = "#f9f9f7"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"


def blue_colormap():
    return LinearSegmentedColormap.from_list("sequential_blue", SEQUENTIAL_BLUE)


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
  --border: rgba(11,11,11,0.10);
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --surface: #1a1a19;
    --page-plane: #0d0d0d;
    --ink: #ffffff;
    --ink-secondary: #c3c2b7;
    --accent: #3987e5;
    --border: rgba(255,255,255,0.10);
  }}
}}
h2, h3 {{
  border-left: 4px solid var(--accent);
  padding-left: 0.6rem;
}}
[data-testid="stMetric"] {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.75rem;
}}
</style>
"""
