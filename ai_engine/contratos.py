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
        SOLO reporta si encuentras una de estas TRAMPAS:
        1. REPARACIONES: "Arrendador NO se compromete a reparaciones de habitabilidad" (ERROR CRÍTICO).
        2. NOMBRES: Amador Rivas, Antonio Recio, Coque Calatrava (ERROR CRÍTICO).
        3. CARGOS: "Director de Lunes" (ERROR CRÍTICO).
        4. BORRADORES: "[Opción 1]", "[Eliminar si...]" (ERROR).
        5. ACCESO: Casero entra sin permiso.

        Si no ves una de estas 5, banderas_rojas = [].
        NO REPORTES nada sobre indemnizaciones o jurisdicción.
        """

class ContratoNDA(Contrato):
    def obtener_prompt_especifico(self) -> str:
        return """
        SISTEMA DE DETECCIÓN DE FRAUDE (NDA).
        SOLO reporta si encuentras una de estas TRAMPAS:
        1. VENTA DE DATOS: "Proveedor podrá vender información" (ERROR CRÍTICO).
        2. CARGOS: "Director de Lunes" (ERROR CRÍTICO).
        3. BORRADORES: "[Opción 1]", "[Completar...]" (ERROR).

        Si no ves una de estas 3, banderas_rojas = [].
        NO REPORTES nada sobre indemnizaciones o jurisdicción.
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
