import json
import os
import time
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class AgenteIA:
    def __init__(self):
        # Configuración Ollama
        self.ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        
        # Configuración Gemini 
        self.gemini_key = os.getenv("GOOGLE_API_KEY")
        if self.gemini_key:
            try:
                self.client = genai.Client(api_key=self.gemini_key)
                print("INFO: Cliente Gemini (google-genai) inicializado.")
            except Exception as e:
                print(f"ERROR: No se pudo inicializar Gemini: {e}")
                self.client = None
        else:
            self.client = None
            print("WARNING: GOOGLE_API_KEY no encontrada. Usando solo Ollama.")

        print(f"INFO: Usando Ollama con modelo '{self.model}' en {self.ollama_url}")

    def analizar_contratos(self, texto: str, prompt_especifico: str) -> dict:
        """
        Analiza un contrato usando Gemini o Ollama como fallback.
        """
        prompt_sistema = f"""
            Eres un abogado experto en derecho contractual espanol.

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
            - SOLO marca como bandera_roja si es ILEGAL, claramente abusiva o SOSPECHOSA/FRAUDULENTA.
            - Si no encuentras el cliente, pon "Desconocido" en cliente_extraido
        """

        prompt_usuario = f"Contrato:\n{texto[:20000]}"

        # 1. Intentar con Gemini
        if self.client:
            try:
                print("DEBUG: Intentando análisis con Gemini (gemini-2.5-flash)...")
                response = self.client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=f"{prompt_sistema}\n\n{prompt_usuario}",
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.1
                    )
                )
                return self._limpiar_y_parsear_json(response.text)
            except Exception as e:
                print(f"WARNING: Gemini fallo: {e}. Cayendo a Ollama...")

        # 2. Fallback a Ollama
        return self._llamar_ollama(prompt_sistema, prompt_usuario)

    def _llamar_ollama(self, system: str, user: str, reintentos: int = 3) -> dict:
        """Llamada a Ollama con reintentos."""
        if not self._esperar_ollama():
            return self._get_error_final("Ni Gemini ni Ollama están disponibles.")

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

        for intento in range(1, reintentos + 1):
            try:
                print(f"DEBUG: Llamando a Ollama (intento {intento}/{reintentos})...")
                # Aseguramos que la URL termina en /api/chat
                url = self.ollama_url
                if not url.endswith("/api/chat"):
                    url = url.split("/api")[0].rstrip("/") + "/api/chat"
                
                response = requests.post(url, json=payload, timeout=600)
                if response.status_code == 404:
                    print(f"ERROR: Ollama devolvió 404. ¿Está el modelo '{self.model}' descargado?")
                response.raise_for_status()
                data = response.json()
                raw_content = data.get('message', {}).get('content', '{}')
                return self._limpiar_y_parsear_json(raw_content)
            except Exception as e:
                print(f"WARNING: Ollama fallo intento {intento}: {e}")
                if intento < reintentos:
                    time.sleep(5 * intento)

        return self._get_error_final(f"Ollama fallo tras {reintentos} reintentos.")

    def _esperar_ollama(self, max_intentos=10) -> bool:
        """Comprobación rápida de Ollama."""
        base_url = self.ollama_url.split("/api")[0].rstrip("/")
        for _ in range(max_intentos):
            try:
                resp = requests.get(f"{base_url}/api/tags", timeout=3)
                return resp.status_code == 200
            except:
                time.sleep(1)
        return False

    def _limpiar_y_parsear_json(self, contenido: str) -> dict:
        """Limpia y parsea el JSON de la respuesta."""
        try:
            contenido = contenido.strip()
            if contenido.startswith("```"):
                contenido = contenido.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            inicio = contenido.find("{")
            fin = contenido.rfind("}") + 1
            if inicio == -1 or fin == 0:
                raise ValueError("No JSON found")
                
            return json.loads(contenido[inicio:fin])
        except Exception as e:
            print(f"DEBUG: Error parseando JSON: {e}")
            return self._get_error_final("Error de formato en la respuesta de la IA")

    def _get_error_final(self, mensaje: str) -> dict:
        return {
            "puntos_clave": ["Error"],
            "banderas_rojas": [mensaje],
            "riesgo_total": "Crítico",
            "cliente_extraido": "Desconocido",
            "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
        }

# Instancia del agente
agente = AgenteIA()
