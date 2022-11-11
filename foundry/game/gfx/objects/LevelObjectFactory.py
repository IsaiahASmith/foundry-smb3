from foundry.core.geometry import Point
from foundry.core.graphics_set.GraphicsSet import GraphicsSet
from foundry.core.palette import PaletteGroup
from foundry.game.gfx.objects.Jump import Jump
from foundry.game.gfx.objects.LevelObject import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    LevelObject,
)


class LevelObjectFactory:
    tileset: int
    graphic_set: int
    palette_group_index: int

    graphics_set: GraphicsSet | None = None
    palette_group: PaletteGroup

    def __init__(
        self,
        tileset: int,
        graphic_set: int | GraphicsSet,
        palette_group_index: int,
        objects_ref: list[LevelObject],
        vertical_level: bool,
        size_minimal: bool = False,
    ):
        self.set_object_set(tileset)
        if isinstance(graphic_set, int):
            self.set_graphic_set(graphic_set)
        else:
            self.graphic_set = 0
            self.graphics_set = graphic_set
        self.set_palette_group_index(palette_group_index)
        self.objects_ref = objects_ref
        self.vertical_level = vertical_level

        self.size_minimal = size_minimal

    def set_object_set(self, tileset: int):
        self.tileset = tileset

    def set_graphic_set(self, graphic_set: int):
        self.graphic_set = graphic_set
        self.graphics_set = GraphicsSet.from_tileset(self.graphic_set)

    def set_palette_group_index(self, palette_group_index: int):
        self.palette_group_index = palette_group_index
        self.palette_group = PaletteGroup.from_tileset(self.tileset, self.palette_group_index)

    def from_data(self, data: bytearray, index: int):
        if Jump.is_jump(data):
            return Jump(data)

        assert self.graphics_set is not None

        # todo get rid of index by fixing ground map
        return LevelObject(
            data,
            self.tileset,
            self.palette_group,
            self.graphics_set,
            self.objects_ref,
            self.vertical_level,
            index,
            size_minimal=self.size_minimal,
        )

    def from_properties(
        self,
        domain: int,
        object_index: int,
        point: Point,
        length: int | None,
        index: int,
    ):
        assert isinstance(domain, int)
        assert isinstance(object_index, int)
        assert isinstance(point, Point)
        assert isinstance(index, int)
        if self.vertical_level:
            offset = point.y // SCREEN_HEIGHT
            point = Point(offset * SCREEN_WIDTH, point.y % SCREEN_HEIGHT)

        data = bytearray(3)

        data[0] = domain << 5 | point.y
        data[1] = point.x
        data[2] = object_index

        if length is not None:
            data.append(length)

        obj = self.from_data(data, index)

        return obj
