"""
Kivy Widgets for representing collidable game objects, utilizing per-frame
bitmasks and with optional animation integration.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from kivy.core.image import Image
from kivy.graphics.texture import Texture
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.widget import Widget
from kivy.vector import Vector

from .bitmask import Bitmask


__all__ = ['bitmask_from_texture', 'Collidable', 'AnimatedCollidable', 'Sprite']


def extract_alpha_bits(texture: Texture):
    return texture.pixels[3::4]


def bitmask_from_texture(texture: Texture, **kw):
    return Bitmask.create_mask(
        texture.id,
        extract_alpha_bits(texture),
        texture.size,
        **kw
    )


class LoaderCache(dict):
    def __init__(self, default_factory: Callable[[Any], Any], *args, **kw):
        super().__init__(*args, **kw)
        self.default_factory = default_factory

    def __missing__(self, key):
        self[key] = value = self.default_factory(key)
        return value


class Collidable(Widget):
    frames: dict[Any, Texture] = ObjectProperty()
    current_frame = ObjectProperty()
    bitmask_args = {'scale': 1}

    def __init__(self, lazy_mask: bool = False, **kw):
        self.bitmask_args: dict = kw.pop('bitmask_args', self.bitmask_args)
        super().__init__(**kw)
        self.bitmasks: dict[Any, Bitmask] = LoaderCache(self._create_mask)
        if not lazy_mask:
            self.bitmasks.update({k: self._create_mask(k) for k in self.frames})

    def _create_mask(self, key):
        return bitmask_from_texture(self.frames[key], **self.bitmask_args)

    def collide_bitmask(self, widget: 'Collidable', offset: tuple[float, float]) -> bool:
        return self.bitmasks[self.current_frame].intersects(widget.bitmasks[widget.current_frame], offset)

    def collide_bitmask_default(self, widget: 'Collidable'):
        offset = Vector(widget.pos) - Vector(self.pos)
        offset = (round(offset.x), round(offset.y))
        return self.collide_bitmask(widget, offset)


class AnimatedCollidable(Collidable):
    frame_groups: dict[str, list[tuple[float, str]]] = {}
    current_state: str = StringProperty()
    next_state: Optional[str] = StringProperty(allownone=True)
    current_frame_index: int = NumericProperty(0)

    def __init__(self, **kw):
        self.dt: float = 0
        self.frame_times: dict[Any, float] = {}
        self.frame_counts: dict[Any, int] = {}

        frames = {}
        for state, group in self.frame_groups.items():
            i = 0
            for duration, path in group:
                frames[(state, i)] = Image(path).texture
                self.frame_times[(state, i)] = duration
                i += 1

            self.frame_counts[state] = i

        super().__init__(
            frames=frames,
            current_frame=(kw['current_state'], 0),
            **kw
        )

    def on_current_state(self, *args):
        self.current_frame = (self.current_state, 0)

    def update(self, dt: float):
        self.dt += dt

        while self.dt > self.frame_times[self.current_frame]:
            self.dt -= self.frame_times[self.current_frame]

            i = self.current_frame_index + 1

            if i >= self.frame_counts[self.current_state]:
                i = 0
                if self.next_state:
                    self.current_state = self.next_state
                    self.next_state = None

            self.current_frame_index = i
            self.current_frame = (self.current_state, self.current_frame_index)


class Sprite(AnimatedCollidable):
    sprite_anchor: Vector = ObjectProperty(Vector(0, 0))
    sprite_offsets: dict[Any, Vector] = ObjectProperty({})
    visualize_hitboxes: bool = BooleanProperty(False)

    def on_frames(self, *args):
        self._calculate_offsets()
    def on_size(self, *args):
        self._calculate_offsets()
    def on_sprite_anchor(self, *args):
        self._calculate_offsets()

    def _calculate_offsets(self):
        self.sprite_offsets = {
            key: Vector(
                self.width / 2 + self.sprite_anchor.x - frame.width / 2,
                self.height / 2 + self.sprite_anchor.y - frame.height / 2
            )
            for key, frame in self.frames.items()
        }

    def collide_bitmask_default(self, widget: Collidable) -> bool:
        offset = Vector(widget.pos) - Vector(self.pos) - self.sprite_offsets[self.current_frame]
        if isinstance(widget, Sprite):
            offset += widget.sprite_offsets[widget.current_frame]

        offset = (round(offset.x), round(offset.y))

        return self.collide_bitmask(widget, offset)
