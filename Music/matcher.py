# matcher.py
# Utilidades de normalización y matching + dataclass Track compartida.

from dataclasses import dataclass
from typing import List, Optional

import re


def norm_text(s: str) -> str:
    """Normaliza cadenas (quita paréntesis, sufijos típicos y espacios extra)."""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(
        r"-\s*(remaster(?:ed)?(?:\s*\d{2,4})?|single|radio edit|live|deluxe)", "", s
    )
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass
class Track:
    title: str
    artists: List[str]
    album: str
    duration_sec: int
    isrc: Optional[str]
    spotify_uri: Optional[str] = None
    tidal_id: Optional[str] = None

    def simple_key(self) -> str:
        a0 = norm_text(self.artists[0]) if self.artists else ""
        return f"{norm_text(self.title)}|{a0}|{self.duration_sec}"

    def key(self) -> str:
        return f"ISRC:{self.isrc.upper()}" if self.isrc else f"ALT:{self.simple_key()}"


def match_track(dest_client, source_track: "Track") -> Optional["Track"]:
    """
    Devuelve la mejor coincidencia de `source_track` en el cliente de destino.
    Estrategia:
      1) Intentar por ISRC (si está disponible en ambos lados).
      2) Búsqueda por "título + primer artista" y verificación por duración (±2 s).
    """
    # 1) Intento por ISRC si existe
    if source_track.isrc:
        candidates = dest_client.search_track_candidates(source_track.isrc, limit=5)
        for c in candidates:
            if c.isrc and c.isrc.upper() == source_track.isrc.upper():
                return c

    # 2) Texto + validación
    q = f"{source_track.title} {source_track.artists[0] if source_track.artists else ''}".strip()
    candidates = dest_client.search_track_candidates(q, limit=10)

    t_title = norm_text(source_track.title)
    t_artist = norm_text(source_track.artists[0]) if source_track.artists else ""
    t_dur = source_track.duration_sec

    for c in candidates:
        ok_title = norm_text(c.title) == t_title
        ok_artist = t_artist in (norm_text(c.artists[0]) if c.artists else "")
        ok_dur = (c.duration_sec == 0) or (abs(c.duration_sec - t_dur) <= 2)
        ok_isrc = True
        if source_track.isrc and c.isrc:
            ok_isrc = source_track.isrc.upper() == c.isrc.upper()
        if ok_title and ok_artist and ok_dur and ok_isrc:
            return c
    return None
