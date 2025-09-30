# tidal_client.py
# Cliente TIDAL (uso personal) basado en tidalapi para leer/crear playlists y buscar pistas.

import os
import time
from typing import List

import tidalapi

from matcher import Track


class TidalClient:
    def __init__(self):
        self.session = tidalapi.Session()
        ok = self.session.login(os.environ["TIDAL_USERNAME"], os.environ["TIDAL_PASSWORD"])
        if not ok:
            raise RuntimeError("No fue posible iniciar sesión en TIDAL. Revise TIDAL_USERNAME/TIDAL_PASSWORD.")
        self.user = tidalapi.User(self.session, self.session.user.id)

    def get_playlist_name(self, playlist_id: str) -> str:
        pl = tidalapi.playlist.Playlist(self.session, playlist_id)
        pl._populate()
        return pl.name

    def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        pl = tidalapi.playlist.Playlist(self.session, playlist_id)
        pl._populate()
        items = pl.tracks()
        tracks: List[Track] = []
        for t in items:
            artists = [a.name for a in t.artists]
            duration = int(getattr(t, "duration", 0))
            isrc = getattr(t, "isrc", None)
            tracks.append(Track(
                title=t.name,
                artists=
