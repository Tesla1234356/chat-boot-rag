class MotorRAG:
    def __init__(self):
        self.fragmentos = []

    def establecer_fragmentos(self, fragmentos):
        self.fragmentos = fragmentos

    def recuperar(self, consulta, top_k=15):
        """
        Recupera fragmentos relevantes con un 'Bono de Coincidencia de Frase'.
        Si frases específicas de la consulta aparecen en el fragmento, obtiene un aumento masivo de puntuación.
        """
        if not self.fragmentos:
            return ""

        import string
        traductor = str.maketrans('', '', string.punctuation)
        
        # Normalización
        consulta_limpia = consulta.translate(traductor).lower()
        palabras_consulta = set(consulta_limpia.split())
        
        puntuaciones = []
        for fragmento in self.fragmentos:
            fragmento_limpio = fragmento.translate(traductor).lower()
            palabras_fragmento = set(fragmento_limpio.split())
            
            # 1. Puntuación Base: Coincidencia de palabras (Intersección)
            interseccion = palabras_consulta.intersection(palabras_fragmento)
            puntuacion_base = len(interseccion)
            
            # 2. Bono de Frase Exacta (Bi-gramas y Tri-gramas)
            bono = 0
            if consulta_limpia in fragmento_limpio:
                bono += 50  # ¡Coincidencia exacta gigante!
            
            # Buscamos sub-frases de 2 o 3 palabras
            lista_q = consulta_limpia.split()
            if len(lista_q) > 1:
                for i in range(len(lista_q) - 1):
                    bigrama = f"{lista_q[i]} {lista_q[i+1]}"
                    if bigrama in fragmento_limpio:
                        bono += 5  # Bono por coincidencia parcial de frase
            
            puntuacion_final = puntuacion_base + bono
            puntuaciones.append((puntuacion_final, fragmento))

        # Ordenar por puntuación descendente
        puntuaciones.sort(key=lambda x: x[0], reverse=True)

        # Devolver los mejores K
        mejores_fragmentos = [item[1] for item in puntuaciones[:top_k]]
        
        return "\n---\n".join(mejores_fragmentos)