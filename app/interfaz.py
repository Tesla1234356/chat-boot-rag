import sys
import uuid
import os
import html
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QMenu,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QTimer
from PyQt6.QtGui import QIcon, QAction, QColor

import pyaudio
import speech_recognition as sr

from app.documento import CargadorDocumentos
from app.procesador_gemini import ProcesadorGemini
from app.cliente_ollama import ClienteOllama
from app.motor_rag import MotorRAG
from app.almacenamiento import GestorAlmacenamiento

# ==========================================
#  CONFIGURACIÓN
# ==========================================
CLAVE_API_GEMINI = "tu api key" 
# ==========================================

HOJA_ESTILOS = """
QMainWindow { background-color: #121212; } 
QWidget { color: #e0e0e0; font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 14px; }

/* BARRA LATERAL (Izquierda) */
QListWidget {
    background-color: #1e1e1e;
    border: none;
    outline: none;
    padding-top: 10px;
}
QListWidget::item {
    padding: 12px 15px;
    border-bottom: 1px solid #2d2d2d;
    color: #b0b0b0;
}
QListWidget::item:selected {
    background-color: #2d2d2d;
    color: white;
    border-left: 3px solid #007acc;
}
QListWidget::item:hover {
    background-color: #262626;
}

/* MARCO DEL CHAT (Centro) */
QFrame#ContenedorChat {
    background-color: #1e1e1e;
    border-radius: 12px;
    border: 1px solid #333;
}

/* AREA DE TEXTO DEL CHAT */
QTextEdit {
    background-color: transparent;
    border: none;
    padding: 10px;
}

/* BARRA DE ENTRADA (Abajo) */
QFrame#ContenedorEntrada {
    background-color: #252526;
    border-radius: 24px; 
    border: 1px solid #3e3e42;
}

QLineEdit {
    background-color: transparent;
    border: none;
    font-size: 15px;
    color: white;
    padding: 0 10px;
}

/* BOTONES */
QPushButton {
    border: none;
    border-radius: 20px;
    font-weight: bold;
}

/* Botón Nuevo Chat */
QPushButton#BotonNuevoChat {
    background-color: #007acc;
    color: white;
    border-radius: 8px;
    padding: 10px;
    margin: 15px;
    font-size: 14px;
}
QPushButton#BotonNuevoChat:hover { background-color: #0062a3; }

/* Botón Adjuntar (Clip) */
QPushButton#BotonAdjuntar {
    background-color: transparent;
    color: #888;
    font-size: 20px;
}
QPushButton#BotonAdjuntar:hover { 
    color: white; 
    background-color: #3e3e42; 
}

/* Botón Microfono */
QPushButton#BotonMicro {
    background-color: transparent;
    color: #888;
    font-size: 20px;
}
QPushButton#BotonMicro:hover { 
    color: white; 
    background-color: #3e3e42; 
}
QPushButton#BotonMicro:checked {
    color: #ff4444;
    background-color: #3e2020;
}

/* Botón Enviar (Flecha) */
QPushButton#BotonEnviar {
    background-color: #007acc;
    color: white;
    font-size: 16px;
}
QPushButton#BotonEnviar:hover { background-color: #0062a3; }

/* BARRA DE PROGRESO */
QProgressBar {
    background-color: #333;
    height: 3px;
    border: none;
}
QProgressBar::chunk { background-color: #007acc; }
"""

class HiloVoz(QThread):
    finalizado = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.grabando = False
        self.cuadros = []
        self.p = pyaudio.PyAudio()

    def run(self):
        try:
            stream = self.p.open(format=pyaudio.paInt16,
                                 channels=1,
                                 rate=16000,
                                 input=True,
                                 frames_per_buffer=1024)
            
            self.grabando = True
            self.cuadros = []
            
            while self.grabando:
                datos = stream.read(1024)
                self.cuadros.append(datos)
            
            stream.stop_stream()
            stream.close()
            
            if not self.cuadros:
                return

            # Procesar
            datos_audio = b''.join(self.cuadros)
            fuente_audio = sr.AudioData(datos_audio, 16000, 2) 
            
            r = sr.Recognizer()
            # Intenta reconocer en español
            texto = r.recognize_google(fuente_audio, language="es-ES")
            self.finalizado.emit(texto)

        except Exception as e:
            # Si no se escucha nada o hay error, emitimos error (o silencio)
            if "No speech could be interpreted" in str(e):
                self.error.emit("No se escuchó nada.")
            else:
                self.error.emit(str(e))
        
    def detener(self):
        self.grabando = False

class HiloTrabajador(QThread):
    finalizado = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, funcion_tarea, *args):
        super().__init__()
        self.funcion_tarea = funcion_tarea
        self.args = args

    def run(self):
        try:
            resultado = self.funcion_tarea(*self.args)
            self.finalizado.emit(resultado)
        except Exception as e:
            self.error.emit(str(e))

class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatBoot")
        self.resize(1200, 850)
        
        # Componentes Lógicos
        self.rag = MotorRAG()
        self.ollama = ClienteOllama(modelo="qwen2.5:7b")
        self.gemini = None
        if CLAVE_API_GEMINI != "TU_API_KEY_AQUI":
            self.gemini = ProcesadorGemini(CLAVE_API_GEMINI)

        # Estado
        self.id_chat_actual = None
        self.historial_chat = []
        self.fragmentos_actuales = []
        self.ruta_doc_actual = None
        self.temporizador_pensando = QTimer(self)
        self.temporizador_pensando.timeout.connect(self.actualizar_indicador_pensando)
        self.contador_puntos = 0
        
        self.iniciar_interfaz()
        self.aplicar_estilos()
        self.crear_nuevo_chat()
        self.refrescar_barra_lateral()

    def aplicar_estilos(self):
        self.setStyleSheet(HOJA_ESTILOS)

    def iniciar_interfaz(self):
        widget_principal = QWidget()
        self.setCentralWidget(widget_principal)
        layout_principal = QHBoxLayout(widget_principal)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # --- BARRA LATERAL (IZQUIERDA) ---
        widget_barra_lateral = QWidget()
        widget_barra_lateral.setFixedWidth(260)
        widget_barra_lateral.setStyleSheet("background-color: #1e1e1e; border-right: 1px solid #333;")
        layout_barra_lateral = QVBoxLayout(widget_barra_lateral)
        layout_barra_lateral.setContentsMargins(0, 0, 0, 0)

        self.btn_nuevo_chat = QPushButton("+ Nuevo Chat")
        self.btn_nuevo_chat.setObjectName("BotonNuevoChat")
        self.btn_nuevo_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nuevo_chat.clicked.connect(self.crear_nuevo_chat)
        layout_barra_lateral.addWidget(self.btn_nuevo_chat)

        etiqueta_barra = QLabel("HISTORIAL")
        etiqueta_barra.setStyleSheet("color: #666; font-size: 11px; font-weight: bold; margin-left: 15px; margin-top: 10px;")
        layout_barra_lateral.addWidget(etiqueta_barra)

        self.lista_historial = QListWidget()
        self.lista_historial.itemClicked.connect(self.cargar_chat_seleccionado)
        self.lista_historial.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lista_historial.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        layout_barra_lateral.addWidget(self.lista_historial)

        # --- CONTENIDO PRINCIPAL (DERECHA) ---
        widget_contenido = QWidget()
        layout_contenido = QVBoxLayout(widget_contenido)
        layout_contenido.setContentsMargins(30, 20, 30, 30) # Márgenes externos
        layout_contenido.setSpacing(15)

        # 1. Cabecera
        self.layout_cabecera = QHBoxLayout()
        self.etiqueta_doc = QLabel("Chat General")
        self.etiqueta_doc.setStyleSheet("font-size: 18px; font-weight: 600; color: #f0f0f0;")
        self.subetiqueta_estado = QLabel("Sin documentos cargados")
        self.subetiqueta_estado.setStyleSheet("font-size: 13px; color: #888;")
        
        layout_texto_cabecera = QVBoxLayout()
        layout_texto_cabecera.addWidget(self.etiqueta_doc)
        layout_texto_cabecera.addWidget(self.subetiqueta_estado)
        
        self.layout_cabecera.addLayout(layout_texto_cabecera)
        self.layout_cabecera.addStretch()
        layout_contenido.addLayout(self.layout_cabecera)

        # 2. Área de Chat
        self.marco_chat = QFrame()
        self.marco_chat.setObjectName("ContenedorChat")
        
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(20)
        sombra.setColor(QColor(0, 0, 0, 80))
        sombra.setOffset(0, 4)
        self.marco_chat.setGraphicsEffect(sombra)

        layout_chat = QVBoxLayout(self.marco_chat)
        layout_chat.setContentsMargins(10, 10, 10, 10) 

        self.pantalla_chat = QTextEdit()
        self.pantalla_chat.setReadOnly(True)
        layout_chat.addWidget(self.pantalla_chat)
        
        layout_contenido.addWidget(self.marco_chat)

        # 3. Barra de Progreso
        self.progreso = QProgressBar()
        self.progreso.setVisible(False)
        layout_contenido.addWidget(self.progreso)

        # 4. Área de Input
        self.marco_entrada = QFrame()
        self.marco_entrada.setObjectName("ContenedorEntrada")
        self.marco_entrada.setFixedHeight(50)
        
        layout_entrada = QHBoxLayout(self.marco_entrada)
        layout_entrada.setContentsMargins(5, 5, 5, 5)
        layout_entrada.setSpacing(10)

        self.btn_subir = QPushButton("📎")
        self.btn_subir.setObjectName("BotonAdjuntar")
        self.btn_subir.setFixedSize(40, 40)
        self.btn_subir.setToolTip("Cargar PDF o DOCX")
        self.btn_subir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_subir.clicked.connect(self.subir_documento)

        self.btn_micro = QPushButton("🎤")
        self.btn_micro.setObjectName("BotonMicro")
        self.btn_micro.setFixedSize(40, 40)
        self.btn_micro.setToolTip("Dictar por voz")
        self.btn_micro.setCheckable(True)
        self.btn_micro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_micro.clicked.connect(self.alternar_entrada_voz)
        
        self.entrada_mensaje = QLineEdit()
        self.entrada_mensaje.setPlaceholderText("Escribe un mensaje a ChatBoot...")
        self.entrada_mensaje.returnPressed.connect(self.enviar_mensaje)

        self.btn_enviar = QPushButton("➤")
        self.btn_enviar.setObjectName("BotonEnviar")
        self.btn_enviar.setFixedSize(40, 40)
        self.btn_enviar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enviar.clicked.connect(self.enviar_mensaje)

        layout_entrada.addWidget(self.btn_subir)
        layout_entrada.addWidget(self.btn_micro)
        layout_entrada.addWidget(self.entrada_mensaje)
        layout_entrada.addWidget(self.btn_enviar)

        layout_contenido.addWidget(self.marco_entrada)

        layout_principal.addWidget(widget_barra_lateral)
        layout_principal.addWidget(widget_contenido)

    # --- LÓGICA: MENÚ CONTEXTUAL (ELIMINAR) ---
    def mostrar_menu_contextual(self, pos: QPoint):
        item = self.lista_historial.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        accion_eliminar = QAction("Eliminar conversación", self)
        accion_eliminar.triggered.connect(lambda: self.eliminar_item_chat(item))
        menu.addAction(accion_eliminar)
        menu.exec(self.lista_historial.mapToGlobal(pos))

    def eliminar_item_chat(self, item):
        id_chat = item.data(Qt.ItemDataRole.UserRole)
        respuesta = QMessageBox.question(self, 'Eliminar', "¿Eliminar este chat permanentemente?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if respuesta == QMessageBox.StandardButton.Yes:
            GestorAlmacenamiento.eliminar_chat(id_chat)
            self.refrescar_barra_lateral()
            if id_chat == self.id_chat_actual: self.crear_nuevo_chat()

    # --- LÓGICA: BURBUJAS DE CHAT ---
    def renderizar_chat(self):
        self.pantalla_chat.clear()
        for msg in self.historial_chat:
            self.agregar_burbuja_html(msg['text'], msg['sender'])
        sb = self.pantalla_chat.verticalScrollBar()
        sb.setValue(sb.maximum())

    def agregar_burbuja_html(self, texto, remitente):
        # 1. Escapar caracteres HTML y procesar bloques de código
        partes = texto.split("```")
        contenido_html_final = ""

        for i, parte in enumerate(partes):
            if i % 2 == 0: # TEXTO NORMAL
                texto_limpio = html.escape(parte).replace("\n", "<br>")
                contenido_html_final += texto_limpio
            else: # BLOQUE DE CÓDIGO
                contenido_codigo = parte
                if "\n" in contenido_codigo:
                    primera_linea = contenido_codigo.split("\n", 1)[0].strip()
                    if len(primera_linea) < 15 and " " not in primera_linea: 
                         contenido_codigo = contenido_codigo.split("\n", 1)[1]
                
                contenido_codigo = html.escape(contenido_codigo)
                
                contenido_html_final += f"""
                <div style="
                    background-color: #121212;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 10px;
                    margin: 10px 0;
                    font-family: 'Consolas', monospace;
                    font-size: 13px;
                    color: #dcdcdc;
                ">
                    <pre style="margin: 0; white-space: pre-wrap;">{contenido_codigo}</pre>
                </div>
                """

        # 2. Definir Márgenes Laterales (Centrado)
        padding_lateral = "15%" 

        if remitente == "user":
            html_burbuja = f"""
            <table width="100%" border="0" cellpadding="0" cellspacing="0">
                <tr>
                    <td width="{padding_lateral}"></td> 
                    <td align="right" style="padding-right: 10px;">
                        <table border="0" cellpadding="0" cellspacing="0" style="background-color: #007acc; border-radius: 15px 15px 0px 15px;">
                            <tr>
                                <td style="padding: 10px 16px; color: white; font-family: 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.4;">
                                    {contenido_html_final}
                                </td>
                            </tr>
                        </table>
                    </td>
                    <td width="{padding_lateral}"></td>
                </tr>
            </table>
            <br>
            """
        else:
            html_burbuja = f"""
            <table width="100%" border="0" cellpadding="0" cellspacing="0">
                <tr>
                    <td width="{padding_lateral}"></td>
                    <td align="left" style="padding-left: 10px;">
                        <table border="0" cellpadding="0" cellspacing="0" style="background-color: #333333; border-radius: 15px 15px 15px 0px;">
                            <tr>
                                <td style="padding: 10px 16px; color: #e6e6e6; font-family: 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.4;">
                                    {contenido_html_final}
                                </td>
                            </tr>
                        </table>
                    </td>
                    <td width="{padding_lateral}"></td>
                </tr>
            </table>
            <br>
            """
        
        cursor = self.pantalla_chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.pantalla_chat.setTextCursor(cursor)
        self.pantalla_chat.insertHtml(html_burbuja)
        
        sb = self.pantalla_chat.verticalScrollBar()
        sb.setValue(sb.maximum())

    # --- LÓGICA: ESTADO Y BARRA LATERAL ---
    def crear_nuevo_chat(self):
        self.id_chat_actual = str(datetime.now().timestamp())
        self.historial_chat = []
        self.fragmentos_actuales = []
        self.ruta_doc_actual = None
        self.rag.establecer_fragmentos([])
        
        self.pantalla_chat.clear()
        self.entrada_mensaje.clear()
        self.actualizar_estado_cabecera()
        
        msg_bienvenida = "Soy tu asistente. Usa el clip (📎) para cargar un documento."
        self.historial_chat.append({"sender": "bot", "text": msg_bienvenida})
        self.renderizar_chat()
        
        self.guardar_estado_actual()
        self.refrescar_barra_lateral()

    def actualizar_estado_cabecera(self):
        if self.ruta_doc_actual:
            nombre_archivo = os.path.basename(self.ruta_doc_actual)
            self.etiqueta_doc.setText(nombre_archivo)
            self.subetiqueta_estado.setText("Documento cargado • Modo RAG Activo")
            self.etiqueta_doc.setStyleSheet("font-size: 18px; font-weight: 600; color: #007acc;")
        else:
            self.etiqueta_doc.setText("Chat General")
            self.subetiqueta_estado.setText("Asistente de IA (Sin contexto)")
            self.etiqueta_doc.setStyleSheet("font-size: 18px; font-weight: 600; color: #f0f0f0;")

    def refrescar_barra_lateral(self):
        self.lista_historial.clear()
        chats = GestorAlmacenamiento.listar_chats()
        for chat in chats:
            item = QListWidgetItem(chat["title"])
            item.setData(Qt.ItemDataRole.UserRole, chat["id"])
            self.lista_historial.addItem(item)

    def cargar_chat_seleccionado(self, item):
        id_chat = item.data(Qt.ItemDataRole.UserRole)
        datos = GestorAlmacenamiento.cargar_chat(id_chat)
        if not datos: return

        self.id_chat_actual = datos["id"]
        self.historial_chat = datos["messages"]
        self.ruta_doc_actual = datos.get("doc_path")
        self.fragmentos_actuales = datos.get("chunks", [])
        
        self.rag.establecer_fragmentos(self.fragmentos_actuales)
        self.actualizar_estado_cabecera()
        self.renderizar_chat()

    def guardar_estado_actual(self):
        if not self.historial_chat: return
        
        if self.ruta_doc_actual:
            titulo = f"📄 {os.path.basename(self.ruta_doc_actual)}"
        elif len(self.historial_chat) > 1:
            primer_msg_usuario = next((m['text'] for m in self.historial_chat if m['sender'] == 'user'), "Conversación")
            titulo = (primer_msg_usuario[:25] + '...') if len(primer_msg_usuario) > 25 else primer_msg_usuario
        else:
            titulo = "Nuevo Chat"

        GestorAlmacenamiento.guardar_chat(self.id_chat_actual, titulo, self.historial_chat, self.fragmentos_actuales, self.ruta_doc_actual)

    # --- LÓGICA: SUBIDA DE ARCHIVOS ---
    def subir_documento(self):
        if not self.gemini and CLAVE_API_GEMINI == "TU_API_KEY_AQUI":
             QMessageBox.critical(self, "Error", "Falta la API Key en el código.")
             return

        ruta_archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar", "", "PDF/DOCX (*.pdf *.docx)")
        if ruta_archivo:
            ruta_local = GestorAlmacenamiento.guardar_documento(ruta_archivo)
            self.ruta_doc_actual = ruta_local
            
            self.subetiqueta_estado.setText(f"Procesando {os.path.basename(ruta_local)}...")
            self.progreso.setVisible(True)
            self.progreso.setRange(0, 0)
            self.btn_subir.setEnabled(False)
            
            self.hilo_trabajador = HiloTrabajador(self.procesar_tuberia, ruta_local)
            self.hilo_trabajador.finalizado.connect(self.al_finalizar_subida)
            self.hilo_trabajador.error.connect(self.al_error_subida)
            self.hilo_trabajador.start()

    def procesar_tuberia(self, ruta_archivo):
        texto_crudo = CargadorDocumentos.cargar_archivo(ruta_archivo)
        if not texto_crudo.strip(): raise Exception("Documento vacío.")
        if not self.gemini: self.gemini = ProcesadorGemini(CLAVE_API_GEMINI)
        return self.gemini.procesar_y_segmentar(texto_crudo)

    def al_finalizar_subida(self, fragmentos):
        self.fragmentos_actuales = fragmentos
        self.rag.establecer_fragmentos(fragmentos)
        self.progreso.setVisible(False)
        self.btn_subir.setEnabled(True)
        self.actualizar_estado_cabecera()
        
        msg_sistema = "He procesado el documento.✅Análisis completado. Hazme cualquier pregunta sobre él"
        self.historial_chat.append({"sender": "bot", "text": msg_sistema})
        self.agregar_burbuja_html(msg_sistema, "bot")
        
        self.guardar_estado_actual()
        self.refrescar_barra_lateral()

    def al_error_subida(self, error):
        self.progreso.setVisible(False)
        self.btn_subir.setEnabled(True)
        self.subetiqueta_estado.setText("Error en carga")
        QMessageBox.critical(self, "Error", error)

    # --- LÓGICA: ENTRADA DE VOZ ---
    def alternar_entrada_voz(self):
        if self.btn_micro.isChecked():
            # Iniciar Grabación
            self.entrada_mensaje.setPlaceholderText("Escuchando... (Haz clic en el micro para enviar)")
            self.entrada_mensaje.setEnabled(False)
            self.btn_enviar.setEnabled(False)
            self.btn_subir.setEnabled(False)
            
            self.hilo_voz = HiloVoz()
            self.hilo_voz.finalizado.connect(self.al_reconocer_voz)
            self.hilo_voz.error.connect(self.al_error_voz)
            self.hilo_voz.start()
        else:
            # Detener Grabación
            if hasattr(self, 'hilo_voz') and self.hilo_voz.isRunning():
                self.entrada_mensaje.setPlaceholderText("Procesando voz...")
                self.hilo_voz.detener()

    def al_reconocer_voz(self, texto):
        self.entrada_mensaje.setEnabled(True)
        self.btn_enviar.setEnabled(True)
        self.btn_subir.setEnabled(True)
        self.entrada_mensaje.setPlaceholderText("Escribe un mensaje a ChatBoot...")
        self.btn_micro.setChecked(False)
        
        if texto:
            self.entrada_mensaje.setText(texto)
            self.enviar_mensaje()
    
    def al_error_voz(self, error):
        self.entrada_mensaje.setEnabled(True)
        self.btn_enviar.setEnabled(True)
        self.btn_subir.setEnabled(True)
        self.entrada_mensaje.setPlaceholderText("Escribe un mensaje a ChatBoot...")
        self.btn_micro.setChecked(False)
        # Opcional: Mostrar error o log
        if "No se escuchó nada" not in error:
             print(f"Error voz: {error}")

    # --- LÓGICA: INDICADOR DE PENSANDO ---
    def mostrar_indicador_pensando(self):
        self.contador_puntos = 0
        cursor = self.pantalla_chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.pos_pensando = cursor.position()
        
        self.agregar_burbuja_pensando("Pensando")
        self.temporizador_pensando.start(400)
        
        self.btn_enviar.setEnabled(False)
        self.entrada_mensaje.setEnabled(False)
        self.btn_subir.setEnabled(False)

    def actualizar_indicador_pensando(self):
        marcos = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.contador_puntos = (self.contador_puntos + 1) % len(marcos)
        icono = marcos[self.contador_puntos]
        
        # Animación de puntos
        puntos = "." * ((self.contador_puntos % 4))
        
        # Limpiar última burbuja
        cursor = self.pantalla_chat.textCursor()
        cursor.setPosition(self.pos_pensando)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        self.agregar_burbuja_pensando(f"{icono} ChatBoot está pensando{puntos}")

    def agregar_burbuja_pensando(self, texto):
        padding_lateral = "15%"
        html_burbuja = f"""
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr>
                <td width="{padding_lateral}"></td>
                <td align="left" style="padding-left: 10px;">
                    <table border="0" cellpadding="0" cellspacing="0" style="background-color: #333333; border-radius: 15px 15px 15px 0px;">
                        <tr>
                            <td style="padding: 10px 16px; color: #888; font-family: 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.4; font-style: italic;">
                                {texto}
                            </td>
                        </tr>
                    </table>
                </td>
                <td width="{padding_lateral}"></td>
            </tr>
        </table>
        <br>
        """
        cursor = self.pantalla_chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.pantalla_chat.setTextCursor(cursor)
        self.pantalla_chat.insertHtml(html_burbuja)
        
        sb = self.pantalla_chat.verticalScrollBar()
        sb.setValue(sb.maximum())

    def ocultar_indicador_pensando(self):
        if self.temporizador_pensando.isActive():
            self.temporizador_pensando.stop()
        
        if hasattr(self, 'pos_pensando'):
            cursor = self.pantalla_chat.textCursor()
            cursor.setPosition(self.pos_pensando)
            cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            delattr(self, 'pos_pensando')
            
        self.btn_enviar.setEnabled(True)
        self.entrada_mensaje.setEnabled(True)
        self.btn_subir.setEnabled(True)
        self.entrada_mensaje.setFocus()

    def al_error_respuesta(self, msg_error):
        self.ocultar_indicador_pensando()
        QMessageBox.critical(self, "Error de respuesta", f"Ocurrió un error: {msg_error}")

    # --- LÓGICA: MENSAJERÍA ---
    def enviar_mensaje(self):
        texto = self.entrada_mensaje.text().strip()
        if not texto: return

        self.entrada_mensaje.clear()
        self.historial_chat.append({"sender": "user", "text": texto})
        self.agregar_burbuja_html(texto, "user")
        
        self.mostrar_indicador_pensando()
        
        self.hilo_trabajador = HiloTrabajador(self.generar_respuesta, texto)
        self.hilo_trabajador.finalizado.connect(self.al_tener_respuesta)
        self.hilo_trabajador.error.connect(self.al_error_respuesta)
        self.hilo_trabajador.start()

    def generar_respuesta(self, pregunta):
        es_rag = (len(self.fragmentos_actuales) > 0)
        contexto = self.rag.recuperar(pregunta) if es_rag else ""
        return self.ollama.generar_respuesta(contexto, pregunta, modo_rag=es_rag)

    def al_tener_respuesta(self, respuesta):
        self.ocultar_indicador_pensando()
        self.historial_chat.append({"sender": "bot", "text": respuesta})
        self.agregar_burbuja_html(respuesta, "bot")
        self.guardar_estado_actual()
        self.refrescar_barra_lateral()
