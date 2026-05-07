from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List


# Definicion de los datos que extraermos del PDF
class EntidadesExtraidas(BaseModel):
    nombres: List[str]
    dni: List[str]
    fechas: List[str]
    importes: List[str]


# Molde final para la respuesta de la IA
class AnalisisResultado(BaseModel):
    puntos_clave: List[str]
    banderas_rojas: List[str]
    riesgo_total: str  # "Bajo", "Medio" o "Crítico"
    entidades: EntidadesExtraidas
    cliente_extraido: str


# Clase abstracta Base
class Contrato(ABC):
    def __init__(self, texto: str, cliente: str):
        self.texto = texto
        self.cliente = cliente

    @abstractmethod
    def obtener_prompt_especifico(self) -> str:
        # Cada tipo de contrato definira sus propios criterios
        pass

    def ejecutar_auditoria(self, agente_ia) -> dict:
        """
        Método Plantilla: Define el flujo de la auditoría.
        Es común para todos los contratos, pero usamos prompts diferentes para cada clase de contrato definido en la clase heredera.
        """
        prompt = self.obtener_prompt_especifico()
        return agente_ia.analizar_contratos(self.texto, prompt)


# clase ContratoAlquiler
class ContratoAlquiler(Contrato):
    def obtener_prompt_especifico(self) -> str:
        return """
        SISTEMA DE DETECCIÓN DE FRAUDE (ALQUILER).
        IGNORA cláusulas legales estándar. SOLO reporta FRAUDES REALES.

        ADVERTENCIA: Algunos estafadores usan encabezados como "MODELO ORIENTATIVO" para parecer legales. IGNORA el encabezado y busca estas TRAMPAS REALES:
        1. REPARACIONES ILEGALES: "El inquilino paga TODAS las reparaciones, incluso estructurales o de habitabilidad" o "El casero NO se compromete a conservar la vivienda".
        2. DEPÓSITOS ABSURDOS: Fianza superior a 3 meses de renta o cantidades de millones de euros.
        3. ENTRADA SIN PERMISO: "El casero puede entrar en la casa cuando quiera sin avisar".
        4. ABSURDO TOTAL: El contrato no tiene nombres reales, el precio es variable según el humor del dueño, o se pide el coche como garantía.
        5. ILEGALIDAD EXTREMA: "Expulsión en 2 horas", "Trabajos forzados", "Deuda perpetua" o "Sanciones de 10 veces la renta por palabra".

        NO REPORTES (ESTO ES LEGAL):
        - Fianza de 1 o 2 meses.
        - El inquilino paga pequeñas reparaciones por uso ordinario.
        - Actualización anual por IPC.
        - Indemnización por desistimiento antes de 6 meses.
        - Sometimiento a tribunales de la ciudad.

        Si el contrato parece legal y normal, banderas_rojas = [] y riesgo_total = "Bajo".
        """

class ContratoNDA(Contrato):
    def obtener_prompt_especifico(self) -> str:
        return """
        SISTEMA DE DETECCIÓN DE FRAUDE (NDA).
        IGNORA cláusulas de confidencialidad estándar. SOLO reporta FRAUDES REALES.

        ADVERTENCIA: Algunos estafadores usan encabezados como "MODELO ORIENTATIVO" para parecer legales. IGNORA el encabezado y busca estas TRAMPAS REALES:
        1. VENTA DE DATOS: "El receptor PODRÁ VENDER la información a terceros".
        2. INDEMNIZACIONES ABSURDAS: Penas de 100 millones de euros por un simple descuido.
        3. ROBO DE IDEAS: "El receptor se queda con la propiedad de todo lo que el emisor le cuente".

        NO REPORTES (ESTO ES LEGAL):
        - Deber de secreto.
        - Devolver la información al terminar.
        - Indemnización por daños y perjuicios reales (sin cifras locas).
        - Duración de 2 o 5 años.

        Si el contrato parece legal y normal, banderas_rojas = [] y riesgo_total = "Bajo".
        """

# Creación de un contrato generico
class ContratoGenerico(Contrato):
    def obtener_prompt_especifico(self) -> str:
        return """
        Analiza este documento buscando puntos clave y cualquier cláusula que pueda ser abusiva o ilegal según el derecho contractual español.
        
        INSTRUCCIONES:
        - Resume los puntos más importantes (partes, objeto, precio, duración).
        - Identifica cláusulas que generen un desequilibrio importante o sean oscuras.
        - COHERENCIA: Si el documento no tiene sentido o parece un fraude, márcalo como Crítico.
        
        Si el contrato es razonable: "banderas_rojas": [] y "riesgo_total": "Bajo".
        Si detectas riesgos: lístalos en banderas_rojas y ajusta el riesgo_total.
        """


class ContratoFactory:
    @staticmethod
    def crear_contrato(tipo: str, texto: str, cliente: str) -> Contrato:
        if tipo.upper() == "ALQUILER":
            return ContratoAlquiler(texto, cliente)
        elif tipo.upper() == "NDA":
            return ContratoNDA(texto, cliente)
        else:
            return ContratoGenerico(texto, cliente)
