import asyncio
import time

from scrapers.scrap_instagram import iniciar_scrapping as ig_scraper
from scrapers.scrap_facebook import iniciar_scrapping as fb_scraper
from scrapers.scrap_linkedin import iniciar_scrapping as li_scraper

async def ejecutar_scraper(nombre_red, funcion_scraper, tema, tiempo_limite_segundos, n_comentarios):
    print(f"[ORQUESTADOR] Lanzando {nombre_red} -> Límite de tiempo: {tiempo_limite_segundos} segundos, {n_comentarios} comentarios.")
    try:
        # Pasamos None como ID ya que no se registran métricas
        await funcion_scraper(tema, tiempo_limite_segundos, n_comentarios, None)
        print(f"[ORQUESTADOR] {nombre_red} completado con éxito.")
    except Exception as e:
        print(f"Error en la ejecución autónoma de {nombre_red}: {e}")


async def orquestador_principal(tema_busqueda, tiempo_limite_segundos, n_comentarios):
    print("=" * 60)
    print(f"INICIANDO EXTRACCIÓN MASIVA CONCURRENTE: TEMA '{tema_busqueda}'")
    print("=" * 60)

    tiempo_inicio_total = time.time()

    # Definimos la lista de tareas pasando los argumentos dinámicos
    tareas = [
        ejecutar_scraper("Instagram", ig_scraper, tema_busqueda, tiempo_limite_segundos, n_comentarios),
        ejecutar_scraper("Facebook", fb_scraper, tema_busqueda, tiempo_limite_segundos, n_comentarios),
        ejecutar_scraper("LinkedIn", li_scraper, tema_busqueda, tiempo_limite_segundos, n_comentarios),
    ]

    # Ejecuta todo al mismo tiempo de forma concurrente
    await asyncio.gather(*tareas)

    tiempo_fin_total = time.time()
    print("\n" + "—" * 60)
    print(f"Tiempo total de orquestación: {tiempo_fin_total - tiempo_inicio_total:.2f}s")
    print("—" * 60)

if __name__ == "__main__":
    # Prueba manual
    asyncio.run(orquestador_principal("patas", 30, 100))
