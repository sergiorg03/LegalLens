import json
import os
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
                "riesgo_total": "Bajo" | "Medio" | "Critico",
                "entidades": {{
                    "nombres": [],
                    "dni": [],
                    "fechas": [],
                    "importes": []
                }}
            }}
        """

        if not self.llm:
            return {
                "puntos_clave": ["Error"],
                "banderas_rojas": ["Falta la API KEY de Google Gemini."],
                "riesgo_total": "Desconocido",
                "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
            }

        prompt_usuario = f"Contrato:\n{texto}"

        try:
            # Llamada al LLM
            response = self.llm.invoke([
                    ("system", prompt_sistema),
                    ("user", prompt_usuario),
                ])

            contenido = response.content.strip()

            # Limpiamos el texto para sacar solo el JSON
            inicio = contenido.find("{")
            fin = contenido.rfind("}") + 1
            json_str = contenido[inicio:fin]

            return json.loads(json_str)

        except Exception as e:
            # En caso de error devolvemos un JSON basico
            return {
                "puntos_clave": ["Error"],
                "banderas_rojas": [f"Fallo de conexion: {str(e)}"],
                "riesgo_total": "Critico",
                "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
            }


# Instancia del agente
agente = AgenteIA()
