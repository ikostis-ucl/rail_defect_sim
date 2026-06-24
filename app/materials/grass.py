from app.materials.base import Material


class GrassMaterial(Material):
    NAME = "Grass_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"

        noise = nodes.new(type="ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 20.0

        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        color_ramp.color_ramp.elements[0].color = (0.01, 0.02, 0.0, 1.0)
        color_ramp.color_ramp.elements[1].color = (0.02, 0.05, 0.01, 1.0)

        links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
        links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
