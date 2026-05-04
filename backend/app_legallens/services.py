import requests
import json
import os

# URL de la API 
API_URL = os.getenv("API_URL", "http://localhost:8001/analizar")

def llamar_api_ia(contrato):
    try:
        with contrato.archivo_pdf.open("rb") as f:
            respuesta = requests.post(
                API_URL, 
                files={"file": f}, 
                data={
                    "tipo": contrato.tipo,
                    "cliente": contrato.cliente
                },
                timeout=1200
            )

            respuesta.raise_for_status()
            return respuesta.json()

    except Exception as e:
        print("ERROR IA: ", e)
        return {
            "riesgo_total": "Crítico",
            "banderas_rojas": [
                "No se pudo conectar con el servicio de IA o la cuota se ha agotado.",
                f"Detalle técnico: {str(e)}"
            ],
            "puntos_clave": ["Error en la comunicación con la IA"],
            "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
            "cliente_extraido": "Desconocido",
        }

def guardar_resultado_ia(contrato, resultado):
    """
        Función que guarda el JSON de la IA en la BBDD.
    """
    contrato.resultado_ia = json.dumps(resultado)
    contrato.save()

def obtener_resultado_ia(contrato):
    """
        Funcón que recupera y parsea el JSON guardado.
    """
    try:
        return json.loads(contrato.resultado_ia) if contrato.resultado_ia else None
    except Exception as e:
        print(f"Error al parsear resultado IA: {e}")
        return {
            "riesgo_total": "Crítico",
            "banderas_rojas": ["Error al procesar la respuesta del servidor."],
            "puntos_clave": ["Error en el procesamiento de la respuesta. "],
            "entidades": {"nombres": [], "dni": [], "fechas": [], "importes": []},
            "cliente_extraido": "Error",
        }