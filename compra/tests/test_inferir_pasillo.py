"""Tests de inferir_pasillo (compra.views) y de las funciones puras de
compra.services (sugerir_categorias, importar_bloque, copiar_pasillos_keywords,
duplicar_supermercado, plantilla_por_defecto) y compra.utils (normalizar)."""
from django.test import TestCase

from compra.utils import normalizar
from compra.views import inferir_pasillo
from compra.services import (
    sugerir_categorias,
    importar_bloque,
    copiar_pasillos_keywords,
    duplicar_supermercado,
    plantilla_por_defecto,
)
from compra.tests.utils import (
    crear_usuario,
    crear_supermercado,
    crear_pasillo,
    crear_keyword,
    crear_categoria,
)


class InferirPasilloTests(TestCase):

    def test_coincidencia_exacta_devuelve_pasillo(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        pasillo = crear_pasillo(supermercado, nombre='Conservas')
        crear_keyword(pasillo, 'atun')

        self.assertEqual(inferir_pasillo('atun', supermercado), pasillo)

    def test_insensible_a_acentos_y_mayusculas(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        conservas = crear_pasillo(supermercado, nombre='Conservas')
        crear_keyword(conservas, 'atun')
        especias = crear_pasillo(supermercado, nombre='Especias', orden=2)
        crear_keyword(especias, 'sal')

        self.assertEqual(inferir_pasillo('Atún', supermercado), conservas)
        self.assertEqual(inferir_pasillo('SAL', supermercado), especias)

    def test_keyword_corta_no_le_roba_pasillo_a_la_larga(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        charcuteria = crear_pasillo(supermercado, nombre='Charcutería')
        crear_keyword(charcuteria, 'salchichon')
        sal = crear_pasillo(supermercado, nombre='Sal', orden=2)
        crear_keyword(sal, 'sal')

        self.assertEqual(inferir_pasillo('salchichón', supermercado), charcuteria)
        self.assertEqual(inferir_pasillo('sal', supermercado), sal)

        snacks = crear_pasillo(supermercado, nombre='Snacks', orden=3)
        crear_keyword(snacks, 'patatas fritas')
        fruteria = crear_pasillo(supermercado, nombre='Frutería', orden=4)
        crear_keyword(fruteria, 'patata')

        self.assertEqual(
            inferir_pasillo('patatas fritas de bolsa', supermercado),
            snacks,
        )

    def test_nombre_contenido_en_keyword_gana_la_mas_corta(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        yogures = crear_pasillo(supermercado, nombre='Yogures')
        crear_keyword(yogures, 'yogur de fresa')
        mermeladas = crear_pasillo(supermercado, nombre='Dulces', orden=2)
        crear_keyword(mermeladas, 'mermelada de fresa')

        self.assertEqual(inferir_pasillo('fresa', supermercado), yogures)

    def test_sin_coincidencia_devuelve_none(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        pasillo = crear_pasillo(supermercado)
        crear_keyword(pasillo, 'leche')

        self.assertIsNone(inferir_pasillo('cemento', supermercado))

    def test_keywords_de_categoria_global(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        categoria = crear_categoria(nombre='Panadería', palabras=['pan'])
        pasillo = crear_pasillo(
            supermercado, nombre='Pan', categorias=[categoria]
        )

        self.assertEqual(inferir_pasillo('pan de molde', supermercado), pasillo)

    def test_prioriza_keyword_propia_frente_a_categoria(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        categoria_pan = crear_categoria(nombre='Pan', palabras=['pan'])
        pasillo_a = crear_pasillo(supermercado, nombre='Pan de molde')
        crear_keyword(pasillo_a, 'pan de molde')
        crear_pasillo(
            supermercado, nombre='Panadería', orden=2,
            categorias=[categoria_pan],
        )

        self.assertEqual(
            inferir_pasillo('pan de molde', supermercado),
            pasillo_a,
        )

    def test_keywords_vacias_se_ignoran(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        pasillo = crear_pasillo(supermercado)
        crear_keyword(pasillo, '')
        crear_keyword(pasillo, '   ')

        self.assertIsNone(inferir_pasillo('lechuga', supermercado))


class NormalizarTests(TestCase):

    def test_quita_tildes_y_pasa_a_minusculas(self):
        self.assertEqual(normalizar('ÁTUN'), 'atun')
        self.assertEqual(normalizar('Salchichón'), 'salchichon')
        self.assertEqual(normalizar('Café con leche'), 'cafe con leche')
        self.assertEqual(normalizar('  PAN  '), 'pan')


class ImportarBloqueTests(TestCase):

    def test_crea_pasillo_con_keywords_en_minusculas(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)

        creados = importar_bloque(
            'Panadería: PAN, Leche de Molde', supermercado
        )

        self.assertEqual(creados, 1)
        pasillo = supermercado.pasillos.get(nombre='Panadería')
        self.assertEqual(
            list(pasillo.keywords.values_list('palabra', flat=True)),
            ['leche de molde', 'pan'],
        )

    def test_linea_sin_dos_puntos_crea_pasillo_sin_keywords(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)

        creados = importar_bloque('Bazar', supermercado)

        self.assertEqual(creados, 1)
        pasillo = supermercado.pasillos.get(nombre='Bazar')
        self.assertEqual(pasillo.keywords.count(), 0)

    def test_saltos_de_linea_vacios_se_ignoran(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)

        creados = importar_bloque(
            'Panadería: pan\n\n\nBazar\n', supermercado
        )

        self.assertEqual(creados, 2)
        self.assertEqual(supermercado.pasillos.count(), 2)

    def test_los_pasillos_se_numeran_a_continuacion_de_los_existentes(self):
        usuario = crear_usuario()
        supermercado = crear_supermercado(usuario)
        crear_pasillo(supermercado, nombre='Frutería', orden=1)
        crear_pasillo(supermercado, nombre='Carnicería', orden=2)

        importar_bloque(
            'Panadería: pan\nPescadería: merluza', supermercado
        )

        ordenes = list(
            supermercado.pasillos.order_by('orden').values_list('orden', flat=True)
        )
        self.assertEqual(ordenes, [1, 2, 3, 4])


class SugerirCategoriasTests(TestCase):

    def test_sugiere_por_nombre_exacto(self):
        categoria = crear_categoria(nombre='Panadería')

        self.assertEqual(sugerir_categorias('Panadería'), [categoria])

    def test_nombre_compuesto_matchea_por_trozo(self):
        categoria = crear_categoria(nombre='Droguería / Animales')

        self.assertEqual(sugerir_categorias('Droguería'), [categoria])
        self.assertEqual(sugerir_categorias('Animales'), [categoria])

    def test_pasillo_sin_relacion_no_sugiere_nada(self):
        crear_categoria(nombre='Panadería')

        self.assertEqual(sugerir_categorias('Bricolaje'), [])


class CopiarPasillosKeywordsTests(TestCase):

    def test_copia_pasillos_keywords_y_categorias(self):
        usuario = crear_usuario()
        origen = crear_supermercado(usuario, nombre='Origen')
        destino = crear_supermercado(usuario, nombre='Destino')
        categoria = crear_categoria(nombre='Panadería', palabras=['pan'])
        pasillo = crear_pasillo(
            origen, nombre='Pan', categorias=[categoria]
        )
        crear_keyword(pasillo, 'pan de molde')
        crear_keyword(pasillo, 'baguette')

        copiar_pasillos_keywords(origen, destino)

        copia = destino.pasillos.get(nombre='Pan')
        self.assertEqual(copia.orden, pasillo.orden)
        self.assertEqual(
            list(copia.keywords.values_list('palabra', flat=True)),
            ['baguette', 'pan de molde'],
        )
        self.assertEqual(list(copia.categorias.all()), [categoria])


class DuplicarSupermercadoTests(TestCase):

    def test_copia_a_otro_usuario_con_sus_pasillos(self):
        dueno = crear_usuario(username='dueno')
        otro = crear_usuario(username='otro')
        origen = crear_supermercado(dueno, nombre='Mi Super')
        pasillo = crear_pasillo(origen, nombre='Pan')
        crear_keyword(pasillo, 'pan')

        copia = duplicar_supermercado(origen, otro)

        self.assertEqual(copia.usuario, otro)
        self.assertEqual(copia.nombre, 'Mi Super')
        self.assertEqual(copia.pasillos.count(), 1)
        self.assertEqual(copia.pasillos.first().keywords.count(), 1)

    def test_anade_sufijo_si_ya_tiene_uno_con_mismo_nombre(self):
        dueno = crear_usuario(username='dueno')
        otro = crear_usuario(username='otro')
        origen = crear_supermercado(dueno, nombre='Mi Super')
        crear_supermercado(otro, nombre='Mi Super')

        primera = duplicar_supermercado(origen, otro)
        segunda = duplicar_supermercado(origen, otro)
        tercera = duplicar_supermercado(origen, otro)

        self.assertEqual(primera.nombre, 'Mi Super (2)')
        self.assertEqual(segunda.nombre, 'Mi Super (3)')
        self.assertEqual(tercera.nombre, 'Mi Super (4)')


class PlantillaPorDefectoTests(TestCase):

    def test_prioriza_superusuario(self):
        normal = crear_usuario(username='normal')
        admin = crear_usuario(username='admin', is_superuser=True)
        crear_supermercado(normal, nombre='Mercadona Agustinos')
        plantilla_admin = crear_supermercado(admin, nombre='Mercadona Agustinos')

        self.assertEqual(plantilla_por_defecto(), plantilla_admin)

    def test_devuelve_el_supermercado_si_solo_hay_uno(self):
        usuario = crear_usuario()
        plantilla = crear_supermercado(usuario, nombre='Mercadona Agustinos')

        self.assertEqual(plantilla_por_defecto(), plantilla)

    def test_devuelve_none_si_no_existe(self):
        self.assertIsNone(plantilla_por_defecto())
