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
        Busca especificamente:
        1. Si la fianza exigida supera el limite legal (1 mes).
        2. Si el contrato obliga al inquilino a pagar reparaciones estructurales (Art. 21 LAU).
        3. Clausulas de acceso del casero a la vivienda sin aviso.
        """


# Clase Confidencialidad NDA
class ContratoNDA(Contrato):
    def obtener_prompt_especifico(self) -> str:
        return """
        Busca especificamente:
        1. Clausulas de duracion infinita o perpetua.
        2. Multas desproporcionadas (superiores a 100.000E).
        3. Definiciones de informacion confidencial demasiado amplias.
        """


# Creacion del objeto contrato segun el tipo de contrato que sea
class ContratoFactory:
    @staticmethod
    def crear_contrato(tipo: str, texto: str, cliente: str) -> Contrato:
        if tipo.upper() == "ALQUILER":
            return ContratoAlquiler(texto, cliente)
        elif tipo.upper() == "NDA":
            return ContratoNDA(texto, cliente)
        else:
            raise ValueError(f"Tipo de contrato desconocido: {tipo}")
