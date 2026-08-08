import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from compra.models import Categoria, Keyword, Pasillo, Supermercado
from compra.tests.utils import (
    crear_categoria,
    crear_item,
    crear_keyword as factory_keyword,
    crear_lista,
    crear_pasillo,
    crear_supermercado,
    crear_superusuario,
    crear_usuario,
)


class SupermercadosTestsBase(TestCase):
    def post_json(self, url, data):
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
        )


class ConfiguracionViewTests(SupermercadosTestsBase):
    def test_sin_login_redirige(self):
        response = self.client.get(reverse('compra:configuracion'))
        self.assertEqual(response.status_code, 302)

    def test_con_login_solo_lista_sus_supermercados(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        propio = crear_supermercado(usuario, nombre='Mi Super')
        crear_supermercado(otro, nombre='Super Ajeno')

        self.client.force_login(usuario)
        response = self.client.get(reverse('compra:configuracion'))

        self.assertEqual(response.status_code, 200)
        supermercados = list(response.context['supermercados'])
        self.assertEqual(supermercados, [propio])


class SupermercadoDetalleViewTests(SupermercadosTestsBase):
    def test_404_si_es_de_otro_usuario(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        supermercado = crear_supermercado(otro, nombre='Ajeno')

        self.client.force_login(usuario)
        response = self.client.get(
            reverse('compra:supermercado_detalle', args=[supermercado.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_contexto_incluye_categorias(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        crear_categoria(nombre='Panadería')

        self.client.force_login(usuario)
        response = self.client.get(
            reverse('compra:supermercado_detalle', args=[supermercado.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['super'], supermercado)
        self.assertIn('categorias', response.context)
        self.assertEqual(list(response.context['categorias']), list(Categoria.objects.all()))


class CrearSupermercadoTests(SupermercadosTestsBase):
    def test_sin_nombre_devuelve_400(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        response = self.post_json(reverse('compra:crear_supermercado'), {'nombre': '  '})
        self.assertEqual(response.status_code, 400)

    def test_nombre_duplicado_devuelve_400(self):
        usuario = crear_usuario()
        crear_supermercado(usuario, nombre='Mi Super')
        self.client.force_login(usuario)
        response = self.post_json(
            reverse('compra:crear_supermercado'), {'nombre': 'Mi Super'}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Ya tienes un supermercado con ese nombre')

    def test_sin_plantilla_no_copia_pasillos(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)

        response = self.post_json(reverse('compra:crear_supermercado'), {
            'nombre': 'Mi Super',
            'direccion': 'Calle Falsa 123',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        supermercado = Supermercado.objects.get(id=data['id'])
        self.assertEqual(supermercado.usuario, usuario)
        self.assertEqual(supermercado.nombre, 'Mi Super')
        self.assertEqual(supermercado.direccion, 'Calle Falsa 123')
        self.assertEqual(supermercado.pasillos.count(), 0)

    def test_con_descripcion_crea_pasillos_desde_ia(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        url = reverse('compra:crear_supermercado')

        with patch(
            'compra.services.estructurar_pasillos_con_ia',
            return_value=("Panadería: pan, leche\nFrutería: manzanas", None),
        ):
            response = self.post_json(url, {
                'nombre': 'Super IA',
                'descripcion': 'tengo panaderia y fruteria',
            })

        self.assertEqual(response.status_code, 200)
        supermercado = Supermercado.objects.get(nombre='Super IA', usuario=usuario)
        self.assertEqual(supermercado.pasillos.count(), 2)
        self.assertEqual(
            set(supermercado.pasillos.values_list('nombre', flat=True)),
            {'Panadería', 'Frutería'},
        )

    def test_sin_descripcion_copia_la_plantilla(self):
        usuario = crear_usuario()
        plantilla = crear_supermercado(
            crear_usuario(username='admin', is_staff=True),
            nombre='Mercadona Agustinos',
        )
        p1 = crear_pasillo(plantilla, nombre='Panadería', orden=1)
        factory_keyword(p1, 'pan')
        crear_pasillo(plantilla, nombre='Frutería', orden=2)

        self.client.force_login(usuario)
        response = self.post_json(reverse('compra:crear_supermercado'), {
            'nombre': 'Super Copia',
        })

        self.assertEqual(response.status_code, 200)
        supermercado = Supermercado.objects.get(nombre='Super Copia', usuario=usuario)
        self.assertEqual(supermercado.pasillos.count(), 2)
        self.assertEqual(
            set(supermercado.pasillos.values_list('nombre', flat=True)),
            {'Panadería', 'Frutería'},
        )
        self.assertEqual(supermercado.pasillos.get(nombre='Panadería').keywords.count(), 1)

    def test_limite_ia_devuelve_429(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        url = reverse('compra:crear_supermercado')

        with patch(
            'compra.services.estructurar_pasillos_con_ia',
            return_value=("Panadería: pan", None),
        ):
            for i in range(10):
                response = self.post_json(url, {
                    'nombre': f'Super {i}',
                    'descripcion': 'una panaderia',
                })
                self.assertEqual(response.status_code, 200)

            response = self.post_json(url, {
                'nombre': 'Super 10',
                'descripcion': 'una panaderia',
            })

        self.assertEqual(response.status_code, 429)
        self.assertEqual(Supermercado.objects.filter(usuario=usuario).count(), 10)


class ImportarBloquePasillosTests(SupermercadosTestsBase):
    def test_crea_pasillos_desde_ia(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        self.client.force_login(usuario)

        with patch(
            'compra.services.estructurar_pasillos_con_ia',
            return_value=("Panadería: pan, leche\nFrutería: manzanas", None),
        ):
            response = self.post_json(
                reverse('compra:importar_bloque_pasillos', args=[supermercado.id]),
                {'descripcion': 'panaderia y fruteria'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['creados'], 2)
        self.assertEqual(supermercado.pasillos.count(), 2)

    def test_limite_ia_devuelve_429(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        self.client.force_login(usuario)
        url = reverse('compra:importar_bloque_pasillos', args=[supermercado.id])

        with patch(
            'compra.services.estructurar_pasillos_con_ia',
            return_value=("Panadería: pan", None),
        ):
            for _ in range(10):
                response = self.post_json(url, {'descripcion': 'una panaderia'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['creados'], 1)

            response = self.post_json(url, {'descripcion': 'una panaderia'})

        self.assertEqual(response.status_code, 429)
        self.assertEqual(supermercado.pasillos.count(), 10)

    def test_descripcion_vacia_devuelve_400(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:importar_bloque_pasillos', args=[supermercado.id]),
            {'descripcion': '   '},
        )
        self.assertEqual(response.status_code, 400)

    def test_supermercado_de_otro_usuario_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        supermercado = crear_supermercado(otro, nombre='Ajeno')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:importar_bloque_pasillos', args=[supermercado.id]),
            {'descripcion': 'panaderia'},
        )
        self.assertEqual(response.status_code, 404)


class CrearPasilloTests(SupermercadosTestsBase):
    def test_crea_pasillo_con_orden_siguiente_y_categorias(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        categoria = crear_categoria(nombre='Panadería')
        self.client.force_login(usuario)
        url = reverse('compra:crear_pasillo', args=[supermercado.id])

        response = self.post_json(url, {'nombre': 'Panadería'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['nombre'], 'Panadería')
        self.assertEqual(data['orden'], 1)
        self.assertEqual(data['categorias'], ['Panadería'])
        pasillo = Pasillo.objects.get(id=data['id'])
        self.assertEqual(pasillo.orden, 1)
        self.assertEqual(list(pasillo.categorias.all()), [categoria])

        response = self.post_json(url, {'nombre': 'Frutería'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['orden'], 2)

    def test_sin_nombre_devuelve_400(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:crear_pasillo', args=[supermercado.id]),
            {'nombre': ''},
        )
        self.assertEqual(response.status_code, 400)

    def test_supermercado_de_otro_usuario_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        supermercado = crear_supermercado(otro, nombre='Ajeno')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:crear_pasillo', args=[supermercado.id]),
            {'nombre': 'Panadería'},
        )
        self.assertEqual(response.status_code, 404)


class RenombrarPasilloTests(SupermercadosTestsBase):
    def test_renombra_pasillo(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        pasillo = crear_pasillo(supermercado, nombre='Viejo')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:renombrar_pasillo', args=[pasillo.id]),
            {'nombre': 'Nuevo'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], 'Nuevo')
        pasillo.refresh_from_db()
        self.assertEqual(pasillo.nombre, 'Nuevo')

    def test_sin_nombre_devuelve_400(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        pasillo = crear_pasillo(supermercado, nombre='Viejo')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:renombrar_pasillo', args=[pasillo.id]),
            {'nombre': '  '},
        )
        self.assertEqual(response.status_code, 400)

    def test_pasillo_de_otro_usuario_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        pasillo = crear_pasillo(crear_supermercado(otro, nombre='Ajeno'), nombre='Viejo')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:renombrar_pasillo', args=[pasillo.id]),
            {'nombre': 'Nuevo'},
        )
        self.assertEqual(response.status_code, 404)


class AlternarCategoriaPasilloTests(SupermercadosTestsBase):
    def test_anade_y_luego_quita_la_categoria(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        pasillo = crear_pasillo(supermercado, nombre='Panadería')
        categoria = crear_categoria(nombre='Panadería')
        self.client.force_login(usuario)
        url = reverse('compra:alternar_categoria_pasillo', args=[pasillo.id, categoria.id])

        response = self.post_json(url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['activa'])
        self.assertIn(categoria, pasillo.categorias.all())

        response = self.post_json(url, {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['activa'])
        self.assertNotIn(categoria, pasillo.categorias.all())

    def test_pasillo_de_otro_usuario_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        pasillo = crear_pasillo(crear_supermercado(otro, nombre='Ajeno'), nombre='Panadería')
        categoria = crear_categoria(nombre='Panadería')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:alternar_categoria_pasillo', args=[pasillo.id, categoria.id]),
            {},
        )
        self.assertEqual(response.status_code, 404)


class EliminarPasilloTests(SupermercadosTestsBase):
    def test_elimina_y_deja_lista_items_con_pasillo_none(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        pasillo = crear_pasillo(supermercado, nombre='Panadería')
        lista = crear_lista(usuario, supermercado)
        item = crear_item(lista, 'pan', pasillo=pasillo)
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:eliminar_pasillo', args=[pasillo.id]), {}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertFalse(Pasillo.objects.filter(id=pasillo.id).exists())
        item.refresh_from_db()
        self.assertIsNone(item.pasillo)

    def test_pasillo_de_otro_usuario_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        pasillo = crear_pasillo(crear_supermercado(otro, nombre='Ajeno'), nombre='Panadería')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:eliminar_pasillo', args=[pasillo.id]), {}
        )
        self.assertEqual(response.status_code, 404)


class ReordenarPasillosTests(SupermercadosTestsBase):
    def setUp(self):
        super().setUp()
        self.usuario = crear_usuario()
        self.supermercado = crear_supermercado(self.usuario, nombre='Mi Super')
        self.p1 = crear_pasillo(self.supermercado, nombre='Panadería', orden=1)
        self.p2 = crear_pasillo(self.supermercado, nombre='Frutería', orden=2)
        self.p3 = crear_pasillo(self.supermercado, nombre='Carnicería', orden=3)
        self.client.force_login(self.usuario)

    def test_orden_invertido_sin_error(self):
        response = self.post_json(
            reverse('compra:reordenar_pasillos', args=[self.supermercado.id]),
            {'orden': [self.p3.id, self.p2.id, self.p1.id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.p3.refresh_from_db()
        self.assertEqual(self.p1.orden, 3)
        self.assertEqual(self.p2.orden, 2)
        self.assertEqual(self.p3.orden, 1)

    def test_subconjunto_de_ids(self):
        response = self.post_json(
            reverse('compra:reordenar_pasillos', args=[self.supermercado.id]),
            {'orden': [self.p2.id, self.p1.id]},
        )

        self.assertEqual(response.status_code, 200)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.p3.refresh_from_db()
        self.assertEqual(self.p1.orden, 2)
        self.assertEqual(self.p2.orden, 1)
        self.assertEqual(self.p3.orden, 3)

    def test_supermercado_de_otro_usuario_devuelve_404(self):
        otro = crear_usuario(username='otro')
        ajeno = crear_supermercado(otro, nombre='Ajeno')
        self.client.force_login(self.usuario)

        response = self.post_json(
            reverse('compra:reordenar_pasillos', args=[ajeno.id]),
            {'orden': [self.p1.id]},
        )
        self.assertEqual(response.status_code, 404)


class CrearKeywordTests(SupermercadosTestsBase):
    def test_crea_y_normaliza_la_keyword(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        pasillo = crear_pasillo(supermercado, nombre='Panadería')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:crear_keyword', args=[pasillo.id]),
            {'palabra': 'PaNadErÍa'},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['palabra'], 'panaderia')
        self.assertTrue(data['creado'])
        self.assertTrue(Keyword.objects.filter(pasillo=pasillo, palabra='panaderia').exists())

    def test_repetida_devuelve_creado_false(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        pasillo = crear_pasillo(supermercado, nombre='Panadería')
        factory_keyword(pasillo, 'panaderia')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:crear_keyword', args=[pasillo.id]),
            {'palabra': 'Panadería'},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['palabra'], 'panaderia')
        self.assertFalse(data['creado'])
        self.assertEqual(Keyword.objects.filter(pasillo=pasillo).count(), 1)

    def test_sin_palabra_devuelve_400(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        pasillo = crear_pasillo(supermercado, nombre='Panadería')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:crear_keyword', args=[pasillo.id]),
            {'palabra': '  '},
        )
        self.assertEqual(response.status_code, 400)

    def test_pasillo_de_otro_usuario_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        pasillo = crear_pasillo(crear_supermercado(otro, nombre='Ajeno'), nombre='Panadería')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:crear_keyword', args=[pasillo.id]),
            {'palabra': 'pan'},
        )
        self.assertEqual(response.status_code, 404)


class EliminarKeywordTests(SupermercadosTestsBase):
    def test_elimina_la_keyword(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        pasillo = crear_pasillo(supermercado, nombre='Panadería')
        keyword = factory_keyword(pasillo, 'pan')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:eliminar_keyword', args=[keyword.id]), {}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertFalse(Keyword.objects.filter(id=keyword.id).exists())

    def test_keyword_de_otro_usuario_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        pasillo = crear_pasillo(crear_supermercado(otro, nombre='Ajeno'), nombre='Panadería')
        keyword = factory_keyword(pasillo, 'pan')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:eliminar_keyword', args=[keyword.id]), {}
        )
        self.assertEqual(response.status_code, 404)


class EliminarSupermercadoTests(SupermercadosTestsBase):
    def test_usuario_normal_elimina_su_supermercado(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:eliminar_supermercado', args=[supermercado.id]), {}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertFalse(Supermercado.objects.filter(id=supermercado.id).exists())

    def test_supermercado_publicado_devuelve_403(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super', publico=True)
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:eliminar_supermercado', args=[supermercado.id]), {}
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn('Está publicado en Explorar', response.json()['error'])
        self.assertTrue(Supermercado.objects.filter(id=supermercado.id).exists())

    def test_staff_elimina_supermercado_publicado_de_otro(self):
        admin = crear_superusuario()
        otro = crear_usuario(username='otro')
        supermercado = crear_supermercado(otro, nombre='Ajeno', publico=True)
        self.client.force_login(admin)

        response = self.post_json(
            reverse('compra:eliminar_supermercado', args=[supermercado.id]), {}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Supermercado.objects.filter(id=supermercado.id).exists())

    def test_supermercado_de_otro_usuario_normal_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        supermercado = crear_supermercado(otro, nombre='Ajeno')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:eliminar_supermercado', args=[supermercado.id]), {}
        )
        self.assertEqual(response.status_code, 404)


class AlternarPublicacionTests(SupermercadosTestsBase):
    def test_publica_y_despublica(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario, nombre='Mi Super')
        self.client.force_login(usuario)
        url = reverse('compra:alternar_publicacion', args=[supermercado.id])

        response = self.post_json(url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['publico'])
        supermercado.refresh_from_db()
        self.assertTrue(supermercado.publico)
        self.assertIsNotNone(supermercado.fecha_publicacion)

        response = self.post_json(url, {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['publico'])
        supermercado.refresh_from_db()
        self.assertFalse(supermercado.publico)
        self.assertIsNone(supermercado.fecha_publicacion)

    def test_supermercado_de_otro_usuario_devuelve_404(self):
        usuario = crear_usuario()
        otro = crear_usuario(username='otro')
        supermercado = crear_supermercado(otro, nombre='Ajeno')
        self.client.force_login(usuario)

        response = self.post_json(
            reverse('compra:alternar_publicacion', args=[supermercado.id]), {}
        )
        self.assertEqual(response.status_code, 404)
