"""
A pure-Python, framework-agnostic implementation of pixel-perfect bitmasks for
collision detection.
"""

from __future__ import annotations

from typing import Any

import math


__all__ = ['Bitmask']


class Bitmask:
    _mask_cache: dict[Any, 'Bitmask'] = {}
    _collision_cache: dict[Any, bool] = {}

    def __init__(self, size, data=[], scale=1):
        self.w: int = size[0]
        self.h: int = size[1]
        self.scale: int = scale
        self.data: list[int] = data.copy()

    @classmethod
    def create_mask(cls, source_id, pixels, size, threshold=128, scale=1):
        mask_key = (source_id, threshold, scale)
        if mask_key in cls._mask_cache:
            return cls._mask_cache[mask_key]

        # cache some values
        _range = range
        _min = min
        adjusted_threshold = threshold * scale**2
        w, h = size
        # Pre-calculate the (starting) x indices and the cooresponding bit
        # magnitudes since they'll be re-used for every row.
        x_vals = _range(0, w, scale)
        x_mags = [2 ** (i-1) for i in _range(math.ceil(w / scale), 0, -1)]
        x_pairs = list(zip(x_vals, x_mags))

        data = []

        for y in _range(0, h, scale):
            # Calculate the starting indices in the 1D pixel array for each row
            # Min here makes sure we don't iterate off the top of the image
            y_vals = [sub_y * w for sub_y in _range(y, _min(y+scale, h))]

            # Calculate the bitmask for a single row of the final 2D mask
            row = 0
            for x, m in x_pairs:
                # Calculate the super-pixel's total alpha
                alpha = 0
                for sub_y in y_vals:
                    # Min here makes sure we don't iterate off the side of the
                    # image
                    for i in _range(sub_y + x, _min(sub_y + x + scale, sub_y + w)):
                        alpha += pixels[i]

                # If the alpha meets the threshold, set the corresponding bit
                # in the output row. We don't have to do much math here because
                # we pre-calculated each super-pixel's magnitude earlier.
                if alpha >= adjusted_threshold:
                    row += m

            data.append(row)

        cls._mask_cache[mask_key] = mask = cls(
            (math.ceil(w / scale), math.ceil(h / scale)),
            data,
            scale
        )
        return mask

    def intersects(self, other: 'Bitmask', offset: tuple[float, float]):
        if self.scale != other.scale:
            raise ValueError(f'incompatible bitmask scales ({self}: {self.scale}, {other}: {other.scale})')

        off_x = round(offset[0] / self.scale)
        off_y = round(offset[1] / self.scale)

        # Optimize cases without overlap
        if off_x >= self.w or -off_x >= other.w or off_y >= self.h or -off_y >= other.h:
            return False

        collision_key = (self, other, offset)
        if collision_key in self._collision_cache:
            return self._collision_cache[collision_key]

        if off_x > 0:
            s_off_x = off_x
            o_off_x = 0
        else:
            o_off_x = -off_x
            s_off_x = 0

        if off_y > 0:
            s_off_y = off_y
            o_off_y = 0
        else:
            s_off_y = 0
            o_off_y = -off_y

        if self.w > other.w:
            o_off_x += self.w - other.w
        else:
            s_off_x += other.w - self.w

        iterations = min(self.h - s_off_y, other.h - o_off_y)
        for i in range(iterations):
            if (self.data[i + s_off_y] << s_off_x) & (other.data[i + o_off_y] << o_off_x):
                self._collision_cache[collision_key] = True
                return True

        self._collision_cache[collision_key] = False
        return False


if __name__ == '__main__':
    b1 = Bitmask(
        (5, 5),
        [
            0b00000,
            0b00100,
            0b01100,
            0b01100,
            0b00001,
        ]
    )
    b2 = Bitmask(
        (3, 3),
        [
            0b000,
            0b001,
            0b011,
        ]
    )
    print((0, 0), b1.intersects(b2, (0, 0)))  # True
    print((2, 0), b1.intersects(b2, (2, 0)))  # False
    print((-2, 0), b1.intersects(b2, (-2, 0)))  # False
    print((10, 10), b1.intersects(b2, (10, 10)))  # False
    print((-10, -10), b1.intersects(b2, (-10, -10)))  # False
    print((1, 0), b1.intersects(b2, (1, 0)))  # True
    print((-1, 0), b1.intersects(b2, (-1, 0)))  # True
    print((1, 1), b1.intersects(b2, (1, 1)))  # True
    print((-1, -1), b1.intersects(b2, (-1, -1)))  # False

    import timeit
    print((0, 0), timeit.timeit(lambda: b1.intersects(b2, (0, 0))))
    print((10, 10), timeit.timeit(lambda: b1.intersects(b2, (10, 10))))
    print((1, 1), timeit.timeit(lambda: b1.intersects(b2, (1, 1))))
    print((-1, -1), timeit.timeit(lambda: b1.intersects(b2, (-1, -1))))
