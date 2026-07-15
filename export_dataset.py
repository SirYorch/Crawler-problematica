import asyncio
import os
import csv
import json
import datetime
import asyncpg

CONN_STR = os.getenv("POSTGRES_CONN_STR", "postgresql://postgres:postgres@localhost:5435/proyecto_web_scraping")
OUTPUT_DIR = "dataset"

def serialize_date(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} is not serializable")

async def exportar_datos():
    print("Conectando a PostgreSQL...")
    conn = await asyncpg.connect(dsn=CONN_STR)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Comentarios
    print("Exportando comentarios...")
    rows_comentarios = await conn.fetch("SELECT id, comentario, red_social, tema, analizado, timestamp FROM comentarios")
    comentarios = [dict(row) for row in rows_comentarios]
    
    csv_file_comm = os.path.join(OUTPUT_DIR, "comentarios.csv")
    with open(csv_file_comm, mode="w", newline="", encoding="utf-8") as f:
        if comentarios:
            writer = csv.DictWriter(f, fieldnames=comentarios[0].keys())
            writer.writeheader()
            writer.writerows(comentarios)
    
    json_file_comm = os.path.join(OUTPUT_DIR, "comentarios.json")
    with open(json_file_comm, mode="w", encoding="utf-8") as f:
        json.dump(comentarios, f, default=serialize_date, indent=2, ensure_ascii=False)
        
    print(f"Se exportaron {len(comentarios)} comentarios.")

    # Posts
    print("Exportando posts...")
    rows_posts = await conn.fetch("SELECT id, post, comentario, red_social, tema, analizado, timestamp FROM posts")
    posts = [dict(row) for row in rows_posts]
    
    csv_file_posts = os.path.join(OUTPUT_DIR, "posts.csv")
    with open(csv_file_posts, mode="w", newline="", encoding="utf-8") as f:
        if posts:
            writer = csv.DictWriter(f, fieldnames=posts[0].keys())
            writer.writeheader()
            writer.writerows(posts)
            
    json_file_posts = os.path.join(OUTPUT_DIR, "posts.json")
    with open(json_file_posts, mode="w", encoding="utf-8") as f:
        json.dump(posts, f, default=serialize_date, indent=2, ensure_ascii=False)
        
    print(f"Se exportaron {len(posts)} posts.")
    
    await conn.close()
    print("Exportacion completada.")

if __name__ == "__main__":
    asyncio.run(exportar_datos())
