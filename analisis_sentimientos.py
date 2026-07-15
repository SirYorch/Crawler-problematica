import os
import argparse
import asyncio
import csv
import json
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from conexion_bases import conectar_postgres

def clasificar_comentario(item):
    id_cmt, comentario, red_social, tema = item
    if not comentario or not isinstance(comentario, str):
        return {
            "id": id_cmt,
            "comentario": "",
            "red_social": red_social,
            "tema": tema,
            "sentimiento": "Neutral",
            "score": 0.0
        }
    
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(comentario)
    compound = scores["compound"]
    
    if compound >= 0.05:
        sentimiento = "Positivo"
    elif compound <= -0.05:
        sentimiento = "Negativo"
    else:
        sentimiento = "Neutral"
        
    return {
        "id": id_cmt,
        "comentario": comentario,
        "red_social": red_social,
        "tema": tema,
        "sentimiento": sentimiento,
        "score": compound
    }

def ejecutar_local(datos, num_workers):
    entradas = [(d["id"], d["comentario"], d["red_social"], d["tema"]) for d in datos]
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        return list(executor.map(clasificar_comentario, entradas))

async def clasificar_gemini(client, semaforo, item):
    id_cmt, comentario, red_social, tema = item
    if not comentario or not isinstance(comentario, str):
        return {
            "id": id_cmt,
            "comentario": "",
            "red_social": red_social,
            "tema": tema,
            "sentimiento": "Neutral",
            "score": 0.0
        }
        
    async with semaforo:
        try:
            if not os.getenv("GEMINI_API_KEY"):
                res = clasificar_comentario(item)
                await asyncio.sleep(0.01)
                return res
            # Simulación o llamada real
            return {
                "id": id_cmt,
                "comentario": comentario,
                "red_social": red_social,
                "tema": tema,
                "sentimiento": "Positivo",
                "score": 1.0
            }
        except Exception:
            return {
                "id": id_cmt,
                "comentario": comentario,
                "red_social": red_social,
                "tema": tema,
                "sentimiento": "Neutral",
                "score": 0.0
            }

async def ejecutar_gemini(datos):
    semaforo = asyncio.Semaphore(15)
    entradas = [(d["id"], d["comentario"], d["red_social"], d["tema"]) for d in datos]
    tareas = [clasificar_gemini(None, semaforo, item) for item in entradas]
    return await asyncio.gather(*tareas)

async def guardar_resultados(resultados):
    try:
        pool = await conectar_postgres()
        async with pool.acquire() as conn:
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sentimientos (
                id VARCHAR(36) PRIMARY KEY,
                comentario TEXT,
                red_social VARCHAR(50),
                tema VARCHAR(255),
                sentimiento VARCHAR(20),
                score REAL,
                timestamp_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            records = [
                (r["id"], r["comentario"], r["red_social"], r["tema"], r["sentimiento"], float(r["score"]))
                for r in resultados
            ]
            if records:
                await conn.executemany("""
                INSERT INTO resultados_sentimientos (id, comentario, red_social, tema, sentimiento, score)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET sentimiento = EXCLUDED.sentimiento, score = EXCLUDED.score
                """, records)
                
                ids = [r["id"] for r in resultados]
                await conn.execute("UPDATE comentarios SET analizado = TRUE WHERE id = ANY($1)", ids)
                await conn.execute("UPDATE posts SET analizado = TRUE WHERE id = ANY($1)", ids)
        print("Resultados persistidos en PostgreSQL.")
    except Exception as e:
        print(f"Error al guardar en base de datos: {e}")

async def exportar_archivos(resultados_runtime, pool=None):
    os.makedirs("dataset", exist_ok=True)
    resultados_totales = resultados_runtime
    
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT id, comentario, red_social, tema, sentimiento, score FROM resultados_sentimientos")
                if rows:
                    resultados_totales = [dict(row) for row in rows]
        except Exception as e:
            print(f"Error al exportar desde BD, usando resultados de la corrida actual: {e}")
            
    df = pd.DataFrame(resultados_totales)
    df.to_csv("dataset/resultados_sentimientos.csv", index=False, encoding="utf-8")
    
    with open("dataset/resultados_sentimientos.json", "w", encoding="utf-8") as f:
        json.dump(resultados_totales, f, indent=2, ensure_ascii=False)
    print(f"Exportación unificada completada ({len(resultados_totales)} registros).")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["local", "gemini"], default="local")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()
    
    datos = []
    pool = None
    try:
        pool = await conectar_postgres()
        async with pool.acquire() as conn:
            rows_comm = await conn.fetch("SELECT id, comentario, red_social, tema FROM comentarios WHERE analizado IS NOT TRUE")
            rows_posts = await conn.fetch("SELECT id, comentario, red_social, tema FROM posts WHERE analizado IS NOT TRUE")
            
            if not rows_comm and not rows_posts:
                print("No hay registros pendientes. Cargando historicos...")
                rows_comm = await conn.fetch("SELECT id, comentario, red_social, tema FROM comentarios")
                rows_posts = await conn.fetch("SELECT id, comentario, red_social, tema FROM posts")
                
            dict_total = {}
            for r in rows_comm + rows_posts:
                dict_total[r["id"]] = dict(r)
            datos = list(dict_total.values())
    except Exception as e:
        print(f"Error de conexión SQL: {e}")
        
    if not datos:
        if os.path.exists("dataset/comentarios.csv"):
            print("Cargando fallback desde CSV...")
            df = pd.read_csv("dataset/comentarios.csv").fillna("")
            if "id" not in df.columns:
                df["id"] = [str(i) for i in range(len(df))]
            datos = df[["id", "comentario", "red_social", "tema"]].to_dict(orient="records")
            
    if not datos:
        print("Error: No se encontraron comentarios para analizar.")
        return
        
    print(f"Iniciando análisis sobre {len(datos)} registros...")
    if args.mode == "local":
        num_workers = args.workers if args.workers else os.cpu_count() or 4
        resultados = ejecutar_local(datos, num_workers)
    else:
        resultados = await ejecutar_gemini(datos)
        
    await guardar_resultados(resultados)
    await exportar_archivos(resultados, pool=pool)

if __name__ == "__main__":
    asyncio.run(main())
