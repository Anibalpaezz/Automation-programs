import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Datos Spotify
PLAYLIST_ID = "4vUdlDCQhQ8AlsLeAmmLPM"
ACCESS_TOKEN = "BQByiHzsKAvaE00tDxFaCrk2PIQ3KPn4KJPWOnx3PsC701kuIGTVy69-SKgJxQjXgml5_UuOgtXSFllv4HTOfO3BMOschEFoR2OrhecLpmPvmXfLm1TB0bxRWu5ApPHJNHV7NpbCwpY"

# Configuración Selenium
CHROMEDRIVER_PATH = r'C:\chromedriver-win64\chromedriver.exe'  # Ajusta la ruta aquí

# --- FUNCIONES SPOTIFY ---
def obtener_nombre_playlist(playlist_id, token):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['name']

def obtener_todas_las_canciones(playlist_id, token):
    canciones = []
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": 100, "offset": 0}

    while True:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        for item in data['items']:
            track = item['track']
            canciones.append({"titulo": track['name'], "artista": track['artists'][0]['name']})
        if data['next']:
            params['offset'] += params['limit']
        else:
            break

    return canciones

# --- FUNCIONES SELENIUM ---
def iniciar_navegador():
    options = Options()
    options.add_argument("--start-maximized")
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def iniciar_sesion_tidal(driver):
    driver.get("https://listen.tidal.com/login")
    time.sleep(5)
    email_input = driver.find_element(By.NAME, "email")
    password_input = driver.find_element(By.NAME, "password")
    email_input.send_keys(TIDAL_USERNAME)
    password_input.send_keys(TIDAL_PASSWORD)
    password_input.send_keys(Keys.ENTER)
    time.sleep(5)

def buscar_y_agregar_cancion(driver, titulo, artista):
    query = f"{titulo} {artista}"
    search_url = f"https://listen.tidal.com/search?q={query}"
    driver.get(search_url)
    time.sleep(3)

    try:
        primera_cancion = driver.find_element(By.XPATH, "//div[@data-test='track-item']//button")
        primera_cancion.click()
        print(f"✅ Añadida a Tidal: {titulo} - {artista}")
        time.sleep(1)
    except Exception:
        print(f"❌ No encontrada en Tidal: {titulo} - {artista}")

# --- PROGRAMA PRINCIPAL ---
def main():
    # 1. Obtener datos desde Spotify
    nombre_playlist = obtener_nombre_playlist(PLAYLIST_ID, ACCESS_TOKEN)
    canciones = obtener_todas_las_canciones(PLAYLIST_ID, ACCESS_TOKEN)
    print(f"Playlist Spotify: '{nombre_playlist}' con {len(canciones)} canciones obtenidas.")

    # 2. Lanzar navegador y login en Tidal
    driver = iniciar_navegador()
    iniciar_sesion_tidal(driver)

    # 3. Agregar canciones
    for cancion in canciones:
        buscar_y_agregar_cancion(driver, cancion['titulo'], cancion['artista'])

    print("✅ Proceso terminado.")
    driver.quit()

if __name__ == "__main__":
    main()
