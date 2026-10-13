"""Executed inside Blender 4.5. Uses only bpy, mathutils and the Python stdlib."""
import argparse
import json
import math
import random
import re
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--camera")
    parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    parser.add_argument("--width", type=int)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--source-units", choices=["mm", "m"])
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def material(name, spec):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    base = list(spec.get("color", [.7, .7, .67]))
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = spec.get("roughness", .6)
    bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0)
    bsdf.inputs["Transmission Weight"].default_value = spec.get("transmission", 0)
    bsdf.inputs["IOR"].default_value = 1.45 if spec.get("transmission", 0) else 1.5
    texture = spec.get("texture", "plain")
    if texture not in {"plain", "glass"}:
        coords = nodes.new("ShaderNodeTexCoord")
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 3.5 * spec.get("scale", 1)
        noise.inputs["Detail"].default_value = 3
        noise.inputs["Roughness"].default_value = .7
        links.new(coords.outputs["Object"], noise.inputs["Vector"])
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = .1
        ramp.color_ramp.elements[0].color = (*[v * .94 for v in base], 1)
        ramp.color_ramp.elements[1].position = .9
        ramp.color_ramp.elements[1].color = (*[min(.98, v * 1.02) for v in base], 1)
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        fine = nodes.new("ShaderNodeTexNoise")
        fine.inputs["Scale"].default_value = 180 if texture == "plaster" else 85
        fine.inputs["Detail"].default_value = 2
        links.new(coords.outputs["Object"], fine.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .2
        bump.inputs["Distance"].default_value = .0009 if texture == "plaster" else .002
        links.new(fine.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        if texture == "paving":
            brick = nodes.new("ShaderNodeTexBrick")
            brick.offset = 0
            brick.inputs["Scale"].default_value = 1
            brick.inputs["Brick Width"].default_value = spec.get("scale", .9)
            brick.inputs["Row Height"].default_value = spec.get("scale", .9)
            brick.inputs["Mortar Size"].default_value = .002
            brick.inputs["Mortar Smooth"].default_value = .002
            brick.inputs["Color1"].default_value = (*base, 1)
            brick.inputs["Color2"].default_value = (*[v * .94 for v in base], 1)
            brick.inputs["Mortar"].default_value = (*[v * .68 for v in base], 1)
            links.new(coords.outputs["Object"], brick.inputs["Vector"])
            links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
            joint = nodes.new("ShaderNodeBump")
            joint.inputs["Distance"].default_value = .002
            joint.inputs["Strength"].default_value = .35
            links.new(brick.outputs["Fac"], joint.inputs["Height"])
            links.new(bump.outputs["Normal"], joint.inputs["Normal"])
            links.new(joint.outputs["Normal"], bsdf.inputs["Normal"])
        elif texture == "wood":
            mapping = nodes.new("ShaderNodeVectorMath")
            mapping.operation = "MULTIPLY"
            mapping.inputs[1].default_value = (4, 4, .18)
            links.new(coords.outputs["Object"], mapping.inputs[0])
            links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        elif texture == "water":
            bsdf.inputs["Transmission Weight"].default_value = .9
            bsdf.inputs["IOR"].default_value = 1.333
            bsdf.inputs["Roughness"].default_value = .045
            fine.inputs["Scale"].default_value = 6
            bump.inputs["Distance"].default_value = .022
            bump.inputs["Strength"].default_value = .25
    return mat


def mesh_object(name, vertices, faces, mat, collection=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    if mat:
        mesh.materials.append(mat)
    return obj


def branch_mesh(segments, mat, name):
    verts, faces = [], []
    sides = 12
    for start, end, r1, r2 in segments:
        axis = (end - start).normalized()
        ref = Vector((0, 0, 1)) if abs(axis.z) < .95 else Vector((1, 0, 0))
        u, v = axis.cross(ref).normalized(), axis.cross(axis.cross(ref)).normalized()
        offset = len(verts)
        for point, radius in [(start, r1), (end, r2)]:
            for i in range(sides):
                angle = i * math.tau / sides
                verts.append(tuple(point + radius * (math.cos(angle) * u + math.sin(angle) * v)))
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((offset + i, offset + j, offset + sides + j, offset + sides + i))
    obj = mesh_object(name, verts, faces, mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def tree(spec, index):
    """Branching citrus canopy with individual curved leaves, not opaque green spheres."""
    rng = random.Random(spec.get("seed", 913 + index))
    position = Vector([v / 1000 for v in spec["position"]])
    height = spec.get("height", 3600) / 1000
    radius = spec.get("crown_radius", 1300) / 1000
    bark = material(f"bark-{index}", {"color": [.16, .105, .060], "texture": "wood", "roughness": .9})
    segments = []
    trunk_end = position + Vector((.05, -.03, height * .46))
    segments.append((position, trunk_end, height * .016, height * .010))
    tips = []
    for i in range(7):
        angle = i * math.tau / 7 + rng.uniform(-.22, .22)
        end = position + Vector((math.cos(angle) * radius * .56, math.sin(angle) * radius * .56,
                                 height * rng.uniform(.62, .79)))
        segments.append((trunk_end, end, height * .010, height * .004))
        for _ in range(6):
            aa = angle + rng.uniform(-1.3, 1.3)
            tip = position + Vector((math.cos(aa) * radius * rng.uniform(.58, .96),
                                     math.sin(aa) * radius * rng.uniform(.58, .96),
                                     height * rng.uniform(.65, 1.0)))
            segments.append((end, tip, height * .005, .007))
            tips.append(tip)
    branch_mesh(segments, bark, f"tree-{index}-branches")
    greens = [[.105, .20, .044], [.15, .255, .062], [.205, .29, .072], [.08, .145, .035], [.22, .31, .09]]
    leaf_mats = [material(f"leaf-{index}-{n}", {"color": c, "roughness": .43}) for n, c in enumerate(greens)]
    vertices, faces, mat_ids = [], [], []
    for tip in tips:
        for _ in range(200):
            centre = tip + Vector((rng.gauss(0, radius * .17), rng.gauss(0, radius * .17), rng.gauss(0, height * .065)))
            length = rng.uniform(.08, .15)
            width = length * rng.uniform(.36, .52)
            direction = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-.35, .75))).normalized()
            side = direction.cross(Vector((0, 0, 1))).normalized() * width / 2
            lift = Vector((0, 0, length * .12))
            points = [centre - direction * length / 2,
                      centre - direction * length * .18 + side,
                      centre + direction * length * .21 + side * .72,
                      centre + direction * length / 2,
                      centre + direction * length * .21 - side * .72,
                      centre - direction * length * .18 - side,
                      centre + lift]
            offset = len(vertices)
            vertices.extend(tuple(p) for p in points)
            for n in range(6):
                faces.append((offset + n, offset + (n + 1) % 6, offset + 6))
                mat_ids.append(rng.randrange(len(leaf_mats)))
    obj = mesh_object(f"tree-{index}-leaves", vertices, faces, leaf_mats[0])
    for mat in leaf_mats[1:]:
        obj.data.materials.append(mat)
    for poly, matid in zip(obj.data.polygons, mat_ids):
        poly.material_index = matid
        poly.use_smooth = True


def load(source, source_units=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    suffix = source.suffix.lower()
    if suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(source))
        scene = bpy.context.scene
        cameras = sorted((o for o in scene.objects if o.type == "CAMERA"), key=lambda o: o != scene.camera)
        return {"preserve_scene": True, "cameras": [{"id": o.name, "existing": o,
                 "aspect": scene.render.resolution_x / scene.render.resolution_y} for o in cameras]}, []
    if suffix != ".json":
        if suffix in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=str(source))
        elif suffix == ".obj":
            bpy.ops.wm.obj_import(filepath=str(source))
        elif suffix == ".ply":
            bpy.ops.wm.ply_import(filepath=str(source))
        elif suffix == ".stl":
            bpy.ops.wm.stl_import(filepath=str(source))
        else:
            raise ValueError(f"Convert unsupported {suffix} using the exchange module before rendering")
        if suffix in {".obj", ".ply", ".stl"}:
            if source_units is None:
                raise ValueError("Unitless input needs explicit source units")
            if source_units == "mm":
                for obj in bpy.context.scene.objects:
                    if obj.parent is None:
                        obj.scale *= .001
                        obj.location *= .001
                bpy.context.view_layer.update()
        return {"source_units": source_units or "m"}, []
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("units") != "mm":
        raise ValueError("EZarch scene geometry must use mm")
    materials = {name: material(name, spec) for name, spec in data["materials"].items()}
    bounds_report = []
    for part in data["objects"]:
        vertices = [[c / 1000 for c in v] for v in part["vertices"]]
        obj = mesh_object(part["id"], vertices, part["faces"], materials[part["material"]])
        obj["ezarch_id"] = part["id"]
        obj["source_category"] = part["category"]
        if part["category"] not in {"glass", "water", "site", "landscape"}:
            bevel = obj.modifiers.new("Physical edge highlight", "BEVEL")
            bevel.width = .006 if part["category"] not in {"frame", "furniture"} else .002
            bevel.segments = 2
            bevel.limit_method = "ANGLE"
            bevel.angle_limit = .5
        stored_points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        lo = [min(v[i] for v in stored_points) * 1000 for i in range(3)]
        hi = [max(v[i] for v in stored_points) * 1000 for i in range(3)]
        bounds_report.append({"id": part["id"], "bounds_mm": lo + hi})
    for i, spec in enumerate(data.get("landscape", [])):
        if spec["kind"] == "tree":
            tree(spec, i)
    return data, bounds_report


def lighting(config):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Architectural daylight")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(config.get("sun_elevation", 42))
    sky.sun_rotation = math.radians(config.get("sun_rotation", 135))
    sky.altitude = 0
    sky.air_density = 1
    sky.dust_density = .8
    world.node_tree.links.new(sky.outputs["Color"], nodes.get("Background").inputs["Color"])
    nodes.get("Background").inputs["Strength"].default_value = config.get("sky_strength", .28)
    scene.world = world
    sun = bpy.data.lights.new("Sun", type="SUN")
    sun.energy = config.get("sun_energy", 2.3)
    sun.angle = math.radians(.75)
    sun.color = (1, .93, .83)
    obj = bpy.data.objects.new("Sun", sun)
    scene.collection.objects.link(obj)
    elev, az = sky.sun_elevation, sky.sun_rotation
    direction = Vector((math.cos(az) * math.cos(elev), math.sin(az) * math.cos(elev), math.sin(elev)))
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()


def choose_device():
    preferences = bpy.context.preferences.addons["cycles"].preferences
    tested = []
    for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            preferences.compute_device_type = backend
            preferences.get_devices()
            devices = [d for d in preferences.devices if d.type != "CPU"]
            tested.append({"backend": backend, "devices": [d.name for d in devices]})
            if devices:
                for d in preferences.devices:
                    d.use = d.type != "CPU"
                bpy.context.scene.cycles.device = "GPU"
                return backend, tested
        except Exception as error:
            tested.append({"backend": backend, "unavailable": str(error)})
            continue
    bpy.context.scene.cycles.device = "CPU"
    return "CPU", tested


def camera_from_spec(spec):
    data = bpy.data.cameras.new(spec["id"])
    obj = bpy.data.objects.new(spec["id"], data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = Vector([v / 1000 for v in spec["position"]])
    target = Vector([v / 1000 for v in spec["target"]])
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
    data.lens = spec.get("lens", 35)
    data.sensor_width = 36
    data.clip_start = .02
    data.clip_end = 1000
    if spec.get("orthographic"):
        data.type = "ORTHO"
        data.ortho_scale = spec.get("ortho_scale", 30000) / 1000
    if spec.get("shift_y"):
        data.shift_y = spec["shift_y"]
    return obj


def main():
    options = args()
    options.out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    data, bounds_report = load(options.input, options.source_units)
    scene = bpy.context.scene
    if not data.get("preserve_scene"):
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1
    config = data.get("render", {})
    if not data.get("preserve_scene"):
        lighting(config)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = options.samples or (24 if options.quality == "preview" else 128)
    scene.cycles.use_denoising = True
    scene.cycles.adaptive_threshold = .025 if options.quality == "preview" else .012
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 8
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.seed = 7123
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = config.get("exposure", -.5)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = config.get("transparent", False)
    backend, device_report = choose_device()
    cameras = data.get("cameras", [])
    if not cameras and scene.camera:
        cameras = [{"id": scene.camera.name, "existing": scene.camera}]
    if not cameras:
        points = [obj.matrix_world @ Vector(p) for obj in scene.objects if obj.type == "MESH" for p in obj.bound_box]
        if not points:
            raise RuntimeError("No model geometry to render")
        lo, hi = Vector([min(p[i] for p in points) for i in range(3)]), Vector([max(p[i] for p in points) for i in range(3)])
        centre = (lo + hi) / 2
        span = max((hi - lo).length, 2)
        cameras = [{"id": "perspective", "position": list((centre + Vector((.7, -.95, .55)) * span) * 1000),
                    "target": list(centre * 1000), "lens": 40}]
    selected = cameras if options.camera == "all" else [c for c in cameras if c["id"] == options.camera] if options.camera else cameras[:1]
    if not selected:
        raise ValueError(f"Unknown camera {options.camera}")
    output = []
    for spec in selected:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", spec["id"]):
            raise ValueError("Camera IDs must be safe filenames")
        scene.camera = spec.get("existing") or camera_from_spec(spec)
        scene.render.resolution_x = options.width or (1100 if options.quality == "preview" else 2600)
        ratio = spec.get("aspect", 1.5)
        scene.render.resolution_y = round(scene.render.resolution_x / ratio)
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(options.out / (spec["id"] + ".png"))
        print(f"EZARCH_RENDER {spec['id']} {scene.render.resolution_x}x{scene.render.resolution_y} {backend}", flush=True)
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError:
            if backend == "CPU":
                raise
            backend = "CPU_AFTER_GPU_FAILURE"
            scene.cycles.device = "CPU"
            bpy.ops.render.render(write_still=True)
        output.append({"file": spec["id"] + ".png", "camera": spec["id"],
                       "width": scene.render.resolution_x, "height": scene.render.resolution_y})
    bpy.ops.wm.save_as_mainfile(filepath=str(options.out / "scene.blend"), compress=True)
    report = {"blender": bpy.app.version_string, "backend": backend, "device_probe": device_report,
              "samples": scene.cycles.samples, "source_project_hash": data.get("project_hash"),
              "source_bounds": bounds_report, "images": output, "elapsed_s": round(time.time() - started, 2),
              "decorative_elements": len(data.get("landscape", [])), "color_management": "AgX"}
    (options.out / "render-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("EZARCH_RENDER_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
