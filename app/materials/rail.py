from app.materials.base import Material


class RailMaterial(Material):
    NAME = "Rail_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Base Color"].default_value = (0.62, 0.64, 0.66, 1.0)
        principled.inputs["Metallic"].default_value = 0.9
        principled.inputs["Roughness"].default_value = 0.35
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
