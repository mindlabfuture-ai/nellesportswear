"""NELLE product renders in Blender/Cycles.

Builds a headless matte-black mannequin from blended metaballs, cuts garment
shells out of the body surface, gives them a knit-fabric material and path
traces them under a studio light rig on black. No faces anywhere: the form
stops at the neck.

Run with the bpy venv:  python tools/blender/scene.py <spec-name|all> [--quick]
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "images", "renders")


# --------------------------------------------------------------------------- scene

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    sc.world = world
    return sc


# --------------------------------------------------------------------------- body

# (type, co, radius, size xyz) -- metres, z up, front of body faces -y
BODY = [
    # legs: ankle -> hip, each side mirrored below
    ("CAPSULE", (0.090, 0.004, 0.13), 0.030, (0.06, 1, 1), (0, 90, 0)),
    ("ELLIPSOID", (0.090, 0.010, 0.33), 0.050, (0.95, 1.05, 2.2), None),   # calf
    ("ELLIPSOID", (0.088, -0.002, 0.49), 0.044, (1, 1, 1.4), None),         # knee
    ("ELLIPSOID", (0.090, 0.000, 0.64), 0.066, (1, 1.05, 2.0), None),       # thigh
    ("ELLIPSOID", (0.088, 0.010, 0.76), 0.080, (1.05, 1.1, 1.3), None),     # upper thigh
    ("ELLIPSOID", (0.075, 0.035, 0.84), 0.080, (1, 1, 1), None),            # glute
]
TORSO = [
    ("ELLIPSOID", (0, 0.010, 0.88), 0.150, (1.18, 0.78, 0.75), None),       # pelvis
    ("ELLIPSOID", (0, 0.012, 1.02), 0.110, (1.05, 0.78, 1.15), None),       # waist
    ("ELLIPSOID", (0, 0.012, 1.18), 0.135, (1.0, 0.72, 1.15), None),        # ribcage
    ("ELLIPSOID", (0, 0.015, 1.34), 0.120, (1.45, 0.62, 0.55), None),       # shoulders
    ("CAPSULE", (0, 0.020, 1.44), 0.045, (0.05, 1, 1), (0, 90, 0)),        # neck
    ("ELLIPSOID", (0.064, -0.060, 1.215), 0.062, (1, 0.9, 0.92), None),     # bust
    ("ELLIPSOID", (-0.064, -0.060, 1.215), 0.062, (1, 0.9, 0.92), None),
    ("CAPSULE", (0.205, 0.015, 1.30), 0.040, (0.06, 1, 1), (0, 70, 0)),    # arm stubs
    ("CAPSULE", (-0.205, 0.015, 1.30), 0.040, (0.06, 1, 1), (0, -70, 0)),
]


def build_body():
    mb = bpy.data.metaballs.new("body")
    mb.resolution = 0.008
    mb.render_resolution = 0.006
    mb.threshold = 0.6
    elems = list(TORSO)
    for t, (x, y, z), r, s, rot in BODY:
        elems.append((t, (x, y, z), r, s, rot))
        elems.append((t, (-x, y, z), r, s, rot))
    for t, co, r, s, rot in elems:
        e = mb.elements.new(type=t)
        e.co = co
        e.radius = r * 2.2
        e.stiffness = 2.0
        if t == "ELLIPSOID":
            e.size_x, e.size_y, e.size_z = (v * r * 2.2 for v in s)
        else:
            e.size_x = s[0] * 2.2
        if rot:
            from mathutils import Euler
            e.rotation = Euler([math.radians(a) for a in rot]).to_quaternion()
    ob = bpy.data.objects.new("body_mb", mb)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    body = bpy.context.active_object
    body.name = "body"
    # flat cuts at neck and ankles like a real form
    bm = bmesh.new()
    bm.from_mesh(body.data)
    for z, keep_above in ((1.465, False), (0.085, True)):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1),
                                     clear_outer=not keep_above, clear_inner=keep_above)
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges)
    bm.to_mesh(body.data)
    bm.free()
    m = body.modifiers.new("remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = 0.004
    bpy.ops.object.modifier_apply(modifier="remesh")
    m = body.modifiers.new("smooth", "CORRECTIVE_SMOOTH")
    m.iterations = 12
    m.smooth_type = "LENGTH_WEIGHTED"
    bpy.ops.object.modifier_apply(modifier="smooth")
    bpy.ops.object.shade_smooth()
    return body


# --------------------------------------------------------------------------- materials

def mat_mannequin():
    m = bpy.data.materials.new("mannequin")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
    b.inputs["Roughness"].default_value = 0.42
    b.inputs["Coat Weight"].default_value = 0.15
    return m


def mat_fabric(name, rgb, rib=False, sheen=0.6, rough=0.62):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Sheen Roughness"].default_value = 0.35
    b.inputs["Specular IOR Level"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # fine knit grain
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 900.0
    noise.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.0004
    height = noise.outputs["Fac"]
    if rib:
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = 180.0
        wave.inputs["Distortion"].default_value = 0.6
        nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMath")
        mix.operation = "ADD"
        nt.links.new(noise.outputs["Fac"], mix.inputs[0])
        nt.links.new(wave.outputs["Fac"], mix.inputs[1])
        height = mix.outputs[0]
        bump.inputs["Strength"].default_value = 0.35
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# --------------------------------------------------------------------------- garments

def shell(body, name, keep, offset, thickness, mat, wrinkle=0.0015):
    """Copy the body faces whose centre passes keep(co, normal) and inflate them."""
    me = body.data.copy()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    dead = [f for f in bm.faces if not keep(f.calc_center_median(), f.normal)]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    # drop tiny islands
    bm.to_mesh(me)
    bm.free()
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    d = ob.modifiers.new("lift", "DISPLACE")
    d.strength = offset
    d.mid_level = 0.0
    if wrinkle:
        tex = bpy.data.textures.new(name + "_wr", "CLOUDS")
        tex.noise_scale = 0.05
        w = ob.modifiers.new("wrinkle", "DISPLACE")
        w.texture = tex
        w.strength = wrinkle
        w.texture_coords = "GLOBAL"
    s = ob.modifiers.new("solid", "SOLIDIFY")
    s.thickness = thickness
    s.offset = 1.0
    s.use_even_offset = True
    sub = ob.modifiers.new("sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    return ob


def leggings(body, mat, band_mat, top=1.06, hem=0.10, band=0.075, flare=False):
    legs = shell(body, "leggings",
                 lambda c, n: hem < c.z < top - band + 0.004,
                 0.0035, 0.0018, mat)
    wb = shell(body, "waistband",
               lambda c, n: top - band < c.z < top,
               0.0058, 0.0026, band_mat, wrinkle=0.0006)
    if flare:
        flare_out(legs, knee=0.47, amount=0.75)
    return [legs, wb]


def flare_out(ob, knee, amount):
    for m in list(ob.modifiers):
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=m.name)
    for v in ob.data.vertices:
        if v.co.z < knee:
            t = (knee - v.co.z) / knee
            cx = 0.09 if v.co.x > 0 else -0.09
            k = 1 + amount * t ** 1.6
            v.co.x = cx + (v.co.x - cx) * k
            v.co.y = 0.004 + (v.co.y - 0.004) * k


def bra(body, mat, band_mat, style="scoop"):
    """style: scoop | racer | longline | tank"""
    bottom = {"scoop": 1.105, "racer": 1.105, "longline": 1.045, "tank": 1.06}[style]

    def keep(c, n):
        ax = abs(c.x)
        if c.z < bottom or c.z > 1.47:
            return False
        front = c.y < 0.01
        # neckline: deeper in the middle of the front
        if front:
            depth = {"scoop": 1.255, "racer": 1.27, "longline": 1.26, "tank": 1.30}[style]
            neck = depth + 0.9 * max(0.0, ax - 0.02) ** 1.15 * (1.0 if style != "tank" else 0.6)
            if c.z > neck and ax < 0.075:
                return False
        else:
            if style == "racer":
                # narrow racerback: back panel funnels to a centre strap
                width = 0.06 + max(0.0, 1.30 - c.z) * 1.4
                if ax > width and c.z > 1.20:
                    return False
            else:
                if c.z > 1.27 and not (0.06 < ax < 0.105):
                    return False
        # straps over shoulders and armholes
        if c.z > 1.27:
            lo, hi = (0.055, 0.11) if style != "tank" else (0.04, 0.125)
            if style == "racer" and not front:
                return ax < 0.06 + max(0.0, 1.30 - c.z) * 1.4 or 1.42 < c.z
            if not (lo < ax < hi):
                return False
        if ax > 0.165 and c.z > 1.19:  # armhole
            return False
        return True

    top = shell(body, "bra", keep, 0.0042, 0.0022, mat, wrinkle=0.0008)
    band_h = 0.05 if style != "longline" else 0.075
    band = shell(body, "underband", lambda c, n: bottom - 0.003 < c.z < bottom + band_h,
                 0.0062, 0.0026, band_mat, wrinkle=0.0004)
    return [top, band]


def tee(body, mat, band_mat):
    def keep(c, n):
        ax = abs(c.x)
        if c.z < 0.99 or c.z > 1.455:
            return False
        if c.z > 1.36 and ax < 0.06:  # crew neckline
            return False
        return True
    t = shell(body, "tee", keep, 0.006, 0.0022, mat, wrinkle=0.0025)
    rib = shell(body, "neckrib", lambda c, n: 1.345 < c.z < 1.375 and abs(c.x) < 0.075,
                0.0075, 0.003, band_mat, wrinkle=0.0)
    return [t, rib]


def logo_text(target, z, y_front=-0.2, size=0.022, color=(0.86, 0.62, 0.55)):
    """Rose-gold NELLE print shrink-wrapped onto the garment front."""
    cu = bpy.data.curves.new("logo", "FONT")
    cu.body = "NELLE"
    cu.size = size
    cu.space_character = 1.6
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.0002
    ob = bpy.data.objects.new("logo", cu)
    bpy.context.collection.objects.link(ob)
    ob.location = (0, y_front, z)
    ob.rotation_euler = (math.radians(90), 0, 0)
    m = bpy.data.materials.new("print")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = 0.6
    b.inputs["Roughness"].default_value = 0.35
    cu.materials.append(m)
    sw = ob.modifiers.new("wrap", "SHRINKWRAP")
    sw.target = target
    sw.wrap_method = "PROJECT"
    sw.use_project_y = True
    sw.use_negative_direction = True
    sw.use_positive_direction = True
    sw.offset = 0.0012
    return ob


# --------------------------------------------------------------------------- lights & camera

def area(name, loc, target, size, energy, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA")
    l.size = size
    l.energy = energy
    l.color = color
    ob = bpy.data.objects.new(name, l)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def rig(center_z):
    area("key", (-1.6, -2.4, center_z + 0.9), (0, 0, center_z), 2.2, 900, (1.0, 0.96, 0.93))
    area("fill", (2.2, -2.0, center_z + 0.2), (0, 0, center_z), 2.5, 220, (0.95, 0.96, 1.0))
    area("rimL", (-1.3, 1.6, center_z + 0.5), (0, 0, center_z), 0.8, 520, (1.0, 0.86, 0.80))
    area("rimR", (1.3, 1.6, center_z + 0.5), (0, 0, center_z), 0.8, 520, (1.0, 0.86, 0.80))
    area("top", (0, -0.3, center_z + 2.2), (0, 0, center_z), 1.2, 160)


def camera(z_lo, z_hi, yaw=0.0):
    cam = bpy.data.cameras.new("cam")
    cam.lens = 85
    cam.sensor_fit = "VERTICAL"
    cam.sensor_height = 24
    h = (z_hi - z_lo) * 1.12
    dist = h / 24 * 85
    cz = (z_lo + z_hi) / 2
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(ob)
    a = math.radians(yaw)
    ob.location = (dist * math.sin(a), -dist * math.cos(a), cz)
    ob.rotation_euler = (math.radians(90), 0, a)
    bpy.context.scene.camera = ob
    return cz


# --------------------------------------------------------------------------- specs

def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


COLORS = {
    "blush": ("#d8a293", "#c58b7c"),
    "noir": ("#1d1d21", "#141417"),
    "mauve": ("#8f5b6c", "#7a4b5b"),
    "sage": ("#8aa28e", "#76907b"),
    "cocoa": ("#8a6253", "#764f42"),
    "rose": ("#c98f86", "#b47a72"),
    "slate": ("#4b5560", "#3d4650"),
}

# name -> (pieces, colour, framing, yaw, options)
SPECS = {
    "sculpt-seamless-leggings": (["leggings"], "noir", "legs", -12, {"rib": True}),
    "compression-training-tights": (["leggings"], "slate", "legs", 0, {}),
    "hip-up-pocket-leggings": (["leggings"], "sage", "legs", 14, {}),
    "soft-flare-leggings": (["flare"], "mauve", "legs", -8, {}),
    "quick-dry-biker-shorts": (["shorts"], "mauve", "hips", 10, {}),
    "scrunch-booty-shorts": (["shorts"], "sage", "hips", -14, {"rib": True}),
    "hip-up-drawstring-shorts": (["shorts"], "blush", "hips", 0, {}),
    "cross-back-bra": (["bra:racer"], "noir", "torso", -14, {}),
    "padded-studio-bra": (["bra:scoop"], "blush", "torso", 0, {}),
    "train-bra": (["bra:scoop"], "sage", "torso", 12, {"rib": True}),
    "beauty-back-bra": (["bra:longline"], "mauve", "torso", -10, {}),
    "pilates-tank-bra": (["bra:tank"], "cocoa", "torso", 8, {}),
    "stretch-training-tee": (["tee"], "noir", "torso", 0, {}),
    "sculpt-padded-set": (["bra:scoop", "leggings"], "noir", "full", -10, {}),
    "cross-back-sports-set": (["bra:racer", "leggings"], "blush", "full", 10, {}),
    "cross-back-support-set": (["bra:longline", "leggings"], "mauve", "full", -6, {}),
    "everyday-workout-set": (["bra:scoop", "leggings"], "sage", "full", 6, {"rib": True}),
    "cross-back-shorts-set": (["bra:racer", "shorts"], "cocoa", "full", -8, {}),
}

FRAMES = {"legs": (0.04, 1.12), "hips": (0.44, 1.12), "torso": (0.98, 1.50), "full": (0.04, 1.50)}


def build(name, quick=False):
    pieces, colour, framing, yaw, opt = SPECS[name]
    sc = reset()
    body = build_body()
    body.data.materials.append(mat_mannequin())
    main, band = COLORS[colour]
    fab = mat_fabric("fab", srgb(main), rib=opt.get("rib", False))
    bandm = mat_fabric("band", srgb(band), rib=True, sheen=0.5)
    for p in pieces:
        if p in ("leggings", "flare"):
            obs = leggings(body, fab, bandm, flare=(p == "flare"))
            logo_text(obs[1], 1.023, size=0.016)
        elif p == "shorts":
            obs = leggings(body, fab, bandm, hem=0.60)
            logo_text(obs[1], 1.023, size=0.016)
        elif p.startswith("bra:"):
            obs = bra(body, fab, bandm, style=p.split(":")[1])
            logo_text(obs[1], 1.13 if "longline" not in p else 1.08, size=0.012)
        elif p == "tee":
            obs = tee(body, fab, bandm)
            logo_text(obs[0], 1.25, size=0.02)
    z_lo, z_hi = FRAMES[framing]
    cz = camera(z_lo, z_hi, yaw)
    rig(cz)
    sc.render.resolution_x = 1000 if not quick else 400
    sc.render.resolution_y = 1250 if not quick else 500
    sc.cycles.samples = 160 if not quick else 24
    os.makedirs(OUT, exist_ok=True)
    sc.render.filepath = os.path.join(OUT, f"{name}.rgba.png")
    sc.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quick = "--quick" in sys.argv
    names = list(SPECS) if not args or args[0] == "all" else args
    for n in names:
        print("rendered", build(n, quick))
