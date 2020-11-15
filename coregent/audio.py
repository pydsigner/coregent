"""
Kivy helpers for orchestrating volume levels for groups of Sounds.
"""

from __future__ import annotations

import os

from kivy.core.audio import Sound, SoundLoader


class AudioManager:
    def __init__(self, prefix='./', volume=.5):
        self._sounds: list[tuple[Sound, float]] = []
        self.prefix = prefix
        self._volume = None
        self.volume = volume

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        if value > 1:
            value /= 100

        if value == self._volume:
            return
        self._volume = value

        for sound, multiplier in self._sounds:
            sound.volume = value * multiplier

    def load(self, path, multiplier=1):
        sound = SoundLoader.load(os.path.join(self.prefix, path))
        if sound is None:
            return

        sound.volume = self._volume * multiplier
        self._sounds.append((sound, multiplier))
        return sound
