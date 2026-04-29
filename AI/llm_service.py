import json
import os
import time
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# cargamos variables de entorno
load_dotenv()

class AgenteIA:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            self.llm = None
            print("WARNING: GOOGLE_API_KEY not found. Using Ollama as fallback.")
        else:
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    temperature=0,
                    max_output_tokens=1000,
                )
                print("INFO: Gemini LLM configurado correctamente.")
            except Exception as e:
                self.llm = None
                print(f"WARNING: No se pudo configurar Gemini: {e}")

    def analizar_contratos(self, texto: str, prompt_especifico: str) -> json:
        """
        Función que analiza un contrato.
        """
        prompt_sistema = f"""Analiza este contrato legal. Devuelve SOLO JSON con estas claves exactas:

puntos_clave: lista de 3-5 puntos importantes
banderas_rojas: lista de clausulas abusivas o riesgosas
riesgo_total: Bajo, Medio o Critico
cliente_extraido: nombre del cliente o empresa principal
entidades: objeto con listas de nombres, dni, fechas, importes

INSTRUCCIONES:
{prompt_especifico}
"""

        prompt_usuario = f"Contrato:\n{texto}"

        # 1. Intentamos con Gemini si está configurado
        if self.llm:
            try:
                response = self.llm.invoke([
                    ("system", prompt_sistema),
                    ("user", prompt_usuario),
                ])
                resultado = self._limpiar_y_parsear_json(response.content)
                
                # Validamos que no sea un error de cuota o similar camuflado
                if "puntos_clave" in resultado and "Error" not in resultado["puntos_clave"][0]:
                    return resultado
                else:
                    print("DEBUG: Gemini devolvió respuesta inválida. Reintentando con Ollama...")
            except Exception as e:
                print(f"DEBUG: Gemini fallo ({str(e)}). Intentando Ollama...")

        # 2. Fallback a Ollama
        return self._llamar_ollama(prompt_sistema, prompt_usuario)

    def _esperar_modelo_ollama(self, max_intentos=120) -> bool:
        """Espera a que el modelo de Ollama esté descargado."""
        url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/chat")
        base_url = url.replace("/api/chat", "")
        model = os.getenv("OLLAMA_MODEL", "llama3:8b")

        for intento in range(1, max_intentos + 1):
            try:
                resp = requests.get(f"{base_url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    modelos = resp.json().get("models", [])
                    nombres = [m.get("name", "") for m in modelos]
                    if any(model in n for n in nombres):
                        print(f"INFO: Modelo '{model}' listo en Ollama.")
                        return True
            except Exception:
                pass
            
            if intento % 10 == 0:
                print(f"DEBUG: Esperando a que Ollama tenga el modelo '{model}'... (intento {intento}/{max_intentos})")
            time.sleep(3)
        
        return False

    def _llamar_ollama(self, system: str, user: str, reintentos: int = 3) -> dict:
        """
        Llamada a Ollama como alternativa con reintentos.
        """
        url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/chat")
        model = os.getenv("OLLAMA_MODEL", "llama3:8b")

        # Esperar a que el modelo esté disponible
        if not self._esperar_modelo_ollama():
            print("ERROR: El modelo de Ollama no está disponible tras esperar.")
            return {
                "puntos_clave": ["Error"],
                "banderas_rojas": ["Ollama no tiene el modelo descargado. Espera unos minutos y reintenta."],
                "riesgo_total": "Crítico",
                "cliente_extraido": "Desconocido",
                "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
            }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": False,
            "format": "json",
            "options": {"num_ctx": 8192}
        }

        ultimo_error = None
        for intento in range(1, reintentos + 1):
            try:
                print(f"DEBUG: Llamando a Ollama (intento {intento}/{reintentos})...")
                response = requests.post(url, json=payload, timeout=600)
                response.raise_for_status()
                data = response.json()
                raw_content = data.get('message', {}).get('content', '{}')
                print(f"DEBUG: Ollama raw response (primeros 300 chars): {raw_content[:300]}")
                return self._limpiar_y_parsear_json(raw_content)
            except Exception as e:
                ultimo_error = str(e)
                print(f"WARNING: Ollama fallo intento {intento}: {ultimo_error}")
                if intento < reintentos:
                    time.sleep(5 * intento)

        print(f"ERROR: Ollama fallo tras {reintentos} reintentos. Ultimo error: {ultimo_error}")
        return {
            "puntos_clave": ["Error"],
            "banderas_rojas": [f"Fallo total de IA (Gemini y Ollama): {ultimo_error}"],
            "riesgo_total": "Crítico",
            "cliente_extraido": "Desconocido",
            "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
        }

    def _limpiar_y_parsear_json(self, contenido: str) -> dict:
        """
        Limpia y parsea el JSON de la respuesta con extraccion robusta.
        """
        fallback_error = {
            "puntos_clave": ["Error de procesamiento"],
            "banderas_rojas": ["La IA no pudo analizar este documento correctamente."],
            "riesgo_total": "Crítico",
            "cliente_extraido": "Desconocido",
            "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
        }

        try:
            contenido = contenido.strip()
            
            # Eliminar markdown code blocks si existen
            if contenido.startswith("```"):
                contenido = contenido.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            # Buscar el primer { y el ultimo }
            inicio = contenido.find("{")
            fin = contenido.rfind("}") + 1
            if inicio == -1 or fin == 0:
                print(f"DEBUG: No se encontro JSON en la respuesta.")
                return fallback_error
                
            json_str = contenido[inicio:fin]
            datos = json.loads(json_str)
            
            # Si el JSON tiene una clave wrapper como "solution", extraer el contenido
            if len(datos) == 1 and "solution" in datos:
                solution = datos["solution"]
                # Buscar JSON dentro de la solucion
                inicio2 = solution.find("{")
                fin2 = solution.rfind("}") + 1
                if inicio2 != -1:
                    datos = json.loads(solution[inicio2:fin2])
                else:
                    return self._construir_desde_texto(solution)
            
            required_keys = ["puntos_clave", "banderas_rojas", "riesgo_total"]
            if not all(key in datos for key in required_keys):
                print(f"DEBUG: JSON incompleto. Claves encontradas: {list(datos.keys())}")
                return self._construir_desde_texto(json_str)
                
            return datos
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON parse error: {e}")
            return fallback_error
        except Exception as e:
            print(f"DEBUG: Error inesperado parseando JSON: {e}")
            return fallback_error

    def _construir_desde_texto(self, texto: str) -> dict:
        """
        Construye un resultado basico cuando el modelo devuelve texto en lugar de JSON estructurado.
        """
        # Intentar extraer info util del texto
        texto_lower = texto.lower()
        if any(p in texto_lower for p in ["clausula abusiva", "ilegal", "prohibido", "riesgo", "peligro"]):
            riesgo = "Medio"
        else:
            riesgo = "Bajo"
        
        return {
            "puntos_clave": [texto[:500] + ("..." if len(texto) > 500 else "")],
            "banderas_rojas": ["El modelo no genero JSON valido. Revisar respuesta manual."],
            "riesgo_total": riesgo,
            "cliente_extraido": "Desconocido",
            "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
        }


# Instancia del agente
agente = AgenteIA()
