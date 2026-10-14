"""
PSSP 2026 eCRC metrics by Puget Sound marine catch area (Areas 5-13).

Inputs
  CRC.gdb.zip                   WDFW Catch Record Card area polygons (EPSG:2927)
  pssp-2026-summary-v2.xlsx     season summary by catch area
  pssp-2026-by-month.xlsx       monthly summary, area x month grids

Outputs (PNG, 300 dpi) written to OUT_DIR.
"""
import sys, zipfile, tempfile, pathlib
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

REPO = pathlib.Path(__file__).resolve().parent
SUMMARY_XLSX = pathlib.Path(sys.argv[1])
MONTH_XLSX = pathlib.Path(sys.argv[2])
OUT_DIR = pathlib.Path(sys.argv[3]); OUT_DIR.mkdir(parents=True, exist_ok=True)

LOW_N = 10  # eCRC interviews below this are flagged "interpret with caution"

# ---------- palette (dataviz reference palette) ----------
INK, INK2, MUTED = "#1f1f1d", "#5c5b57", "#8c8b86"
SURFACE = "#ffffff"
CONTEXT_FILL, CONTEXT_EDGE = "#ecebe7", "#d6d5d0"
NODATA = "#f7f6f3"
BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281"]     # sequential blue 100/250/400/500/650
ORANGE = ["#fde0d0", "#f6a77f", "#eb6834", "#c04a1b", "#86300f"]   # one-hue orange ramp (2nd sequential context)
SERIES = {"fish": "#2a78d6", "refusal": "#eb6834"}                 # categorical slots 1, 2

mpl.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": CONTEXT_EDGE, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": SURFACE,
})

# ---------- geometry ----------
def load_crc():
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(REPO / "CRC.gdb.zip") as z:
        z.extractall(tmp)
    g = gpd.read_file(pathlib.Path(tmp) / "CRC.gdb")
    g = g.set_crs(2927, allow_override=True)
    g["code"] = g["CatchRecordCode"].astype(str)
    return g

CODE_MAP = {"8_1": "81", "8_2": "82"}          # spreadsheet code -> polygon code
LABEL = {"81": "8-1", "82": "8-2"}              # polygon code -> display label
AREAS = ["5", "6", "7", "81", "82", "9", "10", "11", "12", "13"]

# hand-tuned label anchors (EPSG:2927 ft offsets from representative point)
LABEL_NUDGE = {"7": (-60000, 20000), "6": (0, -15000), "13": (-25000, 0),
               "12": (0, 30000), "81": (-15000, 0), "11": (0, 0)}

crc = load_crc()
ps = crc[crc.code.isin(AREAS)].dissolve(by="code", as_index=False)
assert set(ps.code) == set(AREAS), set(AREAS) - set(ps.code)
xmin, ymin, xmax, ymax = ps.total_bounds
pad = 25000
EXTENT = (xmin - pad, xmax + pad, ymin - pad, ymax + pad)
context = crc.cx[EXTENT[0]:EXTENT[1], EXTENT[2]:EXTENT[3]]
context = context[~context.code.isin(AREAS)]

def anchor(code):
    p = ps.loc[ps.code == code].geometry.representative_point().iloc[0]
    dx, dy = LABEL_NUDGE.get(code, (0, 0))
    return p.x + dx, p.y + dy

# ---------- data ----------
def read_summary():
    raw = pd.read_excel(SUMMARY_XLSX, header=None)
    hdr = raw.index[raw[1].astype(str).eq("Catch area")][0]
    df = raw.iloc[hdr + 1:, 1:12].copy()
    df.columns = raw.iloc[hdr, 1:12].tolist()
    df = df[df["Catch area"].notna() & (df["Catch area"].astype(str) != "Total")]
    df["code"] = df["Catch area"].astype(str).replace(CODE_MAP)
    for c in df.columns[1:-1]:
        df[c] = pd.to_numeric(df[c])
    return df.reset_index(drop=True)

def read_grid(title):
    raw = pd.read_excel(MONTH_XLSX, header=None)
    r = raw.index[raw[0].astype(str).str.startswith(title)][0]
    hdr = raw.iloc[r + 1].tolist()
    block = []
    for i in range(r + 2, len(raw)):
        a = raw.iloc[i, 0]
        if pd.isna(a) or str(a) == "All areas":
            allrow = raw.iloc[i] if str(a) == "All areas" else None
            break
        block.append(raw.iloc[i].tolist())
    cols = [h for h in hdr if pd.notna(h)]
    df = pd.DataFrame([b[:len(cols)] for b in block], columns=cols)
    df["code"] = df["Catch area"].astype(str).replace(CODE_MAP)
    df = df.replace("–", np.nan)
    months = [c for c in cols if str(c).startswith("2026-")]
    long = df.melt(id_vars="code", value_vars=months, var_name="month", value_name="value")
    long["value"] = pd.to_numeric(long["value"])
    return long

season = read_summary()
n_long = read_grid("eCRC interviews by area and month").rename(columns={"value": "n"})
fish_long = read_grid("% of fish via eCRC").rename(columns={"value": "pct_fish"})
ref_long = read_grid("% anglers refused scan").rename(columns={"value": "pct_refused"})
monthly = n_long.merge(fish_long, on=["code", "month"]).merge(ref_long, on=["code", "month"])

all_months = pd.read_excel(MONTH_XLSX, header=None, skiprows=4, nrows=8)
all_months.columns = all_months.iloc[0]; all_months = all_months.iloc[1:]
all_months = all_months[all_months["Month"] != "Total"].copy()

MONTHS = sorted(monthly.month.unique())
MON_LABEL = {m: pd.Timestamp(m + "-01").strftime("%b") for m in MONTHS}
MON_LABEL["2026-10"] = "Oct*"

# ---------- helpers ----------
def classify(v, breaks):
    if pd.isna(v):
        return None
    return int(np.digitize(v, breaks[1:-1]))

def base_axes(ax):
    context.plot(ax=ax, color=CONTEXT_FILL, edgecolor=CONTEXT_EDGE, linewidth=0.3)
    ax.set_xlim(EXTENT[0], EXTENT[1]); ax.set_ylim(EXTENT[2], EXTENT[3])
    ax.set_aspect("equal"); ax.set_axis_off()

def draw_choropleth(ax, values, n, breaks, ramp, label_values=True, fmt="{:.0%}", fs=8):
    base_axes(ax)
    d = ps.merge(pd.DataFrame({"code": values.index, "v": values.values, "n": n.reindex(values.index).values}),
                 on="code", how="left")
    for _, row in d.iterrows():
        k = None if (pd.notna(row.n) and row.n == 0) else classify(row.v, breaks)
        geo = gpd.GeoSeries([row.geometry], crs=ps.crs)
        if k is None:
            geo.plot(ax=ax, color=NODATA, edgecolor=MUTED, linewidth=0.5)
        else:
            low = pd.notna(row.n) and row.n < LOW_N
            geo.plot(ax=ax, color=ramp[k], edgecolor=SURFACE, linewidth=0.8,
                     hatch="////" if low else None, alpha=0.55 if low else 1)
            if low:
                geo.plot(ax=ax, facecolor="none", edgecolor=INK2, linewidth=0.5, hatch="////")
        x, y = anchor(row.code)
        txt = LABEL.get(row.code, row.code)
        if label_values:
            txt += "\n" + ("–" if pd.isna(row.v) else fmt.format(row.v))
        ax.annotate(txt, (x, y), ha="center", va="center", fontsize=fs, color=INK,
                    fontweight="bold" if not label_values else "normal",
                    bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec="none", alpha=0.85))

def class_legend(ax_or_fig, breaks, ramp, fmt, title, low=True, loc="lower left", **kw):
    labels = [f"{fmt(breaks[i])}–{fmt(breaks[i+1])}" for i in range(len(ramp) - 1)]
    labels.append(f"≥ {fmt(breaks[-2])}")
    handles = [Patch(facecolor=c, edgecolor=SURFACE, label=l) for c, l in zip(ramp, labels)]
    if low:
        handles.append(Patch(facecolor="#dddddd", edgecolor=INK2, hatch="////", label=f"< {LOW_N} eCRC interviews"))
    handles.append(Patch(facecolor=NODATA, edgecolor=MUTED, label="No eCRC data"))
    return ax_or_fig.legend(handles=handles, title=title, loc=loc, frameon=False,
                            fontsize=8, title_fontsize=9, alignment="left", **kw)

pct = lambda v: f"{v*100:.0f}%"
FISH_BREAKS = [0, .15, .20, .25, .30, 1]
REF_BREAKS = [0, .05, .10, .20, .30, 1]
NOTE = ("Source: PSSP 2026 creel interviews with harvest, Areas 5–13; data as of Oct 9, 2026. "
        "Area 7 excludes waters west of the San Juan Islands not sampled.")
EST_NOTE = "  eCRC fish estimated as total fish × eCRC licenses ÷ (paper + eCRC licenses), by area."
NOTE = "Source: PSSP 2026 creel interviews with harvest, Marine Areas 5–13 (data as of Oct 9, 2026)."

def finish(fig, name, title, subtitle, note=NOTE):
    h = fig.get_figheight()
    fig.suptitle(title, x=0.03, y=1 - 0.18 / h, ha="left", va="top", fontsize=15, fontweight="bold")
    fig.text(0.03, 1 - 0.50 / h, subtitle, ha="left", va="top", fontsize=10.5, color=INK2)
    fig.text(0.03, 0.02, note, ha="left", fontsize=7.5, color=MUTED)
    fig.savefig(OUT_DIR / name, dpi=300, facecolor=SURFACE)
    plt.close(fig)
    print("wrote", name)

s = season.set_index("code")
n_season = s["eCRC interviews"]

# ---------- 1. season: % fish via eCRC ----------
fig, ax = plt.subplots(figsize=(10, 7.5)); fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.05)
draw_choropleth(ax, s["% fish via eCRC"], n_season, FISH_BREAKS, BLUE)
class_legend(ax, FISH_BREAKS, BLUE, pct, "% of fish via eCRC (est.)", low=False, loc="upper left")
finish(fig, "01_season_pct_fish_ecrc.png", "Share of harvested fish via eCRC (estimated)",
       f"Season to date, by marine catch area. Overall: {season['eCRC fish'].sum()/season['Total fish'].sum():.0%} "
       f"of {season['Total fish'].sum():,} fish sampled.", NOTE + EST_NOTE)

# ---------- 2. season: % anglers refused scan ----------
fig, ax = plt.subplots(figsize=(10, 7.5)); fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.05)
draw_choropleth(ax, s["% anglers refused"], n_season, REF_BREAKS, ORANGE)
class_legend(ax, REF_BREAKS, ORANGE, pct, "% of eCRC anglers refusing scan", low=False, loc="upper left")
finish(fig, "02_season_refusal_rate.png", "Share of eCRC anglers refusing a scan",
       f"Season to date, by marine catch area. Overall: {season['Refusing anglers'].sum()/season['eCRC anglers'].sum():.0%} "
       f"of {season['eCRC anglers'].sum():,} eCRC anglers.")

# ---------- 3. season: sample size (proportional symbols) ----------
fig, ax = plt.subplots(figsize=(10, 7.5)); fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.05)
base_axes(ax)
ps.plot(ax=ax, color="#dfe9f5", edgecolor=SURFACE, linewidth=0.8)
SMAX = 1600
for code in AREAS:
    x, y = anchor(code)
    n = n_season[code]
    ax.scatter(x, y, s=SMAX * n / n_season.max(), color=SERIES["fish"], alpha=0.85,
               edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.annotate(f"{LABEL.get(code, code)}\n{n:,}", (x, y), xytext=(0, -np.sqrt(SMAX * n / n_season.max()) / 2 - 4),
                textcoords="offset points", ha="center", va="top", fontsize=8, color=INK,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.85), zorder=4)
ref = [100, 500, 1500]
h = [Line2D([], [], marker="o", ls="", color=SERIES["fish"], alpha=0.85, markeredgecolor=SURFACE,
            markersize=np.sqrt(SMAX * r / n_season.max()), label=f"{r:,}") for r in ref]
ax.legend(handles=h, title="eCRC interviews", loc="upper left", frameon=False, labelspacing=2.6, handletextpad=2.2,
          borderpad=1.2, fontsize=8, title_fontsize=9, alignment="left")
finish(fig, "03_season_ecrc_sample_size.png", "Where the eCRC sample comes from",
       f"Creel interviews with eCRC harvest, season to date. {n_season.sum():,} interviews; "
       f"Areas 8-2, 9 and 10 account for {n_season[['82','9','10']].sum()/n_season.sum():.0%}.")

# ---------- 4/5. faceted monthly maps ----------
def facet(metric, breaks, ramp, legend_title, name, title, subtitle):
    fig, axes = plt.subplots(2, 4, figsize=(13.33, 7.5))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.06, wspace=0.02, hspace=0.12)
    for ax, m in zip(axes.flat, MONTHS):
        sub = monthly[monthly.month == m].set_index("code")
        draw_choropleth(ax, sub[metric], sub["n"], breaks, ramp, label_values=False, fs=6)
        tot = int(sub["n"].sum())
        ax.set_title(f"{MON_LABEL[m]}  (n = {tot:,})", fontsize=10, loc="left", color=INK, pad=2)
    lax = axes.flat[-1]; lax.set_axis_off()
    class_legend(lax, breaks, ramp, pct, legend_title, loc="center left")
    finish(fig, name, title, subtitle,
           NOTE + "  *Oct partial (through Oct 7). n = eCRC interviews." + (EST_NOTE if metric == "pct_fish" else ""))

facet("pct_fish", FISH_BREAKS, BLUE, "% of fish via eCRC (est.)", "04_monthly_map_pct_fish_ecrc.png",
      "Share of fish via eCRC (estimated), by month",
      "Most areas enter the sample in July; hatched cells rest on fewer than 10 eCRC interviews.")
facet("pct_refused", REF_BREAKS, ORANGE, "% of eCRC anglers refusing", "05_monthly_map_refusal.png",
      "Scan refusal rate, by month",
      "Refusals fall through the season in most areas; Area 6 stays high throughout.")

# ---------- 6. monthly lines, all areas ----------
am = all_months.copy()
am["m"] = am["Month"].map(MON_LABEL)
fig, ax = plt.subplots(figsize=(10, 5.6)); fig.subplots_adjust(left=0.08, right=0.97, top=0.84, bottom=0.14)
for key, col, lab in [("fish", "% fish via eCRC (est.)", "% of fish via eCRC (est.)"),
                      ("refusal", "% anglers refused", "% of eCRC anglers refusing scan")]:
    y = am[col].astype(float).values
    ax.plot(am["m"], y, color=SERIES[key], lw=2, marker="o", ms=7, mec=SURFACE, mew=2, label=lab)
for i, n in enumerate(am["eCRC interviews"].astype(int)):
    ax.text(i, -0.045, f"n={n:,}", ha="center", fontsize=8, color=MUTED, transform=ax.get_xaxis_transform())
ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(1, decimals=0))
ax.set_ylim(0, 0.4); ax.grid(axis="y", color="#ecebe7", lw=0.8); ax.set_axisbelow(True)
for sp in ["top", "right", "left"]: ax.spines[sp].set_visible(False)
ax.tick_params(axis="x", pad=16, length=0); ax.tick_params(axis="y", length=0)
ax.legend(loc="upper right", frameon=False, fontsize=9)
finish(fig, "06_monthly_lines_all_areas.png", "eCRC metrics by month, all areas combined",
       "Scan refusals fell from 36% of eCRC anglers in April to 7% in September; estimated share of fish via eCRC held at 26-29% from July to September.",
       NOTE + "  Oct partial. n = eCRC interviews." + EST_NOTE)

# ---------- 7. monthly lines, small multiples by area ----------
fig, axes = plt.subplots(2, 5, figsize=(13.33, 6.6), sharex=True, sharey=True)
fig.subplots_adjust(left=0.06, right=0.99, top=0.80, bottom=0.12, wspace=0.08, hspace=0.32)
x = np.arange(len(MONTHS))
for ax, code in zip(axes.flat, AREAS):
    sub = monthly[monthly.code == code].set_index("month").reindex(MONTHS)
    ok = sub["n"] >= LOW_N
    for key, col in [("fish", "pct_fish"), ("refusal", "pct_refused")]:
        y = sub[col].where(ok).values
        ax.plot(x, y, color=SERIES[key], lw=2, marker="o", ms=5, mec=SURFACE, mew=1.2)
        lo = sub[col].where(~ok & sub[col].notna())
        ax.plot(x, lo.values, ls="", marker="o", ms=5, mfc=SURFACE, mec=SERIES[key], mew=1.2)
    ax.set_title(f"Area {LABEL.get(code, code)}  (n = {int(n_season[code]):,})", fontsize=9.5, loc="left")
    ax.grid(axis="y", color="#ecebe7", lw=0.8); ax.set_axisbelow(True)
    for sp in ["top", "right", "left"]: ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
ax.set_xticks(x, [MON_LABEL[m][0] if m != "2026-10" else "O*" for m in MONTHS])
axes.flat[0].yaxis.set_major_formatter(mpl.ticker.PercentFormatter(1, decimals=0))
axes.flat[0].set_ylim(0, 0.55)
h = [Line2D([], [], color=SERIES["fish"], lw=2, marker="o", mec=SURFACE, label="% of fish via eCRC (est.)"),
     Line2D([], [], color=SERIES["refusal"], lw=2, marker="o", mec=SURFACE, label="% of eCRC anglers refusing scan"),
     Line2D([], [], ls="", marker="o", mfc=SURFACE, mec=INK2, label=f"< {LOW_N} eCRC interviews (not connected)")]
fig.legend(handles=h, loc="upper left", bbox_to_anchor=(0.03, 0.905), ncol=3, frameon=False, fontsize=9)
finish(fig, "07_monthly_lines_by_area.png", "eCRC metrics by month and catch area",
       "",
       NOTE + "  Oct partial. n = season eCRC interviews." + EST_NOTE)
