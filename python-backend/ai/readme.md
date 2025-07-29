# 🧠 AI-Powered SQL Query Generator using FastAPI + Ollama + LLaMA 3 + Vanna + SQL RAG Syste 

This project is an **full AI + SQL RAG (Retrieval-Augmented Generation) system end-to-end using fully open-source, offline, AI-driven system** 
that transforms natural language questions into optimized SQL queries — built entirely with open-source technologies and designed for secure, on-premise deployment.

## 🚀 Features

- 💡 **Natural Language to SQL**: Automatically convert user queries into valid SQL for CRM datasets.
- 🔒 **100% Offline**: Powered by the LLaMA 3 model via [Ollama](https://ollama.com/), no cloud APIs required.
- 🧠 **RAG Architecture**: Combines local vector search (ChromaDB) with LLM reasoning using [Vanna.AI](https://vanna.ai/).
- 📊 **SQL Server Integration**: Real-time query execution and result delivery via `pyodbc`.
- 🔁 **Self-Learning**: Supports background fine-tuning using user input and LLM-generated SQL.
- ⚡ **FastAPI API**: Clean, scalable API interface with CORS enabled for frontend use.
- 📈 **Logging & Validation**: Built-in SQL safety checks, result limit enforcement, and structured logs.

---

## 🧱 Tech Stack

| Layer          | Technology       |
|----------------|------------------|
| Backend API    | FastAPI          |
| LLM Engine     | Ollama (`llama3:8b`) |
| Vector DB      | ChromaDB         |
| SQL Gen Logic  | Vanna.AI (offline) |
| SQL Execution  | pyODBC + SQL Server |
| Caching        | `functools.lru_cache` |
| Background Tasks | FastAPI `BackgroundTasks` |

---

✍️ Author  : RAJESH CHOUDHURY


