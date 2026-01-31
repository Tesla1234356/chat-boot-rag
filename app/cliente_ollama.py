import requests
import json

class ClienteOllama:
    def __init__(self, modelo="qwen2.5:7b", host="http://localhost:11434"):
        self.modelo = modelo
        self.host = host
        self.api_url = f"{host}/api/generate"

    def generar_respuesta(self, contexto, pregunta, modo_rag=True):
        """
        Genera una respuesta.
        Si modo_rag es False, actúa como asistente general.
        Si modo_rag es True, actúa como un analista de documentos estricto.
        """
        
        if modo_rag and contexto:
            # PROMPT ESTRICTO (RAG) - LÓGICA DE INFERENCIA MEJORADA
            prompt = f"""CONTEXTO:
{contexto}

PREGUNTA:
{pregunta}

INSTRUCCIONES OBLIGATORIAS:
Eres un asistente experto en análisis de texto.
1. Responde basándote SOLO en el contexto proporcionado arriba.
2. REGLA DE FECHAS: Si preguntan "cuándo" o "en qué año" y el texto da un RANGO (ej: "entre 1943 y 1944"), ESA ES LA RESPUESTA CORRECTA. No digas que no sabes.
3. REGLA DE SINÓNIMOS: Si preguntan por "inicio" y el texto dice "comienza", o "batalla" y el texto dice "conflicto", conecta los puntos.
4. PROHIBIDO decir: "en esta versión alternativa", "según el documento". Presenta los hechos como VERDAD ABSOLUTA.
5. SI Y SOLO SI la información NO existe en absoluto (ni siquiera implícitamente): Di exactamente: "No tengo información sobre eso en el documento."

RESPUESTA:
"""
            temperatura = 0.1
        else:
            # PROMPT GENERAL (CHAT LIBRE)
            prompt = f"""Eres un asistente de IA útil y profesional llamado 'ChatBoot'.
Responde a la siguiente pregunta del usuario de manera clara, concisa y amable.
No tienes documentos cargados en este momento, así que usa tu conocimiento general.

PREGUNTA:
{pregunta}
"""
            temperatura = 0.7 # Más creativo para charla normal

        payload = {
            "model": self.modelo,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperatura
            }
        }

        try:
            respuesta = requests.post(self.api_url, json=payload)
            respuesta.raise_for_status()
            resultado = respuesta.json()
            return resultado.get("response", "Error: No hay campo 'response' en la salida de Ollama.")
        except requests.exceptions.ConnectionError:
            return "Error: No puedo conectar con Ollama. Asegúrate de que esté corriendo (localhost:11434)."
        except Exception as e:
            return f"Error consultando Ollama: {e}"
