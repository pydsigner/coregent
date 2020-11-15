"""
A framework-agnostic tool for automatically reading in animation frames, with
support for detecting frame length.
"""

from __future__ import annotations

from typing import Optional, Union

import glob
import os
import re


__all__ = ['read_frame_group', 'read_frame_groups']


def read_frame_group(template: str, times: Union[None, float, list[float]] = None) -> list[tuple[float, str]]:
    # Make sure our template works across operating systems since glob
    # paths are localized
    template = os.path.normpath(template)
    # We take in a format string, but we need to protect it from regex escaping
    re_pattern = template.format(index='%index%', time='%time%')
    # Escape parentheses, backslashes, and periods, in particular
    re_pattern = re.escape(re_pattern)
    # Inject our regular expressions now that we've escaped everything else
    re_pattern = re_pattern.replace('%index%', r'(?P<index>\d+)')
    re_pattern = re_pattern.replace('%time%', r'(?P<time>\d+)')
    # Finally, compile the regex for use!
    re_pattern = re.compile(re_pattern)
    # Our glob pattern is much simpler to construct
    glob_pattern = template.format(index='*', time='*')

    frames = []
    files = glob.glob(glob_pattern)
    for file in files:
        m = re_pattern.match(file)
        if m:
            frames.append(m)

    frames.sort(key=lambda m: int(m.group('index')))

    if isinstance(times, float):
        times = [times] * len(frames)

    if times:
        return [(times[i], m.group()) for i, m in enumerate(frames)]
    else:
        return [(int(m.group('time')) / 1000, m.group()) for m in frames]


def read_frame_groups(base: str, groups: dict[str, tuple[str, Optional[float]]]):
    return {
        k: read_frame_group(os.path.join(base, p), t)
         for k, (p, t) in groups.items()
    }
