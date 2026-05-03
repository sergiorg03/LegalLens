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
        Analiza este contrato de arrendamiento de vivienda habitual segun la Ley de
        Arrendamientos Urbanos (LAU) espanola. Distingue entre clausulas legales,
        notas orientativas del modelo y clausulas realmente pactadas.

        Primero extrae los datos basicos: arrendador, arrendatario, vivienda, renta,
        duracion, fianza, garantias, gastos, reparaciones, desistimiento, recuperacion
        de vivienda, actualizacion de renta, acceso a la vivienda y resolucion.

        REGLAS ESTRICTAS:
        - Es legal y estandar: fianza legal de 1 mensualidad en vivienda, pequenas
          reparaciones por uso ordinario a cargo del arrendatario, conservacion y
          reparaciones necesarias a cargo del arrendador, desistimiento tras 6 meses
          con preaviso de 30 dias, prorroga obligatoria hasta 5 anos si el arrendador
          es persona fisica o 7 anos si es persona juridica, recuperacion de vivienda
          por necesidad con causa legal y preaviso suficiente.
        - Es bandera roja: acceso del arrendador sin aviso o en cualquier momento,
          fianza legal superior a 1 mensualidad, garantia adicional que exceda los
          limites legales, no devolucion automatica de la fianza, reparaciones
          estructurales o de habitabilidad siempre a cargo del arrendatario, IBI,
          comunidad, derramas o gastos de gestion cargados sin pacto claro o de forma
          desproporcionada, subida unilateral o ilimitada de renta, penalizaciones
          desproporcionadas, recuperacion o resolucion unilateral sin causa legal,
          renuncia del arrendatario a derechos de prorroga, desistimiento o tutela
          judicial.
        - Si una clausula aparece solo como nota explicativa, pie de pagina o comentario
          del modelo orientativo, no la marques como infraccion salvo que tambien este
          incorporada como clausula pactada.
        - Si el contrato cumple la LAU: "banderas_rojas": [] y "riesgo_total": "Bajo".
        - Si hay violaciones explicitas a la LAU: listalas con una referencia breve a
          la clausula afectada y usa "riesgo_total": "Medio" o "Crítico".
        - NO inventes clausulas que no esten escritas.
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
