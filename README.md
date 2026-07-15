# Extractor Concurrente de Redes Sociales (Mass Data Extraction)

Este proyecto es una plataforma diseñada para la extracción masiva y concurrente de comentarios públicos y publicaciones desde redes sociales (**Instagram**, **Facebook** y **LinkedIn**) utilizando **Playwright** y **PostgreSQL**.

---

##  Tecnologías y Arquitectura

El sistema está estructurado de la siguiente forma:
1. **Scrapers Automatizados (Playwright & Python)**: Orquestador concurrente que maneja múltiples bots asíncronos para simular interacciones reales de usuario y recolectar publicaciones y comentarios.
2. **Capa de Concurrencia**: Utiliza `asyncio` para lanzar los scrapers simultáneamente, acelerando sustancialmente el proceso de recolección.
3. **Persistencia (PostgreSQL)**: Base de datos relacional para estructurar las publicaciones y comentarios extraídos en crudo.

---

##  Requisitos e Instalación

### 1. Levantar PostgreSQL (Docker)

El proyecto incluye un archivo `docker-compose.yml` simplificado que levanta un contenedor de **PostgreSQL** en el puerto `5435`.

```bash
docker-compose up -d
```

### 2. Instalar Dependencias de Python

Instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

### 3. Instalar Binarios de Playwright

Descarga Chromium para Playwright:

```bash
playwright install chromium
```

---

##  Gestión de Sesiones (Autenticación)

El sistema funciona **exclusivamente a través de las cookies de sesión guardadas en la carpeta `sesiones/`**:

- `sesiones/session_instagram.json`
- `sesiones/session_facebook.json`
- `sesiones/session_linkedin.json`

Si una sesión caduca o no existe, el scraper correspondiente imprimirá un mensaje explicativo y finalizará limpiamente para que la ejecución general no se detenga. Para actualizar las sesiones, exporta las cookies desde tu navegador autenticado en formato Playwright storage-state y colócalas en dicho directorio.

---

##  Ejecución del Proyecto (Interfaz CLI)

Para ejecutar una búsqueda interactiva y definir el tema y un tiempo límite de ejecución:

```bash
python cli.py
```

*El script te solicitará:*
- El **tema a investigar** (ej. "Elecciones 2025").
- El **tiempo límite de ejecución en minutos** (tras el cual las tareas se cancelarán de forma segura y se guardarán los resultados obtenidos).
- Parámetros opcionales de cantidad de posts y comentarios.

---

##  Extracción Manual de Datos (Queries SQL)

Puedes conectarte directamente al contenedor de PostgreSQL para extraer y consultar manualmente la información recolectada:

### Conectarse a PostgreSQL mediante consola:
```bash
docker exec -it scraping_postgres psql -U postgres -d proyecto_web_scraping
```

### Consultas útiles (SQL):

1. **Obtener el total de comentarios en bruto por red social**:
   ```sql
   SELECT red_social, COUNT(*) as total_comentarios 
   FROM posts 
   GROUP BY red_social;
   ```

2. **Ver publicaciones y comentarios para un tema de interés**:
   ```sql
   SELECT post, comentario 
   FROM posts 
   WHERE tema ILIKE '%Zamora%'
   LIMIT 10;
   ```

3. **Buscar comentarios que contengan palabras específicas**:
   ```sql
   SELECT red_social, comentario 
   FROM comentarios
   WHERE comentario ILIKE '%obra%' OR comentario ILIKE '%alcalde%';
   ```
