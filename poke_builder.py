#!/usr/bin/env python3
"""
=============================================================================
Ecos de Sincronía - PokéAPI Data Builder
=============================================================================
Este script extrae la información canónica de los Pokémon desde el #1 al #649
(Generaciones 1 a 5: Kanto, Johto, Hoenn, Sinnoh y Teselia/Unova) desde la
PokéAPI y descarga los sprites frontales y traseros optimizados para Godot 3.6.

Salida:
- Base de datos: EcosDeSincronia/data/database/pokemon_db.json
- Sprites:       EcosDeSincronia/assets/sprites/pokemon/{id}_front.png
                 EcosDeSincronia/assets/sprites/pokemon/{id}_back.png
=============================================================================
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuración principal
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "EcosDeSincronia")
DB_OUTPUT_PATH = os.path.join(PROJECT_DIR, "data", "database", "pokemon_db.json")
SPRITES_OUTPUT_DIR = os.path.join(PROJECT_DIR, "assets", "sprites", "pokemon")

START_ID = 1
END_ID = 649
CONCURRENT_WORKERS = 16
MAX_RETRIES = 5
DOWNLOAD_SPRITES = True

USER_AGENT = "EcosDeSincronia-Builder/1.0 (Godot 3.6 Geolocation RPG)"

def get_generation(pokemon_id: int) -> int:
    """Determina la generación canónica según el ID nacional (1 a 5)."""
    if pokemon_id <= 151:
        return 1  # Kanto
    elif pokemon_id <= 251:
        return 2  # Johto
    elif pokemon_id <= 386:
        return 3  # Hoenn
    elif pokemon_id <= 493:
        return 4  # Sinnoh
    elif pokemon_id <= 649:
        return 5  # Teselia / Unova
    return 6

def fetch_json_with_retry(url: str, retries: int = MAX_RETRIES) -> dict:
    """Descarga y parsea un endpoint JSON con reintentos exponenciales."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status == 200:
                    raw_data = response.read().decode("utf-8")
                    return json.loads(raw_data)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as err:
            if attempt == retries:
                raise RuntimeError(f"Fallo definitivo al descargar {url}: {err}")
            time.sleep(0.5 * attempt)
    return {}

def download_file_with_retry(url: str, destination_path: str, retries: int = 3) -> bool:
    """Descarga un archivo binario (sprite) y lo almacena localmente."""
    if not url:
        return False
    if os.path.exists(destination_path) and os.path.getsize(destination_path) > 0:
        return True

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    with open(destination_path, "wb") as f:
                        f.write(response.read())
                    return True
        except Exception:
            if attempt == retries:
                return False
            time.sleep(0.3 * attempt)
    return False

def process_single_pokemon(pokemon_id: int) -> dict:
    """Descarga la data de un Pokémon y sus sprites locales."""
    api_url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    raw = fetch_json_with_retry(api_url)

    # Nombres y tipos
    name_clean = raw.get("name", "").capitalize()
    types_list = [
        t["type"]["name"].capitalize()
        for t in sorted(raw.get("types", []), key=lambda x: x["slot"])
    ]

    # Estadísticas base
    stats_dict = {}
    stat_name_mapping = {
        "hp": "hp",
        "attack": "attack",
        "defense": "defense",
        "special-attack": "special_attack",
        "special-defense": "special_defense",
        "speed": "speed"
    }

    total_stats = 0
    for s in raw.get("stats", []):
        raw_stat_name = s["stat"]["name"]
        clean_name = stat_name_mapping.get(raw_stat_name, raw_stat_name.replace("-", "_"))
        base_val = s["base_stat"]
        stats_dict[clean_name] = base_val
        total_stats += base_val
    stats_dict["total"] = total_stats

    # Rutas relativas de Godot y URLs
    front_filename = f"{pokemon_id}_front.png"
    back_filename = f"{pokemon_id}_back.png"

    front_local_res = f"res://assets/sprites/pokemon/{front_filename}"
    back_local_res = f"res://assets/sprites/pokemon/{back_filename}"

    front_disk_path = os.path.join(SPRITES_OUTPUT_DIR, front_filename)
    back_disk_path = os.path.join(SPRITES_OUTPUT_DIR, back_filename)

    # URLs de sprites (PokéAPI standard)
    sprites_obj = raw.get("sprites", {})
    front_url = sprites_obj.get("front_default") or f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
    back_url = sprites_obj.get("back_default") or f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/{pokemon_id}.png"

    # Descarga opcional de imágenes
    if DOWNLOAD_SPRITES:
        if front_url:
            download_file_with_retry(front_url, front_disk_path)
        if back_url:
            download_file_with_retry(back_url, back_disk_path)

    # Estructura del registro
    record = {
        "id": pokemon_id,
        "name": name_clean,
        "slug": raw.get("name", ""),
        "generation": get_generation(pokemon_id),
        "types": types_list,
        "base_stats": stats_dict,
        "height_m": round(raw.get("height", 0) * 0.1, 2),
        "weight_kg": round(raw.get("weight", 0) * 0.1, 2),
        "base_experience": raw.get("base_experience", 0),
        "sprites": {
            "front": front_local_res,
            "back": back_local_res,
            "front_url": front_url,
            "back_url": back_url
        }
    }
    return record

def main():
    print("=" * 70)
    print("ECOS DE SINCRONÍA - GENERADOR DE BASE DE DATOS Y SPRITES")
    print(f"Rango objetivo: #{START_ID} a #{END_ID} (Gen I a Gen V)")
    print(f"Directorio de destino BD: {DB_OUTPUT_PATH}")
    print(f"Directorio de sprites:    {SPRITES_OUTPUT_DIR}")
    print(f"Hilos concurrentes:       {CONCURRENT_WORKERS}")
    print("=" * 70)

    os.makedirs(os.path.dirname(DB_OUTPUT_PATH), exist_ok=True)
    os.makedirs(SPRITES_OUTPUT_DIR, exist_ok=True)

    start_time = time.time()
    pokemon_database = {}
    completed_count = 0

    pokemon_ids = list(range(START_ID, END_ID + 1))

    with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
        future_to_id = {
            executor.submit(process_single_pokemon, pid): pid
            for pid in pokemon_ids
        }

        for future in as_completed(future_to_id):
            pid = future_to_id[future]
            try:
                data = future.result()
                pokemon_database[str(pid)] = data
                completed_count += 1
                if completed_count % 50 == 0 or completed_count == len(pokemon_ids):
                    elapsed = time.time() - start_time
                    speed = completed_count / elapsed if elapsed > 0 else 0
                    print(f"[{completed_count:3d}/{len(pokemon_ids)}] Procesados... ({speed:.1f} Pokémon/s)")
            except Exception as exc:
                print(f"[ERROR] No se pudo procesar #{pid}: {exc}", file=sys.stderr)

    # Ordenar las claves por ID numérico
    sorted_database = {
        str(i): pokemon_database[str(i)]
        for i in range(START_ID, END_ID + 1)
        if str(i) in pokemon_database
    }

    final_payload = {
        "metadata": {
            "project": "Ecos de Sincronia",
            "version": "1.0.0",
            "generations": "I - V (Kanto, Johto, Hoenn, Sinnoh, Teselia)",
            "total_count": len(sorted_database),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "pokemon": sorted_database
    }

    # Guardar en data/database/pokemon_db.json
    with open(DB_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2, ensure_ascii=False)

    total_time = time.time() - start_time
    file_size_kb = os.path.getsize(DB_OUTPUT_PATH) / 1024

    print("=" * 70)
    print(f"PROCESO COMPLETADO CON ÉXITO")
    print(f"Total Pokémon registrados: {len(sorted_database)} / {END_ID}")
    print(f"Archivo JSON generado:     {DB_OUTPUT_PATH} ({file_size_kb:.2f} KB)")
    print(f"Tiempo total invertido:    {total_time:.2f} segundos")
    print("=" * 70)

if __name__ == "__main__":
    main()
