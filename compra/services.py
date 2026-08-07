import io
import PIL.Image
import PIL.ImageOps
from django.conf import settings


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


def leer_lista_desde_imagen(imagen_file):
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    modelos = [
    'gemini-3-flash-preview',
    'gemini-robotics-er-1.6-preview',
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
            response = model.generate_content([prompt, img])
            if response.text:
                texto = response.text.replace('\n', ',').replace(';', ',')
                productos = [
                    p.strip().lower()
                    for p in texto.split(',')
                    if p.strip() and len(p.strip()) > 1
                ]
                return productos, None
        except Exception as e:
            ultimo_error = str(e)
            continue

    return [], f"El servicio de análisis no está disponible ahora mismo. Inténtalo más tarde. ({ultimo_error[:100]})"