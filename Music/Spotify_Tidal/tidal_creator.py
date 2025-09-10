import tidalapi
import time

# Iniciar sesión manual
sesion = tidalapi.Session()
sesion.login('TU_USUARIO', 'TU_CONTRASEÑA')  # Puedes usar login_oauth_simple() si quieres evitar contraseña

# Obtener el objeto de usuario
usuario = tidalapi.User(sesion, sesion.user.id)

# Crear una nueva playlist (opcional)
nueva_playlist = usuario.create_playlist('Importada de Spotify', 'Migrada automáticamente desde Spotify')
tidal_playlist_id = nueva_playlist.id

def buscar_y_agregar_a_playlist(tidal_playlist_id, canciones):
    for c in canciones:
        busqueda = f"{c['titulo']} {c['artista']}"
        resultados = sesion.search(busqueda)
        if resultados.tracks:
            track_id = resultados.tracks[0].id
            sesion.playlist_add_tracks(tidal_playlist_id, [track_id])
            print(f"✔️ Añadido: {c['titulo']} - {c['artista']}")
        else:
            print(f"❌ No encontrado: {c['titulo']} - {c['artista']}")
        time.sleep(0.5)  # Evitar rate limit

# Ejemplo de uso (usar los datos del script anterior)
buscar_y_agregar_a_playlist(tidal_playlist_id, canciones)
