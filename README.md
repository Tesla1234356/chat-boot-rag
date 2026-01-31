# ChatBoot (rag) 🤖📄

**ChatBoot** es un asistente de IA inteligente desarrollado en Python que permite a los usuarios interactuar con sus propios documentos (PDF y DOCX) utilizando tecnología **RAG** (Generación Aumentada por Recuperación).

El programa combina la potencia de procesamiento de lenguaje de **Google Gemini** para la estructuración de datos y la privacidad/flexibilidad de **Ollama** para la generación de respuestas locales.

---

## 🚀 Características Principales

- **Chat con Documentos (RAG):** Sube archivos PDF o Word y haz preguntas específicas sobre su contenido.
- **Procesamiento Inteligente:** Utiliza Gemini para limpiar texto, eliminar ruido (como números de página) y segmentar el contenido de forma semántica.
- **IA Local:** Generación de respuestas mediante Ollama, garantizando rapidez y control sobre el modelo utilizado.
- **Entrada de Voz:** Soporte para dictado por voz en español.
- **Historial de Conversaciones:** Guarda automáticamente tus chats y el contexto de los documentos para retomarlos más tarde.
- **Interfaz Moderna:** UI oscura y profesional construida con PyQt6, con soporte para bloques de código y formato HTML.

---

## 🛠️ Arquitectura del Proyecto (Español)

El código ha sido refactorizado totalmente al español para facilitar su comprensión:

- **`main.py`**: Punto de entrada de la aplicación.
- **`app/interfaz.py`**: Lógica de la interfaz gráfica y manejo de eventos.
- **`app/motor_rag.py`**: Motor de búsqueda y recuperación de fragmentos relevantes.
- **`app/documento.py`**: Cargador y extractor de texto para PDF y DOCX.
- **`app/procesador_gemini.py`**: Integración con Google Gemini para limpieza y segmentación.
- **`app/cliente_ollama.py`**: Cliente para la comunicación con el servidor local de Ollama.
- **`app/almacenamiento.py`**: Gestor de persistencia para chats y archivos subidos.

---

## 📋 Requisitos Previos

1. **Ollama:** Debes tener Ollama instalado y ejecutándose con el modelo qwen2.5:7b (o el que prefieras configurar).
   ```bash
   ollama run qwen2.5:7b
   ```
2. **Clave de API de Gemini:** Se requiere una API Key de Google AI Studio configurada en `app/interfaz.py`.
3. **Dependencias de Python:** Instalación de librerías necesarias:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Cómo Ejecutar

Simplemente ejecuta el archivo principal desde tu terminal:

```bash
python main.py
```

---

## 💡 Cómo funciona el sistema RAG

1. **Carga:** El usuario sube un documento.
2. **Segmentación:** Gemini divide el documento en "fragmentos" con sentido completo.
3. **Búsqueda:** Cuando el usuario pregunta algo, el `MotorRAG` busca los fragmentos que más coinciden con la pregunta (usando búsqueda por palabras clave y bonos por frases exactas).
4. **Respuesta:** Se envía la pregunta junto con los fragmentos encontrados a Ollama, quien genera una respuesta basada exclusivamente en esa información.

---

Desarrollado como una herramienta avanzada de procesamiento de lenguaje natural.
