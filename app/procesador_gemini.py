import google.generativeai as genai
import json

class ProcesadorGemini:
    def __init__(self, clave_api):
        """
        Inicializa el Procesador Gemini con el modelo específico.
        """
        genai.configure(api_key=clave_api)
        # Usamos explícitamente el modelo solicitado
        self.nombre_modelo = "gemini-2.5-flash" 
        try:
            self.modelo = genai.GenerativeModel(self.nombre_modelo)
        except Exception as e:
            print(f"Error cargando {self.nombre_modelo}: {e}")
            # Respaldo seguro
            self.modelo = genai.GenerativeModel("gemini-1.5-flash")

    def procesar_y_segmentar(self, texto_crudo):
        """
        Envía texto crudo a Gemini para limpiar ruido y segmentar en fragmentos coherentes.
        """
        prompt = """
        Eres un experto pre-procesador de datos. 
        Tu tarea es tomar el siguiente texto crudo (extraído de un documento) y:
        1. Limpiarlo (eliminar números de página, artefactos raros, encabezados/pies si interrumpen el flujo).
        2. Dividirlo en segmentos/fragmentos semánticamente coherentes.
        3. Cada fragmento debe tener aproximadamente menos de 500 tokens, pero prioriza mantener oraciones y párrafos juntos.
        
        Genera ESTRICTAMENTE un JSON válido con el siguiente formato:
        [
            "texto del fragmento 1...",
            "texto del fragmento 2...",
            ...
        ]
        
        Texto Crudo:
        """
        
        try:
            # Límite de seguridad para el prompt
            respuesta = self.modelo.generate_content(prompt + texto_crudo[:40000]) 
            texto_limpio = respuesta.text.strip()
            
            if texto_limpio.startswith("```json"):
                texto_limpio = texto_limpio[7:]
            if texto_limpio.startswith("```"):
                texto_limpio = texto_limpio[3:]
            if texto_limpio.endswith("```"):
                texto_limpio = texto_limpio[:-3]
                
            fragmentos = json.loads(texto_limpio.strip())
            return fragmentos
        except Exception as e:
            raise Exception(f"Error de Procesamiento en Gemini: {e}")
