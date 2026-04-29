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
        Analiza segun la Ley de Arrendamientos Urbanos (LAU) espanola y la legislacion de consumo.
        
        Busca CUALQUIER clausula abusiva o desequilibrada, no solo las tipicas:
        - Fianzas o depositos excesivos.
        - Reparto injusto de gastos y reparaciones.
        - Limitaciones excesivas al uso del inquilino.
        - Penalizaciones desproporcionadas.
        - Renuncia de derechos legales del inquilino.
        - Facultades abusivas del arrendador.
        
        Si el contrato cumple la ley, NO marques nada como bandera_roja y pon riesgo_total como "Bajo".
        """


# Clase Confidencialidad NDA
class ContratoNDA(Contrato):
    def obtener_prompt_especifico(self) -> str:
        return """
        Analiza el acuerdo de confidencialidad buscando CUALQUIER clausula abusiva:
        - Obligaciones desequilibradas entre las partes.
        - Penalizaciones o multas desproporcionadas.
        - Definiciones excesivamente amplias de informacion confidencial.
        - Restricciones que limiten el trabajo o desarrollo profesional.
        - Ausencia de excepciones legitimas al secreto.
        
        Si el NDA es estandar y equilibrado, NO marques nada como bandera_roja y pon riesgo_total como "Bajo".
        """

# Creación de un contrato generico
class ContratoGenerico(Contrato):
    def obtener_prompt_especifico(self) -> str:
        return """
        Analiza este contrato buscando CUALQUIER clausula abusiva, ilegal o desequilibrada:
        - Obligaciones desproporcionadas para una de las partes.
        - Penalizaciones o multas excesivas.
        - Renuncia de derechos legales.
        - Clausulas que limiten injustamente la libertad o derechos.
        - Desequilibrios evidentes entre derechos y obligaciones.
        - Terminos ambiguos que puedan perjudicar a una parte.
        
        Si el contrato parece equilibrado y legal, NO marques nada como bandera_roja y pon riesgo_total como "Bajo".
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
