import io
import logging

import PIL.Image
import PIL.ImageOps
from django.conf import settings
from .utils import normalizar

logger = logging.getLogger(__name__)

# Topes a la salida de la IA para evitar abusos (import_bloque se alimenta
# con texto estructurado, tanto pegado por el usuario como generado por Gemini).
MAX_PASILLOS_IMPORTACION = 100
MAX_KEYWORDS_POR_PASILLO = 30


def sugerir_categorias(nombre_pasillo):
    """
    Categorías globales cuyo nombre (o alguno de sus "trozos" separados
    por '/', para las compuestas tipo "Droguería / Animales") aparece en
    el nombre del pasillo o viceversa. Se usa para etiquetar pasillos
    automáticamente al crearlos, sin que el usuario tenga que hacer nada.
    """
    from .models import Categoria

    nombre_norm = normalizar(nombre_pasillo)
    sugeridas = []
    for categoria in Categoria.objects.all():
        trozos = [normalizar(t) for t in categoria.nombre.split('/')]
        for trozo in trozos:
            trozo = trozo.strip()
            if trozo and (trozo in nombre_norm or nombre_norm in trozo):
                sugeridas.append(categoria)
                break
    return sugeridas


def importar_bloque(texto, supermercado):
    """
    Crea pasillos (y sus keywords) a partir de texto pegado o dictado,
    uno por línea, formato 'Nombre del pasillo: palabra1, palabra2...'.
    Las palabras clave son opcionales (una línea sin ':' crea el pasillo
    sin keywords). Los pasillos se añaden a continuación de los que ya
    tenga el supermercado. Devuelve cuántos pasillos se crearon.
    """
    from .models import Pasillo, Keyword

    orden = supermercado.pasillos.count() + 1
    creados = 0

    for linea in texto.splitlines()[:MAX_PASILLOS_IMPORTACION]:
        linea = linea.strip()
        if not linea:
            continue

        if ':' in linea:
            nombre, resto = linea.split(':', 1)
            palabras = [
                p.strip().lower().rstrip('.,;')[:100]
                for p in resto.split(',')
                if p.strip()
            ][:MAX_KEYWORDS_POR_PASILLO]
            palabras = [p for p in palabras if p]
        else:
            nombre, palabras = linea, []

        nombre = nombre.strip()[:200]
        if not nombre:
            continue

        pasillo = Pasillo.objects.create(
            supermercado=supermercado,
            nombre=nombre,
            orden=orden,
        )
        orden += 1
        creados += 1

        if palabras:
            keywords = [Keyword(pasillo=pasillo, palabra=p) for p in palabras]
            Keyword.objects.bulk_create(keywords, ignore_conflicts=True)

        categorias = sugerir_categorias(nombre)
        if categorias:
            pasillo.categorias.set(categorias)

    return creados


def copiar_pasillos_keywords(origen, destino):
    """Copia los pasillos y keywords de un Supermercado a otro ya existente."""
    from .models import Pasillo, Keyword

    for pasillo_original in origen.pasillos.all():
        nuevo_pasillo = Pasillo.objects.create(
            supermercado=destino,
            nombre=pasillo_original.nombre,
            orden=pasillo_original.orden,
        )
        keywords = [
            Keyword(pasillo=nuevo_pasillo, palabra=kw.palabra)
            for kw in pasillo_original.keywords.all()
        ]
        Keyword.objects.bulk_create(keywords, ignore_conflicts=True)

        categorias = list(pasillo_original.categorias.all())
        if categorias:
            nuevo_pasillo.categorias.set(categorias)


def duplicar_supermercado(origen, usuario, nombre=None):
    """
    Copia un Supermercado (con sus pasillos y keywords) como uno nuevo,
    propiedad de `usuario`. Si ya tiene uno con ese nombre, le añade un
    sufijo numérico para no chocar con la restricción unique_together.
    """
    from .models import Supermercado

    nombre_base = nombre or origen.nombre
    nombre_final = nombre_base
    sufijo = 2
    while Supermercado.objects.filter(usuario=usuario, nombre=nombre_final).exists():
        nombre_final = f"{nombre_base} ({sufijo})"
        sufijo += 1

    nuevo = Supermercado.objects.create(
        usuario=usuario,
        nombre=nombre_final,
        direccion=origen.direccion,
        activo=True,
    )
    copiar_pasillos_keywords(origen, nuevo)
    return nuevo


def plantilla_por_defecto():
    """
    Supermercado usado como base al crear uno nuevo desde cero, para no
    empezar totalmente vacío. Prioriza el de un superusuario si hay varios
    con ese nombre (por si algún usuario normal crea el suyo propio
    llamado igual).
    """
    from .models import Supermercado

    return Supermercado.objects.filter(
        nombre="Mercadona Agustinos"
    ).order_by('-usuario__is_superuser').first()


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


def estructurar_pasillos_con_ia(descripcion_libre):
    """
    Convierte una descripción libre de pasillos (dictada o escrita sin
    ningún formato) en el texto estructurado que espera `importar_bloque`
    ("Nombre del pasillo: palabra1, palabra2..."), usando Gemini, para
    que el usuario no tenga que aprender ninguna sintaxis.
    """
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    modelos = [
        'gemini-3-flash-preview',
        'gemini-2.5-flash',
    ]

    prompt = """
    Eres un experto organizando supermercados. Un usuario te va a describir,
    de forma libre y desordenada (puede estar dictado por voz, con errores
    o de forma coloquial), los pasillos de un supermercado y lo que hay en
    cada uno.

    Devuelve el resultado EXCLUSIVAMENTE en este formato, una línea por
    pasillo, sin numerar y sin ningún texto antes ni después:

    Nombre del pasillo: producto1, producto2, producto3...

    Reglas:
    - Una línea por pasillo, sin líneas en blanco entre medio.
    - Las palabras clave en minúsculas, sin tildes si es posible.
    - No repitas la misma palabra clave en dos pasillos distintos.
    - Si el usuario solo da el nombre de una categoría sin productos,
      complétala tú con entre 8 y 15 productos típicos de esa categoría
      en un supermercado español.
    - No añadas explicaciones, numeración, guiones ni comentarios: SOLO
      las líneas con el formato pedido.

    Esto es lo que ha descrito el usuario:
    """ + descripcion_libre

    for nombre_modelo in modelos:
        try:
            model = genai.GenerativeModel(model_name=nombre_modelo)
            response = model.generate_content(
                prompt, request_options={'timeout': 60}
            )
            if response.text:
                return response.text.strip(), None
        except Exception as e:
            logger.warning('Error de IA en estructurar_pasillos_con_ia (%s): %s', nombre_modelo, e)
            continue

    return None, "El servicio de IA no está disponible ahora mismo. Inténtalo más tarde."


def leer_lista_desde_imagen(imagen_file):
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    modelos = [
    'gemini-3-flash-preview',
    'gemini-2.5-flash',
    ]

    prompt = """
    Eres un experto en transcripción de listas de la compra.
    En la imagen hay una lista de compra manuscrita o escrita.
    Extrae únicamente los nombres de los productos.
    Devuelve SOLO los productos separados por comas, sin explicaciones,
    sin numeración, sin guiones. Ejemplo: leche, pan, tomates, jabón
    """

    buffer_reducido = redimensionar_imagen(imagen_file)
    img = PIL.Image.open(buffer_reducido)

    for nombre_modelo in modelos:
        try:
            model = genai.GenerativeModel(model_name=nombre_modelo)
            response = model.generate_content(
                [prompt, img], request_options={'timeout': 60}
            )
            if response.text:
                texto = response.text.replace('\n', ',').replace(';', ',')
                productos = [
                    p.strip().lower()
                    for p in texto.split(',')
                    if p.strip() and len(p.strip()) > 1
                ][:MAX_KEYWORDS_POR_PASILLO]
                return productos, None
        except Exception as e:
            logger.warning('Error de IA en leer_lista_desde_imagen (%s): %s', nombre_modelo, e)
            continue

    return [], "El servicio de análisis no está disponible ahora mismo. Inténtalo más tarde."