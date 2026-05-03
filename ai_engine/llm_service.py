import json
import os
import re
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
            Eres un abogado experto en derecho contractual espanol. Tu salida debe
            ser estable, verificable y basada solo en el texto del contrato.

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
            - Cita la clausula o fragmento del contrato que justifica cada bandera roja.
            - No uses Markdown, comentarios, texto adicional ni claves distintas a las solicitadas.
            - riesgo_total solo puede ser uno de estos valores exactos: "Bajo", "Medio", "Crítico".
            - Si no encuentras el cliente, pon "Desconocido" en cliente_extraido
        """

        prompt_usuario = f"Contrato:\n<<<INICIO_CONTRATO>>>\n{texto[:30000]}\n<<<FIN_CONTRATO>>>"

        # 1. Intentar con Gemini
        if self.client:
            try:
                gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                print(f"DEBUG: Intentando análisis con Gemini ({gemini_model})...")
                response = self.client.models.generate_content(
                    model=gemini_model,
                    contents=f"{prompt_sistema}\n\n{prompt_usuario}",
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.1
                    )
                )
                return self._limpiar_y_parsear_json(response.text)
            except Exception as e:
                print(f"WARNING: Gemini fallo (Clave inválida o cuota agotada): {e}. Cayendo a Ollama...")

        # 2. Fallback a Ollama
        return self._llamar_ollama(prompt_sistema, prompt_usuario)

    def _llamar_ollama(self, system: str, user: str, reintentos: int = 3) -> dict:
        """Llamada a Ollama con reintentos."""
        if not self._esperar_ollama():
            return self._get_error_final("Ollama no está respondiendo. Verifica que el contenedor esté activo.")

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
                    msg = f"El modelo '{self.model}' no está disponible en Ollama. Puede que aún se esté descargando o el nombre sea incorrecto."
                    print(f"ERROR: {msg}")
                    return self._get_error_final(msg)

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

            return self._normalizar_resultado(json.loads(contenido[inicio:fin]))
        except Exception as e:
            print(f"DEBUG: Error parseando JSON: {e}")
            return self._get_error_final("Error de formato en la respuesta de la IA")

    def _normalizar_resultado(self, resultado: dict) -> dict:
        """Garantiza que la respuesta tenga siempre el contrato JSON esperado."""
        if not isinstance(resultado, dict):
            raise ValueError("La IA no devolvio un objeto JSON")

        puntos_clave = self._normalizar_lista_texto(resultado.get("puntos_clave"))
        banderas_rojas = self._normalizar_lista_texto(resultado.get("banderas_rojas"))
        entidades = resultado.get("entidades") if isinstance(resultado.get("entidades"), dict) else {}

        riesgo_total = self._normalizar_riesgo(resultado.get("riesgo_total"), banderas_rojas)
        cliente_extraido = resultado.get("cliente_extraido") or "Desconocido"
        if not isinstance(cliente_extraido, str):
            cliente_extraido = "Desconocido"
        cliente_extraido = cliente_extraido.strip() or "Desconocido"

        return {
            "puntos_clave": puntos_clave or ["No se han identificado puntos clave."],
            "banderas_rojas": banderas_rojas,
            "riesgo_total": riesgo_total,
            "cliente_extraido": cliente_extraido,
            "entidades": {
                "nombres": self._normalizar_lista_texto(entidades.get("nombres")),
                "dni": self._normalizar_lista_texto(entidades.get("dni")),
                "fechas": self._normalizar_lista_texto(entidades.get("fechas")),
                "importes": self._normalizar_lista_texto(entidades.get("importes")),
            },
        }

    def _normalizar_lista_texto(self, valor) -> list:
        if valor is None:
            return []
        if isinstance(valor, str):
            valor = [valor]
        if not isinstance(valor, list):
            return []
        return [str(item).strip() for item in valor if str(item).strip()]

    def _normalizar_riesgo(self, valor, banderas_rojas: list) -> str:
        texto = str(valor or "").strip().lower()
        texto = re.sub(r"[\s_-]+", " ", texto)
        if texto in {"critico", "crítico", "alto", "grave"}:
            return "Crítico"
        if texto in {"medio", "moderado"}:
            return "Medio"
        if texto in {"bajo", "limpio", "sin riesgo"}:
            return "Bajo"
        return "Medio" if banderas_rojas else "Bajo"

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
