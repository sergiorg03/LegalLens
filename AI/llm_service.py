import json
import os
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
            print(
                "WARNING: GOOGLE_API_KEY not found in environment. AI service will not work."
            )
        else:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=0,
                max_output_tokens=1000,
            )

    def analizar_contratos(self, texto: str, prompt_especifico: str) -> json:
        """
        Función que analiza un contrato.
        Parámetros:
            - texto: texto del contrato a analizar
        Retorna:
            - dict: diccionario con el resultado del análisis
        """
        # Definimos el prompt para el análisis
        prompt_sistema = f"""
            Eres un experto en derecho contractual. Analiza el contrato siguiendo estas instrucciones.
            
            INSTRUCCIONES:
            {prompt_especifico}

            EXTRAE TAMBIEN:
            - Nombres de las partes.
            - DNIs o identificaciones.
            - Fechas clave.
            - Importes economicos.

            RESPONDE SOLO EN JSON:
            {{
                "puntos_clave": ["..."],
                "banderas_rojas": ["..."],
                "riesgo_total": "Bajo" | "Medio" | "Crítico",
                "cliente_extraido": "Nombre del cliente/empresa principal",
                "entidades": {{
                    "nombres": [],
                    "dni": [],
                    "fechas": [],
                    "importes": []
                }}
            }}
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
                    print("DEBUG: Gemini devolvió una respuesta inválida o error. Reintentando con Ollama...")
            except Exception as e:
                print(f"DEBUG: Gemini fallo ({str(e)}). Intentando Ollama...")

        # 2. Fallback a Ollama
        return self._llamar_ollama(prompt_sistema, prompt_usuario)

    def _llamar_ollama(self, system: str, user: str) -> dict:
        """
        Llamada a Ollama como alternativa.
        """
        url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/chat")
        model = os.getenv("OLLAMA_MODEL", "llama3")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post(url, json=payload, timeout=90)
            response.raise_for_status()
            data = response.json()
            return self._limpiar_y_parsear_json(data['message']['content'])
        except Exception as e:
            print(f"ERROR: Ollama también fallo ({str(e)})")
            return {
                "puntos_clave": ["Error"],
                "banderas_rojas": [f"Fallo total de IA (Gemini y Ollama): {str(e)}"],
                "riesgo_total": "Crítico",
                "cliente_extraido": "Desconocido",
                "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
            }

    def _limpiar_y_parsear_json(self, contenido: str) -> dict:
        """
        Limpia y parsea el JSON de la respuesta, validando que tenga la estructura correcta.
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
            inicio = contenido.find("{")
            fin = contenido.rfind("}") + 1
            if inicio == -1 or fin == 0:
                return fallback_error
                
            json_str = contenido[inicio:fin]
            datos = json.loads(json_str)
            
            # Validacion minima de claves
            required_keys = ["puntos_clave", "banderas_rojas", "riesgo_total"]
            if not all(key in datos for key in required_keys):
                return fallback_error
                
            return datos
        except Exception:
            return fallback_error


# Instancia del agente
agente = AgenteIA()
