#  Documentación Explicativa de la Práctica 6
## Extracción Masiva y Concurrente de Redes Sociales

Este documento contiene el diseño de ingeniería, la justificación del paralelismo, y la descripción detallada de la problemática abordada para la **Práctica de Laboratorio 06**, cumpliendo de forma rigurosa con los criterios de evaluación especificados en la rúbrica de la materia de Computación Paralela (Universidad Politécnica Salesiana).

---

##  1. Definición Clara de la Problemática (0.7 Puntos)

*   **Tema de Investigación**:  
    *"Impacto emocional de eventos deportivos de interés común en la era digital: análisis de las reacciones públicas ante la Copa Mundial FIFA 2026, UFC y NBA/F1".*

*   **Contexto y Problema Real**:  
    Los eventos deportivos masivos de interés global desatan intensas reacciones emocionales colectivas en tiempo real. Momentos críticos como una victoria in-extremis, una decisión controvertida del VAR (en fútbol), un knock-out espectacular (en UFC) o un adelantamiento arriesgado en la última vuelta (en F1) provocan que millones de personas expresen euforia, enojo, frustración o admiración en redes sociales. 
    
    El problema central radica en **cómo capturar, rastrear y estructurar de manera rápida y eficiente este pulso emocional masivo**. Esto requiere recolectar un gran volumen de opiniones textuales públicas distribuidas en múltiples plataformas sociales al mismo tiempo, manejando la latencia de red y la estructura DOM dinámica propia de las redes sociales.

*   **Estrategia de Búsqueda**:
    Se ha diseñado una interfaz de línea de comandos (CLI) que permite configurar de manera dinámica la estrategia bajo:
    1.  **Palabras Clave y Hashtags**: Búsquedas centralizadas bajo temas unificados de interés como `#fifa`, `#copa2026`, `UFC`, `Copa Mundial`, entre otros.
    2.  **Parámetros Dinámicos**: Límite de tiempo en segundos, comentarios máximos a extraer por cada publicación encontrada, y profundidad de búsqueda en la recolección inicial.

---

##  2. Justificación de las Tres Fuentes Directas/Redes Sociales (0.6 Puntos)

Para obtener un espectro representativo y diverso de opiniones y niveles socio-afectivos, se seleccionaron estas tres fuentes digitales:

1.  **Facebook (WebLite / Mobile Framework)**:
    *   *Justificación*: Permite tomar el pulso a la demografía digital más amplia y general. Históricamente, Facebook alberga comunidades muy activas en grupos públicos de deportes tradicionales y noticias deportivas masivas. Los comentarios tienden a ser coloquiales y a extenderse con argumentos informales sobre rivalidades de selecciones nacionales y equipos de fútbol.
2.  **Instagram (Explore / Search Interface)**:
    *   *Justificación*: Su demografía es predominantemente joven, ávida del contenido micro-informativo e inmediato de organizaciones de deportes como la UFC o la F1. Los comentarios en posts oficiales de deportistas o marcas asociadas capturan el sentimiento emocional más "crudo" e impulsivo en forma de mensajes muy cortos, jergas digitales y abundantes emojis representativos del estado de ánimo inmediato.
3.  **LinkedIn (Content / Feed Search)**:
    *   *Justificación*: Aporta la perspectiva corporativa y profesional de la problemática. En lugar de reacciones viscerales de fanáticos, LinkedIn almacena opiniones y debates racionales acerca del impacto comercial de los eventos (sponsorships, inversiones multimillonarias de marcas en la Copa del Mundo, logística e impacto financiero de la UFC/F1). Con esto, el dataset adquiere un balance maduro e integral de la percepción social.

---

##  3. ESTRATEGIA DE BÚSQUEDA Y DISEÑO DE LA SOLUCIÓN (0.7 Puntos)
La solución está estructurada usando una capa de control CLI (`cli.py`), un orquestador principal asíncrono (`main.py`), scrapers modulares de Playwright por cada red social, y una base de datos relacional PostgreSQL con un pool de conexiones y exportación simplificada.

```mermaid
graph TD
    CLI[cli.py Interface] -->|Configura variables dinámicas| M[main.py Orquestador]
    M -->|Orquesta ejecución paralela| Concur[asyncio.gather]
    
    Concur -->|Task 1: Playwright Async| IG[Instagram Scraper]
    Concur -->|Task 2: Playwright Async| FB[Facebook Scraper]
    Concur -->|Task 3: Playwright Async| LI[LinkedIn Scraper]
    
    IG -->|Escritura concurrente al Pool| DB[(PostgreSQL Database)]
    FB -->|Escritura concurrente al Pool| DB
    LI -->|Escritura concurrente al Pool| DB
    
    DB -->|Ejecución de script| Export[export_dataset.py]
    Export -->|Dataset estructurado| Outputs[dataset/ CSV & JSON]
```

### Flujo de Operación:
1.  El usuario inicia `cli.py`, define el tema deportivo (ej. "fifa") y un tiempo límite de ejecución.
2.  El motor principal inicializa un pool de base de datos asíncrono PostgreSQL accesible concurrentemente.
3.  Los scrapers de Facebook, Instagram y LinkedIn se instancian concurrentemente mediante `asyncio.gather`. Cada uno abre su respectivo navegador emulado con Playwright, autentica usando cookies previas del módulo `sesiones/`, busca posts del tema, navega internamente y extrae los comentarios agregados al buffer.
4.  Llegado el límite de tiempo u objetivo de posts, se insertan los datos a las tablas relacionales garantizando persistencia inmediata.

---

##  4. IMPLEMENTACIÓN DE EXTRACCIÓN PARALELA O CONCURRENTE (1.2 Puntos)

La concurrencia es implementada directamente utilizando el framework nativo **`asyncio`** de Python a través de la función `asyncio.gather(...)`.

### Fragmento de Código de Orquestación Principal ([main.py]):
El orquestador configura la ejecución concurrente lanzando las tareas asíncronas para las tres redes al mismo tiempo:
```python
# main.py
async def orquestador_principal(tema_busqueda, tiempo_limite_segundos, n_comentarios):
    # ...
    # Definimos la lista de tareas pasando los argumentos dinámicos
    tareas = [
        ejecutar_scraper("Instagram", ig_scraper, tema_busqueda, tiempo_limite_segundos, n_comentarios),
        ejecutar_scraper("Facebook", fb_scraper, tema_busqueda, tiempo_limite_segundos, n_comentarios),
        ejecutar_scraper("LinkedIn", li_scraper, tema_busqueda, tiempo_limite_segundos, n_comentarios),
    ]

    # Ejecuta todo al mismo tiempo de forma concurrente
    await asyncio.gather(*tareas)
    # ...
```

---

##  5. USO ADECUADO Y JUSTIFICACIÓN DE LA TÉCNICA DE PARALELISMO (0.7 Puntos)

### ¿Por qué Concurrencia Asíncrona (`asyncio`) en vez de Procesos (`multiprocessing`) o Hilos (`threading`)?

*   **Identificación del cuello de botella (I/O Bound)**:  
    La extracción de datos a través de scrapers web es una tarea **limitada por la Entrada/Salida (I/O Bound)**. El programa pasa más del 95% de su tiempo esperando que el servidor web responda las peticiones HTTP, cargue el código JS pesado de las redes sociales y renderice los nodos del DOM de la página. El procesamiento matemático por parte de la CPU es mínimo.
    
*   **Decisión de Diseño y Justificación Técnica**:
    1.  **Inviabilidad de Procesos (`multiprocessing`)**: Ejecutar los tres Scrapers mediante procesos independientes asignaría copias completas del entorno de memoria Python y crearía procesos pesados a nivel de sistema operativo para manejar Chromium. Esto provocaría una sobrecarga dramática de RAM en el sistema del usuario, corriendo el riesgo de saturación y congelamiento del sistema.
    2.  **Limitación de Hilos Tradicionales (`threading`)**: Los hilos tradicionales en Python están fuertemente limitados por el **GIL (Global Interpreter Lock)** para tareas mixtas de procesamiento de strings. Además, el manejo manual de hilos aumenta la probabilidad de condiciones de carrera (Race Conditions) y sobrecarga del CPU al sincronizar la base de datos PostgreSQL.
    3.  **Ventaja Directa de `asyncio`**: Al emplear un bucle de eventos reactivo (`Event Loop`), `asyncio` permite abrir y orquestar las tres páginas de Chromium concurrentemente de forma asincrónica. Mientras un scraper espera la descarga de nuevos comentarios, cede el control del Event Loop de forma cooperativa para que el otro scraper procese comentarios en pantalla. Esto reduce la huella de memoria al mínimo y simplifica el guardado y apagado automático seguro tras el vencimiento de la alarma.

---

##  6. ALMACENAMIENTO DE LOS DATOS EXTRAÍDOS Y TRAZABILIDAD (0.5 Puntos)

El almacenamiento se realiza en una base de datos relacional local **PostgreSQL** para organizar y mantener formalmente la integridad de los datos crudos extraídos de múltiples redes de manera concurrente.

### Esquema de la Tabla (`posts`):
```sql
CREATE TABLE IF NOT EXISTS posts (
    id VARCHAR(36) PRIMARY KEY,      -- UUID Único autogenerado
    post TEXT,                      -- URL directa o ID del post
    comentario TEXT,                -- Comentario textual crudo
    red_social VARCHAR(50),         -- Marca de origen ('instagram', 'facebook', 'linkedin')
    tema VARCHAR(255),              -- Consulta/Tema clave consultado en CLI (ej. 'fifa', 'UFC')
    analizado BOOLEAN DEFAULT FALSE, -- Estado para posterior análisis de opiniones
    timestamp TIMESTAMP             -- Fecha y hora exacta de captura
);
```

### Garantía de Trazabilidad:
*   Cada registro garantiza la **trazabilidad formal** de procedencia. Si se analiza el comentario `"Excelente pelea de Holloway, histórico!"`, el registro indica explícitamente que proviene de la red social `instagram`, con tema de búsqueda `UFC`, su URL respectiva de procedencia en la columna `post`, y el sello de tiempo `timestamp` exacto del momento en que el scraper concurrente lo procesó y persistió.

---

##  7. dataset GENERADO Y INTEGRACIÓN CON EL PROYECTO FINAL (0.6 Puntos)

### Dataset Evidenciado:
El dataset actual cuenta con **1264 comentarios/registros estructurados**, exportados de manera centralizada en formatos planos listos para análisis:
*   **Formatos**: Archivos planos `.csv` y `.json` accesibles en el directorio [dataset/](file:///home/karen/Documentos/Octavo/paralela/practicas/practica6/Crawler-problematica/dataset).
*   **Comentarios**: [comentarios.csv](file:///home/karen/Documentos/Octavo/paralela/practicas/practica6/Crawler-problematica/dataset/comentarios.csv) / [comentarios.json](file:///home/karen/Documentos/Octavo/paralela/practicas/practica6/Crawler-problematica/dataset/comentarios.json)
*   **Publicaciones**: [posts.csv](file:///home/karen/Documentos/Octavo/paralela/practicas/practica6/Crawler-problematica/dataset/posts.csv) / [posts.json](file:///home/karen/Documentos/Octavo/paralela/practicas/practica6/Crawler-problematica/dataset/posts.json)

### Integración en el Proyecto Final:
Los datos recopilados e historiados asincrónicamente forman el insumo base del proyecto integrador. Este dataset de reacciones al deporte nos permitirá:
1.  **Modelado de Sentimientos**: Aplicar algoritmos de procesamiento de lenguaje natural (modelos VADER en Python o redes neuronales BERT) sobre la columna `comentario` para clasificar las expresiones afectivas como positivas, negativas o neutras.
2.  **Storytelling y Visualización**: Graficar la polaridad de reacciones emocionales según la red social (ej. contrastar la negatividad analizada en Facebook vs el tinte más profesional de LinkedIn ante patrocinios de FIFA).
3.  **Extrapolación Temporal**: Determinar momentos de picos emocionales de las competencias deportivas a nivel global en la era digital.
