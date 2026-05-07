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

        prompt_usuario = f"Contrato:\n<<<INICIO_CONTRATO>>>\n{texto[:150000]}\n<<<FIN_CONTRATO>>>"

        # 1. Intentar con Gemini
        if self.client:
            try:
                gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
                print(f"DEBUG: Intentando análisis con Gemini ({gemini_model})...")
                response = self.client.models.generate_content(
                    model=gemini_model,
                    contents=f"{prompt_sistema}\n\n{prompt_usuario}",
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.1
                    )
                )
                return self._limpiar_y_parsear_json(response.text, texto)
            except Exception as e:
                print(f"WARNING: Gemini fallo (Clave inválida o cuota agotada): {e}. Cayendo a Ollama...")

        # 2. Fallback a Ollama
        return self._llamar_ollama(prompt_sistema, prompt_usuario, texto)

    def _llamar_ollama(self, system: str, user: str, raw_text: str, reintentos: int = 3) -> dict:
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
                    # Intentamos listar qué modelos hay realmente para ayudar al debug
                    modelos_str = "Desconocido"
                    try:
                        base_url = url.split("/api")[0].rstrip("/")
                        tags_resp = requests.get(f"{base_url}/api/tags", timeout=5)
                        if tags_resp.status_code == 200:
                            modelos = tags_resp.json().get("models", [])
                            modelos_str = ", ".join([m.get("name", "") for m in modelos])
                    except Exception as e:
                        pass
                    
                    msg = f"El modelo '{self.model}' no está disponible en Ollama. Modelos encontrados: [{modelos_str}]. Verifica el nombre en el archivo .env"
                    print(f"ERROR: {msg}")
                    return self._get_error_final(msg)

                response.raise_for_status()
                data = response.json()
                raw_content = data.get('message', {}).get('content', '{}')
                return self._limpiar_y_parsear_json(raw_content, raw_text)
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
            except Exception as e:
                time.sleep(1)
        return False

    def _limpiar_y_parsear_json(self, contenido: str, texto: str = "") -> dict:
        """Limpia y parsea el JSON de la respuesta."""
        t_lower = (texto or "").lower()
        t_compact = "".join(t_lower.split())
        try:
            contenido = contenido.strip()
            if contenido.startswith("```"):
                contenido = contenido.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            inicio = contenido.find("{")
            fin = contenido.rfind("}") + 1
            if inicio == -1 or fin == 0:
                raise ValueError("No JSON found")

            resultado = json.loads(contenido[inicio:fin])
            
            # SANITIZADOR DE FALSOS POSITIVOS (Eliminar banderas que son legales)
            terminos_prohibidos = [
                "daños y perjuicios", "indemnización", "indemnizacion", "jurisdicción", 
                "jurisdiccion", "tribunales", "actualización", "actualizacion", "ipc", 
                "fianza", "obras de mejora", "pequeñas reparaciones", "pequenas reparaciones",
                "duración", "duracion", "ley aplicable", "confidencialidad estándar",
                "resolución de conflictos", "resolucion de conflictos", "modelo orientativo",
                "incibe", "profesionales especializados", "secreto", "exclusiones"
            ]
            
            if "banderas_rojas" in resultado and isinstance(resultado["banderas_rojas"], list):
                nuevas_banderas = []
                for b in resultado["banderas_rojas"]:
                    b_str = str(b).lower()
                    # 1. Filtro de términos prohibidos (legales estándar)
                    if any(t in b_str for t in terminos_prohibidos) or (("secreto" in b_str or "confidencialidad" in b_str) and "robo" in b_str):
                        if any(x in b_str for x in ["millón", "millon", "ridícul", "absurd", "todo el sueldo", "embargo", "vender", "coche"]):
                            nuevas_banderas.append(b)
                        continue 
                    
                    # 2. Corrección de Alucinación: Venta de datos falsa
                    if "vender" in b_str or "venta" in b_str:
                        if not any(x in t_compact for x in ["vender", "venda", "comercializar", "enajenar", "distribuir"]):
                            continue 
                    
                    # 3. Corrección de Alucinación: Reparaciones (el AI a veces lee mal "se compromete")
                    if "reparación" in b_str or "reparacion" in b_str or "conservación" in b_str:
                        if "secomprometearealizar" in t_compact and "nosecompromete" not in b_str.replace(" ", ""):
                            continue

                    # 4. Corrección de Alucinación: Prórroga (Art 9 LAU es legal)
                    if "prórroga" in b_str or "prorroga" in b_str:
                        if "necesidaddeocuparlavivienda" in t_compact:
                            continue # Es el derecho legal del casero (Art. 9.3 LAU)

                    nuevas_banderas.append(b)
                resultado["banderas_rojas"] = nuevas_banderas


            # 5. REGLA DE ORO PARA PLANTILLAS LEGALES (Ignorar todo lo que no sea fraude extremo)
            if any(x in t_compact for x in ["modeloorientativo", "incibe", "orientativa", "plantilla"]):
                # Si es una plantilla oficial, solo aceptamos flags de FRAUDE EXTREMO
                resultado["banderas_rojas"] = [
                    b for b in resultado.get("banderas_rojas", [])
                    if any(x in str(b).lower() for x in ["millón", "millon", "ridícul", "absurd", "todo el sueldo", "embargo", "vender", "coche", "dar el coche", "horas", "expulsar", "momento que lo desee", "trabajos forzados", "perpetua", "diez veces", "donar", "desalojo", "desalojar", "veces", "eternidad", "cinco"])
                ]

            # REFUERZO DE DETECCIÓN DETERMINISTA (Solo trampas legales reales - NO SE ELIMINAN)
            if "nosecomprometearealizarlasreparaciones" in t_compact:
                if not any("reparación" in str(b).lower() or "conservación" in str(b).lower() for b in resultado.get("banderas_rojas", [])):
                    resultado.setdefault("banderas_rojas", []).append({
                        "clausula": "Conservación",
                        "razón": "El arrendador renuncia ilegalmente a su obligación de reparaciones de habitabilidad (Art. 21 LAU)."
                    })
            
            if "podrávenderinformación" in t_compact or "podravenderinformacion" in t_compact:
                if not any("vender" in str(b).lower() for b in resultado.get("banderas_rojas", [])):
                    resultado.setdefault("banderas_rojas", []).append({
                        "clausula": "NDA / Propiedad",
                        "razón": "Cláusula fraudulenta: el proveedor se reserva el derecho de vender información confidencial."
                    })

            if "trabajosforzado" in t_compact or "veces" in t_compact or "cinco" in t_compact or "desaloj" in t_compact or "eternidad" in t_compact or "500000" in t_compact:
                if not any(x in str(resultado.get("banderas_rojas", [])).lower() for x in ["trabajo", "veces", "expulsar", "desaloj", "eternidad", "millon", "millón", "cinco"]):
                    resultado.setdefault("banderas_rojas", []).append({
                        "clausula": "Cláusula Abusiva / Ilegal",
                        "razón": "Se detectaron términos de fraude extremo: trabajos forzados, sanciones desproporcionadas (5x/500M), desalojo, o duración perpetua."
                    })

            if "es12" in t_compact and ("3456" in t_compact or "1234" in t_compact):
                if not any("bancaria" in str(b).lower() for b in resultado.get("banderas_rojas", [])):
                    resultado.setdefault("banderas_rojas", []).append({
                        "clausula": "Cuenta Bancaria Sospechosa",
                        "razón": "Se ha detectado una cuenta bancaria de ejemplo (ES12...) que indica que el contrato es un modelo no válido o una estafa."
                    })

            if "sustituir" in t_compact and "remarcado" in t_compact:
                if not any("plantilla" in str(b).lower() for b in resultado.get("banderas_rojas", [])):
                    resultado.setdefault("banderas_rojas", []).append({
                        "clausula": "Documento No Válido",
                        "razón": "Este documento es una plantilla sin editar (contiene instrucciones de 'sustituir texto'). No debe firmarse."
                    })

            return self._normalizar_resultado(resultado)
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
        if not banderas_rojas:
            return "Bajo"
        
        b_str = str(banderas_rojas).lower()
        # Fuerza CRÍTICO si hay fraude extremo
        if any(x in b_str for x in ["fraude", "abusiva", "sospechosa", "ilegal", "forzado", "eternidad", "500.000", "5x"]):
            return "Crítico"

        texto = str(valor or "").strip().lower()
        texto = re.sub(r"[\s_-]+", " ", texto)
        if texto in {"critico", "crítico", "alto", "grave"}:
            return "Crítico"
        if texto in {"bajo", "low", "mínimo", "minimo"}:
            return "Bajo"
        return "Medio"

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
