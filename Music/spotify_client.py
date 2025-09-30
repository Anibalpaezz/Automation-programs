# spotify_client.py
# Cliente Spotify para lectura/creación de playlists y búsqueda de pistas.

import os
import time
from typing import Dict, List

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

from matcher import Track  # misma interfaz de atributos que usa main.py


class SpotifyClient:
    def __init__(self):
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=os.environ["SPOTIFY_CLIENT_ID"],
                client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
                scope="playlist-read-private playlist-modify-private playlist-modify-public",
            )
        )

    @staticmethod
    def _extract_playlist_id(url_or_id: str) -> str:
        return url_or_id.split("/")[-1].split("?")[0]

    def get_me(self) -> Dict:
        return self.sp.me()

    def get_playlist_name(self, playlist_id_or_url: str) -> str:
        pid = self._extract_playlist_id(playlist_id_or_url)
        p = self.sp.playlist(pid, fields="name")
        return p["name"]

    def get_playlist_tracks(self, playlist_id_or_url: str) -> List[Track]:
        pid = self._extract_playlist_id(playlist_id_or_url)
        results = self.sp.playlist_items(pid, additional_types=["track"], limit=100)
        items = results.get("items", [])
        while results.get("next"):
            results = self.sp.next(results)
            items.extend(results.get("items", []))

        tracks: List[Track] = []
        for it in items:
            t = it.get("track") or {}
            if not t:
                continue
            artists = [a["name"] for a in t.get("artists", [])]
            album = (t.get("album") or {}).get("name", "")
            isrc = (t.get("external_ids") or {}).get("isrc")
            duration = int((t.get("duration_ms") or 0) / 1000)
            uri = t.get("uri")
            tracks.append(
                Track(
                    title=t.get("name", ""),
                    artists=artists,
                    album=album,
                    duration_sec=duration,
                    isrc=isrc,
                    spotify_uri=uri,
                )
            )
        return tracks

    def ensure_playlist(self, name: str, public: bool = False) -> str:
        me = self.get_me()
        user_id = me["id"]
        p = self.sp.user_playlist_create(
            user_id, name, public=public, description="Importada vía sync personal"
        )
        return p["id"]

    def add_tracks(self, playlist_id: str, spotify_uris: List[str]):
        CHUNK = 50
        for i in range(0, len(spotify_uris), CHUNK):
            chunk = spotify_uris[i : i + CHUNK]
            self._retry(lambda: self.sp.playlist_add_items(playlist_id, chunk))
            time.sleep(0.1)

    def remove_tracks(self, playlist_id: str, spotify_uris: List[str]):
        CHUNK = 50
        for i in range(0, len(spotify_uris), CHUNK):
            chunk = [{"uri": u} for u in spotify_uris[i : i + CHUNK]]
            self._retry(
                lambda: self.sp.playlist_remove_specific_occurrences_of_items(
                    playlist_id, chunk
                )
            )
            time.sleep(0.1)

    def search_track_candidates(self, query: str, limit: int = 10) -> List[Track]:
        res = self._retry(lambda: self.sp.search(q=query, type="track", limit=limit))
        out: List[Track] = []
        for t in res.get("tracks", {}).get("items", []):
            artists = [a["name"] for a in t.get("artists", [])]
            album = (t.get("album") or {}).get("name", "")
            isrc = (t.get("external_ids") or {}).get("isrc")
            duration = int((t.get("duration_ms") or 0) / 1000)
            out.append(
                Track(
                    title=t.get("name", ""),
                    artists=artists,
                    album=album,
                    duration_sec=duration,
                    isrc=isrc,
                    spotify_uri=t.get("uri"),
                )
            )
        return out

    @staticmethod
    def _retry(fn, max_tries=5, base_sleep=0.5):
        tries = 0
        while True:
            try:
                return fn()
            except SpotifyException as e:
                tries += 1
                if e.http_status == 429:
                    ra = int(e.headers.get("Retry-After", "1"))
                    time.sleep(ra + 0.25)
                elif tries < max_tries:
                    time.sleep(base_sleep * (2 ** (tries - 1)))
                else:
                    raise
