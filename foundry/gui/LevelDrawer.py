from itertools import product
from json import loads

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, Qt

from foundry import data_dir, namespace_path
from foundry.core.drawable.Drawable import Drawable as DrawableValidator
from foundry.core.geometry import Point
from foundry.core.graphics_set.GraphicsSet import GraphicsSet
from foundry.core.icon import Icon
from foundry.core.namespace import Namespace, TypeHandlerManager, generate_namespace
from foundry.core.palette import ColorPalette, PaletteGroup
from foundry.core.tiles import MASK_COLOR
from foundry.game.File import ROM
from foundry.game.gfx.drawable import apply_selection_overlay
from foundry.game.gfx.drawable.Block import Block
from foundry.game.gfx.objects.EnemyItem import EnemyObject
from foundry.game.gfx.objects.LevelObject import (
    GROUND,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    LevelObject,
)
from foundry.game.gfx.objects.ObjectLike import (
    EXPANDS_BOTH,
    EXPANDS_HORIZ,
    EXPANDS_VERT,
)
from foundry.game.level.Level import Level
from foundry.gui.AutoScrollDrawer import AutoScrollDrawer
from foundry.gui.settings import UserSettings
from foundry.smb3parse.constants import OBJ_AUTOSCROLL, TILESET_BACKGROUND_BLOCKS
from foundry.smb3parse.levels import LEVEL_MAX_LENGTH
from foundry.smb3parse.objects.object_set import (
    CLOUDY_OBJECT_SET,
    DESERT_OBJECT_SET,
    DUNGEON_OBJECT_SET,
    ICE_OBJECT_SET,
)

namespace: None | Namespace = None
level_images: Namespace[DrawableValidator] = None  # type: ignore


def load_namespace() -> Namespace:
    global namespace
    global level_images
    with open(str(namespace_path)) as f:
        namespace = generate_namespace(
            loads(f.read()),
            validators=TypeHandlerManager.from_managers(DrawableValidator.type_manager, Icon.type_manager),
        )

    level_images = namespace.children["graphics"].children["level_images"]
    return namespace


png = QImage(str(data_dir / "gfx.png"))
png.convertTo(QImage.Format.Format_RGB888)


def _make_image_selected(image: QImage) -> QImage:
    alpha_mask = image.createAlphaMask()
    alpha_mask.invertPixels()

    selected_image = QImage(image)

    apply_selection_overlay(selected_image, alpha_mask)

    return selected_image


def _load_from_png(point: Point):
    image = png.copy(QRect(point.x * 16, point.y * 16, 16, 16))
    mask = image.createMaskFromColor(QColor(*MASK_COLOR).rgb(), Qt.MaskMode.MaskOutColor)
    image.setAlphaChannel(mask)

    return image


FIRE_FLOWER = lambda: level_images["fire_flower"].image()  # noqa: E731
LEAF = lambda: level_images["leaf"].image()  # noqa: E731
NORMAL_STAR = lambda: level_images["star"].image()  # noqa: E731
CONTINUOUS_STAR = lambda: level_images["star_continuous"].image()  # noqa: E731
MULTI_COIN = lambda: level_images["coins_multiple"].image()  # noqa: E731
ONE_UP = lambda: level_images["extra_life"].image()  # noqa: E731
COIN = lambda: level_images["coin"].image()  # noqa: E731
VINE = lambda: level_images["vine"].image()  # noqa: E731
P_SWITCH = lambda: level_images["p_switch"].image()  # noqa: E731
SILVER_COIN = lambda: level_images["coin_silver"].image()  # noqa: E731
INVISIBLE_COIN = lambda: level_images["coin_invisible"].image()  # noqa: E731
INVISIBLE_1_UP = lambda: level_images["coin_extra_life"].image()  # noqa: E731

NO_JUMP = lambda: level_images["no_jump"].image()  # noqa: E731
UP_ARROW = lambda: level_images["up_arrow"].image()  # noqa: E731
DOWN_ARROW = lambda: level_images["down_arrow"].image()  # noqa: E731
LEFT_ARROW = lambda: level_images["left_arrow"].image()  # noqa: E731
RIGHT_ARROW = lambda: level_images["right_arrow"].image()  # noqa: E731

ITEM_ARROW = lambda: level_images["item_arrow"].image()  # noqa: E731

EMPTY_IMAGE = lambda: level_images["empty"].image()  # noqa: E731


SPECIAL_BACKGROUND_OBJECTS = [
    "blue background",
    "starry background",
    "underground background under this",
    "sets background to actual background color",
]


def get_blocks(level: Level) -> list[Block]:
    palette_group = PaletteGroup.from_tileset(level.object_set_number, level.header.object_palette_index)
    palette_group = palette_group
    graphics_set = GraphicsSet.from_tileset(level.header.graphic_set_index)
    tsa_data = ROM().get_tsa_data(level.object_set_number)

    return [Block(i, palette_group, graphics_set, tsa_data) for i in range(0x100)]


def _block_from_index(block_index: int, level: Level) -> Block:
    """
    Returns the block at the given index, from the TSA table for the given level.

    :param block_index:
    :param level:
    :return:
    """

    palette_group = PaletteGroup.from_tileset(level.object_set_number, level.header.object_palette_index)
    graphics_set = GraphicsSet.from_tileset(level.header.graphic_set_index)
    tsa_data = ROM().get_tsa_data(level.object_set_number)

    return Block(block_index, palette_group, graphics_set, tsa_data)


class LevelDrawer:
    def __init__(self, user_settings: UserSettings):
        self.user_settings = user_settings

        self.block_length = Block.WIDTH

        self.grid_pen = QPen(QColor(0x80, 0x80, 0x80, 0x80))
        self.grid_pen.setWidth(1)
        self.screen_pen = QPen(QColor(0xFF, 0x00, 0x00, 0xFF))
        self.screen_pen.setWidth(1)

    def draw(self, painter: QPainter, level: Level):
        self._draw_background(painter, level)

        self._draw_default_graphics(painter, level)

        if level.object_set_number == DESERT_OBJECT_SET:
            self._draw_desert_default_graphics(painter, level)
        elif level.object_set_number == DUNGEON_OBJECT_SET:
            self._draw_dungeon_default_graphics(painter, level)
        elif level.object_set_number == ICE_OBJECT_SET:
            self._draw_ice_default_graphics(painter, level)

        self._draw_objects(painter, level)

        self._draw_overlays(painter, level)

        if self.user_settings.draw_expansion:
            self._draw_expansions(painter, level)

        if self.user_settings.draw_mario:
            self._draw_mario(painter, level)

        if self.user_settings.draw_jumps:
            self._draw_jumps(painter, level)

        if self.user_settings.draw_grid:
            self._draw_grid(painter, level)

        if self.user_settings.draw_autoscroll:
            self._draw_auto_scroll(painter, level)

    def _draw_background(self, painter: QPainter, level: Level):
        painter.save()

        if level.object_set_number == CLOUDY_OBJECT_SET:
            bg_color = ColorPalette.from_default()[
                PaletteGroup.from_tileset(level.object_set_number, level.header.object_palette_index)[3, 2]
            ].to_qt()
        else:
            bg_color = PaletteGroup.from_tileset(
                level.object_set_number, level.header.object_palette_index
            ).background_color

        painter.fillRect(level.get_rect(self.block_length).to_qt(), bg_color)

        painter.restore()

    def _draw_dungeon_default_graphics(self, painter: QPainter, level: Level):
        # draw_background
        bg_block = _block_from_index(140, level)

        for x, y in product(range(level.width), range(level.height)):
            bg_block.draw(painter, x * self.block_length, y * self.block_length, self.block_length)

        # draw ceiling
        ceiling_block = _block_from_index(139, level)

        for x in range(level.width):
            ceiling_block.draw(painter, x * self.block_length, 0, self.block_length)

        # draw floor
        upper_floor_blocks = [_block_from_index(20, level), _block_from_index(21, level)]
        lower_floor_blocks = [_block_from_index(22, level), _block_from_index(23, level)]

        upper_y = (GROUND - 2) * self.block_length
        lower_y = (GROUND - 1) * self.block_length

        for block_x in range(level.width):
            pixel_x = block_x * self.block_length

            upper_floor_blocks[block_x % 2].draw(painter, pixel_x, upper_y, self.block_length)
            lower_floor_blocks[block_x % 2].draw(painter, pixel_x, lower_y, self.block_length)

    def _draw_desert_default_graphics(self, painter: QPainter, level: Level):
        floor_level = (GROUND - 1) * self.block_length
        floor_block_index = 86

        floor_block = _block_from_index(floor_block_index, level)

        for x in range(level.width):
            floor_block.draw(painter, x * self.block_length, floor_level, self.block_length)

    def _draw_ice_default_graphics(self, painter: QPainter, level: Level):
        bg_block = _block_from_index(0x80, level)

        for x, y in product(range(level.width), range(level.height)):
            bg_block.draw(painter, x * self.block_length, y * self.block_length, self.block_length)

    def _draw_default_graphics(self, painter: QPainter, level: Level):
        bg_block = _block_from_index(TILESET_BACKGROUND_BLOCKS[level.object_set_number], level)

        for x, y in product(range(level.width), range(level.height)):
            bg_block.draw(painter, x * self.block_length, y * self.block_length, self.block_length)

    def _draw_objects(self, painter: QPainter, level: Level):
        bg_palette_group = PaletteGroup.from_tileset(level.object_set_number, level.header.object_palette_index)
        spr_palette_group = PaletteGroup.from_tileset(level.object_set_number, 8 + level.header.enemy_palette_index)

        blocks = get_blocks(level)
        for level_object in level.objects:
            level_object.palette_group = bg_palette_group
        for enemy in level.enemies:
            enemy.palette_group = spr_palette_group

        for level_object in level.get_all_objects():

            level_object.render()

            if level_object.name.lower() in SPECIAL_BACKGROUND_OBJECTS and isinstance(level_object, LevelObject):
                width = LEVEL_MAX_LENGTH
                height = GROUND - level_object.position.y

                blocks_to_draw = [level_object.blocks[0]] * width * height

                for index, block_index in enumerate(blocks_to_draw):
                    x = level_object.position.x + index % width
                    y = level_object.position.y + index // width

                    level_object._draw_block(painter, block_index, x, y, self.block_length, False, blocks=blocks)
            else:
                if isinstance(level_object, LevelObject):
                    level_object.draw(painter, self.block_length, self.user_settings.block_transparency, blocks=blocks)
                else:
                    level_object.draw(painter, self.block_length, True)

            if level_object.selected:
                painter.save()

                pen = QPen(QColor(0x00, 0x00, 0x00, 0x80))
                pen.setWidth(1)
                painter.setPen(pen)
                painter.drawRect(level_object.get_rect(self.block_length).to_qt())

                painter.restore()

    def _draw_overlays(self, painter: QPainter, level: Level):
        if namespace is None:
            load_namespace()

        painter.save()

        for level_object in level.get_all_objects():
            point = level_object.get_rect(self.block_length).upper_left_point
            rect = level_object.get_rect(self.block_length)

            for overlay in level_object.definition.get_overlays():
                drawable = overlay.drawable
                painter.drawImage(
                    drawable.point_offset.x + point.x * self.block_length,
                    drawable.point_offset.y + point.y * self.block_length,
                    drawable.image(self.block_length),
                )

            name = level_object.name.lower()

            # only handle this specific enemy item for now
            if isinstance(level_object, EnemyObject) and "invisible door" not in name:
                continue

            # invisible coins, for example, expand and need to have multiple overlays drawn onto them
            # set true by default, since for most overlays it doesn't matter
            fill_object = True

            # pipe entries
            if "pipe" in name and "can go" in name:
                if not self.user_settings.draw_jump_on_objects:
                    continue

                fill_object = False

                point: Point = rect.mid_point
                trigger_position: Point = level_object.position

                if "left" in name:
                    image = LEFT_ARROW()
                    point = point.evolve(x=rect.right, y=point.y - self.block_length // 2)

                    # leftward pipes trigger on the column to the left of the opening
                    trigger_position = level_object.rect.lower_right_point - Point(1, 0)
                elif "right" in name:
                    image = RIGHT_ARROW()
                    point = point.evolve(x=rect.left - self.block_length, y=point.y - self.block_length // 2)
                elif "down" in name:
                    image = DOWN_ARROW()
                    point = point.evolve(x=point.x - self.block_length // 2, y=rect.top - self.block_length)
                else:
                    # upwards pipe
                    image = UP_ARROW()
                    point = point.evolve(x=point.x - self.block_length // 2, y=rect.bottom)

                    # upwards pipes trigger on the second to last row
                    trigger_position = level_object.rect.lower_left_point - Point(0, 1)

                if not self._object_in_jump_area(level, trigger_position):
                    image = NO_JUMP()

            elif "door" == name or "door (can go" in name or "invisible door" in name or "red invisible note" in name:
                fill_object = False

                if "note" in name:
                    image = UP_ARROW()
                else:
                    # door
                    image = DOWN_ARROW()

                point = point.evolve(y=rect.top - self.block_length)

                # jumps seemingly trigger on the bottom block
                if not self._object_in_jump_area(level, level_object.position + Point(0, 1)):
                    image = NO_JUMP()

            # "?" - blocks, note blocks, wooden blocks and bricks
            elif "'?' with" in name or "brick with" in name or "bricks with" in name or "block with" in name:
                if not self.user_settings.draw_items_in_blocks:
                    continue

                point = point.evolve(y=point.y - self.block_length)

                if "flower" in name:
                    image = FIRE_FLOWER()
                elif "leaf" in name:
                    image = LEAF()
                elif "continuous star" in name:
                    image = CONTINUOUS_STAR()
                elif "star" in name:
                    image = NORMAL_STAR()
                elif "multi-coin" in name:
                    image = MULTI_COIN()
                elif "coin" in name:
                    image = COIN()
                elif "1-up" in name:
                    image = ONE_UP()
                elif "vine" in name:
                    image = VINE()
                elif "p-switch" in name:
                    image = P_SWITCH()
                else:
                    image = EMPTY_IMAGE()

                # draw little arrow for the offset item overlay
                arrow_pos = point.to_qt()
                arrow_pos.setY(arrow_pos.y() + self.block_length / 4)
                painter.drawImage(arrow_pos, ITEM_ARROW().scaled(self.block_length, self.block_length))

            elif "invisible" in name:
                if not self.user_settings.draw_invisible_items:
                    continue

                if "coin" in name:
                    image = INVISIBLE_COIN()
                elif "1-up" in name:
                    image = INVISIBLE_1_UP()
                else:
                    image = EMPTY_IMAGE()

            elif "silver coins" in name:
                if not self.user_settings.draw_invisible_items:
                    continue

                image = SILVER_COIN()
            else:
                continue

            if fill_object:
                for x in range(level_object.rendered_size.width):
                    adapted_pos = point.to_qt()
                    adapted_pos.setX(point.x + x * self.block_length)

                    image = image.scaled(self.block_length, self.block_length)
                    painter.drawImage(adapted_pos, image)

                    if level_object.selected:
                        painter.drawImage(adapted_pos, _make_image_selected(image))

            else:
                image = image.scaled(self.block_length, self.block_length)
                painter.drawImage(point.to_qt(), image)

        painter.restore()

    @staticmethod
    def _object_in_jump_area(level: Level, point: Point) -> bool:
        for jump in level.jumps:
            jump_rect = jump.get_rect(1, level.is_vertical)

            if jump_rect.contains(point):
                return True
        else:
            return False

    def _draw_expansions(self, painter: QPainter, level: Level):
        for level_object in level.get_all_objects():
            if level_object.selected:
                painter.drawRect(level_object.get_rect(self.block_length).to_qt())

            if self.user_settings.draw_expansion:
                painter.save()

                painter.setPen(Qt.PenStyle.NoPen)

                if level_object.expands() == EXPANDS_BOTH:
                    painter.setBrush(QColor(0xFF, 0, 0xFF, 0x80))
                elif level_object.expands() == EXPANDS_HORIZ:
                    painter.setBrush(QColor(0xFF, 0, 0, 0x80))
                elif level_object.expands() == EXPANDS_VERT:
                    painter.setBrush(QColor(0, 0, 0xFF, 0x80))

                painter.drawRect(level_object.get_rect(self.block_length).to_qt())

                painter.restore()

    def _draw_mario(self, painter: QPainter, level: Level):
        mario_actions = QImage(str(data_dir / "mario.png"))

        mario_actions.convertTo(QImage.Format.Format_RGBA8888)

        mario_position = QPoint(*level.header.mario_position()) * self.block_length

        x_offset = 32 * level.start_action
        MARIO_POWERUP_Y_OFFSETS = [0, 0x20, 0x60, 0x40, 0xC0, 0xA0, 0x80, 0x60, 0xC0]
        y_offset = MARIO_POWERUP_Y_OFFSETS[self.user_settings.default_powerup]

        mario_cutout = mario_actions.copy(QRect(x_offset, y_offset, 32, 32)).scaled(
            2 * self.block_length, 2 * self.block_length
        )

        painter.drawImage(mario_position, mario_cutout)

    def _draw_jumps(self, painter: QPainter, level: Level):
        for jump in level.jumps:
            painter.setBrush(QBrush(QColor(0xFF, 0x00, 0x00), Qt.BrushStyle.FDiagPattern))

            painter.drawRect(jump.get_rect(self.block_length, level.is_vertical).to_qt())

    def _draw_grid(self, painter: QPainter, level: Level):
        panel_size = level.get_rect(self.block_length).size

        painter.setPen(self.grid_pen)

        for x in range(0, panel_size.width, self.block_length):
            painter.drawLine(x, 0, x, panel_size.height)
        for y in range(0, panel_size.height, self.block_length):
            painter.drawLine(0, y, panel_size.width, y)

        painter.setPen(self.screen_pen)

        if level.is_vertical:
            for y in range(0, panel_size.height, self.block_length * SCREEN_HEIGHT):
                painter.drawLine(0, self.block_length + y, panel_size.width, self.block_length + y)
        else:
            for x in range(0, panel_size.width, self.block_length * SCREEN_WIDTH):
                painter.drawLine(x, 0, x, panel_size.height)

    def _draw_auto_scroll(self, painter: QPainter, level: Level):
        for item in level.enemies:
            if item.obj_index == OBJ_AUTOSCROLL:
                break
        else:
            return

        drawer = AutoScrollDrawer(item.position.y, level)

        drawer.draw(painter, self.block_length)
