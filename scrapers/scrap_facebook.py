import asyncio
import time
import re
import random
import os
import json
from playwright.async_api import async_playwright
from utils import limpiar_texto
from conexion_bases import guardar_comentarios, guardar_posts

SESSION_FILE = "sesiones/session_facebook.json"
BROWSER_EXECUTABLE_PATH = None

async def cargar_sesion(browser, device_settings):
    if os.path.exists(SESSION_FILE):
        print(f"[Facebook] Cargando sesión de Facebook...")
        context = await browser.new_context(storage_state=SESSION_FILE, **device_settings)
        page = await context.new_page()

        try:
            await page.goto("https://m.facebook.com/")
            await asyncio.sleep(4)

            # Si aparece el ID de login, la sesión expiró
            if await page.locator('#email').is_visible():
                print("[Facebook] La sesión de Facebook CADUCÓ. No se pueden renovar credenciales.")
                await context.close()
                raise Exception("Sesión caducada.")
            return context, page
        except Exception as e:
            await context.close()
            raise Exception(f"Sesión no válida: {e}")
    else:
        raise FileNotFoundError(f"Falta el archivo de sesión '{SESSION_FILE}'.")


async def extraer_comentarios(page, cantidad_comentarios):
    comentarios = []
    # Expresión regular para limpiar caracteres raros de Facebook (PUA)
    regex_raros = re.compile(r'[\uE000-\uF8FF]|\U000F0000-\U000FFFFF|\U00100000-\U0010FFFFF')

    # Palabras que indican que los comentarios aún no han empezado
    marcadores_inicio = ["más pertinentes", "todos los comentarios", "comentarios"]

    try:
        xpath_comentarios = "//div[@dir='auto']"
        intentos = 0
        cantidad_anterior = 0
        han_empezado_comentarios = False

        while len(comentarios) < cantidad_comentarios and intentos < 3:
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(2)

            elementos = page.locator(xpath_comentarios)
            count = await elementos.count()

            # Verificación de progreso para el bucle
            if count == cantidad_anterior:
                intentos += 1
            else:
                intentos = 0
            cantidad_anterior = count

            for i in range(count):
                raw_texto = await elementos.nth(i).inner_text()
                texto_limpio = regex_raros.sub('', raw_texto).strip()
                texto_limpio = limpiar_texto(texto_limpio.replace("\n", " "))

                if not texto_limpio:
                    continue

                if not han_empezado_comentarios:
                    if any(m in texto_limpio.lower() for m in marcadores_inicio):
                        han_empezado_comentarios = True
                    continue

                texto_lower = texto_limpio.lower()
                es_basura = any(x in texto_lower for x in [
                    "responder", "compartir",
                    "ver respuestas", "más pertinentes", "autor", "ver las",
                    "..."
                ])

                if han_empezado_comentarios and not es_basura:
                    if len(texto_limpio.split()) > 3 and texto_limpio not in comentarios:
                        comentarios.append(texto_limpio)
                        if len(comentarios) >= cantidad_comentarios:
                            break

            if len(comentarios) < cantidad_comentarios:
                print(f"[Facebook] Cargando más comentarios... ({len(comentarios)}/{cantidad_comentarios})")

    except Exception as e:
        print(f"[Facebook] Error extrayendo: {e}")

    return comentarios


async def scraping(page, tema, tiempo_limite_segundos, cantidad_comentarios, tiempo_inicio):
    print(f"[Facebook] Buscando: '{tema}'")
    comentarios_totales = []
    ids_procesados = set()

    #search_url = f"https://m.facebook.com/search/posts/?q={tema}"
    search_url = f"https://m.facebook.com/search_results/?q={tema}"
    await page.goto(search_url)
    await asyncio.sleep(5)

    intentos_scrolling = 0
    while intentos_scrolling < 3:
        if time.time() - tiempo_inicio >= tiempo_limite_segundos:
            print("[Facebook] Límite de tiempo alcanzado al buscar posts.")
            break

        # Localizar los contenedores que identificaste
        contenedores = await page.locator('div[data-tracking-duration-id]').all()
        encontrados = 0

        i = 1
        for post in contenedores:
            if time.time() - tiempo_inicio >= tiempo_limite_segundos:
                print("[Facebook] Límite de tiempo alcanzado durante el procesamiento de posts.")
                break

            post_id = await post.get_attribute("data-tracking-duration-id")
            if post_id in ids_procesados: continue

            try:
                # Buscar el disparador que mencionaste: "Toca para ver los comentarios..."
                trigger = post.locator('div[aria-label*="ver los comentarios"]')

                if await trigger.is_visible():
                    print(f"[Facebook] Abriendo post ID: {post_id}")
                    print(f"[Facebook] Procesando post: {i}/{len(contenedores)}")
                    await trigger.click()
                    await asyncio.sleep(3) # Esperar carga del post

                    url_post = page.url
                    print(f"[Facebook] Url del Post: {url_post}")

                    # Extraer comentarios usando tu función
                    coms = await extraer_comentarios(page, cantidad_comentarios)
                    #print(f"Comentarios extraidos: {coms}")
                    post_data = [url_post, coms]
                    comentarios_totales.append(post_data)
                    print(f"[Facebook] Post procesado. Acumulados: {len(comentarios_totales)} comentarios.")
                    ids_procesados.add(post_id)
                    encontrados += 1

                    # Volver a la lista de búsqueda
                    await page.go_back()
                    await asyncio.sleep(3)

                    # Re-localizar los contenedores tras volver (importante por el cambio de DOM)
                    break
            except Exception as e:
                print(f"[Facebook] Error en post {post_id}: {e}")
                ids_procesados.add(post_id)

        # Scroll en la lista de búsqueda si necesitamos más posts
        if encontrados == 0:
            if time.time() - tiempo_inicio >= tiempo_limite_segundos:
                break
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(3)
            intentos_scrolling += 1
        else:
            intentos_scrolling = 0
    return comentarios_totales


async def iniciar_scrapping(tema, tiempo_limite_segundos, n_comentarios, id):
    async with async_playwright() as p:
        # Configuramos la emulación móvil
        device = p.devices['Pixel 7']

        launch_args = {"headless": False, "args": ["--disable-notifications"]}

        tiempo_inicio = time.time()
        browser = await p.chromium.launch(**launch_args)

        # Creamos el contexto emulando el móvil
        context = await browser.new_context(**device)

        # Aquí cargarías tu sesión/cookies si ya las tienes
        context, page = await cargar_sesion(browser, device)

        print("--- [Facebook] Extrayendo comentarios ---")
        comentarios = await scraping(page, tema, tiempo_limite_segundos, n_comentarios, tiempo_inicio)

        tiempo_fin = time.time()
        tiempo_total_scraping = tiempo_fin - tiempo_inicio

        print(f"[Facebook] Cantidad de comentarios extraidos: {len(comentarios)}")
        print(f"[Facebook] Tiempo total de ejecucion: {tiempo_total_scraping:.2f}s")

        await asyncio.sleep(2)
        await browser.close()

        print("--- [Facebook] Guardando comentarios ---")
        await guardar_posts(comentarios, tema, "Facebook")
        
        comentarios_planos = [comm for _, post_comms in comentarios for comm in post_comms]
        if comentarios_planos:
            await guardar_comentarios(comentarios_planos, tema, "Facebook")

        #tiempo_inicio = time.time()
        #print("--- [Facebook] Analizando comentarios ---")
        #resultado = await procesar_sentimientos(comentarios, 20, "Facebook")
        #tiempo_fin = time.time()
        #tiempo_total_modelo = tiempo_fin - tiempo_inicio

        #print("--- [Facebook] Guardando analisis ---")
        #guardar_procesados_csv(resultado, tema, "Facebook")




if __name__ == "__main__":
    asyncio.run(iniciar_scrapping("nicolas muñoz", 30, 5, None))
