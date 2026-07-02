from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import models
from .models import Supermercado, Lista, ListaItem, Pasillo, Keyword
import json
from usuarios.models import FeatureFlag
from django.core.cache import cache
from django.conf import settings


def inferir_pasillo(nombre_producto, supermercado):
    nombre = nombre_producto.lower().strip()
    keywords = Keyword.objects.filter(
        pasillo__supermercado=supermercado
    ).select_related('pasillo')
    for kw in keywords:
        if kw.palabra in nombre or nombre in kw.palabra:
            return kw.pasillo
    return None


@method_decorator(login_required, name='dispatch')
class ListaCompraView(View):
    template_name = 'compra/lista.html'

    def get(self, request):
        supermercados = Supermercado.objects.filter(
            usuario=request.user,
            activo=True
        )

        super_id = request.GET.get('supermercado')
        if super_id:
            supermercado = get_object_or_404(
                Supermercado,
                id=super_id,
                usuario=request.user
            )
        elif supermercados.exists():
            supermercado = supermercados.first()
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
    data = json.loads(request.body)
    nombre = data.get('nombre', '').strip()
    lista_id = data.get('lista_id')

    if not nombre or not lista_id:
        return JsonResponse({'error': 'Datos incompletos'}, status=400)

    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)
    pasillo = inferir_pasillo(nombre, lista.supermercado)

    item = ListaItem.objects.create(
        lista=lista,
        nombre=nombre,
        pasillo=pasillo
    )
    return JsonResponse({
        'id': item.id,
        'nombre': item.nombre,
        'pasillo': item.pasillo.nombre if item.pasillo else 'Sin asignar',
        'pasillo_orden': item.pasillo.orden if item.pasillo else 999,
        'en_carro': item.en_carro,
    })


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
    data = json.loads(request.body)
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

    Keyword.objects.get_or_create(
        pasillo=pasillo,
        palabra=item.nombre.lower().strip()
    )

    return JsonResponse({
        'ok': True,
        'pasillo': pasillo.nombre,
        'pasillo_orden': pasillo.orden,
    })


def usuario_supero_limite_fotos(usuario, limite=10, ventana_segundos=3600):
    """
    Comprueba si el usuario ha superado el límite de fotos
    permitidas en la ventana de tiempo (por defecto 10 fotos/hora).
    """
    clave = f"limite_fotos_{usuario.id}"
    intentos = cache.get(clave, 0)

    if intentos >= limite:
        return True

    cache.set(clave, intentos + 1, ventana_segundos)
    return False


@login_required
@require_POST
def analizar_foto(request):
    lista_id = request.POST.get('lista_id')
    foto = request.FILES.get('foto')

    if not lista_id or not foto:
        return JsonResponse({'error': 'Faltan datos'}, status=400)

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
    template_name = 'compra/configuracion.html'

    def get(self, request):
        supermercados = Supermercado.objects.filter(usuario=request.user)
        return render(request, self.template_name, {
            'supermercados': supermercados,
        })


@login_required
@require_POST
def crear_pasillo(request, supermercado_id):
    supermercado = get_object_or_404(
        Supermercado, id=supermercado_id, usuario=request.user
    )
    data = json.loads(request.body)
    nombre = data.get('nombre', '').strip()

    if not nombre:
        return JsonResponse({'error': 'Falta el nombre'}, status=400)

    ultimo_orden = supermercado.pasillos.count() + 1
    pasillo = Pasillo.objects.create(
        supermercado=supermercado,
        nombre=nombre,
        orden=ultimo_orden
    )
    return JsonResponse({
        'id': pasillo.id,
        'nombre': pasillo.nombre,
        'orden': pasillo.orden,
    })


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
    supermercado = get_object_or_404(
        Supermercado, id=supermercado_id, usuario=request.user
    )
    data = json.loads(request.body)
    orden_ids = data.get('orden', [])

    for posicion, pasillo_id in enumerate(orden_ids, start=1):
        Pasillo.objects.filter(
            id=pasillo_id,
            supermercado=supermercado
        ).update(orden=posicion)

    return JsonResponse({'ok': True})


@login_required
@require_POST
def crear_keyword(request, pasillo_id):
    pasillo = get_object_or_404(
        Pasillo, id=pasillo_id, supermercado__usuario=request.user
    )
    data = json.loads(request.body)
    palabra = data.get('palabra', '').strip().lower()

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
    lista = get_object_or_404(Lista, id=lista_id, usuario=request.user)
    data = json.loads(request.body)
    nombre = data.get('nombre', '').strip()

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
    plantilla = get_object_or_404(
        Lista, id=plantilla_id, usuario=request.user, es_plantilla=True
    )
    plantilla.delete()
    return JsonResponse({'ok': True})


@method_decorator(login_required, name='dispatch')
class HistorialView(View):
    template_name = 'compra/historial.html'

    def get(self, request):
        listas = Lista.objects.filter(
            usuario=request.user, es_plantilla=False, activa=False
        ).order_by('-fecha')
        plantillas = Lista.objects.filter(
            usuario=request.user, es_plantilla=True
        ).order_by('-fecha')
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