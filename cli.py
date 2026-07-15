import asyncio
import sys
import time

from main import orquestador_principal

async def main():
    print("=" * 60)
    print("      📊 DASHBOARD SOCIAL ANALYTICS - CLI INTERFACE 📊      ")
    print("=" * 60)
    
    # 1. Tema a investigar
    try:
        tema = input("🔍 Ingrese el tema a investigar: ").strip()
        if not tema:
            print("❌ El tema a investigar no puede estar vacío.")
            return
            
        # 2. Tiempo de ejecución límite (minutos y segundos)
        minutos_raw = input("⏱️ Ingrese el tiempo límite de ejecución en minutos [default: 0]: ").strip()
        minutos = float(minutos_raw) if minutos_raw else 0.0

        segundos_raw = input("⏱️ Ingrese el tiempo límite de ejecución en segundos [default: 30]: ").strip()
        segundos = float(segundos_raw) if segundos_raw else 30.0
        
        tiempo_segundos = (minutos * 60) + segundos
        if tiempo_segundos <= 0:
            tiempo_segundos = 30.0
            
        n_comentarios_raw = input("💬 Ingrese comentarios por post [default: 10]: ").strip()
        n_comentarios = int(n_comentarios_raw) if n_comentarios_raw else 10
        
    except (KeyboardInterrupt, EOFError):
        print("\n👋 Ejecución cancelada por el usuario.")
        return

    print("\n" + "-" * 50)
    print(f"Iniciando extracción para: '{tema}'")
    print(f"Parámetros: {n_comentarios} comentarios por post")
    print(f"Tiempo máximo de ejecución: {tiempo_segundos} segundos")
    print("-" * 50 + "\n")
    
    inicio_time = time.time()
    try:
        # Envolver la ejecución concurrente en un límite de tiempo con un buffer de seguridad
        await asyncio.wait_for(
            orquestador_principal(tema, tiempo_segundos, n_comentarios),
            timeout=tiempo_segundos + 15
        )
        print("\n✅ Proceso de extracción completado exitosamente dentro del tiempo límite.")
    except asyncio.TimeoutError:
        print(f"\n⚠️ [Límite de Tiempo Alcanzado] Se cumplió el tiempo límite de {tiempo_segundos} segundos (más buffer).")
        print("La extracción se interrumpió de manera segura y los datos recolectados hasta el momento han sido guardados en PostgreSQL.")
    except Exception as e:
        print(f"\n❌ Se produjo un error durante la extracción: {e}")
        
    fin_time = time.time()
    print(f"⏱️ Tiempo total transcurrido: {fin_time - inicio_time:.2f}s")
    print("\nℹ️ Puedes consultar los datos recolectados directamente en PostgreSQL (tablas 'posts' y 'comentarios').")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Ejecución interrumpida por teclado.")
