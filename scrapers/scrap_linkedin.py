import asyncio
import time
import random
import os
import json
import re
from playwright.async_api import async_playwright
from utils import limpiar_texto
from conexion_bases import guardar_comentarios, guardar_posts

# --- CONFIGURACIÓN ---
SESSION_FILE = "sesiones/session_linkedin.json"
BROWSER_EXECUTABLE_PATH = None


async def obtener_clipboard_pegando(page):
    try:
        # 1. Inyectar un textarea invisible en el DOM
        await page.evaluate("""() => {
            const input = document.createElement('textarea');
            input.id = 'clipboard_test_area';
            input.style.position = 'fixed';
            input.style.left = '-9999px';
            document.body.appendChild(input);
            input.focus();
        }""")

        # 2. Simular el comando de pegado (Linux/Windows usa Control+V)
        # Nota: Si estuvieras en Mac sería 'Meta+V', pero usas Artix Linux.
        await page.keyboard.press("Control+V")
        await asyncio.sleep(0.5)  # Espera a que el navegador procese el pegado

        # 3. Leer el valor del textarea
        contenido = await page.evaluate("document.getElementById('clipboard_test_area').value")

        # 4. Limpiar el DOM (Borrar el textarea)
        await page.evaluate("document.getElementById('clipboard_test_area').remove()")

        return contenido

    except Exception as e:
        print(f"[LinkedIn] Error al intentar pegar: {e}")
        return ""


async def obtener_contexto_linkedin(browser):
    if os.path.exists(SESSION_FILE):
        print(f"[LinkedIn] Detectado '{SESSION_FILE}'. Cargando sesión existente...")
        context = await browser.new_context(
            storage_state=SESSION_FILE,
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = await context.new_page()

        try:
            await page.goto("https://www.linkedin.com/feed/", wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Si nos redirige al login o vemos el botón de "Unirse", la cookie murió
            if "login" in page.url or await page.locator('.nav__button-secondary').is_visible():
                print("[LinkedIn] La sesión de LinkedIn CADUCÓ. No se pueden renovar credenciales.")
                await context.close()
                raise Exception("Sesión caducada.")

            return context, page
        except Exception as e:
            await context.close()
            raise Exception(f"Sesión no válida: {e}")
    else:
        raise FileNotFoundError(f"Falta el archivo de sesión '{SESSION_FILE}'.")



async def extraer_comentarios_post(page, cantidad_objetivo):
    """Extrae comentarios entrando al detalle del post"""
    comentarios = []
    try:
        # Esperamos carga del post
        await page.wait_for_selector('div.feed-shared-update-v2', timeout=15000)
        await page.mouse.wheel(0, 2000)
        await asyncio.sleep(2)

        # XPath quirúrgico para comentarios y contenido
        xpath_filtro = (
            "//div[contains(@class, 'comments-comment-list__container')]"
            "//span[@dir='ltr' "
            "and not(ancestor::a) "
            "and not(ancestor::button) "
            "and not(ancestor::h3)]"
        )

        locator = page.locator(f"xpath={xpath_filtro}")

        # Intentar cargar más comentarios
        try:
            btn_mas = page.locator(
                "button.comments-comments-list__load-more-comments-button")
            if await btn_mas.is_visible():
                await btn_mas.click()
                await asyncio.sleep(2)
        except:
            pass

        textos = await locator.all_inner_texts()

        for txt in textos:
            t_limpio = limpiar_texto(txt.replace("\n", " ").strip())
            if len(t_limpio.split()) > 2 and "ver traducción" not in t_limpio.lower():
                if t_limpio not in comentarios:
                    comentarios.append(t_limpio)
                    # print(f"Comentarios: {comentarios}")
            if len(comentarios) >= cantidad_objetivo:
                break

    except Exception as e:
        print(f"[LinkedIn] Error en post individual: {e}")

    return comentarios


async def tarea_scraping(page, tema, tiempo_limite_segundos, cantidad_comentarios, tiempo_inicio):
    print(f"[LinkedIn] BUSCANDO EN LINKEDIN: '{tema}'")
    comentarios_totales = []
    try:
        # 1. Búsqueda (codificamos el hashtag correctamente como %23 para evitar redirección vacía)
        url_busqueda = f"https://www.linkedin.com/search/results/content/?keywords=%23{tema}&origin=GLOBAL_SEARCH_HEADER&sortBy=[%22relevance%22]&datePosted=[%22past-month%22]"
        await page.goto(url_busqueda, wait_until='domcontentloaded')

        # Esperamos al contenedor de resultados
        try:
            await page.wait_for_selector('div.search-results-container, button[aria-label*="control" i], div[role="listitem"]', timeout=20000)
        except Exception:
            print("[LinkedIn] Advertencia: Selector principal no encontrado, intentando continuar...")

        urls_recolectadas = set()

        # Scroll inicial
        for _ in range(3):
            if time.time() - tiempo_inicio >= tiempo_limite_segundos:
                break
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(2)

        # 2. Recolección de Links vía Menú
        # Buscamos los botones de 'tres puntos' (independiente de clases ofuscadas)
        botones = page.locator('button[aria-label*="control menu" i], button[aria-label*="menú de controles" i], button[aria-label*="controles" i]')
        count = await botones.count()
        print(f"[LinkedIn] Analizando {count} publicaciones...")

        for i in range(count):
            # Límite de búsqueda: 30% del tiempo total o mínimo 10 segundos para buscar
            tiempo_busqueda_transcurrido = time.time() - tiempo_inicio
            max_tiempo_busqueda = max(10.0, tiempo_limite_segundos * 0.3)
            if tiempo_busqueda_transcurrido >= max_tiempo_busqueda:
                print("[LinkedIn] Se alcanzó el límite de tiempo asignado para la búsqueda de posts.")
                break

            # Evitar recolectar demasiados posts en ejecuciones cortas
            if len(urls_recolectadas) >= 10:
                break

            try:
                btn = botones.nth(i)
                await btn.scroll_into_view_if_needed()

                if await btn.is_visible():
                    await btn.click()  # 1. Clic en los 3 puntos
                    await asyncio.sleep(2)

                    # 2. Buscar opción "Copiar enlace" (soportando divs de menú modernos y li)
                    opcion_copiar = page.locator('div[role="menuitem"], li, button').filter(
                        has_text=re.compile(
                            r"Copy link|Copiar enlace", re.IGNORECASE)
                    )

                    if await opcion_copiar.count() > 0:
                        # Hover para activar estilos visuales
                        await opcion_copiar.first.hover()
                        await asyncio.sleep(0.3)

                        # Click forzado
                        await opcion_copiar.first.click(force=True)

                        # --- VERIFICACIÓN CON PEGADO SIMULADO ---
                        # Espera crítica para el copiado
                        await asyncio.sleep(1.5)

                        link_pegado = await obtener_clipboard_pegando(page)
                        # print(f"[LinkedIn] [Prueba Ctrl+V]: '{link_pegado}'")

                        if "linkedin.com" in link_pegado:
                            if link_pegado not in urls_recolectadas:
                                urls_recolectadas.add(link_pegado)
                                print(f"[LinkedIn] URL capturada: {link_pegado}")
                            else:
                                print(f"[LinkedIn] Duplicada.")

                        # Cerrar menú (Vital)
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.5)
                    else:
                        print("[LinkedIn] Opción 'Copiar' no visible en este menú.")
                        await page.keyboard.press("Escape")

            except Exception as e:
                print(f"[LinkedIn] Error procesando botón: {e}")
                await page.keyboard.press("Escape")
                pass

        lista_urls = list(urls_recolectadas)
        print(f"[LinkedIn] Total posts válidos: {len(lista_urls)}")

        # 3. Visita y Extracción
        i = 1
        for url in lista_urls:
            if time.time() - tiempo_inicio >= tiempo_limite_segundos:
                print("[LinkedIn] Límite de tiempo alcanzado durante el procesamiento de posts.")
                break

            print(f"[LinkedIn] Procesando post: {url}, post {i}/{len(lista_urls)}")
            try:
                i += 1
                await page.goto(url)
                await asyncio.sleep(random.uniform(3, 5))
                nuevos = await extraer_comentarios_post(page, cantidad_comentarios)
                post = [url, nuevos]
                print(f"[LinkedIn] Comentarios extraidos del post: {len(nuevos)}")
                comentarios_totales.append(post)
            except Exception as e:
                print(f"[LinkedIn] Error navegando: {e}")

    except Exception as e:
        print(f"[LinkedIn] Error crítico LinkedIn: {e}")

    return comentarios_totales


# --- ENTRADA PARA ORQUESTADOR ---
async def iniciar_scrapping(tema, tiempo_limite_segundos, cantidad_comentarios, id):
    async with async_playwright() as p:
        launch_args = {"headless": False, "args": ["--disable-notifications"]}
        if BROWSER_EXECUTABLE_PATH:
            launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH

        tiempo_inicio = time.time()

        browser = await p.chromium.launch(**launch_args)
        context, page = await obtener_contexto_linkedin(browser)



        print("--- [LinkedIn] Extrayendo comentarios ---")
        comentarios = await tarea_scraping(page, tema, tiempo_limite_segundos, cantidad_comentarios, tiempo_inicio)

        tiempo_fin = time.time()
        tiempo_total_scraping = tiempo_fin - tiempo_inicio

        print(f"[LinkedIn] Cantidad de comentarios extraidos: {len(comentarios)}")
        print(f"[LinkedIn] Tiempo total de ejecucion: {tiempo_total_scraping:.2f}s")

        await asyncio.sleep(2)
        await browser.close()

        print("--- [LinkedIn] Guardando comentarios ---")
        await guardar_posts(comentarios, tema, "LinkedIn")
        
        comentarios_planos = [comm for _, post_comms in comentarios for comm in post_comms]
        if comentarios_planos:
            await guardar_comentarios(comentarios_planos, tema, "LinkedIn")

        #tiempo_inicio = time.time()
        #print("--- [LinkedIn] Analizando comentarios ---")
        #resultado = await procesar_sentimientos(comentarios, 20, "LinkedIn")
        #tiempo_fin = time.time()
        #tiempo_total_modelo = tiempo_fin - tiempo_inicio

        #print("--- [LinkedIn] Guardando analisis ---")
        #guardar_procesados_csv(resultado, tema, "LinkedIn")



if __name__ == "__main__":
    asyncio.run(iniciar_scrapping("venezuela", 30, 10, None))
