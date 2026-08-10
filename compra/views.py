from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import models
from django.core.cache import cache
from .cache_pasillos import CANDIDATOS_TTL, clave_candidatos
from .models import Supermercado, Lista, ListaItem, Pasillo, Keyword, Categoria, CategoriaKeyword
import json
from .utils import normalizar as _normalizar
from usuarios.models import FeatureFlag
from django.conf import settings


def _bloqueo_premium(request, ajax=True):
    """Devuelve una respuesta de bloqueo si el usuario no es premium.

    None si puede pasar. Las funciones premium se protegen siempre en el
    servidor, no solo ocultando el botón en la interfaz: si el usuario no
    es premium, la vista redirige (HTML) o devuelve 403 (AJAX) aunque
    conozca la URL.
    """
    if request.user.es_premium:
        return None

    from django.contrib import messages
    from django.shortcuts import redirect

    if ajax:
        return JsonResponse({
            'error': 'Esto es Premium. Hazte premium para usar esta función.',
            'premium': True,
        }, status=403)

    messages.info(request, 'Esto es Premium: mejora tu plan para usarlo.')
    return redirect('usuarios:premium')


def _candidatos(supermercado):
    """Palabras de pasillos (propias + heredadas de categorías globales)
    cacheadas por supermercado, para no re-leerlas por cada producto."""
    clave = clave_candidatos(supermercado)
    candidatos = cache.get(clave)
    if candidatos is not None:
        return candidatos

    candidatos = []
    keywords_propias = Keyword.objects.filter(
        pasillo__supermercado=supermercado
    ).select_related('pasillo')
    for kw in keywords_propias:
        candidatos.append((_normalizar(kw.palabra), kw.pasillo_id))

    pasillos = Pasillo.objects.filter(
        supermercado=supermercado
    ).prefetch_related('categorias__keywords')
    for pasillo in pasillos:
        for categoria in pasillo.categorias.all():
            for ck in categoria.keywords.all():
                candidatos.append((_normalizar(ck.palabra), pasillo.id))

    cache.set(clave, candidatos, CANDIDATOS_TTL)
    return candidatos


def _json_body(request):
    """Devuelve el body parseado como dict o None si el JSON es inválido."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


@require_GET
def salud(request):
    """Healthcheck: devuelve 200 solo si la BD responde. Sin datos sensibles."""
    from django.db import connection
    from django.http import JsonResponse

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'estado': 'ok'})
    except Exception:
        return JsonResponse({'estado': 'error'}, status=503)


def inferir_pasillo(nombre_producto, supermercado):
    """
    Busca la keyword más específica que encaje con el nombre del producto.
    Combina dos fuentes: las keywords propias del pasillo (Keyword) y las
    de cualquier categoría global con la que esté etiquetado (Pasillo.
    categorias -> CategoriaKeyword), para que un supermercado nuevo con
    pocas keywords propias siga teniendo buena cobertura si sus pasillos
    están etiquetados.

    Prioridad: coincidencia exacta > keyword contenida en el nombre (la más
    larga gana) > nombre contenido en una keyword (la más corta gana), para
    que compuestos genéricos ("sal", "fresa", "patata"...) no le roben el
    pasillo a coincidencias más precisas ("salchichón", "yogur de fresa",
    "patatas fritas"...).
    """
    nombre = _normalizar(nombre_producto)

    candidatos = _candidatos(supermercado)  # (palabra_normalizada, pasillo_id)

    contenidas = []
    contenedoras = []
    for palabra, pasillo_id in candidatos:
        if not palabra:
            continue
        if palabra == nombre:
            return Pasillo.objects.filter(pk=pasillo_id).first()
        if palabra in nombre:
            contenidas.append((len(palabra), pasillo_id))
        elif nombre in palabra:
            contenedoras.append((len(palabra), pasillo_id))

    if contenidas:
        return Pasillo.objects.filter(pk=max(contenidas, key=lambda x: x[0])[1]).first()
    if contenedoras:
        return Pasillo.objects.filter(pk=min(contenedoras, key=lambda x: x[0])[1]).first()
    return None


@method_decorator(login_required, name='dispatch')
class ListaCompraView(View):
    template_name = 'compra/lista.html'

    def get(self, request):
        supermercados = list(
            Supermercado.objects.filter(
                usuario=request.user,
                activo=True
            ).prefetch_related('pasillos')
        )

        super_id = request.GET.get('supermercado')
        if super_id:
            supermercado = get_object_or_404(
                Supermercado.objects.prefetch_related('pasillos'),
                id=super_id,
                usuario=request.user
            )
        elif supermercados:
            supermercado = supermercados[0]
        else:
            supermercado = None

        lista = None
        items = []
        if supermercado:
            lista, _ = Lista.objects.get_or_create(
                supermercado=supermercado,
                usuario=request.user,
                activa=True,
                defaults={}
            )
            lista = Lista.objects.annotate(
                num_productos=models.Count('items'),
                num_carro=models.Count('items', filter=models.Q(items__en_carro=True)),
                num_pendientes=models.Count('items', filter=models.Q(items__en_carro=False)),
            ).get(pk=lista.pk)
            lista.supermercado = supermercado
            items = lista.items.select_related('pasillo').all()

        return render(request, self.template_name, {
            'supermercados': supermercados,
            'supermercado': supermercado,
            'lista': lista,
            'items': items,
        })


@login_required
@require_POST
def añadir_producto(request):
    resp = _rechazo_limite_escritura(request)
    if resp:
        return resp
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    texto = str(data.get('nombre') or '').strip()[:5000]
    lista_id = data.get('lista_id')

    if not texto or not lista_id:
        return JsonResponse({'error': 'Datos incompletos'}, status=400)

    try:
        lista_id = int(lista_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'lista_id inválido'}, status=400)

    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)

    nombres = [
        p.strip()[:200]
        for p in texto.replace('\n', ',').replace(';', ',').split(',')
        if p.strip()
    ][:50]

    items_creados = []
    for nombre in nombres:
        pasillo = inferir_pasillo(nombre, lista.supermercado)
        item = ListaItem.objects.create(
            lista=lista,
            nombre=nombre,
            pasillo=pasillo
        )
        items_creados.append({
            'id': item.id,
            'nombre': item.nombre,
            'pasillo': item.pasillo.nombre if item.pasillo else 'Sin asignar',
            'pasillo_orden': item.pasillo.orden if item.pasillo else 999,
            'en_carro': item.en_carro,
        })

    return JsonResponse({'items': items_creados})


@login_required
@require_POST
def toggle_en_carro(request, item_id):
    item = get_object_or_404(
        ListaItem,
        id=item_id,
        lista__usuario=request.user
    )
    item.en_carro = not item.en_carro
    item.save()
    return JsonResponse({'en_carro': item.en_carro})


@login_required
@require_POST
def eliminar_producto(request, item_id):
    item = get_object_or_404(
        ListaItem,
        id=item_id,
        lista__usuario=request.user
    )
    item.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def vaciar_lista(request, lista_id):
    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)
    lista.items.all().delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def vaciar_marcados(request, lista_id):
    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)
    lista.items.filter(en_carro=True).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def asignar_pasillo(request, item_id):
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    pasillo_id = data.get('pasillo_id')

    if not pasillo_id:
        return JsonResponse({'error': 'Falta el pasillo'}, status=400)

    item = get_object_or_404(
        ListaItem,
        id=item_id,
        lista__usuario=request.user
    )
    pasillo = get_object_or_404(
        Pasillo,
        id=pasillo_id,
        supermercado__usuario=request.user
    )

    item.pasillo = pasillo
    item.save()

    palabra = _normalizar(item.nombre)
    Keyword.objects.filter(
        pasillo__supermercado=pasillo.supermercado,
        palabra=palabra
    ).exclude(pasillo=pasillo).delete()
    Keyword.objects.get_or_create(
        pasillo=pasillo,
        palabra=palabra
    )

    return JsonResponse({
        'ok': True,
        'pasillo': pasillo.nombre,
        'pasillo_orden': pasillo.orden,
    })


def usuario_supero_limite(usuario, accion, limite=10, ventana_segundos=3600):
    """
    Comprueba si el usuario ha superado el límite de usos de una acción
    (identificada por `accion`) en la ventana de tiempo dada. Respaldado
    en base de datos para que el contador sea compartido entre workers.
    """
    from usuarios.seguridad import supero_limite
    return supero_limite(f"uso_{accion}_{usuario.id}", limite, ventana_segundos)


def usuario_supero_limite_fotos(usuario, limite=10, ventana_segundos=3600):
    return usuario_supero_limite(usuario, 'fotos', limite, ventana_segundos)


def _rechazo_limite_escritura(request, limite=300, ventana_segundos=3600):
    """Rate limit por usuario para los endpoints que crean datos en la BD
    (productos, pasillos, plantillas, copias de supermercados). Devuelve la
    respuesta 429 si se supera, o None si el usuario puede seguir."""
    if usuario_supero_limite(request.user, 'escritura', limite, ventana_segundos):
        return JsonResponse({
            'error': f'Has alcanzado el límite de {limite} escrituras por hora.'
        }, status=429)
    return None


@login_required
@require_POST
def analizar_foto(request):
    lista_id = request.POST.get('lista_id')
    foto = request.FILES.get('foto')

    if not lista_id or not foto:
        return JsonResponse({'error': 'Faltan datos'}, status=400)

    peso = int(request.META.get('CONTENT_LENGTH') or 0)
    if peso > 16 * 1024 * 1024:
        return JsonResponse({'error': 'La foto supera los 16MB.'}, status=413)

    if usuario_supero_limite_fotos(request.user):
        return JsonResponse({
            'error': 'Has alcanzado el límite de 10 fotos por hora. Inténtalo más tarde.'
        }, status=429)

    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)

    from .services import leer_lista_desde_imagen

    try:
        productos, error = leer_lista_desde_imagen(foto)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

    if error:
        return JsonResponse({'error': error}, status=500)

    items_creados = []
    for nombre in productos:
        if nombre:
            pasillo = inferir_pasillo(nombre, lista.supermercado)
            item = ListaItem.objects.create(
                lista=lista,
                nombre=nombre,
                pasillo=pasillo
            )
            items_creados.append({
                'id': item.id,
                'nombre': item.nombre,
                'pasillo': item.pasillo.nombre if item.pasillo else 'Sin asignar',
            })

    return JsonResponse({
        'ok': True,
        'productos_añadidos': len(items_creados),
        'items': items_creados,
    })

@method_decorator(login_required, name='dispatch')
class ConfiguracionView(View):
    """Lista los supermercados del usuario. Elegir uno lleva al detalle
    (pasillos/keywords) para no amontonarlo todo en una sola pantalla."""
    template_name = 'compra/configuracion.html'

    def get(self, request):
        supermercados_qs = Supermercado.objects.filter(
            usuario=request.user
        ).annotate(
            num_pasillos=models.Count('pasillos', distinct=True),
            num_likes=models.Count('likes', distinct=True),
        ).order_by('nombre')
        supermercados = Paginator(supermercados_qs, 20).get_page(
            request.GET.get('page')
        )
        return render(request, self.template_name, {
            'supermercados': supermercados,
        })


@method_decorator(login_required, name='dispatch')
class SupermercadoDetalleView(View):
    """Gestión de pasillos y keywords de UN supermercado del usuario."""
    template_name = 'compra/supermercado_detalle.html'

    def get(self, request, supermercado_id):
        supermercado = get_object_or_404(
            Supermercado.objects.prefetch_related(
                'pasillos__keywords', 'pasillos__categorias'
            ).annotate(num_likes=models.Count('likes', distinct=True)),
            id=supermercado_id, usuario=request.user
        )
        return render(request, self.template_name, {
            'super': supermercado,
            'categorias': Categoria.objects.all(),
        })


@login_required
@require_POST
def crear_supermercado(request):
    from .services import (
        plantilla_por_defecto, copiar_pasillos_keywords,
        importar_bloque, estructurar_pasillos_con_ia,
    )

    resp = _rechazo_limite_escritura(request)
    if resp:
        return resp
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    nombre = str(data.get('nombre') or '').strip()[:200]
    direccion = str(data.get('direccion') or '').strip()[:300]
    descripcion = str(data.get('descripcion') or '').strip()[:10000]

    if not nombre:
        return JsonResponse({'error': 'Falta el nombre'}, status=400)

    if Supermercado.objects.filter(usuario=request.user, nombre=nombre).exists():
        return JsonResponse({'error': 'Ya tienes un supermercado con ese nombre'}, status=400)

    bloque = None
    if descripcion:
        if usuario_supero_limite(request.user, 'ia_pasillos'):
            return JsonResponse({
                'error': 'Has alcanzado el límite de 10 usos por hora. Inténtalo más tarde.'
            }, status=429)
        bloque, error = estructurar_pasillos_con_ia(descripcion)
        if error:
            return JsonResponse({'error': error}, status=500)

    supermercado = Supermercado.objects.create(
        usuario=request.user,
        nombre=nombre,
        direccion=direccion,
    )

    if bloque:
        importar_bloque(bloque, supermercado)
    else:
        plantilla = plantilla_por_defecto()
        if plantilla:
            copiar_pasillos_keywords(plantilla, supermercado)

    return JsonResponse({
        'ok': True,
        'id': supermercado.id,
        'nombre': supermercado.nombre,
    })


@login_required
@require_POST
def importar_bloque_pasillos(request, supermercado_id):
    from .services import importar_bloque, estructurar_pasillos_con_ia

    resp = _rechazo_limite_escritura(request)
    if resp:
        return resp
    supermercado = get_object_or_404(
        Supermercado, id=supermercado_id, usuario=request.user
    )
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    descripcion = str(data.get('descripcion') or '').strip()[:3000]

    if not descripcion:
        return JsonResponse({'error': 'Cuéntanos qué pasillos quieres añadir'}, status=400)

    if usuario_supero_limite(request.user, 'ia_pasillos'):
        return JsonResponse({
            'error': 'Has alcanzado el límite de 10 usos por hora. Inténtalo más tarde.'
        }, status=429)

    bloque, error = estructurar_pasillos_con_ia(descripcion)
    if error:
        return JsonResponse({'error': error}, status=500)

    creados = importar_bloque(bloque, supermercado)
    return JsonResponse({'ok': True, 'creados': creados})


@login_required
@require_POST
def eliminar_supermercado(request, supermercado_id):
    if request.user.is_staff:
        supermercado = get_object_or_404(Supermercado, id=supermercado_id)
    else:
        supermercado = get_object_or_404(
            Supermercado, id=supermercado_id, usuario=request.user
        )
        if supermercado.publico:
            return JsonResponse({
                'error': 'Está publicado en Explorar; despublícalo primero o pide a un administrador que lo elimine.'
            }, status=403)

    supermercado.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def alternar_publicacion(request, supermercado_id):
    """Publica o despublica un supermercado propio en 'Explorar'."""
    supermercado = get_object_or_404(
        Supermercado, id=supermercado_id, usuario=request.user
    )
    supermercado.publico = not supermercado.publico
    supermercado.fecha_publicacion = timezone.now() if supermercado.publico else None
    supermercado.save()
    return JsonResponse({'ok': True, 'publico': supermercado.publico})


@method_decorator(login_required, name='dispatch')
class ExplorarSupermercadosView(View):
    template_name = 'compra/explorar.html'

    def get(self, request):
        me_gusta = models.Exists(
            Supermercado.likes.through.objects.filter(
                supermercado=models.OuterRef('pk'),
                usuario=request.user,
            )
        )
        supermercados = Supermercado.objects.filter(
            publico=True
        ).select_related('usuario').annotate(
            num_likes=models.Count('likes', distinct=True),
            num_pasillos=models.Count('pasillos', distinct=True),
            likes_me=me_gusta,
        ).order_by('-num_likes', '-fecha_publicacion')

        ya_tengo = set(
            Supermercado.objects.filter(usuario=request.user).values_list('nombre', flat=True)
        )

        paginator = Paginator(supermercados, 20)
        pagina = request.GET.get('pagina', 1)
        try:
            pagina = int(pagina)
        except (TypeError, ValueError):
            pagina = 1
        pagina = max(1, min(pagina, paginator.num_pages))

        return render(request, self.template_name, {
            'supermercados': paginator.get_page(pagina),
            'ya_tengo': ya_tengo,
        })


@login_required
@require_POST
def alternar_like(request, supermercado_id):
    supermercado = get_object_or_404(
        Supermercado, id=supermercado_id, publico=True
    )
    if request.user in supermercado.likes.all():
        supermercado.likes.remove(request.user)
        te_gusta = False
    else:
        supermercado.likes.add(request.user)
        te_gusta = True
    return JsonResponse({
        'ok': True,
        'te_gusta': te_gusta,
        'total_likes': supermercado.total_likes(),
    })


@login_required
@require_POST
def usar_supermercado_publico(request, supermercado_id):
    """Copia un supermercado público (pasillos y keywords) a la cuenta del usuario."""
    from .services import duplicar_supermercado

    resp = _rechazo_limite_escritura(request)
    if resp:
        return resp
    origen = get_object_or_404(Supermercado, id=supermercado_id, publico=True)
    nuevo = duplicar_supermercado(origen, request.user)
    return JsonResponse({'ok': True, 'id': nuevo.id, 'nombre': nuevo.nombre})


@login_required
@require_POST
def crear_pasillo(request, supermercado_id):
    resp = _rechazo_limite_escritura(request)
    if resp:
        return resp
    supermercado = get_object_or_404(
        Supermercado, id=supermercado_id, usuario=request.user
    )
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    nombre = str(data.get('nombre') or '').strip()[:200]

    if not nombre:
        return JsonResponse({'error': 'Falta el nombre'}, status=400)

    from .services import sugerir_categorias

    ultimo_orden = supermercado.pasillos.count() + 1
    pasillo = Pasillo.objects.create(
        supermercado=supermercado,
        nombre=nombre,
        orden=ultimo_orden
    )

    categorias = sugerir_categorias(nombre)
    if categorias:
        pasillo.categorias.set(categorias)

    return JsonResponse({
        'id': pasillo.id,
        'nombre': pasillo.nombre,
        'orden': pasillo.orden,
        'categorias': [c.nombre for c in categorias],
    })


@login_required
@require_POST
def renombrar_pasillo(request, pasillo_id):
    pasillo = get_object_or_404(
        Pasillo, id=pasillo_id, supermercado__usuario=request.user
    )
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    nombre = str(data.get('nombre') or '').strip()[:200]

    if not nombre:
        return JsonResponse({'error': 'Falta el nombre'}, status=400)

    pasillo.nombre = nombre
    pasillo.save()
    return JsonResponse({'ok': True, 'nombre': pasillo.nombre})


@login_required
@require_POST
def alternar_categoria_pasillo(request, pasillo_id, categoria_id):
    """Añade o quita una categoría global de un pasillo (hereda/deja de
    heredar sus keywords)."""
    pasillo = get_object_or_404(
        Pasillo, id=pasillo_id, supermercado__usuario=request.user
    )
    categoria = get_object_or_404(Categoria, id=categoria_id)

    if categoria in pasillo.categorias.all():
        pasillo.categorias.remove(categoria)
        activa = False
    else:
        pasillo.categorias.add(categoria)
        activa = True

    return JsonResponse({'ok': True, 'activa': activa})


@login_required
@require_POST
def eliminar_pasillo(request, pasillo_id):
    pasillo = get_object_or_404(
        Pasillo, id=pasillo_id, supermercado__usuario=request.user
    )
    pasillo.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def reordenar_pasillos(request, supermercado_id):
    """
    Recibe una lista de IDs en el nuevo orden y actualiza
    el campo 'orden' de cada pasillo.
    """
    resp = _rechazo_limite_escritura(request)
    if resp:
        return resp
    supermercado = get_object_or_404(
        Supermercado, id=supermercado_id, usuario=request.user
    )
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    orden_ids = data.get('orden', []) or []
    if not isinstance(orden_ids, list):
        return JsonResponse({'error': 'orden debe ser una lista'}, status=400)
    orden_ids = [i for i in orden_ids[:200] if isinstance(i, int)]

    # Primero a un rango temporal alto: si se actualizara directamente al
    # orden final, un pasillo podía chocar con el 'orden' que todavía
    # tenía otro pendiente de actualizar (unique_together supermercado+orden).
    OFFSET = 100000
    for posicion, pasillo_id in enumerate(orden_ids, start=1):
        Pasillo.objects.filter(
            id=pasillo_id,
            supermercado=supermercado
        ).update(orden=OFFSET + posicion)

    for posicion, pasillo_id in enumerate(orden_ids, start=1):
        Pasillo.objects.filter(
            id=pasillo_id,
            supermercado=supermercado
        ).update(orden=posicion)

    return JsonResponse({'ok': True})


@login_required
@require_POST
def crear_keyword(request, pasillo_id):
    resp = _rechazo_limite_escritura(request)
    if resp:
        return resp
    pasillo = get_object_or_404(
        Pasillo, id=pasillo_id, supermercado__usuario=request.user
    )
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    palabra = _normalizar(data.get('palabra', ''))[:60]

    if not palabra:
        return JsonResponse({'error': 'Falta la palabra'}, status=400)

    keyword, creado = Keyword.objects.get_or_create(
        pasillo=pasillo,
        palabra=palabra
    )
    return JsonResponse({
        'id': keyword.id,
        'palabra': keyword.palabra,
        'creado': creado,
    })


@login_required
@require_POST
def eliminar_keyword(request, keyword_id):
    keyword = get_object_or_404(
        Keyword, id=keyword_id, pasillo__supermercado__usuario=request.user
    )
    keyword.delete()
    return JsonResponse({'ok': True})

@login_required
@require_POST
def guardar_como_plantilla(request, lista_id):
    resp = _bloqueo_premium(request)
    if resp:
        return resp
    resp = _rechazo_limite_escritura(request)
    if resp:
        return resp
    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    nombre = str(data.get('nombre') or '').strip()[:100]

    if not nombre:
        return JsonResponse({'error': 'Falta el nombre'}, status=400)

    nueva_plantilla = Lista.objects.create(
        usuario=request.user,
        supermercado=lista.supermercado,
        activa=False,
        es_plantilla=True,
        nombre_plantilla=nombre
    )
    for item in lista.items.all():
        ListaItem.objects.create(
            lista=nueva_plantilla,
            nombre=item.nombre,
            pasillo=item.pasillo,
            en_carro=False
        )
    return JsonResponse({'ok': True, 'plantilla_id': nueva_plantilla.id})


@login_required
@require_POST
def usar_plantilla(request, plantilla_id):
    resp = _bloqueo_premium(request)
    if resp:
        return resp
    plantilla = get_object_or_404(
        Lista, id=plantilla_id, usuario=request.user, es_plantilla=True
    )
    lista_activa, _ = Lista.objects.get_or_create(
        supermercado=plantilla.supermercado,
        usuario=request.user,
        activa=True,
        defaults={}
    )
    for item in plantilla.items.all():
        ListaItem.objects.get_or_create(
            lista=lista_activa,
            nombre=item.nombre,
            defaults={'pasillo': item.pasillo, 'en_carro': False}
        )
    return JsonResponse({'ok': True})

@login_required
@require_POST
def repetir_lista(request, lista_id):
    """Copia los productos de una lista anterior a la lista activa actual."""
    resp = _bloqueo_premium(request)
    if resp:
        return resp
    lista_origen = get_object_or_404(Lista, id=lista_id, usuario=request.user)
    lista_activa, _ = Lista.objects.get_or_create(
        supermercado=lista_origen.supermercado,
        usuario=request.user,
        activa=True,
        defaults={}
    )
    for item in lista_origen.items.all():
        ListaItem.objects.get_or_create(
            lista=lista_activa,
            nombre=item.nombre,
            defaults={'pasillo': item.pasillo, 'en_carro': False}
        )
    return JsonResponse({'ok': True})

@login_required
@require_POST
def eliminar_plantilla(request, plantilla_id):
    resp = _bloqueo_premium(request)
    if resp:
        return resp
    plantilla = get_object_or_404(
        Lista, id=plantilla_id, usuario=request.user, es_plantilla=True
    )
    plantilla.delete()
    return JsonResponse({'ok': True})


@method_decorator(login_required, name='dispatch')
class HistorialView(View):
    template_name = 'compra/historial.html'

    def get(self, request):
        resp = _bloqueo_premium(request, ajax=False)
        if resp:
            return resp
        listas_qs = Lista.objects.filter(
            usuario=request.user, es_plantilla=False, activa=False
        ).select_related('supermercado').annotate(
            num_productos=models.Count('items')
        ).order_by('-fecha')
        plantillas = Lista.objects.filter(
            usuario=request.user, es_plantilla=True
        ).select_related('supermercado').annotate(
            num_productos=models.Count('items')
        ).order_by('-fecha')
        listas = Paginator(listas_qs, 10).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'listas': listas,
            'plantillas': plantillas,
        })


@login_required
@require_POST
def archivar_lista(request, lista_id):
    """Cierra la lista activa y crea una nueva vacía."""
    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)
    lista.activa = False
    lista.save()
    return JsonResponse({'ok': True})


@login_required
def exportar_pdf(request, lista_id):
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    from weasyprint import HTML

    resp = _bloqueo_premium(request, ajax=False)
    if resp:
        return resp

    if usuario_supero_limite(request.user, 'pdf_export', limite=20, ventana_segundos=3600):
        from django.contrib import messages
        messages.error(request, 'Has alcanzado el límite de 20 exportaciones a PDF por hora.')
        return HttpResponse(status=429)

    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)
    items = lista.items.select_related('pasillo').order_by(
        models.F('pasillo__orden').asc(nulls_last=True), 'nombre'
    )

    html_string = render_to_string('compra/pdf_lista.html', {
        'lista': lista,
        'items': items,
    })

    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="lista_{lista.fecha}.pdf"'
    return response