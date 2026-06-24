from app.materials.base import Material


class SleeperMaterial(Material):
    NAME = "Sleeper_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Base Color"].default_value = (0.26, 0.16, 0.09, 1.0)
        principled.inputs["Roughness"].default_value = 0.85
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
