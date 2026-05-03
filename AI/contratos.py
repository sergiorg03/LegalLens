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
        Analiza este contrato de alquiler segun la Ley de Arrendamientos Urbanos (LAU).
        
        REGLAS ESTRICTAS:
        - Es LEGAL: fianza de 1 mes, reparaciones a cargo del propietario, acceso con aviso
        - Es ILEGAL: fianza > 1 mes, reparaciones a cargo del inquilino, acceso sin aviso
        - Si el contrato cumple la LAU: "banderas_rojas": [] y "riesgo_total": "Bajo"
        - Si hay violaciones EXPLICITAS a la LAU: listarlas en "banderas_rojas" y "riesgo_total": "Critico" o "Medio"
        - NO inventes clausulas que no esten escritas
        """

class ContratoNDA(Contrato):
    def obtener_prompt_especifico(self) -> str:
        return """
        Analiza el acuerdo de confidencialidad buscando CUALQUIER clausula abusiva o señal de FRAUDE:
        - Obligaciones desequilibradas entre las partes.
        - Penalizaciones o multas desproporcionadas.
        - Definiciones excesivamente amplias de informacion confidencial.
        - Restricciones que limiten el trabajo o desarrollo profesional.
        - Ausencia de excepciones legitimas al secreto.
        - COHERENCIA: Si el documento no parece un contrato real, contiene lenguaje sospechoso o incoherente, márcalo como FRAUDE.
        
        Si el documento NO es un NDA o parece fraudulento, pon riesgo_total como "Crítico" y lístalo en banderas_rojas.
        Si el NDA es estandar y equilibrado, NO marques nada como bandera_roja y pon riesgo_total como "Bajo".
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
