import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

class AgenteIA:
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
        self.model = os.getenv("OLLAMA_MODEL", "llama3:8b")
        print(f"INFO: Usando Ollama con modelo '{self.model}'")

    def analizar_contratos(self, texto: str, prompt_especifico: str) -> dict:
        """
        Analiza un contrato usando Ollama.
        """
        prompt_sistema = f"""Eres un abogado experto en derecho contractual espanol.

Analiza el contrato y devuelve EXCLUSIVAMENTE un JSON valido con esta estructura exacta:
{{
  "puntos_clave": ["punto1", "punto2"],
  "banderas_rojas": [],
  "riesgo_total": "Bajo",
  "cliente_extraido": "nombre del cliente",
  "entidades": {{"nombres": [], "dni": [], "fechas": [], "importes": []}}
}}

INSTRUCCIONES:
{prompt_especifico}

REGLAS:
- Si el contrato es legal y justo, devuelve "banderas_rojas": [] y "riesgo_total": "Bajo"
- NO marques como abusivas clausulas que sean legales y estandar
- SOLO marca como bandera_roja si es ILEGAL o claramente abusiva segun la ley
- Si no encuentras el cliente, pon "Desconocido" en cliente_extraido
"""

        prompt_usuario = f"Contrato:\n{texto[:8000]}"  # Limitamos contexto

        return self._llamar_ollama(prompt_sistema, prompt_usuario)

    def _llamar_ollama(self, system: str, user: str, reintentos: int = 3) -> dict:
        """
        Llamada a Ollama con reintentos.
        """
        # Esperar a que Ollama este listo
        if not self._esperar_ollama():
            return {
                "puntos_clave": ["Error"],
                "banderas_rojas": ["Ollama no esta disponible."],
                "riesgo_total": "Crítico",
                "cliente_extraido": "Desconocido",
                "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
            }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_ctx": 8192}
        }

        ultimo_error = None
        for intento in range(1, reintentos + 1):
            try:
                print(f"DEBUG: Llamando a Ollama (intento {intento}/{reintentos})...")
                response = requests.post(self.ollama_url, json=payload, timeout=600)
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
            "banderas_rojas": [f"Fallo total de IA: {ultimo_error}"],
            "riesgo_total": "Crítico",
            "cliente_extraido": "Desconocido",
            "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
        }

    def _esperar_ollama(self, max_intentos=120) -> bool:
        """Espera a que Ollama este listo."""
        base_url = self.ollama_url.replace("/api/chat", "")
        
        for intento in range(1, max_intentos + 1):
            try:
                resp = requests.get(f"{base_url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    modelos = resp.json().get("models", [])
                    nombres = [m.get("name", "") for m in modelos]
                    if any(self.model in n for n in nombres):
                        print(f"INFO: Modelo '{self.model}' listo en Ollama.")
                        return True
            except Exception:
                pass
            
            if intento % 10 == 0:
                print(f"DEBUG: Esperando a que Ollama tenga el modelo '{self.model}'... (intento {intento}/{max_intentos})")
            time.sleep(3)
        
        return False

    def _limpiar_y_parsear_json(self, contenido: str) -> dict:
        """
        Limpia y parsea el JSON de la respuesta.
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
            
            # Eliminar markdown code blocks
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
            
            # Validar claves requeridas
            required_keys = ["puntos_clave", "banderas_rojas", "riesgo_total"]
            if not all(key in datos for key in required_keys):
                print(f"DEBUG: JSON incompleto. Claves encontradas: {list(datos.keys())}")
                return fallback_error
                
            # Asegurar que cliente_extraido existe
            if "cliente_extraido" not in datos:
                datos["cliente_extraido"] = "Desconocido"
                
            return datos
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON parse error: {e}")
            return fallback_error
        except Exception as e:
            print(f"DEBUG: Error inesperado parseando JSON: {e}")
            return fallback_error


# Instancia del agente
agente = AgenteIA()
