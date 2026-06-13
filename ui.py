#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#Claude Code was used to generate parts of this code
#ChatGPT helped us understand how to render custom HTML components via
#st.markdown(..., unsafe_allow_html=True)
#The logic and design decisions are our own product

"""Reusable UI components so every page looks and behaves the same.

These helpers wrap st.* (and a few matplotlib charts shared across pages) and
never do any finance maths — that all lives in core/.
"""

import io
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import streamlit as st

import theme

#path to the stylesheet, anchored to this file so it works regardless of working directory
_STYLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style.css")
_FONTS_URL = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
#Material Symbols, so page headers can show the same icons as the sidebar navigation
_ICONS_URL = "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"


def inject_css() -> None:
    """Load the Google fonts and inject the stylesheet, with the palette from theme.py.

    Call this once near the top of the app so every page is styled. If the
    stylesheet is missing, the app still runs (just unstyled) instead of crashing.

    AI Usage Declaration: the CSS assembled and injected here (and in
    assets/style.css) is AI-generated (Claude). Streamlit's built-in theming
    is not flexible enough to restyle individual components, so this CSS
    overrides Streamlit's defaults directly; the resulting look (colours,
    fonts, layout) is our own design choice.
    """
    try:
        with open(_STYLE_PATH, encoding="utf-8") as f:
            stylesheet = f.read()
    except OSError:
        stylesheet = ""

    #@import must be the first rule; this reliably loads Inter. a <link> tag injected via
    #st.markdown gets stripped by Streamlit's HTML sanitiser, which left a system-font fallback.
    css = f"@import url('{_FONTS_URL}');\n@import url('{_ICONS_URL}');\n{theme.css_variables()}\n{stylesheet}"
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str | None = None, action_label: str | None = None, icon: str | None = None) -> bool:
    """Render the page title in a rounded indigo box, with an optional icon and subtitle.

    `icon` is a Material Symbols name (same set as the sidebar nav: home,
    search, build, insights, balance, menu_book). Returns True when the
    optional action button was clicked.
    """
    clicked = False
    if action_label:
        left, right = st.columns([4, 1], vertical_alignment="center")
    else:
        left, right = st.container(), None

    with left:
        icon_html = f"<span class='material-symbols-outlined'>{icon}</span>" if icon else ""
        html = f"<div class='page-header-center'><div class='page-title-box'>{icon_html}<span class='page-title'>{title}</span></div>"
        if subtitle:
            html += f"<p class='page-subtitle'>{subtitle}</p>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    if right is not None:
        with right:
            clicked = st.button(action_label, use_container_width=True)
    return clicked


def kpi_card(label: str, value: str, hint: str | None = None, good: bool | None = None, tooltip: str | None = None) -> None:
    """Render a single KPI tile.

    `good` drives the value colour: True -> green, False -> red, None ->
    neutral text. `hint` is shown as small text under the value (e.g. a short
    classification); `tooltip` is the hover explanation and falls back to `hint`.
    """
    if good is True:
        color = theme.POSITIVE
    elif good is False:
        color = theme.NEGATIVE
    else:
        color = theme.TEXT

    #a "?" badge that opens a small popover with the explanation on hover (no layout shift)
    info = f"<span class='info-badge'>?<span class='info-pop'>{tooltip}</span></span>" if tooltip else ""
    html = (
        f"<div class='kpi-card'>"
        f"<div class='kpi-label'>{label}{info}</div>"
        f"<div class='kpi-value' style='color:{color}'>{value}</div>"
    )
    if hint:
        html += f"<div class='kpi-hint'>{hint}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def verb_stepper(active: str) -> None:
    """Render the Build -> Evaluate -> Compare & Decide step indicator.

    `active` is one of "Build", "Evaluate", "Compare & Decide".
    """
    steps = ["Build", "Evaluate", "Compare & Decide"]
    html = "<div class='stepper'>"
    for i, step in enumerate(steps):
        css_class = "step active" if step == active else "step"
        html += f"<span class='{css_class}'>{step}</span>"
        if i < len(steps) - 1:
            html += "<span class='step-arrow'>→</span>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def empty_state(message: str, cta_label: str) -> bool:
    """Render a friendly empty state with a centred call-to-action button.

    Returns True when the button was clicked.
    """
    st.markdown(f"<div class='empty-state'><p>{message}</p></div>", unsafe_allow_html=True)
    left, middle, right = st.columns([1, 1, 1])
    with middle:
        return st.button(cta_label, type="primary", use_container_width=True)


def next_step(label: str, page: str) -> None:
    """Render a "next step" footer: a right-aligned arrow button that jumps to `page`."""
    st.divider()
    left, right = st.columns([3, 1])
    with right:
        if st.button(f"{label}  →", type="primary", use_container_width=True, key=f"next_{page}"):
            st.switch_page(page)


def data_table(frame, highlights: dict | None = None, good: dict | None = None, tips: dict | None = None, bold: bool = True) -> None:
    """Render `frame` as a styled HTML table with column headers and index.

    `frame` must already hold the display strings. `highlights`/`good` map a
    column name to the index labels to tint (indigo / green); `tips` maps a
    column name to a hover explanation on its header. Set `bold=False` for a
    table whose headers and row labels should render at normal weight.
    """
    highlights = highlights or {}
    good = good or {}
    tips = tips or {}
    css_class = "data-table" if bold else "data-table compact"
    header = ["<th></th>"]
    for col in frame.columns:
        badge = f"<span class='info-badge'>?<span class='info-pop'>{tips[col]}</span></span>" if col in tips else ""
        header.append(f"<th>{col}{badge}</th>")
    body = []
    for idx in frame.index:
        cells = [f"<th>{idx}</th>"]
        for col in frame.columns:
            if idx in highlights.get(col, ()):
                klass = " class='best'"
            elif idx in good.get(col, ()):
                klass = " class='good'"
            else:
                klass = ""
            cells.append(f"<td{klass}>{frame.loc[idx, col]}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(f"<table class='{css_class}'><thead><tr>" + "".join(header) +
                "</tr></thead><tbody>" + "".join(body) + "</tbody></table>", unsafe_allow_html=True)


def show_figure(fig: plt.Figure, **kwargs) -> None:
    """Render a matplotlib figure as a crisp, resolution-independent SVG and free it.

    SVG is a vector format, so charts stay perfectly sharp at any zoom level or
    screen resolution. Any kwargs are passed through to Matplotlib's savefig
    (e.g. bbox_inches=None to keep a fixed aspect ratio instead of the default
    tight crop, used by the Home page's allocation donuts).
    """
    kwargs.setdefault("bbox_inches", "tight")
    buf = io.StringIO()
    fig.savefig(buf, format="svg", **kwargs)
    st.image(buf.getvalue(), use_container_width=True)
    plt.close(fig)


def rebase_to_100(data: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Rebase a Series or DataFrame so it starts at 100 (on its first valid value).

    For a DataFrame, each column is rebased independently. Used so equity
    curves with different starting values can be compared on the same chart.
    """
    if isinstance(data, pd.Series):
        return data / data.iloc[0] * 100
    rebased = data.copy()
    for column in rebased.columns:
        valid = rebased[column].dropna()
        if not valid.empty:
            rebased[column] = rebased[column] / valid.iloc[0] * 100
    return rebased


def cml_chart(strategies: list[dict], benchmark: dict, rf: float, height: int = 420) -> list[bool]:
    """Render a risk/return scatter with the Capital Market Line (CML).

    `strategies` is a list of {"name", "vol", "ann_return"} dicts, one point
    per strategy. `benchmark` is {"ticker", "vol", "ann_return"}. `rf` is the
    annualised risk-free rate, where the CML starts on the y-axis.

    Returns, for each strategy, whether it lies above the CML (i.e. has a
    higher Sharpe ratio than the benchmark). Returns an empty list (and
    renders nothing) if the benchmark has zero or negative volatility.
    """
    benchmark_vol = benchmark["vol"]
    benchmark_return = benchmark["ann_return"]
    if benchmark_vol <= 0:
        return []

    slope = (benchmark_return - rf) / benchmark_vol
    x_max = max([s["vol"] for s in strategies] + [benchmark_vol]) * 1.3

    fig, ax = plt.subplots(figsize=(8, height / 100))
    ax.plot([0, x_max], [rf, rf + slope * x_max], color=theme.TEXT_MUTED, linewidth=1.5, linestyle="--")
    for i, strategy in enumerate(strategies):
        color = theme.CHART_SEQUENCE[i % len(theme.CHART_SEQUENCE)]
        ax.scatter(strategy["vol"], strategy["ann_return"], s=110, color=color, zorder=3)
        ax.annotate(strategy["name"], (strategy["vol"], strategy["ann_return"]),
                    textcoords="offset points", xytext=(0, 8), ha="center")
    ax.scatter(benchmark_vol, benchmark_return, s=110, color=theme.TEXT_MUTED, marker="D", zorder=3)
    ax.annotate(benchmark["ticker"], (benchmark_vol, benchmark_return),
                textcoords="offset points", xytext=(0, 8), ha="center")
    #mark the risk-free rate where the CML meets the y-axis
    ax.scatter(0, rf, s=60, color=theme.TEXT_MUTED, zorder=3)

    ax.set_xlabel("Volatility (annualised)")
    ax.set_ylabel("Return (annualised)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_xlim(left=0)
    show_figure(fig)

    return [s["ann_return"] > rf + slope * s["vol"] for s in strategies]
