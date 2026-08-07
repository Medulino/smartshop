import unicodedata


def normalizar(texto):
    """Minúsculas y sin tildes/diacríticos, para comparar sin depender de acentos."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in texto if not unicodedata.combining(c))
