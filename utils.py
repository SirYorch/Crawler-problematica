import re
import emoji
import os

# Asegurar directorios de salida
for folder in ["sesiones"]:
    os.makedirs(folder, exist_ok=True)


def limpiar_texto(texto):
    # 1. Convertir a minúsculas
    texto = texto.lower()

    # 2. Quitar URLs
    texto = re.sub(r'http\S+|www\S+|https\S+', '', texto, flags=re.MULTILINE)

    # 3. Quitar menciones (@usuario) y hashtags (#tema)
    texto = re.sub(r'@\w+|#\w+', '', texto)

    # 4. Quitar emoticones
    texto = emoji.replace_emoji(texto, replace='')

    # 5. Eliminar espacios vacíos extra
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto
