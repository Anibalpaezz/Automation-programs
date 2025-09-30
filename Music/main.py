#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Sync personal Spotify <-> TIDAL (transfer + sync) en un único script.

Requisitos:
  pip install spotipy tidalapi python-dotenv

Variables .env:
  SPOTIFY_CLIENT_ID=...
  SPOTIFY_CLIENT_SECRET=...
  SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback

  # Para uso personal con tidalapi (login directo):
  TIDAL_USERNAME=...
  TIDAL_PASSWORD=...

Uso:
  ver README en el encabezado del mensaje (transfer, pair add, sync, etc.)
"""

import argparse
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Spotify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

# TIDAL (cliente práctico para uso personal)
import tidalapi


# ============== Utilidades de normalización y claves =================


def _norm_text(s: str) -> str:
    """Normaliza cadenas para matching por texto."""
    if not s:
        return ""
    s = s.lower()
    # Elimine paréntesis, corchetes y sufijos típicos.
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(
        r"-\s*(remaster(?:ed)?(?:\s*\d{2,4})?|single|radio edit|live|deluxe)", "", s
    )
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass
class Track:
    """Representa una pista 'neutral' (independiente del proveedor)."""

    title: str
    artists: List[str]
    album: str
    duration_sec: int
    isrc: Optional[str]  # puede ser None
    # Identificadores por proveedor para acelerar futuras operaciones
    spotify_uri: Optional[str] = None
    tidal_id: Optional[str] = None

    def simple_key(self) -> str:
        """
        Clave alternativa cuando no hay ISRC: título + primer artista + duración ~.
        """
        t = _norm_text(self.title)
        a = _norm_text(self.artists[0]) if self.artists else ""
        d = str(self.duration_sec)
        return f"{t}|{a}|{d}"

    def key(self) -> str:
        """Devuelve clave preferida (ISRC si existe) o simple_key."""
        if self.isrc:
            return f"ISRC:{self.isrc.upper()}"
        return f"ALT:{self.simple_key()}"


# ============== Cliente Spotify =================


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
        # admite URL completa o ID
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
            isrc = None
            try:
                exids = t.get("external_ids") or {}
                isrc = exids.get("isrc")
            except Exception:
                pass
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
        """Crea (si no existe) y devuelve playlist_id. Para simplicidad siempre crea una nueva."""
        me = self.get_me()
        user_id = me["id"]
        p = self.sp.user_playlist_create(
            user_id, name, public=public, description="Importada vía sync personal"
        )
        return p["id"]

    def add_tracks(self, playlist_id: str, spotify_uris: List[str]):
        """Añade pistas en lotes. spotify_uris son URIs tipo 'spotify:track:...'."""
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


# ============== Cliente TIDAL =================


class TidalClient:
    def __init__(self):
        self.session = tidalapi.Session()
        ok = self.session.login(
            os.environ["TIDAL_USERNAME"], os.environ["TIDAL_PASSWORD"]
        )
        if not ok:
            raise RuntimeError(
                "No fue posible iniciar sesión en TIDAL (revise TIDAL_USERNAME/TIDAL_PASSWORD)."
            )
        self.user = tidalapi.User(self.session, self.session.user.id)

    def get_playlist_name(self, playlist_id: str) -> str:
        pl = tidalapi.playlist.Playlist(self.session, playlist_id)
        pl._populate()  # fuerza fetch
        return pl.name

    def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        pl = tidalapi.playlist.Playlist(self.session, playlist_id)
        pl._populate()
        items = pl.tracks()
        tracks: List[Track] = []
        for t in items:
            artists = [a.name for a in t.artists]
            duration = int(getattr(t, "duration", 0))  # segundos
            isrc = getattr(t, "isrc", None)
            tracks.append(
                Track(
                    title=t.name,
                    artists=artists,
                    album=(
                        getattr(t.album, "name", "")
                        if getattr(t, "album", None)
                        else ""
                    ),
                    duration_sec=duration,
                    isrc=isrc,
                    tidal_id=str(t.id),
                )
            )
        return tracks

    def ensure_playlist(self, name: str, public: bool = False) -> str:
        # TIDAL no distingue public/private en el mismo modo que Spotify desde esta librería.
        pl = self.user.create_playlist(
            name=name, description="Importada vía sync personal"
        )
        return pl.id

    def add_tracks(self, playlist_id: str, tidal_track_ids: List[str]):
        CHUNK = 50
        pl = tidalapi.playlist.Playlist(self.session, playlist_id)
        for i in range(0, len(tidal_track_ids), CHUNK):
            chunk = tidal_track_ids[i : i + CHUNK]
            pl.add(chunk)
            time.sleep(0.2)

    def remove_tracks(self, playlist_id: str, tidal_track_ids: List[str]):
        CHUNK = 50
        pl = tidalapi.playlist.Playlist(self.session, playlist_id)
        for i in range(0, len(tidal_track_ids), CHUNK):
            chunk = tidal_track_ids[i : i + CHUNK]
            try:
                pl.remove(chunk)
            except Exception:
                # Algunas versiones de tidalapi aceptan remove(ids) y otras requieren objetos Track.
                # Fallback: no eliminar si no está disponible.
                pass
            time.sleep(0.2)

    def search_track_candidates(self, query: str, limit: int = 10) -> List[Track]:
        res = self.session.search("tracks", query, limit=limit)
        out: List[Track] = []
        for t in getattr(res, "tracks", []):
            artists = [a.name for a in t.artists]
            duration = int(getattr(t, "duration", 0))
            isrc = getattr(t, "isrc", None)
            out.append(
                Track(
                    title=t.name,
                    artists=artists,
                    album=(
                        getattr(t.album, "name", "")
                        if getattr(t, "album", None)
                        else ""
                    ),
                    duration_sec=duration,
                    isrc=isrc,
                    tidal_id=str(t.id),
                )
            )
        return out


# ============== Matching =================


def match_in_destination(dest_client, source_track: Track) -> Optional[Track]:
    """
    Estrategia:
      1) Si hay ISRC, buscar por texto y validar ISRC exacto (TIDAL) o directamente candidates (Spotify).
      2) Búsqueda por título + primer artista; validar por duración ±2 s y normalización.
    """
    # 1) Intento por ISRC si existe (algunos clientes permiten incluir ISRC en query textual)
    if source_track.isrc:
        # Probamos consulta ISRC como texto literal
        candidates = dest_client.search_track_candidates(source_track.isrc, limit=5)
        for c in candidates:
            if c.isrc and c.isrc.upper() == source_track.isrc.upper():
                return c

    # 2) Texto: "titulo artista"
    q = f"{source_track.title} {source_track.artists[0] if source_track.artists else ''}".strip()
    candidates = dest_client.search_track_candidates(q, limit=10)

    t_title = _norm_text(source_track.title)
    t_artist = _norm_text(source_track.artists[0]) if source_track.artists else ""
    t_dur = source_track.duration_sec

    for c in candidates:
        ok_title = _norm_text(c.title) == t_title
        ok_artist = t_artist in _norm_text(c.artists[0]) if c.artists else False
        ok_dur = (c.duration_sec == 0) or (abs(c.duration_sec - t_dur) <= 2)
        # Si hay ISRC en el candidato y también en el origen, úselo como verificación fuerte
        ok_isrc = True
        if source_track.isrc and c.isrc:
            ok_isrc = source_track.isrc.upper() == c.isrc.upper()
        if ok_title and ok_artist and ok_dur and ok_isrc:
            return c
    return None


# ============== Almacenamiento (SQLite) =================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS playlist_pairs (
  name TEXT PRIMARY KEY,
  spotify_id TEXT NOT NULL,
  tidal_id   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pair_name TEXT,
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  direction TEXT,           -- 'S->T', 'T->S', 'BOTH'
  added_to_spotify INTEGER,
  added_to_tidal   INTEGER,
  removed_from_spotify INTEGER,
  removed_from_tidal   INTEGER
);
"""


class Storage:
    def __init__(self, path="sync.db"):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self):
        with self.conn:
            self.conn.executescript(SCHEMA_SQL)

    def add_pair(self, name: str, spotify_id_or_url: str, tidal_id: str):
        spid = SpotifyClient._extract_playlist_id(spotify_id_or_url)
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO playlist_pairs (name, spotify_id, tidal_id) VALUES (?,?,?)",
                (name, spid, tidal_id),
            )

    def get_pair(self, name: str) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM playlist_pairs WHERE name=?", (name,))
        return cur.fetchone()

    def list_pairs(self) -> List[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM playlist_pairs ORDER BY name")
        return cur.fetchall()

    def log_run(
        self,
        pair_name: str,
        direction: str,
        added_sp: int,
        added_td: int,
        removed_sp: int,
        removed_td: int,
    ):
        with self.conn:
            self.conn.execute(
                "INSERT INTO runs (pair_name, direction, added_to_spotify, added_to_tidal, removed_from_spotify, removed_from_tidal) VALUES (?,?,?,?,?,?)",
                (pair_name, direction, added_sp, added_td, removed_sp, removed_td),
            )


# ============== Operaciones de alto nivel =================


def transfer(
    src_name: str, dst_name: str, src_playlist: str, dst_new_name: str
) -> Tuple[int, int]:
    """Copia una playlist A -> B. Devuelve (añadidas, no_encontradas)."""
    sp = SpotifyClient()
    td = TidalClient()
    src = sp if src_name == "spotify" else td
    dst = td if dst_name == "tidal" else sp

    print(f"Cargando pistas de origen ({src_name})…")
    tracks = src.get_playlist_tracks(src_playlist)
    print(f"  {len(tracks)} pistas recuperadas.")

    added_ids: List[str] = []
    not_found: List[Track] = []

    print(f"Buscando equivalentes en destino ({dst_name}) y preparando inserción…")
    for i, t in enumerate(tracks, start=1):
        found = match_in_destination(dst, t)
        if found:
            # guarde el id apropiado del destino
            if dst_name == "spotify" and found.spotify_uri:
                added_ids.append(found.spotify_uri)
            elif dst_name == "tidal" and found.tidal_id:
                added_ids.append(found.tidal_id)
        else:
            not_found.append(t)
        if i % 25 == 0:
            print(f"  Progreso: {i}/{len(tracks)}")
        time.sleep(0.05)

    print(f"Creando playlist destino «{dst_new_name}»…")
    dst_pl_id = dst.ensure_playlist(dst_new_name)
    print("Añadiendo pistas…")
    dst.add_tracks(dst_pl_id, added_ids)

    print(f"Listo. Añadidas: {len(added_ids)} | No encontradas: {len(not_found)}")
    if not_found:
        print("Ejemplos no encontrados:")
        for t in not_found[:10]:
            print(f"  - {t.title} — {', '.join(t.artists)}")
        if len(not_found) > 10:
            print(f"  … y {len(not_found)-10} más")

    return len(added_ids), len(not_found)


def sync_pair(pair_name: str, delete_missing: bool = False) -> Dict[str, int]:
    """Sincroniza una pareja S<->T (añadir faltantes en ambos; opcionalmente eliminar sobrantes)."""
    st = Storage()
    pair = st.get_pair(pair_name)
    if not pair:
        raise SystemExit(f"No existe la pareja «{pair_name}». Use: pair add …")

    sp = SpotifyClient()
    td = TidalClient()

    print("Leyendo playlists…")
    S_tracks = sp.get_playlist_tracks(pair["spotify_id"])
    T_tracks = td.get_playlist_tracks(pair["tidal_id"])

    S_map: Dict[str, Track] = {t.key(): t for t in S_tracks}
    T_map: Dict[str, Track] = {t.key(): t for t in T_tracks}

    # Qué falta en cada lado
    missing_in_T = [S_map[k] for k in S_map.keys() - T_map.keys()]
    missing_in_S = [T_map[k] for k in T_map.keys() - S_map.keys()]

    print(
        f"Faltan en TIDAL: {len(missing_in_T)} | Faltan en Spotify: {len(missing_in_S)}"
    )

    # Resolver equivalentes y preparar IDs para añadir
    add_ids_T: List[str] = []
    for t in missing_in_T:
        found = match_in_destination(td, t)
        if found and found.tidal_id:
            add_ids_T.append(found.tidal_id)
    add_ids_S: List[str] = []
    for t in missing_in_S:
        found = match_in_destination(sp, t)
        if found and found.spotify_uri:
            add_ids_S.append(found.spotify_uri)

    # Añadir
    if add_ids_T:
        td.add_tracks(pair["tidal_id"], add_ids_T)
    if add_ids_S:
        sp.add_tracks(pair["spotify_id"], add_ids_S)

    removed_sp = removed_td = 0

    # Eliminar sobrantes si se solicita espejo estricto
    if delete_missing:
        # En S sobran las claves que están en S y no en T
        extra_in_S = [S_map[k] for k in S_map.keys() - T_map.keys()]
        # En T sobran las claves que están en T y no en S
        extra_in_T = [T_map[k] for k in T_map.keys() - S_map.keys()]

        rem_ids_S = [t.spotify_uri for t in extra_in_S if t.spotify_uri]
        rem_ids_T = [t.tidal_id for t in extra_in_T if t.tidal_id]

        if rem_ids_S:
            sp.remove_tracks(pair["spotify_id"], rem_ids_S)
            removed_sp = len(rem_ids_S)
        if rem_ids_T:
            td.remove_tracks(pair["tidal_id"], rem_ids_T)
            removed_td = len(rem_ids_T)

    st.log_run(
        pair_name, "BOTH", len(add_ids_S), len(add_ids_T), removed_sp, removed_td
    )

    print("Sincronización completada.")
    print(
        f"Añadidas en Spotify: {len(add_ids_S)} | Añadidas en TIDAL: {len(add_ids_T)}"
    )
    if delete_missing:
        print(
            f"Eliminadas en Spotify: {removed_sp} | Eliminadas en TIDAL: {removed_td}"
        )

    return {
        "added_spotify": len(add_ids_S),
        "added_tidal": len(add_ids_T),
        "removed_spotify": removed_sp,
        "removed_tidal": removed_td,
    }


# ============== CLI =================


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Sync personal Spotify <-> TIDAL")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # transfer
    p_transfer = sub.add_parser("transfer", help="Transferir playlist completa A -> B")
    p_transfer.add_argument(
        "--from", dest="src", choices=["spotify", "tidal"], required=True
    )
    p_transfer.add_argument(
        "--to", dest="dst", choices=["spotify", "tidal"], required=True
    )
    p_transfer.add_argument(
        "--playlist", required=True, help="ID/URL de la playlist origen"
    )
    p_transfer.add_argument(
        "--target-name", required=True, help="Nombre de la playlist destino a crear"
    )

    # pair
    p_pair = sub.add_parser("pair", help="Gestionar parejas (Spotify<->TIDAL)")
    pair_sub = p_pair.add_subparsers(dest="pair_cmd", required=True)
    p_pair_add = pair_sub.add_parser("add", help="Registrar/actualizar pareja")
    p_pair_add.add_argument("--name", required=True)
    p_pair_add.add_argument("--spotify", required=True, help="ID/URL playlist Spotify")
    p_pair_add.add_argument("--tidal", required=True, help="ID playlist TIDAL")
    pair_sub.add_parser("list", help="Listar parejas")

    # sync
    p_sync = sub.add_parser(
        "sync", help="Sincronizar (bidireccional) una pareja o todas"
    )
    g = p_sync.add_mutually_exclusive_group(required=True)
    g.add_argument("--pair", help="Nombre de la pareja registrada")
    g.add_argument("--all", action="store_true", help="Sincronizar todas las parejas")
    p_sync.add_argument(
        "--delete-missing",
        action="store_true",
        help="Espejo estricto: elimina también las pistas sobrantes",
    )

    args = parser.parse_args()

    if args.cmd == "transfer":
        if args.src == args.dst:
            raise SystemExit("--from y --to no pueden ser iguales.")
        added, missing = transfer(args.src, args.dst, args.playlist, args.target_name)
        print(
            f"Transferencia finalizada. Añadidas: {added} | No encontradas: {missing}"
        )
        return

    if args.cmd == "pair":
        st = Storage()
        if args.pair_cmd == "add":
            st.add_pair(args.name, args.spotify, args.tidal)
            print(f"Pareja «{args.name}» registrada.")
        elif args.pair_cmd == "list":
            rows = st.list_pairs()
            if not rows:
                print("No hay parejas registradas.")
            else:
                for r in rows:
                    print(
                        f"- {r['name']}: spotify={r['spotify_id']} | tidal={r['tidal_id']}"
                    )
        return

    if args.cmd == "sync":
        st = Storage()
        if args.all:
            rows = st.list_pairs()
            if not rows:
                print("No hay parejas registradas.")
                return
            for r in rows:
                print(f"\n== Sincronizando «{r['name']}» ==")
                sync_pair(r["name"], delete_missing=args.delete_missing)
        else:
            sync_pair(args.pair, delete_missing=args.delete_missing)
        return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
