"""Bake reference-pose form shading into editable UV paint; run inside Blender."""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from materials import linear_color, pixel_material


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--maps', type=Path, required=True)
    parser.add_argument('--reuse', action='store_true', help='apply the same paint to another motion')
    parser.add_argument('--resolution', type=int, default=128)
    parser.add_argument('--unwrap', action='store_true', help='create unique paint islands while retaining the original UV input')
    parser.add_argument('--freeze', action='store_true', help='bake existing emission paint without adding form shades')
    parser.add_argument('--form-guide', action='store_true', help='explicitly add continuous form shading for a paint guide')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists() or args.resolution < 8:
        raise ValueError('output must be fresh; map resolution must be at least 8')
    if args.freeze and args.form_guide:
        raise ValueError('freeze and form-guide are mutually exclusive')
    palette = json.loads(args.config.read_text()).get('palette',{})
    if not args.reuse:
        args.maps.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()), use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(scene.frame_start)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1
    scene.render.bake.margin = 2
    scene.render.bake.use_clear = True
    scene.render.dither_intensity = 0
    painted_count = 0
    for obj in list(scene.objects):
        if obj.type != 'MESH' or not obj.data.uv_layers.active:
            continue
        if not any(slot.material and any(n.type == 'TEX_IMAGE' for n in slot.material.node_tree.nodes)
                   for slot in obj.material_slots):
            continue
        path = args.maps / (obj.name.replace('/', '_') + '.png')
        role = obj.data.materials[0].name.split('.')[0]
        original_uv = obj.data.uv_layers.active.name
        if args.unwrap:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True); bpy.context.view_layer.objects.active = obj
            target_uv = obj.data.uv_layers.new(name='Fixed surface paint')
            obj.data.uv_layers.active = target_uv
            target_uv.active_render = True
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(island_margin=.01)
            bpy.ops.object.mode_set(mode='OBJECT')
        if not args.reuse:
            image = bpy.data.images.new(obj.name + ' painted guide', args.resolution, args.resolution, alpha=True)
            for slot in obj.material_slots:
                material_role = slot.material.name.split('.')[0]
                material = slot.material.copy()
                slot.material = material
                nodes, links = material.node_tree.nodes, material.node_tree.links
                if args.unwrap:
                    source_uv = nodes.new('ShaderNodeUVMap'); source_uv.uv_map = original_uv
                    for coordinate in list(nodes):
                        if coordinate.type == 'TEX_COORD':
                            for connection in list(coordinate.outputs['UV'].links):
                                links.new(source_uv.outputs['UV'],connection.to_socket)
                emission = next((n for n in nodes if n.type == 'EMISSION'), None)
                if emission is None:
                    raise ValueError('form guides require pixel_material emission graphs: ' + slot.material.name)
                if args.form_guide and emission.inputs['Color'].is_linked:
                    paint_color = emission.inputs['Color'].links[0].from_socket
                    normal = nodes.new('ShaderNodeNewGeometry')
                    dot = nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
                    dot.inputs[1].default_value = Vector((-.5,-.7,1)).normalized()
                    links.new(normal.outputs['Normal'], dot.inputs[0])
                    ramp = nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'LINEAR'
                    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
                    shades = palette[material_role]
                    for i,shade in enumerate(shades):
                        position=i*.85/max(1,len(shades)-1)
                        stop = ramp.color_ramp.elements[0] if i == 0 else ramp.color_ramp.elements.new(position)
                        stop.position, stop.color = position, linear_color(shade)
                    links.new(dot.outputs['Value'], ramp.inputs[0])
                    ratio = nodes.new('ShaderNodeVectorMath'); ratio.operation = 'DIVIDE'
                    ratio.inputs[1].default_value = linear_color(shades[round(.67*(len(shades)-1))])[:3]
                    links.new(paint_color, ratio.inputs[0])
                    multiply = nodes.new('ShaderNodeVectorMath'); multiply.operation = 'MULTIPLY'
                    links.new(ramp.outputs['Color'], multiply.inputs[0]); links.new(ratio.outputs['Vector'], multiply.inputs[1])
                    links.new(multiply.outputs['Vector'], emission.inputs['Color'])
                target = nodes.new('ShaderNodeTexImage'); target.image = image
                nodes.active = target
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True); bpy.context.view_layer.objects.active = obj
            # Solidify duplicates the exterior UVs on inward-facing surfaces.
            # Bake exterior paint only; keep the shell and rig in the saved model.
            shells = [(m, m.show_viewport, m.show_render) for m in obj.modifiers if m.type == 'SOLIDIFY']
            try:
                for modifier, _, _ in shells:
                    modifier.show_viewport = modifier.show_render = False
                bpy.ops.object.bake(type='EMIT')
            finally:
                for modifier, viewport, render in shells:
                    modifier.show_viewport, modifier.show_render = viewport, render
            image.filepath_raw = str(path.resolve()); image.file_format = 'PNG'; image.save()
        # The baked guide is an authoring input, not live render lighting. It
        # remains editable and is shared across clips without rebaking each pose.
        obj.data.materials.clear()
        obj.data.materials.append(pixel_material(role, palette.get(role), path))
        painted_count += 1
    if not painted_count:
        raise ValueError('source has no UV-painted meshes')
    scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)


if __name__ == '__main__':
    main()
