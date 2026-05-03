from fastapi import FastAPI, UploadFile, File, Form
import fitz  # PyMuPDF
from ai_engine.llm_service import agente
from ai_engine.contratos import ContratoFactory
import uvicorn
import json
import os
import requests
import time
import threading

# Inicializamos la app FastAPI
app = FastAPI()

# Estado global para saber si Ollama esta listo
ollama_state = {"model_ready": False, "downloading": False}


def esperar_y_cargar_modelo_ollama():
    """Hilo en segundo plano que espera a Ollama y descarga el modelo."""
    ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
    # Limpiamos la URL para obtener la base (host:puerto) sin endpoints
    base_url = ollama_url.split("/api")[0].rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3:8b")

    print(f"INFO: Verificando Ollama en {base_url}...")

    # Esperar a que Ollama responda
    for intento in range(1, 61):
        try:
            resp = requests.get(f"{base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                print(f"INFO: Ollama respondio despues de {intento} intentos.")
                break
        except Exception:
            pass
        print(f"INFO: Esperando a Ollama (intento {intento}/60)...")
        time.sleep(5)
    else:
        print("WARNING: No se pudo conectar con Ollama despues de 60 intentos.")
        return

    # Verificar si el modelo ya esta descargado
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=10)
        modelos = resp.json().get("models", [])
        nombres_modelos = [m.get("name", "") for m in modelos]

        modelo_disponible = any(model in nombre for nombre in nombres_modelos)

        if not modelo_disponible:
            print(f"INFO: El modelo '{model}' no esta. Iniciando descarga...")
            ollama_state["downloading"] = True
            with requests.post(
                f"{base_url}/api/pull",
                json={"name": model, "stream": True},
                stream=True,
                timeout=None
            ) as pull_resp:
                pull_resp.raise_for_status()
                for line in pull_resp.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            status = chunk.get("status", "")
                            if status:
                                print(f"DEBUG: Ollama -> {status}")
                        except:
                            pass
            print(f"INFO: Descarga finalizada.")
            ollama_state["model_ready"] = True
        else:
            print(f"INFO: Modelo '{model}' ya esta disponible.")
            ollama_state["model_ready"] = True

        ollama_state["model_ready"] = True
    except Exception as e:
        print(f"WARNING: No se pudo verificar/descargar el modelo: {e}")
    finally:
        ollama_state["downloading"] = False


@app.on_event("startup")
def startup_event():
    # Lanzamos la descarga en segundo plano sin bloquear el servidor
    hilo = threading.Thread(target=esperar_y_cargar_modelo_ollama, daemon=True)
    hilo.start()

# Endpoint de analisis del contrato
@app.post("/analizar")
async def analizar_contrato(
    file: UploadFile = File(...),
    tipo: str = Form(...),
    cliente: str = Form("Desconocido")
):
    contenido = await file.read()

    # Validacion basica
    if not file.filename.endswith(".pdf"):
        return {"error": "Solo se aceptan archivos PDF"}

    # Obtenemos el contenido y extraemos texto
    texto = ""
    try:
        with fitz.open(stream=contenido, filetype="pdf") as f:
            paginas = []
            for numero_pagina, page in enumerate(f, start=1):
                texto_pagina = page.get_text().strip()
                if texto_pagina:
                    paginas.append(f"\n\n--- PAGINA {numero_pagina} ---\n{texto_pagina}")
            texto = "".join(paginas)
    except Exception as e:
        return {"error": f"Error al leer el PDF: {str(e)}"}
    
    # Verificar si se extrajo texto
    if not texto or len(texto.strip()) < 50:
        print(f"WARNING: Texto extraído muy corto ({len(texto)} chars). PDF posiblemente vacío o sea imagen.")
        return {
            "puntos_clave": ["Error de lectura"],
            "banderas_rojas": ["No se pudo extraer texto del documento. Verifica que el PDF no esté vacío o sea una imagen escaneada."],
            "riesgo_total": "Crítico",
            "cliente_extraido": "Desconocido",
            "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []}
        }

    try:
        
        # Detectamos el tipo de contrato y obtenemos el prompt personalizado
        contrato = ContratoFactory.crear_contrato(tipo, texto, cliente)

        resultado = contrato.ejecutar_auditoria(agente)

        return resultado

    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error al procesar el contrato: {str(e)}"}


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "ollama_ready": ollama_state["model_ready"],
        "ollama_downloading": ollama_state["downloading"]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
