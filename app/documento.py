import pdfplumber
import docx
import os

class CargadorDocumentos:
    @staticmethod
    def cargar_archivo(ruta_archivo):
        """Detecta el tipo de archivo y extrae el texto sin procesar."""
        extension = os.path.splitext(ruta_archivo)[1].lower()
        if extension == '.pdf':
            return CargadorDocumentos._leer_pdf(ruta_archivo)
        elif extension == '.docx':
            return CargadorDocumentos._leer_docx(ruta_archivo)
        else:
            raise ValueError("Formato de archivo no soportado. Por favor use PDF o DOCX.")

    @staticmethod
    def _leer_pdf(ruta_archivo):
        texto = ""
        try:
            with pdfplumber.open(ruta_archivo) as pdf:
                for pagina in pdf.pages:
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto += texto_pagina + "\n"
        except Exception as e:
            raise Exception(f"Error leyendo PDF: {e}")
        return texto

    @staticmethod
    def _leer_docx(ruta_archivo):
        texto = ""
        try:
            doc = docx.Document(ruta_archivo)
            for para in doc.paragraphs:
                texto += para.text + "\n"
        except Exception as e:
            raise Exception(f"Error leyendo DOCX: {e}")
        return texto
