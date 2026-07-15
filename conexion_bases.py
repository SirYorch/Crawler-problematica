import datetime
import asyncio
import uuid
import os
import asyncpg

# PostgreSQL client configuration
db_pool = None
pool_loop = None

async def conectar_postgres():
    global db_pool, pool_loop
    current_loop = asyncio.get_running_loop()
    if db_pool is None or pool_loop != current_loop:
        if db_pool is not None:
            await db_pool.close()
        print("--- [PostgreSQL] Creando nuevo pool para el loop actual ---")
        conn_str = os.getenv("POSTGRES_CONN_STR", "postgresql://postgres:postgres@localhost:5435/proyecto_web_scraping")
        db_pool = await asyncpg.create_pool(dsn=conn_str)
        pool_loop = current_loop
        # Crear tablas si no existen
        await crear_tablas(db_pool)
    return db_pool

async def crear_tablas(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS comentarios (
            id VARCHAR(36) PRIMARY KEY,
            comentario TEXT,
            red_social VARCHAR(50),
            tema VARCHAR(255),
            analizado BOOLEAN DEFAULT FALSE,
            timestamp TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS posts (
            id VARCHAR(36) PRIMARY KEY,
            post TEXT,
            comentario TEXT,
            red_social VARCHAR(50),
            tema VARCHAR(255),
            analizado BOOLEAN DEFAULT FALSE,
            timestamp TIMESTAMP
        );
        """)


async def guardar_comentarios(comentarios, tema, red_social):
    pool = await conectar_postgres()
    async with pool.acquire() as conn:
        records = []
        for comentario in comentarios:
            shared_id = str(uuid.uuid4())
            records.append((
                shared_id,
                comentario,
                red_social.lower(),
                tema,
                False,
                datetime.datetime.now()
            ))
        if records:
            await conn.executemany(
                """
                INSERT INTO comentarios (id, comentario, red_social, tema, analizado, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
                """,
                records
            )


async def guardar_posts(posts, tema, red_social):
    pool = await conectar_postgres()
    async with pool.acquire() as conn:
        records = []
        for post, comentarios in posts:
            for comentario in comentarios:
                shared_id = str(uuid.uuid4())
                records.append((
                    shared_id,
                    post,
                    comentario,
                    red_social.lower(),
                    tema,
                    False,
                    datetime.datetime.now()
                ))
        if records:
            await conn.executemany(
                """
                INSERT INTO posts (id, post, comentario, red_social, tema, analizado, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                records
            )


async def leer_comentarios(red_social):
    pool = await conectar_postgres()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT comentario FROM comentarios WHERE red_social = $1 AND analizado IS NOT TRUE",
            red_social.lower()
        )
        return [{"comentario": row["comentario"]} for row in rows]


async def leer_comentarios_tema(red_social, tema):
    pool = await conectar_postgres()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT comentario FROM comentarios WHERE red_social = $1 AND tema = $2 AND analizado IS NOT TRUE",
            red_social.lower(), tema
        )
        return [{"comentario": row["comentario"]} for row in rows]


async def leer_comentarios_post_tema(red_social, tema):
    pool = await conectar_postgres()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT post, comentario FROM posts WHERE red_social = $1 AND tema = $2 AND analizado IS NOT TRUE",
            red_social.lower(), tema
        )
        return [{"post": row["post"], "comentario": row["comentario"]} for row in rows]
