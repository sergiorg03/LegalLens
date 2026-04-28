from fastapi import FastAPI, UploadFile, File, Form
import fitz  # PyMuPDF
from AI.llm_service import agente
from AI.contratos import ContratoFactory
import uvicorn

# Inicializamos la app FastAPI
app = FastAPI()

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
    texto = ''
    try:
        with fitz.open(stream=contenido, filetype="pdf") as f:
            texto = "".join(page.get_text() for page in f)
    except Exception as e:
        return {"error": f"Error al leer el PDF: {str(e)}"}

    try:
        
        # Detectamos el tipo de contrato y obtenemos el prompt personalizado
        contrato = ContratoFactory.crear_contrato(tipo, texto, cliente)

        resultado = contrato.ejecutar_auditoria(agente)

        return resultado

    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error al procesar el contrato: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)