import os
import shutil

UPLOAD_FOLDER = r"C:\projects\brotes_app\app\static\uploads"  # Ajusta a tu ruta real

def migrar():
    origen_base = UPLOAD_FOLDER
    destino_base = os.path.join(UPLOAD_FOLDER, "2025")
    os.makedirs(destino_base, exist_ok=True)

    for nombre in os.listdir(origen_base):
        if not nombre.startswith("brote_"):
            continue

        origen = os.path.join(origen_base, nombre)
        if not os.path.isdir(origen):
            continue

        destino = os.path.join(destino_base, nombre)

        # Si ya migraste, no lo vuelvas a mover
        if os.path.exists(destino):
            print(f"[SKIP] Ya existe: {destino}")
            continue

        print(f"[MOVE] {origen} -> {destino}")
        shutil.move(origen, destino)

if __name__ == "__main__":
    migrar()
    print("Migración de carpetas 2025 terminada.")
