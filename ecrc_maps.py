"""
PSSP 2026 eCRC metrics by Puget Sound marine catch area (Marine Areas 5-13).

Maps: agency GIS style. Lightened Esri World Imagery basemap, lat/long axes,
north arrow, scale bar, Washington locator inset showing all CRC areas.
Line plots: ggplot2-like theme_bw() or theme_classic().

Usage
  python ecrc_maps.py <summary.xlsx> <by-month.xlsx> <out_dir> [--slide]

  --slide  omit figure titles and captions (the slide title carries the message)

Inputs
  CRC.gdb.zip                         WDFW Catch Record Card area polygons (EPSG:2927)
  data/context_boundaries.geojson     WA, neighboring states and BC (us-atlas / world-atlas 10m)
"""
import os, json, sys, textwrap, zipfile, tempfile, pathlib
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap, BoundaryNorm

REPO = pathlib.Path(__file__).resolve().parent
SUMMARY_XLSX, MONTH_XLSX = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
OUT_DIR = pathlib.Path(sys.argv[3]); OUT_DIR.mkdir(parents=True, exist_ok=True)
SLIDE = "--slide" in sys.argv

NI = r"$\it{n}$"                  # italic n for sample-size labels
DPI = 400                        # high enough to stay sharp when scaled in PowerPoint
LOW_N = 10                      # eCRC interviews below this are flagged
from matplotlib import font_manager as _fm
_have = {f.name for f in _fm.fontManager.ttflist}
F = next((f for f in ["Arial", "Helvetica", "FreeSans", "Liberation Sans"] if f in _have), "DejaVu Sans")  # Arial-metric sans
INK = "#111111"
IMAGERY, WASH, DESAT = os.environ.get("NO_IMAGERY") is None, 0.62, 0.45

# validation log: what each figure actually draws (written when ECRC_LOG is set)
LOG = {}
def log(key, val):
    LOG[key] = val
YLGN = ["#ffffcc", "#c2e699", "#78c679", "#31a354", "#006837"]      # ColorBrewer YlGn 5
ORANGES = ["#feedde", "#fdbe85", "#fd8d3c", "#e6550d", "#a63603"]   # ColorBrewer Oranges 5
FISH_COL, REF_COL = "#238b45", "#d94801"                            # line colors tied to map ramps
DATA_NOTE = "Data: PSSP creel interviews, Apr 1–Oct 7, 2026 (October partial)."
MAP_NOTE = " Map: WDFW Catch Record Card areas; imagery: Esri World Imagery."
EST_NOTE = " eCRC fish estimated as total fish × eCRC licenses ÷ (paper + eCRC licenses), by area."

mpl.rcParams.update({"mathtext.fontset": "custom", "mathtext.rm": F, "mathtext.it": F + ":italic",
                     "mathtext.bf": F + ":bold", "font.family": F, "font.size": 10, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})

# ---------------- geometry ----------------
tmp = tempfile.mkdtemp()
zipfile.ZipFile(REPO / "CRC.gdb.zip").extractall(tmp)
crc = gpd.read_file(pathlib.Path(tmp) / "CRC.gdb").set_crs(2927, allow_override=True)
crc["code"] = crc["CatchRecordCode"].astype(str)
CODE_MAP = {"8_1": "81", "8_2": "82"}
LABEL = {"81": "8-1", "82": "8-2"}
AREAS = ["5", "6", "7", "81", "82", "9", "10", "11", "12", "13"]
ps = crc[crc.code.isin(AREAS)].dissolve(by="code", as_index=False)
x0, y0, x1, y1 = ps.total_bounds; pad = 42000
corners = gpd.GeoSeries(gpd.points_from_xy([x0 - pad, x1 + pad], [y0 - pad, y1 + pad]), crs=2927).to_crs(4326)
EXT = (corners.x.min(), corners.x.max(), corners.y.min(), corners.y.max())
ASPECT = 1 / np.cos(np.deg2rad(47.8))
ps4 = ps.to_crs(4326)
crc4 = crc.to_crs(4326)
CTXB = gpd.read_file(REPO / "data/context_boundaries.geojson")
NUDGE = {"7": (-60000, 20000), "6": (0, -15000), "13": (-25000, 0), "12": (0, 30000), "81": (-15000, 0)}

def anchor(code):
    p = ps4.loc[ps4.code == code].geometry.representative_point().iloc[0]
    dx, dy = NUDGE.get(code, (0, 0))
    return p.x + dx / 270000, p.y + dy / 365000          # ft offsets to approx degrees

# ---------------- data ----------------
def read_summary():
    raw = pd.read_excel(SUMMARY_XLSX, header=None)
    hdr = raw.index[raw[1].astype(str).eq("Catch area")][0]
    ncol = int(raw.iloc[hdr].last_valid_index()) + 1
    df = raw.iloc[hdr + 1:, 1:ncol].copy(); df.columns = raw.iloc[hdr, 1:ncol].tolist()
    df = df[df["Catch area"].notna() & (df["Catch area"].astype(str) != "Total")]
    df["code"] = df["Catch area"].astype(str).replace(CODE_MAP)
    for c in df.columns[1:-1]:
        df[c] = pd.to_numeric(df[c])
    return df.set_index("code")

def read_grid(title):
    raw = pd.read_excel(MONTH_XLSX, header=None)
    r = raw.index[raw[0].astype(str).str.startswith(title)][0]
    cols = [h for h in raw.iloc[r + 1].tolist() if pd.notna(h)]
    rows = []
    for i in range(r + 2, len(raw)):
        a = raw.iloc[i, 0]
        if pd.isna(a) or str(a) == "All areas":
            break
        rows.append(raw.iloc[i].tolist()[:len(cols)])
    df = pd.DataFrame(rows, columns=cols)
    df["code"] = df["Catch area"].astype(str).replace(CODE_MAP)
    df = df.replace("–", np.nan)
    months = [c for c in cols if str(c).startswith("2026-")]
    long = df.melt(id_vars="code", value_vars=months, var_name="month", value_name="value")
    long["value"] = pd.to_numeric(long["value"])
    return long

season = read_summary()
monthly = (read_grid("eCRC interviews by area and month").rename(columns={"value": "n"})
           .merge(read_grid("% of fish via eCRC").rename(columns={"value": "pct_fish"}), on=["code", "month"])
           .merge(read_grid("% anglers refused scan").rename(columns={"value": "pct_refused"}), on=["code", "month"]))
all_months = pd.read_excel(MONTH_XLSX, header=None, skiprows=4, nrows=8)
all_months.columns = all_months.iloc[0]; all_months = all_months.iloc[1:]
all_months = all_months[all_months["Month"] != "Total"].reset_index(drop=True)
MONTHS = sorted(monthly.month.unique())
MON = {m: pd.Timestamp(m + "-01").strftime("%b") for m in MONTHS}; MON["2026-10"] = "Oct*"

# ---------------- map pieces ----------------
def basemap(ax, zoom=11):
    ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(ASPECT)
    if IMAGERY:
        import contextily as cx, xyzservices.providers as xp
        cx.add_basemap(ax, crs="EPSG:4326", source=xp.Esri.WorldImagery, zoom=zoom, attribution=False, zorder=0)
        im = ax.images[-1]; arr = np.asarray(im.get_array()).astype(float)
        rgb = arr[..., :3] / (255.0 if arr.max() > 1 else 1.0)
        gray = rgb @ np.array([0.299, 0.587, 0.114])
        im.set_data(np.clip(DESAT * gray[..., None] + (1 - DESAT) * rgb, 0, 1))
        ax.add_patch(Rectangle((EXT[0], EXT[2]), EXT[1] - EXT[0], EXT[3] - EXT[2], fc="white", alpha=WASH, lw=0, zorder=0.5))
    else:
        ax.set_facecolor("#d6e6f2")

def latlong_axes(ax):
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{abs(v):.1f}°W"))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:.1f}°N"))
    ax.set_xlabel("Longitude (degree)", fontsize=9.5); ax.set_ylabel("Latitude (degree)", fontsize=9.5)
    ax.tick_params(labelsize=9)
    frame(ax)

def no_axes(ax):
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel(""); frame(ax)

def frame(ax, lw=1):
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_edgecolor("#333333"); sp.set_linewidth(lw)

def north_arrow(ax):
    ax.annotate("N", xy=(0.92, 0.95), xytext=(0.92, 0.88), xycoords="axes fraction", textcoords="axes fraction",
                ha="center", va="center", fontsize=11, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.5))

def scale_bar(ax, miles=20):
    d = miles * 1609.34 / (111320 * np.cos(np.deg2rad(47.8)))
    xs, ys = EXT[0] + 0.05 * (EXT[1] - EXT[0]), EXT[2] + 0.035 * (EXT[3] - EXT[2])
    ax.plot([xs, xs + d], [ys, ys], color="#333333", lw=3, solid_capstyle="butt", zorder=6)
    ax.plot([xs, xs + d / 2], [ys, ys], color="white", lw=1.2, solid_capstyle="butt", zorder=6)
    ax.text(xs + d / 2, ys + 0.03, f"{miles} mi", ha="center", fontsize=9, color="#333333", zorder=6)

def inset(ax):
    W = (-125.45, -116.35, 45.3, 49.35)
    ia = ax.inset_axes([0.12, 0.075, 0.38, 0.22])
    ia.set_facecolor("#dce8f1")
    CTXB[CTXB.name != "Washington"].plot(ax=ia, color="#a9a7a0", edgecolor="#f4f3ef", linewidth=0.5, zorder=1)
    wa = CTXB[CTXB.name == "Washington"]
    wa.plot(ax=ia, color="#fbfaf7", edgecolor="none", zorder=1)
    crc4[~crc4.code.isin(["1", "2", "3", "4"])].plot(ax=ia, facecolor="none", edgecolor="#9a988f", linewidth=0.12, zorder=2)
    ps4.plot(ax=ia, color="#31a354", edgecolor="#333333", linewidth=0.15, zorder=3)
    wa.boundary.plot(ax=ia, color="#222222", linewidth=0.7, zorder=4)
    ia.add_patch(Rectangle((EXT[0], EXT[2]), EXT[1] - EXT[0], EXT[3] - EXT[2], fill=False, ec="#c0392b", lw=1.2, zorder=5))
    ia.set_xlim(W[0], W[1]); ia.set_ylim(W[2], W[3]); ia.set_aspect(1 / np.cos(np.deg2rad(47.3)))
    no_axes(ia); frame(ia, 0.8)

def pct_half_up(v):
    """Whole-percent label rounded half up (9/40 = 22.5% -> 23%), matching conventional reporting."""
    from decimal import Decimal, ROUND_HALF_UP
    return f"{Decimal(str(round(v * 100, 9))).quantize(Decimal('1'), rounding=ROUND_HALF_UP)}%"

def area_labels(ax, values=None, fs=10, fmt=None, key=None):
    for c in AREAS:
        x, y = anchor(c)
        txt = LABEL.get(c, c)
        if values is not None:
            v = values.get(c, np.nan)
            txt += "\n" + ("–" if pd.isna(v) else (fmt.format(v) if fmt else pct_half_up(v)))
        if key: LOG.setdefault(key, {})[c] = txt
        ax.text(x, y, txt, ha="center", va="center", fontsize=fs, fontweight="bold", color=INK, linespacing=1.0,
                zorder=7, path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

def choropleth(ax, values, n, breaks, ramp, key=None):
    d = ps4.copy()
    d["v"] = d.code.map(values); d["n"] = d.code.map(n)
    d.loc[d.n == 0, "v"] = np.nan
    has = d[d.v.notna()]
    has.plot(ax=ax, column="v", cmap=ListedColormap(ramp), norm=BoundaryNorm(breaks, len(ramp)),
             edgecolor="#333333", linewidth=0.6, zorder=2)
    if key:   # read back the colors actually drawn (geopandas explodes multipart geometries, colors repeat per part)
        fc = ax.collections[-1].get_facecolor(); parts = has.geometry.apply(lambda g: len(getattr(g, "geoms", [g])))
        ramp_rgb = [mpl.colors.to_rgba(c) for c in ramp]; i = 0; drawn = {}
        for code, k in zip(has.code, parts):
            col = tuple(np.round(fc[i], 4)); i += k
            drawn[code] = int(np.argmin([np.abs(np.array(col) - np.array(r)).sum() for r in ramp_rgb]))
        log(key, {c: {"v": None if pd.isna(v) else float(v), "n": None if pd.isna(nn) else float(nn),
                      "class": drawn.get(c), "hatched": bool(c in set(has[has.n < LOW_N].code)),
                      "nodata": bool(pd.isna(v))} for c, v, nn in zip(d.code, d.v, d.n)})
    low = has[has.n < LOW_N]
    if len(low):
        low.plot(ax=ax, facecolor="none", edgecolor="#333333", hatch="////", linewidth=0.6, zorder=3)
    nod = d[d.v.isna()]
    if len(nod):
        nod.plot(ax=ax, facecolor="#ffffff", alpha=0.55, edgecolor="#333333", linewidth=0.5, zorder=2)
        nod.plot(ax=ax, facecolor="none", edgecolor="#333333", linewidth=0.5, linestyle="--", zorder=3)

def class_handles(breaks, ramp, low=False, nodata=False):
    lab = [f"< {breaks[1]:.0%}"] + [f"{breaks[i]:.0%}–{breaks[i+1]:.0%}" for i in range(1, len(ramp) - 1)] + [f"{breaks[-2]:.0%} +"]
    h = [Patch(fc=c, ec="#333333", lw=0.6, label=l) for c, l in zip(ramp, lab)]
    if low:
        h.append(Patch(fc="white", ec="#333333", hatch="////", lw=0.6, label=f"< {LOW_N} eCRC interviews"))
    if nodata:
        h.append(Patch(fc="white", ec="#333333", ls="--", lw=0.6, label="No eCRC data"))
    return h

def boxed_legend(ax, handles, title, loc="upper left", **kw):
    return ax.legend(handles=handles, title=title, loc=loc, fontsize=9, title_fontsize=9.5, frameon=True,
                     framealpha=1, edgecolor="#333333", fancybox=False, alignment="left", **kw)

def finish(fig, ax_or_none, name, title, note):
    LOG.setdefault("captions", {})[name] = {"title": title, "note": note}
    if not SLIDE:
        if ax_or_none is not None:
            ax_or_none.set_title(title, fontsize=11, fontweight="bold", loc="left", pad=8)
        else:
            fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
        fig.canvas.draw()
        bb = fig.get_tightbbox(fig.canvas.get_renderer())          # inches; place note just below everything drawn
        x = bb.x0 / fig.get_figwidth(); y = bb.y0 / fig.get_figheight() - 0.012
        width_chars = int((bb.x1 - bb.x0) * 17)                      # ~17 chars per inch at 7.5 pt
        fig.text(x, y, textwrap.fill(note, width_chars), fontsize=7.5, color="#444444", va="top", ha="left")
    fig.savefig(OUT_DIR / name, dpi=DPI, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    plt.close(fig); print("wrote", name)

FISH_BREAKS = [0, .15, .20, .25, .30, 1]
REF_BREAKS = [0, .05, .10, .20, .30, 1]
s = season

def season_map(name, values, breaks, ramp, legend_title, title, note):
    fig, ax = plt.subplots(figsize=(7.5, 9))
    basemap(ax); choropleth(ax, values, s["eCRC interviews"], breaks, ramp, key=name)
    area_labels(ax, values, key=name + ":labels")
    latlong_axes(ax); north_arrow(ax); scale_bar(ax); inset(ax)
    boxed_legend(ax, class_handles(breaks, ramp), legend_title)
    finish(fig, ax, name, title, note)

# 1. % fish via eCRC
season_map("01_season_pct_fish_ecrc.png", s["% fish via eCRC"], FISH_BREAKS, YLGN, "Percent of fish\n(eCRC, estimated)",
           "Estimated percent of harvested fish reported by eCRC, Marine Areas 5–13, 2026",
           DATA_NOTE + MAP_NOTE + EST_NOTE)
# 2. refusal rate
season_map("02_season_refusal_rate.png", s["% anglers refused"], REF_BREAKS, ORANGES, "Percent of eCRC\nanglers refusing",
           "Percent of eCRC anglers refusing barcode scan, Marine Areas 5–13, 2026", DATA_NOTE + MAP_NOTE)

# 3. sample size: eCRC interviews (outer) with barcode scans nested inside
OUTER, INNER, EDGE = "#9ecae1", "#08519c", "#08306b"
fig, ax = plt.subplots(figsize=(7.5, 9))
basemap(ax)
ps4.plot(ax=ax, facecolor="white", alpha=0.45, edgecolor="none", zorder=1.5)
ps4.plot(ax=ax, facecolor="none", edgecolor="#333333", linewidth=0.6, zorder=2)
n = s["eCRC interviews"]; scans = s["Barcode scans"]; SMAX = 1400
size = lambda v: SMAX * v / n.max()
SIDE = {"82": "right", "9": "left", "81": "left"}   # keep crowded central-Sound labels apart
for c in AREAS:
    x, y = anchor(c)
    ax.scatter(x, y, s=size(n[c]), color=OUTER, edgecolor=EDGE, linewidth=0.8, alpha=0.95, zorder=4)
    ax.scatter(x, y, s=size(scans[c]), color=INNER, edgecolor="white", linewidth=0.5, zorder=5)
    r = np.sqrt(size(n[c])) / 2
    side = SIDE.get(c, "below")
    lines = [(LABEL.get(c, c), "bold", 9), (f"({NI} = {n[c]:,})", "normal", 8.5),
             (f"{int(scans[c]):,} scans", "normal", 8.5)]
    LOG.setdefault("03:circles", {})[c] = {"outer_size": float(size(n[c])), "inner_size": float(size(scans[c])),
                                           "labels": [t for t, _, _ in lines]}
    for k, (txt, wt, fs) in enumerate(lines):
        if side == "below":
            xy, ha, va = (0, -(r + 3) - [0, 11, 21.5][k]), "center", "top"
        else:   # beside the circle, three lines centered vertically on it
            dx = r + 4 if side == "right" else -(r + 4)
            xy, ha, va = (dx, 10.5 - 10.5 * k), ("left" if side == "right" else "right"), "center"
        ax.annotate(txt, (x, y), xytext=xy, textcoords="offset points", ha=ha, va=va,
                    fontsize=fs, fontweight=wt, zorder=7, path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
latlong_axes(ax); north_arrow(ax); scale_bar(ax); inset(ax)
h = [Line2D([], [], marker="o", ls="", color=OUTER, mec=EDGE, markersize=np.sqrt(size(r)), label=f"{r:,}")
     for r in [100, 500, 1500]]
leg1 = boxed_legend(ax, h, "Circle size (count)", ncol=3, columnspacing=2.2, handletextpad=1.6, borderpad=1.4,
                    handleheight=3.2)
ax.add_artist(leg1)
h2 = [Line2D([], [], marker="o", ls="", ms=9, color=OUTER, mec=EDGE, label="eCRC interviews"),
      Line2D([], [], marker="o", ls="", ms=9, color=INNER, mec="white", label="Barcode scans")]
fig.canvas.draw()
bb = leg1.get_window_extent().transformed(ax.transAxes.inverted())
boxed_legend(ax, h2, None, loc="upper left", bbox_to_anchor=(bb.x0, bb.y0 - 0.008), borderaxespad=0, ncol=2)
finish(fig, ax, "03_season_ecrc_sample_size.png",
       "eCRC interviews and barcode scans by catch area, Marine Areas 5–13, 2026", DATA_NOTE + MAP_NOTE)

# 4/5. faceted monthly maps
def facet(metric, breaks, ramp, legend_title, name, title, note):
    fig, axes = plt.subplots(2, 4, figsize=(13.33, 8.2))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.04, wspace=0.04, hspace=0.12)
    for ax, m in zip(axes.flat, MONTHS):
        sub = monthly[monthly.month == m].set_index("code")
        basemap(ax, zoom=10); choropleth(ax, sub[metric], sub["n"], breaks, ramp, key=f"{name}:{m}")
        for c in AREAS:
            x, y = anchor(c)
            ax.text(x, y, LABEL.get(c, c), ha="center", va="center", fontsize=6.5, fontweight="bold", zorder=7,
                    path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])
        no_axes(ax)
        ax.set_title(f"{MON[m]} ({NI} = {int(sub['n'].sum()):,})", fontsize=10, loc="left", pad=3)
        LOG.setdefault(f"{name}:titles", {})[m] = ax.get_title(loc="left")
    lax = axes.flat[-1]; lax.set_axis_off()
    boxed_legend(lax, class_handles(breaks, ramp, low=True, nodata=True), legend_title, loc="center left")
    finish(fig, None, name, title, note + " " + NI + " = eCRC interviews in month. *October partial.")

facet("pct_fish", FISH_BREAKS, YLGN, "Percent of fish\n(eCRC, estimated)", "04_monthly_map_pct_fish_ecrc.png",
      "Estimated percent of harvested fish reported by eCRC by month, Marine Areas 5–13, 2026",
      DATA_NOTE + MAP_NOTE + EST_NOTE)
facet("pct_refused", REF_BREAKS, ORANGES, "Percent of eCRC\nanglers refusing", "05_monthly_map_refusal.png",
      "Percent of eCRC anglers refusing barcode scan by month, Marine Areas 5–13, 2026", DATA_NOTE + MAP_NOTE)

# ---------------- line plots: ggplot2-like themes ----------------
def gg_theme(ax, theme):
    ax.set_facecolor("white")
    if theme == "bw":            # theme_bw(): grey92 major/minor grid, black panel border
        ax.grid(True, which="major", color="#ebebeb", lw=0.8); ax.grid(True, which="minor", color="#f5f5f5", lw=0.5)
        ax.yaxis.set_minor_locator(mpl.ticker.AutoMinorLocator(2))
        for sp in ax.spines.values(): sp.set_visible(True); sp.set_color("#333333"); sp.set_linewidth(0.8)
    else:                        # theme_classic(): no grid, black x and y axis lines only
        ax.grid(False)
        for k, sp in ax.spines.items():
            sp.set_visible(k in ("left", "bottom")); sp.set_color("black"); sp.set_linewidth(0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors="black", labelcolor="black", length=3, width=0.6, which="major")
    ax.tick_params(which="minor", length=0)

def strip(ax, text, theme):
    """facet_wrap strip: grey85 box with border (bw) or white box with black border (classic)."""
    fc = "#d9d9d9" if theme == "bw" else "white"
    ax.text(0.5, 1.02, text, transform=ax.transAxes, ha="center", va="bottom", fontsize=9,
            bbox=dict(boxstyle="square,pad=0.3", fc=fc, ec="#333333" if theme == "bw" else "black", lw=0.8),
            clip_on=False)

SERIES = [("pct_fish", "Percent of fish via eCRC (est.)", FISH_COL, "% fish via eCRC (est.)"),
          ("pct_refused", "Percent of eCRC anglers refusing scan", REF_COL, "% anglers refused")]
pct = mpl.ticker.PercentFormatter(1, decimals=0)

for theme in ("bw",):
    # 6. all areas
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(all_months))
    for key, lab, col, src in SERIES:
        ax.plot(x, all_months[src].astype(float), color=col, lw=1.2, marker="o", ms=5, label=lab)
    ax.set_xticks(x, [f"{MON[m]}\n({NI} = {int(v):,})" for m, v in zip(all_months["Month"], all_months["eCRC interviews"])])
    log("06:xticks", [t.get_text() for t in ax.get_xticklabels()])
    log("06:lines", {lab: [float(v) for v in l.get_ydata()] for l, lab in zip(ax.get_lines(), [x_[0] for x_ in SERIES])})
    ax.yaxis.set_major_formatter(pct); ax.set_ylim(0, 0.4)
    ax.set_xlabel("Month"); ax.set_ylabel("Percent")
    gg_theme(ax, theme)
    ax.legend(title="Metric", loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=9, title_fontsize=9.5,
              alignment="left")
    finish(fig, ax, "06_monthly_lines_all_areas.png",
           "Monthly eCRC metrics, all Marine Areas 5–13 combined, 2026",
           DATA_NOTE + EST_NOTE + " " + NI + " = eCRC interviews.")

    # 7. by area
    fig, axes = plt.subplots(2, 5, figsize=(13.33, 6.4), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.06, right=0.84, top=0.88, bottom=0.12, wspace=0.08, hspace=0.32)
    xm = np.arange(len(MONTHS))
    for ax, c in zip(axes.flat, AREAS):
        sub = monthly[monthly.code == c].set_index("month").reindex(MONTHS)
        ok = sub["n"] >= LOW_N
        for key, lab, col, _ in SERIES:
            ax.plot(xm, sub[key].where(ok), color=col, lw=1.2, marker="o", ms=4)
            ax.plot(xm, sub[key].where(~ok & sub[key].notna()), ls="", marker="o", ms=4, mfc="white", mec=col, mew=1)
        LOG.setdefault("07:panels", {})[c] = {
            "solid": {k: [None if not np.isfinite(v) else float(v) for v in ax.get_lines()[2 * j].get_ydata()] for j, (k, *_ ) in enumerate(SERIES)},
            "hollow": {k: [None if not np.isfinite(v) else float(v) for v in ax.get_lines()[2 * j + 1].get_ydata()] for j, (k, *_ ) in enumerate(SERIES)}}
        gg_theme(ax, theme)
        strip(ax, f"Area {LABEL.get(c, c)} ({NI} = {int(s.loc[c, 'eCRC interviews']):,})", theme)
        LOG["07:panels"][c]["strip"] = ax.texts[-1].get_text()
    axes.flat[0].yaxis.set_major_formatter(pct); axes.flat[0].set_ylim(-0.02, 0.55)
    for ax in axes[1]:
        ax.set_xticks(xm, [MON[m][0] if m != "2026-10" else "O*" for m in MONTHS])
    fig.supxlabel("Month", fontsize=10, y=0.04); fig.supylabel("Percent", fontsize=10, x=0.015)
    h = [Line2D([], [], color=col, lw=1.2, marker="o", ms=5, label=lab) for _, lab, col, _ in SERIES]
    h.append(Line2D([], [], ls="", marker="o", ms=5, mfc="white", mec="#4d4d4d", label=f"< {LOW_N} eCRC interviews"))
    fig.legend(handles=h, title="Metric", loc="center left", bbox_to_anchor=(0.85, 0.5), frameon=False,
               fontsize=9, title_fontsize=9.5, alignment="left")
    finish(fig, None, "07_monthly_lines_by_area.png",
           "Monthly eCRC metrics by catch area, Marine Areas 5–13, 2026",
           DATA_NOTE + EST_NOTE + " " + NI + " = season eCRC interviews.")


# 8. barcode scans and refusals per eCRC interview, by area (theme_bw)
fig, ax = plt.subplots(figsize=(9, 5))
xa = np.arange(len(AREAS)); w = 0.38
scan_rate = (s["Barcode scans"] / s["eCRC interviews"]).reindex(AREAS)
ref_rate = (s["Interviews w/ a refusal"] / s["eCRC interviews"]).reindex(AREAS)
b1 = ax.bar(xa - w / 2, scan_rate, w, color="#2c7fb8", edgecolor="#333333", lw=0.4, label="Barcode scans")
b2 = ax.bar(xa + w / 2, ref_rate, w, color=REF_COL, edgecolor="#333333", lw=0.4, label="Interviews with a scan refusal")
for bars, vals in [(b1, s["Barcode scans"].reindex(AREAS)), (b2, s["Interviews w/ a refusal"].reindex(AREAS))]:
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.008, f"{int(v):,}", ha="center", va="bottom",
                fontsize=7.5, color="black")
ax.axhline(0.6, color="#333333", ls="--", lw=1)
ax.text(len(AREAS) - 0.5, 0.612, "Barcode question shown in a random 60% of eligible interviews", ha="right", va="bottom", fontsize=8.5)
ax.set_xticks(xa, [f"{LABEL.get(c, c)}\n({NI} = {int(s.loc[c, 'eCRC interviews']):,})" for c in AREAS])
ax.yaxis.set_major_formatter(pct); ax.set_ylim(0, 0.7)
ax.set_xlabel("Catch area"); ax.set_ylabel("Percent of eCRC interviews")
gg_theme(ax, "bw"); ax.grid(axis="x", which="both", visible=False)
ax.legend(title="Outcome", loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=9,
          title_fontsize=9.5, alignment="left")
tot_rate = s["Barcode scans"].sum() / s["eCRC interviews"].sum()
log("08:bars", {c: {"scan_h": float(b1[i].get_height()), "ref_h": float(b2[i].get_height())} for i, c in enumerate(AREAS)})
log("08:labels", [t.get_text() for t in ax.texts])
log("08:xticks", [t.get_text() for t in ax.get_xticklabels()])
finish(fig, ax, "08_scans_refusals_by_area.png",
       "Barcode scans and scan refusals per eCRC interview by catch area, Marine Areas 5–13, 2026",
       DATA_NOTE + f" Eligible interviews: an eCRC angler harvested a salmon or steelhead. Overall: {int(s["Barcode scans"].sum()):,} scans in {int(s['eCRC interviews'].sum()):,} eCRC interviews"
       f" ({tot_rate:.0%}). Counts above bars. A group can produce more than one scan, so scans per interview"
       " is an upper bound on interviews with a completed scan. " + NI + " = eCRC interviews.")

if os.environ.get("ECRC_LOG"):
    json.dump(LOG, open(os.environ["ECRC_LOG"], "w", encoding="utf-8"), indent=1, default=float)
    print("log written")
