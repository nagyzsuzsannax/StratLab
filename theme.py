#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#Claude Code was used to generate parts of this code
#ChatGPT helped us understand how matplotlib rcParams work so the same
#colours and fonts apply to every chart
#The logic and design decisions are our own product

#design tokens for StratLab — the single source of truth for colours, font and spacing
#both the CSS (assets/style.css via ui.inject_css) and the matplotlib charts read from
#here, so a colour is only ever defined in this one file

import os

import matplotlib as mpl
from matplotlib import font_manager

#the Inter font file, so matplotlib charts use the same typeface as the page
_INTER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "Inter-Variable.ttf")

#colours — modern fintech, light
BACKGROUND = "#FAFAFA"   #app background
SURFACE = "#FFFFFF"      #cards and raised surfaces
TEXT = "#0F172A"         #primary text
TEXT_MUTED = "#64748B"   #secondary text, captions, labels
BORDER = "#E2E8F0"       #card borders and chart grid lines

PRIMARY = "#4338CA"      #indigo — primary actions and brand
ACCENT = "#14B8A6"       #teal — secondary accent
POSITIVE = "#10B981"     #green — gains
NEGATIVE = "#EF4444"     #red — losses
AMBER = "#F59E0B"        #amber — third series colour

#colour sequence for charts with several series, one colour per line
CHART_SEQUENCE = [PRIMARY, ACCENT, AMBER, "#6366F1", "#0EA5E9", "#EC4899", "#84CC16", "#F97316"]

#typography
FONT = "Inter"

#spacing scale in pixels — keeps padding and margins consistent across the app
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 40

#corner radius for cards and buttons
RADIUS = 12


#format a fraction as a percentage string, e.g. 0.087 -> "8.7%"
def format_pct(x: float | None, decimals: int = 1) -> str:
    if x is None:
        return "—"
    return f"{x * 100:.{decimals}f}%"


#format a number as a money string, e.g. 12345.6 -> "$12,346"
def format_money(x: float | None, decimals: int = 0) -> str:
    if x is None:
        return "—"
    return f"${x:,.{decimals}f}"


#expose the tokens as CSS custom properties so the stylesheet reads the exact same
#values as this file — ui.inject_css() injects this block before the stylesheet
def css_variables() -> str:
    variables = {
        "--bg": BACKGROUND,
        "--surface": SURFACE,
        "--text": TEXT,
        "--text-muted": TEXT_MUTED,
        "--border": BORDER,
        "--primary": PRIMARY,
        "--accent": ACCENT,
        "--positive": POSITIVE,
        "--negative": NEGATIVE,
        "--font": FONT,
        "--radius": f"{RADIUS}px",
        "--space-sm": f"{SPACE_SM}px",
        "--space-md": f"{SPACE_MD}px",
        "--space-lg": f"{SPACE_LG}px",
        "--space-xl": f"{SPACE_XL}px",
    }
    lines = []
    for name, value in variables.items():
        lines.append(f"  {name}: {value};")
    body = "\n".join(lines)
    return ":root {\n" + body + "\n}"


#apply the StratLab palette to matplotlib so every chart matches the app —
#call this once on startup, the same role plotly_theme.py used to play
def apply_mpl_theme() -> None:
    #register Inter (loaded from assets/, since it's a web font and not installed system-wide)
    #so charts use the same typeface as the rest of the page
    font_manager.fontManager.addfont(_INTER_PATH)

    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Inter", FONT, "Segoe UI", "DejaVu Sans"],
        "font.size": 11,
        "text.color": TEXT,
        "axes.facecolor": "none",
        "figure.facecolor": "none",
        "savefig.facecolor": "none",
        "axes.edgecolor": BORDER,
        "axes.labelcolor": TEXT,
        "axes.titlecolor": TEXT,
        "axes.grid": True,
        "grid.color": BORDER,
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": TEXT_MUTED,
        "ytick.color": TEXT_MUTED,
        "axes.prop_cycle": mpl.cycler(color=CHART_SEQUENCE),
        "legend.frameon": False,
        "legend.labelcolor": TEXT,
        "legend.facecolor": SURFACE,
        "legend.edgecolor": BORDER,
        "legend.framealpha": 0.95,
        "legend.fontsize": 9,
        #render SVG text as real <text> elements (not paths) so charts use the
        #page's Inter font instead of whatever was embedded at save time
        "svg.fonttype": "none",
    })
