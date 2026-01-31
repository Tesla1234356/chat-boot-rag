import sys
import os
from PyQt6.QtWidgets import QApplication
from app.interfaz import VentanaPrincipal

def principal():
    app = QApplication(sys.argv)
    
    # Opcional: Establecer un estilo o tema aquí
    app.setStyle('Fusion')
    
    ventana = VentanaPrincipal()
    ventana.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    principal()
