"""Render the season eCRC fish-share map in three candidate styles for comparison."""
import sys, zipfile, tempfile, pathlib
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib as mpl, matplotlib.pyplot as plt
from matplotlib.patches import Patch, FancyArrow
from matplotlib.colors import ListedColormap, BoundaryNorm

REPO = pathlib.Path(__file__).resolve().parent
SUMMARY = sys.argv[1]; OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

tmp = tempfile.mkdtemp(); zipfile.ZipFile(REPO / "CRC.gdb.zip").extractall(tmp)
crc = gpd.read_file(pathlib.Path(tmp) / "CRC.gdb").set_crs(2927, allow_override=True)
crc["code"] = crc.CatchRecordCode.astype(str)
AREAS = ["5", "6", "7", "81", "82", "9", "10", "11", "12", "13"]
LAB = {"81": "8-1", "82": "8-2"}
ps = crc[crc.code.isin(AREAS)].dissolve(by="code", as_index=False)
raw = pd.read_excel(SUMMARY, header=None)
h = raw.index[raw[1].astype(str).eq("Catch area")][0]
df = raw.iloc[h + 1:, 1:12]; df.columns = raw.iloc[h, 1:12].tolist()
df = df[df["Catch area"].astype(str) != "Total"].dropna(subset=["Catch area"])
df["code"] = df["Catch area"].astype(str).replace({"8_1": "81", "8_2": "82"})
ps = ps.merge(df[["code", "% fish via eCRC"]].rename(columns={"% fish via eCRC": "v"}), on="code")
ps["v"] = ps.v.astype(float)
x0, y0, x1, y1 = ps.total_bounds; pad = 25000
EXT = (x0 - pad, x1 + pad, y0 - pad, y1 + pad)
ctx = crc.cx[EXT[0]:EXT[1], EXT[2]:EXT[3]]; ctx = ctx[~ctx.code.isin(AREAS)]
NUDGE = {"7": (-60000, 20000), "6": (0, -15000), "13": (-25000, 0), "12": (0, 30000), "81": (-15000, 0)}
def anchor(c):
    p = ps.loc[ps.code == c].geometry.representative_point().iloc[0]; d = NUDGE.get(c, (0, 0))
    return p.x + d[0], p.y + d[1]
BREAKS = [0, .15, .20, .25, .30, 1]
LABELS = ["< 15%", "15–20%", "20–25%", "25–30%", "30% +"]

def north_arrow(ax, x, y, size, color, font):
    ax.annotate("N", xy=(x, y), xytext=(x, y - size), ha="center", va="center", fontsize=11,
                fontfamily=font, fontweight="bold", color=color,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5), xycoords="axes fraction",
                textcoords="axes fraction")

def scale_bar(ax, miles, font, color="#333333"):
    ft = miles * 5280
    xs, ys = EXT[0] + 0.05 * (EXT[1] - EXT[0]), EXT[2] + 0.04 * (EXT[3] - EXT[2])
    ax.plot([xs, xs + ft], [ys, ys], color=color, lw=3, solid_capstyle="butt")
    ax.plot([xs, xs + ft / 2], [ys, ys], color="white", lw=1.2, solid_capstyle="butt")
    ax.text(xs + ft / 2, ys + 9000, f"{miles} mi", ha="center", fontsize=9, fontfamily=font, color=color)

# ---------- Option A: classic agency GIS map ----------
def option_a():
    F = "FreeSans"
    ramp = ["#ffffcc", "#c2e699", "#78c679", "#31a354", "#006837"]
    fig, ax = plt.subplots(figsize=(7.5, 9))
    ax.set_facecolor("#dbe9f4")
    ctx.plot(ax=ax, color="#f0efe9", edgecolor="#b8b6ae", linewidth=0.3)
    ps.plot(ax=ax, column="v", cmap=ListedColormap(ramp), norm=BoundaryNorm(BREAKS, 5), edgecolor="#333333", linewidth=0.6)
    for c in AREAS:
        x, y = anchor(c)
        ax.text(x, y, LAB.get(c, c), ha="center", va="center", fontsize=10, fontfamily=F, fontweight="bold", color="#111111",
                path_effects=[mpl.patheffects.withStroke(linewidth=2.5, foreground="white")])
    ax.set_xlim(EXT[:2]); ax.set_ylim(EXT[2:]); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
    for sp in ax.spines.values(): sp.set_edgecolor("#333333"); sp.set_linewidth(1)
    leg = ax.legend(handles=[Patch(fc=c, ec="#333333", lw=0.6, label=l) for c, l in zip(ramp, LABELS)],
                    title="Percent of fish\n(eCRC, estimated)", loc="upper left", fontsize=9, title_fontsize=9.5,
                    frameon=True, framealpha=1, edgecolor="#333333", fancybox=False, prop={"family": F})
    leg.get_title().set_fontfamily(F)
    north_arrow(ax, 0.92, 0.95, 0.07, "#111111", F)
    scale_bar(ax, 20, F)
    ax.set_title("Estimated percent of harvested fish reported by eCRC, Marine Areas 5–13, 2026",
                 fontsize=11, fontfamily=F, fontweight="bold", loc="left", pad=8)
    fig.text(0.02, 0.01, "Data: PSSP creel interviews, Apr 1–Oct 7, 2026. Map: WDFW Catch Record Card areas.",
             fontsize=7.5, fontfamily=F, color="#444444")
    fig.savefig(OUT / "style_A_agency_gis.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- Option B: matches the PSSU deck (Calibri-like, WDFW greens, no figure title) ----------
def option_b():
    F = "Carlito"
    ramp = ["#d9efe6", "#9fd3bd", "#4fae8a", "#007b55", "#0e4d3a"]
    fig, ax = plt.subplots(figsize=(7.5, 9))
    ctx.plot(ax=ax, color="#e6e7e8", edgecolor="#ffffff", linewidth=0.4)
    ps.plot(ax=ax, column="v", cmap=ListedColormap(ramp), norm=BoundaryNorm(BREAKS, 5), edgecolor="#ffffff", linewidth=0.8)
    for c in AREAS:
        x, y = anchor(c); v = ps.loc[ps.code == c, "v"].iloc[0]
        ax.text(x, y, f"{LAB.get(c, c)}\n{v:.0%}", ha="center", va="center", fontsize=11, fontfamily=F, color="#0f426b",
                linespacing=1.0, path_effects=[mpl.patheffects.withStroke(linewidth=3, foreground="white")])
    ax.set_xlim(EXT[:2]); ax.set_ylim(EXT[2:]); ax.set_aspect("equal"); ax.set_axis_off()
    ax.legend(handles=[Patch(fc=c, ec="none", label=l) for c, l in zip(ramp, LABELS)], loc="upper left",
              frameon=False, prop={"family": F, "size": 11}, title="eCRC share of fish", title_fontproperties={"family": F, "size": 11, "weight": "bold"})
    fig.savefig(OUT / "style_B_deck_match.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- Option C: report figure, ggplot-like with graticule and continuous scale ----------
def option_c():
    F = "Bitstream Charter"
    p4 = ps.to_crs(4326); c4 = ctx.to_crs(4326)
    e = gpd.GeoSeries(gpd.points_from_xy([EXT[0], EXT[1]], [EXT[2], EXT[3]]), crs=2927).to_crs(4326)
    fig, ax = plt.subplots(figsize=(7.5, 9))
    c4.plot(ax=ax, color="#ededed", edgecolor="#c9c9c9", linewidth=0.3)
    p4.plot(ax=ax, column="v", cmap="viridis_r", vmin=0.15, vmax=0.37, edgecolor="#555555", linewidth=0.4,
            legend=True, legend_kwds={"shrink": 0.45, "label": "Fish via eCRC (est.)", "format": mpl.ticker.PercentFormatter(1, 0)})
    for cc in AREAS:
        pt = p4.loc[p4.code == cc].geometry.representative_point().iloc[0]
        d = NUDGE.get(cc, (0, 0))
        ax.text(pt.x + d[0] / 270000, pt.y + d[1] / 365000, LAB.get(cc, cc), ha="center", va="center", fontsize=10, fontfamily=F,
                path_effects=[mpl.patheffects.withStroke(linewidth=2.5, foreground="white")])
    ax.set_xlim(e.x.min(), e.x.max()); ax.set_ylim(e.y.min(), e.y.max())
    ax.set_aspect(1 / np.cos(np.deg2rad(47.8)))
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.grid(color="#e3e3e3", lw=0.6); ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{abs(v):.1f}°W"))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:.1f}°N"))
    for t in ax.get_xticklabels() + ax.get_yticklabels(): t.set_fontfamily(F); t.set_fontsize(9)
    for sp in ax.spines.values(): sp.set_visible(False)
    cb = fig.axes[-1]; cb.yaxis.label.set_fontfamily(F)
    for t in cb.get_yticklabels(): t.set_fontfamily(F)
    fig.text(0.08, 0.04, "Figure 1. Estimated percent of harvested fish from eCRC anglers by Marine Area,\nApril 1 to October 7, 2026.",
             fontsize=10, fontfamily=F, va="top")
    fig.savefig(OUT / "style_C_report_figure.png", dpi=200, bbox_inches="tight"); plt.close(fig)

import matplotlib.patheffects
print("ok")

# ---------- Option A2: agency GIS map, lat/long axes, island-filled land ----------
from shapely.geometry import Polygon
MARINE = ["1", "2", "3", "4", "5", "6", "7", "9", "10", "11", "12", "13", "21", "22", "22W", "81", "82"]
def holes(geom):
    polys = getattr(geom, "geoms", [geom])
    return [Polygon(r) for p in polys for r in p.interiors]

def option_a2(inset=None):
    F = "FreeSans"
    ramp = ["#ffffcc", "#c2e699", "#78c679", "#31a354", "#006837"]
    LAND, LAND_EDGE, WATER = "#f2f1ec", "#d9d7cf", "#d6e6f2"
    marine = crc[crc.code.isin(MARINE)]
    land_main = crc[~crc.code.isin(MARINE)]
    isl = gpd.GeoDataFrame(geometry=[h for g in marine.geometry for h in holes(g)], crs=crc.crs)
    land = pd.concat([land_main[["geometry"]], isl]).to_crs(4326)
    p4 = ps.to_crs(4326)
    e = gpd.GeoSeries(gpd.points_from_xy([EXT[0], EXT[1]], [EXT[2], EXT[3]]), crs=2927).to_crs(4326)
    lon0, lon1, lat0, lat1 = e.x.min(), e.x.max(), e.y.min(), e.y.max()
    land = land.cx[lon0 - .2:lon1 + .2, lat0 - .2:lat1 + .2]
    fig, ax = plt.subplots(figsize=(7.5, 9))
    ax.set_xlim(lon0, lon1); ax.set_ylim(lat0, lat1); ax.set_aspect(1 / np.cos(np.deg2rad(47.8)))
    if IMAGERY:
        import contextily as cx, xyzservices.providers as xp
        cx.add_basemap(ax, crs="EPSG:4326", source=xp.Esri.WorldImagery, zoom=10, attribution=False, zorder=0)
        im = ax.images[-1]; arr = np.asarray(im.get_array()).astype(float)
        rgb = arr[..., :3] / (255.0 if arr.max() > 1 else 1.0)
        gray = rgb @ np.array([0.299, 0.587, 0.114])
        rgb = DESAT * gray[..., None] + (1 - DESAT) * rgb   # pull color toward gray so it does not compete with the green fills
        im.set_data(np.clip(rgb, 0, 1))
        ax.add_patch(mpl.patches.Rectangle((lon0, lat0), lon1 - lon0, lat1 - lat0, fc="white", alpha=WASH, zorder=0.5, lw=0))
    else:
        ax.set_facecolor(WATER)
        land.plot(ax=ax, color=LAND, edgecolor=LAND, linewidth=0.2)
        land_main.to_crs(4326).cx[lon0 - .2:lon1 + .2, lat0 - .2:lat1 + .2].boundary.plot(ax=ax, color=LAND_EDGE, linewidth=0.3)
    p4.plot(ax=ax, column="v", cmap=ListedColormap(ramp), norm=BoundaryNorm(BREAKS, 5), edgecolor="#333333", linewidth=0.6, zorder=2)
    for c in AREAS:
        pt = p4.loc[p4.code == c].geometry.representative_point().iloc[0]; d = NUDGE.get(c, (0, 0))
        ax.text(pt.x + d[0] / 270000, pt.y + d[1] / 365000, LAB.get(c, c), ha="center", va="center", fontsize=10,
                fontfamily=F, fontweight="bold", color="#111111",
                path_effects=[mpl.patheffects.withStroke(linewidth=2.5, foreground="white")])
    ax.set_xlim(lon0, lon1); ax.set_ylim(lat0, lat1); ax.set_aspect(1 / np.cos(np.deg2rad(47.8)))
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{abs(v):.1f}°W"))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:.1f}°N"))
    ax.set_xlabel("Longitude (degree)", fontfamily=F, fontsize=9.5)
    ax.set_ylabel("Latitude (degree)", fontfamily=F, fontsize=9.5)
    for t in ax.get_xticklabels() + ax.get_yticklabels(): t.set_fontfamily(F); t.set_fontsize(9)
    for sp in ax.spines.values(): sp.set_edgecolor("#333333"); sp.set_linewidth(1)
    leg = ax.legend(handles=[Patch(fc=c, ec="#333333", lw=0.6, label=l) for c, l in zip(ramp, LABELS)],
                    title="Percent of fish\n(eCRC, estimated)", loc="upper left", fontsize=9, title_fontsize=9.5,
                    frameon=True, framealpha=1, edgecolor="#333333", fancybox=False, prop={"family": F})
    leg.get_title().set_fontfamily(F)
    north_arrow(ax, 0.92, 0.95, 0.07, "#111111", F)
    mi = 20 * 1609.34 / (111320 * np.cos(np.deg2rad(47.8)))
    xs, ys = lon0 + 0.05 * (lon1 - lon0), lat0 + 0.04 * (lat1 - lat0)
    ax.plot([xs, xs + mi], [ys, ys], color="#333333", lw=3, solid_capstyle="butt")
    ax.plot([xs, xs + mi / 2], [ys, ys], color="white", lw=1.2, solid_capstyle="butt")
    ax.text(xs + mi / 2, ys + 0.03, "20 mi", ha="center", fontsize=9, fontfamily=F, color="#333333")
    ax.set_title("Estimated percent of harvested fish reported by eCRC, Marine Areas 5–13, 2026",
                 fontsize=11, fontfamily=F, fontweight="bold", loc="left", pad=8)
    fig.text(0.02, 0.005, "Data: PSSP creel interviews, Apr 1–Oct 7, 2026. Map: WDFW Catch Record Card areas"
             + ("; imagery: Esri World Imagery." if IMAGERY else "."), fontsize=7.5, fontfamily=F, color="#444444")
    if inset:
        add_inset(ax, inset, ramp, (lon0, lon1, lat0, lat1), F)
    name = "style_A3_agency_gis_imagery" if IMAGERY else "style_A2_agency_gis_latlong"
    if inset: name += f"_inset_{inset}"
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)

def add_inset(ax, mode, ramp, box, F):
    """Washington locator inset: all CRC areas inside WA, neighbors shaded darker so WA stands out."""
    W = (-125.45, -116.35, 45.3, 49.35)
    ctxb = gpd.read_file(REPO / "data/context_boundaries.geojson")
    ia = ax.inset_axes([0.12, 0.075, 0.38, 0.22])
    ia.set_facecolor("#dce8f1")                                            # ocean
    ctxb[ctxb.name != "Washington"].plot(ax=ia, color="#a9a7a0", edgecolor="#f4f3ef", linewidth=0.5, zorder=1)
    wa = ctxb[ctxb.name == "Washington"]
    wa.plot(ax=ia, color="#fbfaf7", edgecolor="none", zorder=1)
    all4 = crc.to_crs(4326)
    if mode == "all":
        all4[~all4.code.isin(["1", "2", "3", "4"])].plot(ax=ia, facecolor="none", edgecolor="#9a988f", linewidth=0.12, zorder=2)
    ps.to_crs(4326).plot(ax=ia, column="v", cmap=ListedColormap(ramp), norm=BoundaryNorm(BREAKS, 5),
                         edgecolor="#333333", linewidth=0.15, zorder=3)
    wa.boundary.plot(ax=ia, color="#222222", linewidth=0.7, zorder=4)
    ia.add_patch(mpl.patches.Rectangle((box[0], box[2]), box[1] - box[0], box[3] - box[2], fill=False,
                                       ec="#c0392b", lw=1.2, zorder=5))
    ia.set_xlim(W[0], W[1]); ia.set_ylim(W[2], W[3]); ia.set_aspect(1 / np.cos(np.deg2rad(47.3)))
    ia.set_xticks([]); ia.set_yticks([]); ia.set_xlabel(""); ia.set_ylabel("")
    for sp in ia.spines.values(): sp.set_edgecolor("#333333"); sp.set_linewidth(0.8)

IMAGERY, WASH, DESAT = True, 0.62, 0.45
option_a2(inset="all")
