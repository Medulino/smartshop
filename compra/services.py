import io
import PIL.Image
import PIL.ImageOps
from django.conf import settings


def redimensionar_imagen(imagen_file, max_lado=1600, max_peso_mb=15):
    imagen_file.seek(0, 2)
    peso_mb = imagen_file.tell() / (1024 * 1024)
    imagen_file.seek(0)

    if peso_mb > max_peso_mb:
        raise ValueError(f"La imagen pesa demasiado ({peso_mb:.1f}MB). Máximo {max_peso_mb}MB.")

    try:
        img = PIL.Image.open(imagen_file)
        img.verify()
        imagen_file.seek(0)
        img = PIL.Image.open(imagen_file)
    except Exception:
        raise ValueError("El archivo no es una imagen válida.")

    img = PIL.ImageOps.exif_transpose(img)

    ancho, alto = img.size
    lado_mayor = max(ancho, alto)

    if lado_mayor > max_lado:
        ratio = max_lado / lado_mayor
        nuevo_tamano = (int(ancho * ratio), int(alto * ratio))
        img = img.resize(nuevo_tamano, PIL.Image.LANCZOS)

    if img.mode != 'RGB':
        img = img.convert('RGB')

    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85, optimize=True)
    buffer.seek(0)
    return buffer


import PIL.Image
import google.generativeai as genai

def leer_lista_desde_imagen(imagen_file):
    """
    Transcribe una lista de la compra manuscrita a partir de una imagen
    utilizando el modelo estable Gemini 1.5 Flash.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)

    prompt = """
    Eres un experto en transcripción de listas de la compra.
    En la imagen hay una lista de compra manuscrita o escrita.
    Extrae únicamente los nombres de los productos.
    Devuelve SOLO los productos separados por comas, sin explicaciones,
    sin numeración, sin guiones. Ejemplo: leche, pan, tomates, jabón
    """

    try:
        # Preparamos y abrimos la imagen
        buffer_reducido = redimensionar_imagen(imagen_file)
        img = PIL.Image.open(buffer_reducido)

        # Usamos directamente el modelo rápido, económico y estable de producción
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt, img])

        if response.text:
            # Normalizamos saltos de línea y puntos y comas a comas simples
            texto = response.text.replace('\n', ',').replace(';', ',')
            productos = [
                p.strip().lower()
                for p in texto.split(',')
                if p.strip() and len(p.strip()) > 1
            ]
            return productos, None

        return [], "No se pudo extraer texto de la imagen."

    except Exception as e:
        error_msg = str(e)[:100]
        return [], f"El servicio de análisis no está disponible ahora mismo. ({error_msg})"