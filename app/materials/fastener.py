from app.materials.base import Material


class FastenerMaterial(Material):
    NAME = "Fastener_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1.0)
        principled.inputs["Metallic"].default_value = 0.15
        principled.inputs["Roughness"].default_value = 0.7
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
