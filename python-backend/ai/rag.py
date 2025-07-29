from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel
import pyodbc
import re
from typing import List, Tuple
import logging
from vanna.ollama import Ollama
from vanna.chromadb import ChromaDB_VectorStore
import time
from functools import lru_cache
import httpx
import requests
import threading
import traceback
from typing import List

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("vanna").setLevel(logging.WARNING)
logging.getLogger("ollama").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.ERROR)

app = FastAPI(title="Custom RAG API", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB config
DB_CONFIG = {
    "DRIVER": "{ODBC Driver 17 for SQL Server}",
    "SERVER": "4.247.166.77",
    "DATABASE": "ABICRM",
    "UID": "rajeshc",
    "PWD": "Admin@123$"
}

def get_connection():
    try:
        conn_str = ";".join([f"{k}={v}" for k, v in DB_CONFIG.items()])
        return pyodbc.connect(conn_str)
    except Exception as e:
        logger.error("Database connection failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Database connection error")

# Vanna setup
class MyVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)

vn = MyVanna(config={
    'model': 'gemma3:12b',
    'host': 'localhost',
    'port': 11434,
    'n_results': 3,
    'chroma_path': './chroma_db'
})
vn.connect_to_mssql(odbc_conn_str=";".join([f"{k}={v}" for k, v in DB_CONFIG.items()]))

class UserPrompt(BaseModel):
    prompt: str
    train: bool = False
    
    
class VisionPrompt(BaseModel):
    prompt: str
    images: List[str]  
    

def extract_sql_from_response(response: str) -> str:
    response = response.replace('\r\n', '\n')
    if response.strip().upper().startswith('SELECT'):
        return response.strip()
    match = re.search(r'(?i)(SELECT\s+[\s\S]+)', response)
    if match:
        sql_block = match.group(1).strip()
        sql_lines = sql_block.split('\n')
        cleaned_lines = []
        for line in sql_lines:
            if re.match(
                r'^\s*(SELECT|FROM|WHERE|AND|OR|GROUP BY|ORDER BY|TOP|INNER|LEFT|RIGHT|JOIN|ON|LIMIT|OFFSET|HAVING|UNION|AS|IS NOT NULL|IS NULL|BETWEEN|IN|NOT IN|DISTINCT|CASE|WHEN|THEN|ELSE|END)\b',
                line.strip(), re.IGNORECASE):
                cleaned_lines.append(line)
            else:
                break
        return '\n'.join(cleaned_lines).strip()
    logger.warning("No valid SQL found in response: %s", response)
    return response.strip()

def build_sql_query(prompt: str) -> Tuple[str, List, str]:
    raw_llm_response = vn.generate_sql(question=prompt)
    if not raw_llm_response:
        raise ValueError("Empty SQL generated")
    sql = extract_sql_from_response(raw_llm_response)
    return sql, [], raw_llm_response

@lru_cache(maxsize=256)
def cached_generate_sql(prompt: str) -> Tuple[str, List, str]:
    normalized_prompt = ' '.join(prompt.strip().lower().split())
    return build_sql_query(normalized_prompt)

def is_duplicate_prompt(prompt: str) -> bool:
    try:
        results = vn.vector_db.query(query_texts=[prompt], n_results=1)
        return bool(results and results['documents'] and results['documents'][0][0].strip().lower() == prompt.strip().lower())
    except Exception as e:
        logger.warning("Duplicate check failed: %s", str(e))
        return False

def train_vanna_in_background(prompt: str, sql: str):
    try:
        if not is_duplicate_prompt(prompt):
            vn.train(question=prompt, sql=sql)
            logger.info("Vanna trained: %s", prompt)
        else:
            logger.info("Duplicate prompt: %s", prompt)
    except Exception as e:
        logger.error("Vanna training failed: %s", str(e))

# ✅ Async LLM response for casual prompts + SQL
async def fast_llama(prompt: str, stream: bool = False):
    system_msg = {
        "role": "system",
        "content": "You are a real senior doctor from ABI Health. Answer only medical queries—clearly, briefly, and accurately—in the user's language, using a clean table if helpful. Politely decline anything non-medical."
    }

    user_msg = {
        "role": "user",
        "content": prompt
    }

    if stream:
        async def event_stream():
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=360.0) as client:
                    async with client.stream("POST", "http://localhost:11434/api/chat", json={
                        "model": "gemma3:12b",
                        "stream": True,
                        "messages": [system_msg, user_msg]
                    }) as res:
                        async for line in res.aiter_lines():
                            if line.strip():
                                yield f"data: {line}\n\n"
            except Exception as e:
                logger.error(f"LLM stream error: {e}")
                yield f"data: {json.dumps({'message': {'content': '❌ LLM stream error'}})}\n\n"
                
            finally:
                end_time = time.time()
                logger.info(f"🕒 Total LLM streaming duration: {end_time - start_time:.2f} seconds")    

        return event_stream()

    else:
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=360.0) as client:
                res = await client.post("http://localhost:11434/api/chat", json={
                    "model": "gemma3:12b",
                    "stream": False,
                    "messages": [system_msg, user_msg]
                })
                data = res.json()
                end_time = time.time()
                tokens_per_sec = data.get("stats", {}).get("tokens_per_second", "N/A")
                logger.info(f"💬 LLM Response time: {end_time - start_time:.2f} sec | 🔢 Tokens/sec: {tokens_per_sec}")
                return data.get("message", {}).get("content", "❓ No content.")
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "❌ LLM error occurred."


# ✅ Keyword filter
def is_patient_prompt(prompt: str) -> bool:
    prompt = prompt.lower()
    return 'patient' in prompt or 'patients' in prompt

# ✅ Warm up Ollama with retry
def warmup_ollama():
    def try_warm():
        for _ in range(3):
            try:
                logger.info("Warming up Ollama model...")
                res = requests.post("http://localhost:11434/api/chat", json={
                    "model": "gemma3:12b",
                    "messages": [
                        {
                            "role": "user",
                            "content": "hi"
                        }
                    ],
                    "stream": False
                }, timeout=60)
                logger.info("Ollama warm-up complete")
                return
            except Exception as e:
                logger.warning(f"Warm-up attempt failed: {e}")
                time.sleep(5)
    threading.Thread(target=try_warm).start()

warmup_ollama()

# ✅ query-patients route for casual streaming response  + SQL
@app.post("/query-patients/")
async def query_patients(user_input: UserPrompt, background_tasks: BackgroundTasks):
    start_time = time.time()
    prompt = user_input.prompt.strip()
    logger.info("Prompt: %s", prompt)

    try:
        if is_patient_prompt(prompt):
            logger.info("Routing to Vanna SQL")
            sql, params, llm_response = cached_generate_sql(prompt)

            if not sql.strip().lower().startswith("select"):
                return {
                    "query": None,
                    "params": [],
                    "llm_response": llm_response,
                    "result_count": 0,
                    "result": []
                }

            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                result = [dict(zip(column_names, row)) for row in rows]

            if user_input.train:
                background_tasks.add_task(train_vanna_in_background, prompt, sql)

            total_duration = time.time() - start_time
            logger.info(f"✅ Total API response time: {total_duration:.2f} sec")

            return {
                "query": sql,
                "params": params,
                "llm_response": llm_response,
                "result_count": len(result),
                "result": result,
                "no_data": len(result) == 0
            }

        else:
            logger.info("Routing to LLM with streaming ✅")
            return StreamingResponse(
                await fast_llama(prompt, stream=True),
                media_type="text/event-stream"
            )

    except Exception as e:
        logger.error("Error: %s", str(e))
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ✅ Image Vision Route
@app.post("/vision-proxy/")
async def vision_proxy(v: VisionPrompt):
    try:
        payload = {
            "model": "gemma3:12b",
            "prompt": v.prompt,
            "images": v.images,  # must be a list of base64 strings
            "stream": False
        }

        logger.info(f"Sending to /api/generate: {payload}")
        start_time = time.time()
        async with httpx.AsyncClient(timeout=360) as client:
            res = await client.post(
                "http://localhost:11434/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}  # Force proper header
            )
            res.raise_for_status()
            elapsed_time = time.time() - start_time  # ⏱️ Stop timing
            logger.info(f"Image Processing completed in {elapsed_time:.2f} seconds")
            return res.json()

    except Exception as e:
        logger.error(f"Vision proxy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Extra streaming route
@app.post("/query-patients/stream")
async def query_patients_stream(user_input: UserPrompt):
    prompt = user_input.prompt.strip()

    async def stream():
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", "http://localhost:11434/api/chat", json={
                "model": "gemma3:12b",
                "stream": True,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a real senior doctor from ABI Health. Answer only medical queries—clearly, briefly, and accurately—in the user's language, using a clean table if helpful. Politely decline anything non-medical."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }) as res:
                async for chunk in res.aiter_lines():
                    if chunk.strip() == '':
                        continue
                    # Wrap it in SSE format
                    yield f"data: {chunk}\n\n"
        end_time = time.time()
        logger.info(f"🕒 LLM stream time: {end_time - start_time:.2f} sec")
    return StreamingResponse(stream(), media_type="text/event-stream")

