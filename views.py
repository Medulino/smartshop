from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views import View
from .models import Supermercado, Lista, ListaItem, Pasillo, Keyword
import json


def inferir_pasillo(nombre_producto, supermercado):
    """
    Busca en las keywords del supermercado para asignar
    automáticamente el pasillo correcto al producto.
    Devuelve un Pasillo o None si no encuentra coincidencia.
    """
    nombre = nombre_producto.lower().strip()
    keywords = Keyword.objects.filter(
        pasillo__supermercado=supermercado
    ).select_related('pasillo')

    for kw in keywords:
        if kw.palabra in nombre or nombre in kw.palabra:
            return kw.pasillo
    return None


class ListaCompraView(View):
    """Vista principal: muestra la lista activa del supermercado seleccionado."""

    template_name = 'compra/lista.html'

    def get(self, request):
        supermercados = Supermercado.objects.filter(activo=True)

        # Selección de supermercado (por GET o el primero disponible)
        super_id = request.GET.get('supermercado')
        if super_id:
            supermercado = get_object_or_404(Supermercado, id=super_id)
        elif supermercados.exists():
            supermercado = supermercados.first()
        else:
            supermercado = None

        lista = None
        items = []

        if supermercado:
            # Obtenemos o creamos la lista activa de hoy
            lista, _ = Lista.objects.get_or_create(
                supermercado=supermercado,
                activa=True,
                defaults={}
            )
            items = lista.items.select_related('pasillo').all()

        context = {
            'supermercados': supermercados,
            'supermercado': supermercado,
            'lista': lista,
            'items': items,
        }
        return render(request, self.template_name, context)


@require_POST
def añadir_producto(request):
    """Añade un producto a la lista activa y le asigna pasillo automáticamente."""
    data = json.loads(request.body)
    nombre = data.get('nombre', '').strip()
    lista_id = data.get('lista_id')

    if not nombre or not lista_id:
        return JsonResponse({'error': 'Datos incompletos'}, status=400)

    lista = get_object_or_404(Lista, id=lista_id)
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


@require_POST
def toggle_en_carro(request, item_id):
    """Marca o desmarca un producto como ya cogido."""
    item = get_object_or_404(ListaItem, id=item_id)
    item.en_carro = not item.en_carro
    item.save()
    return JsonResponse({'en_carro': item.en_carro})


@require_POST
def eliminar_producto(request, item_id):
    """Elimina un producto de la lista."""
    item = get_object_or_404(ListaItem, id=item_id)
    item.delete()
    return JsonResponse({'ok': True})


@require_POST
def vaciar_lista(request, lista_id):
    """Elimina todos los productos de la lista."""
    lista = get_object_or_404(Lista, id=lista_id)
    lista.items.all().delete()
    return JsonResponse({'ok': True})


@require_POST
def vaciar_marcados(request, lista_id):
    """Elimina solo los productos ya marcados como en el carro."""
    lista = get_object_or_404(Lista, id=lista_id)
    lista.items.filter(en_carro=True).delete()
    return JsonResponse({'ok': True})
