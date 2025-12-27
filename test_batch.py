
import json
from ocr_service import batch_extract_from_data_folder

if __name__ == "__main__":
    results = batch_extract_from_data_folder("data")
    total = len(results)
    errors = [r for r in results if 'error' in r]
    ok = [r for r in results if 'raw_text' in r]
    # Guardar resultados en archivo
    with open("results_batch.txt", "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"Archivo: {r['filename']}\n")
            if 'error' in r:
                f.write("Error: " + r['error'] + "\n")
            else:
                # Guardar el JSON extendido
                f.write(json.dumps(r, ensure_ascii=False, indent=2) + "\n")
            f.write("="*40 + "\n")
    # Mostrar resumen en consola
    print(f"\nBatch finalizado. Total archivos: {total}")
    print(f"Exitosos: {len(ok)} | Errores: {len(errors)}")
    if errors:
        print("Archivos con error:")
        for r in errors:
            print(f"- {r['filename']}: {r['error']}")
    else:
        print("Todos los archivos procesados correctamente.")
