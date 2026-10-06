#!/usr/bin/env python3
"""Generate NELLE product renders as lit SVGs (faceless, black background).

Each garment is a flat vector shape run through an SVG lighting filter
(blurred alpha as height map + fabric noise) so it reads as a soft 3D
product shot rather than flat clip-art. Output: images/svg/<handle>.svg
(black bg) and images/svg/<handle>.transparent.svg.
"""
import os

W, H = 1000, 1250
OUT = os.path.join(os.path.dirname(__file__), "..", "images", "svg")


def smooth(pts, t=0.5):
    """Catmull-Rom through pts -> cubic bezier path segments (no leading M)."""
    d = ""
    p = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) * t / 3, p1[1] + (p2[1] - p0[1]) * t / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * t / 3, p2[1] - (p3[1] - p1[1]) * t / 3)
        d += f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} "
    return d


def mirror(pts):
    return [(W - x, y) for x, y in pts]


def leggings_path(length="full"):
    if length == "full":
        outer = [(292, 150), (272, 300), (262, 430), (268, 600), (295, 800), (318, 980), (332, 1150)]
        inner = [(440, 1150), (452, 980), (470, 800), (488, 620), (498, 500)]
        yb = 1150
    else:  # biker shorts
        outer = [(292, 150), (272, 300), (262, 430), (258, 580), (262, 730)]
        inner = [(484, 730), (490, 620), (497, 520)]
        yb = 730
    right_outer = mirror(outer)
    right_inner = mirror(inner)
    d = f"M{outer[0][0]},{outer[0][1]} "
    d += smooth(outer)
    d += f"L{inner[0][0]},{inner[0][1]} "
    d += smooth(inner)
    d += f"L{W/2:.0f},470 "
    d += f"L{right_inner[-1][0]},{right_inner[-1][1]} "
    d += smooth(right_inner[::-1])
    d += f"L{right_outer[-1][0]},{right_outer[-1][1]} "
    d += smooth(right_outer[::-1])
    d += f"Q{W/2:.0f},172 {outer[0][0]},{outer[0][1]} Z"
    return d, yb


def bra_path():
    left = [(500, 452), (455, 422), (425, 335), (402, 176)]
    outer = [(338, 172), (322, 262), (300, 342), (278, 410), (258, 480), (250, 570), (258, 700)]
    right_left = mirror(left)
    right_outer = mirror(outer)
    d = f"M{left[0][0]},{left[0][1]} "
    d += smooth(left)
    d += f"L{outer[0][0]},{outer[0][1]} "
    d += smooth(outer)
    d += f"Q{W/2:.0f},722 {right_outer[-1][0]},{right_outer[-1][1]} "
    d += smooth(right_outer[::-1])
    d += f"L{right_left[-1][0]},{right_left[-1][1]} "
    d += smooth(right_left[::-1])
    d += "Z"
    return d


def garment(kind, c):
    """Return svg group content for one garment in a 1000x1250 local space."""
    fill, band, seam, rim = c["fill"], c["band"], c["seam"], c["rim"]
    body = ""
    if kind in ("leggings", "shorts"):
        d, yb = leggings_path("full" if kind == "leggings" else "short")
        body += f'<defs><clipPath id="clipTop{kind}"><rect x="0" y="0" width="1000" height="262"/></clipPath></defs>'
        body += f'<g filter="url(#fabric)"><path d="{d}" fill="{fill}"/>'
        body += f'<path d="{d}" fill="{band}" clip-path="url(#clipTop{kind})"/></g>'
        body += f'<path d="{d}" fill="none" stroke="{rim}" stroke-width="2.2" stroke-opacity=".55"/>'
        # waistband seam + centre seam + side seams
        body += f'<path d="M278,262 Q500,284 722,262" fill="none" stroke="{seam}" stroke-width="2.2" stroke-opacity=".7"/>'
        body += f'<path d="M281,270 Q500,292 719,270" fill="none" stroke="{seam}" stroke-width="1.2" stroke-dasharray="5 5" stroke-opacity=".5"/>'
        body += f'<path d="M500,284 L500,470" fill="none" stroke="{seam}" stroke-width="2" stroke-opacity=".55"/>'
        if kind == "leggings":
            body += f'<path d="M262,430 C262,560 290,800 332,1150" fill="none" stroke="{seam}" stroke-width="2" stroke-opacity=".35" transform="translate(26,0)"/>'
            body += f'<path d="M738,430 C738,560 710,800 668,1150" fill="none" stroke="{seam}" stroke-width="2" stroke-opacity=".35" transform="translate(-26,0)"/>'
        body += f'<text x="500" y="226" text-anchor="middle" font-family="Montserrat,Helvetica,Arial,sans-serif" font-size="22" letter-spacing="9" fill="{seam}" fill-opacity=".85">NELLE</text>'
    else:
        d = bra_path()
        body += '<defs><clipPath id="clipBand"><rect x="0" y="620" width="1000" height="120"/></clipPath></defs>'
        body += f'<g filter="url(#fabric)"><path d="{d}" fill="{fill}"/>'
        body += f'<path d="{d}" fill="{band}" clip-path="url(#clipBand)"/></g>'
        body += f'<path d="{d}" fill="none" stroke="{rim}" stroke-width="2.2" stroke-opacity=".55"/>'
        body += f'<path d="M252,622 Q500,650 748,622" fill="none" stroke="{seam}" stroke-width="2.2" stroke-opacity=".7"/>'
        body += f'<path d="M256,632 Q500,660 744,632" fill="none" stroke="{seam}" stroke-width="1.2" stroke-dasharray="5 5" stroke-opacity=".5"/>'
        # cup seams
        body += f'<path d="M455,422 C440,500 400,560 300,600" fill="none" stroke="{seam}" stroke-width="2" stroke-opacity=".45"/>'
        body += f'<path d="M545,422 C560,500 600,560 700,600" fill="none" stroke="{seam}" stroke-width="2" stroke-opacity=".45"/>'
        body += f'<text x="500" y="690" text-anchor="middle" font-family="Montserrat,Helvetica,Arial,sans-serif" font-size="20" letter-spacing="8" fill="{seam}" fill-opacity=".85">NELLE</text>'
    return body


FILTER = """
<filter id="fabric" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
  <feGaussianBlur in="SourceAlpha" stdDeviation="15" result="vol"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7" result="noise"/>
  <feColorMatrix in="noise" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.9 -0.35" result="grain"/>
  <feComposite in="vol" in2="grain" operator="arithmetic" k1="0" k2="1" k3="0.09" k4="0" result="bump"/>
  <feDiffuseLighting in="bump" surfaceScale="11" diffuseConstant="1.15" lighting-color="#ffffff" result="diffuse">
    <feDistantLight azimuth="235" elevation="52"/>
  </feDiffuseLighting>
  <feSpecularLighting in="vol" surfaceScale="10" specularConstant="0.55" specularExponent="22" lighting-color="#fff4ee" result="spec">
    <feDistantLight azimuth="235" elevation="48"/>
  </feSpecularLighting>
  <feGaussianBlur in="SourceAlpha" stdDeviation="38" result="vol2"/>
  <feDiffuseLighting in="vol2" surfaceScale="20" diffuseConstant="1.0" lighting-color="#ffffff" result="diffuse2">
    <feDistantLight azimuth="230" elevation="38"/>
  </feDiffuseLighting>
  <feComposite in="diffuse" in2="diffuse2" operator="arithmetic" k1="1.05" k2="0" k3="0" k4="0" result="diffuseAll"/>
  <feComposite in="SourceGraphic" in2="diffuseAll" operator="arithmetic" k1="1.45" k2="0" k3="0" k4="0" result="lit"/>
  <feComposite in="spec" in2="lit" operator="arithmetic" k1="0" k2="0.55" k3="1" k4="0" result="lit2"/>
  <feComposite in="lit2" in2="SourceAlpha" operator="in"/>
</filter>
"""

PALETTES = {
    "blush": dict(fill="#d9a597", band="#c98f81", seam="#f6d9cf", rim="#ffe9e1"),
    "noir": dict(fill="#2b2b31", band="#212126", seam="#d9a597", rim="#e8c2b6"),
    "mauve": dict(fill="#946273", band="#7f5262", seam="#e9c3cf", rim="#f5d9e1"),
    "sage": dict(fill="#8fa593", band="#7a917f", seam="#dfeadf", rim="#eef6ee"),
}

# handle -> (layout, palette, palette2 for set top)
PRODUCTS = {
    "aura-high-waist-leggings": ("leggings", "blush"),
    "sculpt-seamless-leggings": ("leggings", "noir"),
    "contour-biker-shorts": ("shorts", "mauve"),
    "halo-sports-bra": ("bra", "blush"),
    "core-racerback-bra": ("bra", "noir"),
    "luxe-longline-bra": ("bra", "mauve"),
    "aura-matching-set": ("set", "blush"),
    "noir-matching-set": ("set", "noir"),
    "sage-matching-set": ("set", "sage"),
}


def build(handle, kind, pal, transparent=False):
    c = PALETTES[pal]
    if kind == "set":
        inner = (
            f'<g transform="translate(250,60) scale(.5)">{garment("bra", c)}</g>'
            f'<g transform="translate(160,410) scale(.68)">{garment("leggings", c)}</g>'
        )
    elif kind == "bra":
        inner = f'<g transform="translate(-75,117) scale(1.15)">{garment(kind, c)}</g>'
    elif kind == "shorts":
        inner = f'<g transform="translate(-75,150) scale(1.15)">{garment(kind, c)}</g>'
    else:
        inner = garment(kind, c)
    bg = "" if transparent else f'<rect width="{W}" height="{H}" fill="#050505"/>'
    glow = "" if transparent else (
        '<radialGradient id="glow" cx="50%" cy="45%" r="55%"><stop offset="0" stop-color="#2a2022" stop-opacity=".55"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>'
        f'<rect width="{W}" height="{H}" fill="url(#glow)"/>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f"<defs>{FILTER}</defs>{bg}{glow}{inner}</svg>"
    )


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for handle, (kind, pal) in PRODUCTS.items():
        for transparent in (False, True):
            name = f"{handle}{'.transparent' if transparent else ''}.svg"
            with open(os.path.join(OUT, name), "w") as f:
                f.write(build(handle, kind, pal, transparent))
    print("wrote", len(PRODUCTS) * 2, "svgs to", os.path.abspath(OUT))
