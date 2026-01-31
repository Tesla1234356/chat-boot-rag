import json
import os
import shutil
import glob
from datetime import datetime

class GestorAlmacenamiento:
    DIR_BASE = "data"
    DIR_CHATS = os.path.join(DIR_BASE, "conversations")
    DIR_SUBIDAS = os.path.join(DIR_BASE, "uploads")

    @staticmethod
    def guardar_documento(ruta_archivo):
        """Copia el archivo subido al almacenamiento local."""
        if not os.path.exists(GestorAlmacenamiento.DIR_SUBIDAS):
            os.makedirs(GestorAlmacenamiento.DIR_SUBIDAS)
        
        nombre_archivo = os.path.basename(ruta_archivo)
        ruta_destino = os.path.join(GestorAlmacenamiento.DIR_SUBIDAS, nombre_archivo)
        
        # Simplemente sobrescribimos si ya existe
        shutil.copy2(ruta_archivo, ruta_destino)
        return ruta_destino

    @staticmethod
    def guardar_chat(id_chat, titulo, mensajes, fragmentos, ruta_doc):
        """Guarda el estado de la conversación en un archivo JSON."""
        if not os.path.exists(GestorAlmacenamiento.DIR_CHATS):
            os.makedirs(GestorAlmacenamiento.DIR_CHATS)

        datos = {
            "id": id_chat,
            "title": titulo, # Mantenemos 'title' en inglés en el JSON para compatibilidad si quisieras, pero aquí en código es 'titulo'
            "updated_at": datetime.now().isoformat(),
            "doc_path": ruta_doc,
            "messages": mensajes, # Mantenemos keys en inglés para compatibilidad con JSONs viejos si los hubiera
            "chunks": fragmentos
        }
        
        ruta_archivo = os.path.join(GestorAlmacenamiento.DIR_CHATS, f"{id_chat}.json")
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    @staticmethod
    def cargar_chat(id_chat):
        ruta_archivo = os.path.join(GestorAlmacenamiento.DIR_CHATS, f"{id_chat}.json")
        if not os.path.exists(ruta_archivo):
            return None
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def listar_chats():
        """Devuelve una lista de resúmenes de chats ordenados por fecha."""
        if not os.path.exists(GestorAlmacenamiento.DIR_CHATS):
            return []
            
        archivos = glob.glob(os.path.join(GestorAlmacenamiento.DIR_CHATS, "*.json"))
        chats = []
        for f in archivos:
            try:
                with open(f, 'r', encoding='utf-8') as archivo:
                    datos = json.load(archivo)
                    chats.append({
                        "id": datos.get("id"),
                        "title": datos.get("title", "Sin título"),
                        "updated_at": datos.get("updated_at", "")
                    })
            except:
                continue
        
        # Ordenar por fecha descendente
        chats.sort(key=lambda x: x["updated_at"], reverse=True)
        return chats

    @staticmethod
    def eliminar_chat(id_chat):
        ruta_archivo = os.path.join(GestorAlmacenamiento.DIR_CHATS, f"{id_chat}.json")
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
