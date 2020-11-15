"""
A framework-agnostic tool for automatically reading in animation frames, with
support for detecting frame length.
"""

from __future__ import annotations

from typing import Union

import glob
import re


__all__ = ['read_frame_group']


def read_frame_group(template: str, times: Union[float, list[float]] = None) -> list[tuple[float, str]]:
    # Allow parentheses in filenames
    re_ready = template.replace('(', '\\(').replace(')', '\\)')
    regex = re.compile(re_ready.format(index=r'(?P<index>\d+)', time=r'(?P<time>\d+)'))

    frames = []
    files = glob.glob(template.format(index='*', time='*'))
    for file in files:
        # Make sure our template works across operating systems since glob
        # paths are localized
        m = regex.match(file.replace('\\', '/'))
        if m:
            frames.append(m)

    frames.sort(key=lambda m: int(m.group('index')))

    if isinstance(times, int):
        times = [times / 1000] * len(frames)
    elif isinstance(times, float):
        times = [times] * len(frames)

    if times:
        return [(times[i], m.group()) for i, m in enumerate(frames)]
    else:
        return [(int(m.group('time')) / 1000, m.group()) for m in frames]
