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
            
        # 2. Tiempo de ejecución límite
        tiempo_raw = input("⏱️ Ingrese el tiempo límite de ejecución en minutos [default: 5.0]: ").strip()
        if not tiempo_raw:
            tiempo_minutos = 5.0
        else:
            try:
                tiempo_minutos = float(tiempo_raw)
            except ValueError:
                print("❌ El tiempo debe ser un número decimal válido.")
                return
                
        # 3. Parámetros opcionales adicionales
        n_posts_raw = input("📮 Ingrese cantidad de posts por red social [default: 3]: ").strip()
        n_posts = int(n_posts_raw) if n_posts_raw else 3
        
        n_comentarios_raw = input("💬 Ingrese comentarios por post [default: 10]: ").strip()
        n_comentarios = int(n_comentarios_raw) if n_comentarios_raw else 10
        
    except (KeyboardInterrupt, EOFError):
        print("\n👋 Ejecución cancelada por el usuario.")
        return

    tiempo_segundos = tiempo_minutos * 60
    
    print("\n" + "-" * 50)
    print(f"Iniciando extracción para: '{tema}'")
    print(f"Parámetros: {n_posts} posts, {n_comentarios} comentarios")
    print(f"Tiempo máximo de ejecución: {tiempo_minutos} minutos ({tiempo_segundos} segundos)")
    print("-" * 50 + "\n")
    
    inicio_time = time.time()
    try:
        # Envolver la ejecución concurrente en un límite de tiempo
        await asyncio.wait_for(
            orquestador_principal(tema, n_posts, n_comentarios),
            timeout=tiempo_segundos
        )
        print("\n✅ Proceso de extracción completado exitosamente dentro del tiempo límite.")
    except asyncio.TimeoutError:
        print(f"\n⚠️ [Límite de Tiempo Alcanzado] Se cumplió el tiempo límite de {tiempo_minutos} minutos.")
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
