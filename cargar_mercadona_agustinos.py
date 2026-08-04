"""
Carga el supermercado "Mercadona Agustinos" con el orden real de pasillos
y sus palabras clave, para un usuario concreto.

Uso (una sola vez, en el shell del servidor de producción):
    python cargar_mercadona_agustinos.py email@del-usuario.com
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from compra.models import Supermercado, Pasillo, Keyword


def cargar_mercadona_agustinos(email):
    from usuarios.models import Usuario

    try:
        usuario = Usuario.objects.get(email=email)
    except Usuario.DoesNotExist:
        print(f"❌ No existe ningún usuario con el email {email}")
        return

    print(f"ℹ️  Cargando 'Mercadona Agustinos' para el usuario: {usuario.username}")

    super_, creado = Supermercado.objects.get_or_create(
        nombre="Mercadona Agustinos",
        usuario=usuario,
        defaults={'direccion': '', 'activo': True}
    )
    if creado:
        print("✅ Supermercado creado")
    else:
        print("ℹ️  Supermercado ya existía")

    if not creado:
        pasillos_existentes = Pasillo.objects.filter(supermercado=super_).count()
        if pasillos_existentes > 0:
            print(f"ℹ️  Pasillos ya existían ({pasillos_existentes}), no se recarga")
            return

    datos = [
        ("Perfumería / Higiene personal / Fitoterapia / Bebé / Lavavajillas", 1, [
            "champu", "gel", "gel de baño", "gel de ducha", "gel de manos", "jabon de manos",
            "desodorante", "desodorante spray", "desodorante rollon", "pasta de dientes",
            "dentifrico", "colutorio", "enjuague bucal", "cepillo de dientes", "hilo dental",
            "compresas", "tampones", "salvaslips", "algodon", "discos desmaquillantes",
            "crema de afeitar", "espuma de afeitar", "cuchillas afeitar", "gillette",
            "preservativos", "tiritas", "alcohol 96", "acondicionador", "mascarilla pelo",
            "gomina", "laca", "espuma pelo", "tinte", "tinte de pelo", "crema hidratante",
            "crema de manos", "crema de la cara", "protector solar", "crema solar", "aftersun",
            "toallitas desmaquillantes", "colonia", "perfume",
            "complementos alimentarios", "vitaminas", "jarabe", "propolis", "jalea real",
            "melatonina", "colageno", "magnesio", "omega 3", "probioticos", "multivitaminico",
            "pañales", "toallitas bebe", "leche bebe", "potito", "papilla", "cereales bebe",
            "biberon", "chupete", "colonia bebe", "crema bebe",
            "lavavajillas", "lavavajillas mano", "fairy", "pastillas lavavajillas", "finish",
            "bayetas", "estropajo", "bolsas basura", "bolsas de basura",
            "escoba", "recogedor", "fregona", "cubo fregona", "guantes de fregar",
        ]),
        ("Zumos / Lácteos / Yogures / Panadería", 2, [
            "zumo", "zumo de naranja", "zumo de piña", "zumo de melocoton", "zumo de manzana",
            "nectar", "horchata",
            "leche", "leche entera", "leche desnatada", "leche semidesnatada",
            "leche sin lactosa", "leche con calcio", "leche de cabra",
            "nata", "nata para cocinar", "nata para montar", "batido", "batido chocolate",
            "yogur", "yogur natural", "yogur griego", "yogur bifidus", "yogur desnatado",
            "yogur de fresa", "yogur de limon", "actimel", "bifidus", "petit suisse",
            "flan", "flan de huevo", "natillas", "natillas de chocolate", "arroz con leche",
            "cuajada", "kefir",
            "queso", "queso tierno", "queso semicurado", "queso curado", "queso en lonchas",
            "queso rallado", "queso fresco", "queso de burgos", "queso crema", "philadelphia",
            "pan", "barra de pan", "pistola", "baguette", "pan integral", "pan de centeno",
            "croissant", "napolitana", "ensaimada", "magdalenas", "donuts", "sobaos", "bizcocho",
        ]),
        ("Desayuno / Café / Menaje / Pañuelos", 3, [
            "tarta", "tarta de queso", "tarta de chocolate", "brownie",
            "fajita", "tortilla de trigo", "kit fajitas", "taco",
            "pan de molde", "pan de molde blanco", "pan de molde integral",
            "pan de molde sin corteza", "pan de hamburguesa", "pan de perrito", "pan pita",
            "galletas", "galletas maria", "galletas tostadas", "galletas con chocolate",
            "cookies", "principe", "oreo", "barritas de cereales", "digestive",
            "tostadas", "mantequilla", "margarina",
            "pan tostado", "biscotes", "picos", "colines", "pan rallado",
            "cafe", "cafe molido", "cafe en grano", "cafe soluble", "cafe descafeinado",
            "cafe capsulas", "capsulas nespresso", "capsulas dolce gusto",
            "cola cao", "nesquik", "cacao", "cacao puro", "cacao en polvo",
            "te", "te verde", "te negro", "te rojo", "poleo menta", "tila", "infusion",
            "manzanilla", "valeriana",
            "vasos desechables", "platos desechables", "cubiertos desechables",
            "papel film", "papel horno", "moldes silicona", "bolsas congelacion",
            "papel aluminio", "tupper", "bolsas zip", "bolsas hermeticas",
            "carbon vegetal", "briquetas", "pastillas de encendido",
            "vela", "mechero", "cerillas",
            "pañuelos", "pañuelos de papel", "servilletas", "servilletas de papel", "kleenex",
        ]),
        ("Droguería / Limpieza / Animales", 4, [
            "papel higienico", "papel de cocina", "rollo de cocina",
            "detergente", "detergente liquido", "detergente capsulas", "detergente polvo",
            "suavizante",
            "lejia", "lejia ropa", "amoniaco", "limpiacristales", "multiusos",
            "desengrasante", "kh7", "friegasuelos", "limpiador hogar", "don limpio",
            "pienso", "pienso perro", "pienso gato", "comida perro", "comida gato",
            "premios perro", "snacks perro", "premios gato", "arena gato", "arena para gatos",
            "comida pajaros", "alpiste",
            "ambientador", "insecticida", "matamoscas", "antipolillas",
        ]),
        ("Bodega / Agua / Cerveza", 5, [
            "vino", "vino tinto", "vino blanco", "vino rosado", "rioja", "ribera del duero",
            "cava", "sidra", "vermut", "ginebra", "ron", "whisky", "vodka",
            "tinto de verano", "sangria",
            "agua", "agua mineral", "agua con gas", "garrafa de agua",
            "cerveza", "cerveza sin alcohol", "cerveza 00", "mahou", "heineken",
            "estrella", "san miguel", "radler", "shandy",
        ]),
        ("Despensa / Dulces / Cereales", 6, [
            "sal", "sal fina", "sal gorda",
            "harina", "harina de trigo", "harina de reposteria", "harina integral",
            "levadura", "gasificante",
            "aceite", "aceite de oliva", "aceite virgen extra", "aceite de girasol",
            "gominolas", "chuches", "caramelos", "chicles", "lacasitos", "conguitos",
            "chocolate", "chocolate con leche", "chocolate negro", "tableta de chocolate",
            "bombones", "nutella", "nocilla", "crema de cacao",
            "cereales", "cereales integrales", "corn flakes", "chocapic", "muesli",
            "avena", "copos de avena",
            "napolitana de chocolate", "berlinesas", "plumcake",
            "mermelada", "mermelada de fresa", "miel",
            "melocoton en almibar", "piña en almibar", "macedonia de frutas", "fruta en almibar",
            "azucar", "azucar blanco", "azucar moreno", "sacarina", "edulcorante", "stevia",
        ]),
        ("Salsas / Conservas / Pasta / Arroz", 7, [
            "mayonesa", "ketchup", "mostaza", "salsa barbacoa", "alioli", "salsa de soja",
            "salsa rosa", "tabasco", "salsa carbonara", "salsa boloñesa", "salsa pesto",
            "vinagre", "vinagre de vino", "vinagre de modena",
            "tomate triturado", "tomate frito", "tomate pelado",
            "esparragos blancos", "pimientos del piquillo", "guisantes en conserva",
            "maiz dulce", "champiñones en conserva",
            "coca-cola", "cocacola", "coca cola zero", "coca cola light",
            "fanta", "fanta naranja", "fanta limon", "sprite", "seven up",
            "schweppes", "tonica", "aquarius", "gatorade", "monster", "red bull",
            "caldo de pollo", "caldo de verduras", "avecrem", "pastilla de caldo",
            "caldo de carne",
            "lentejas de bote", "fabada", "cocido", "gazpacho envasado", "pisto",
            "pure de patatas",
            "macarrones", "espaguetis", "tallarines", "fideos", "espirales", "lazos",
            "pasta integral", "raviolis", "tortellini", "lasaña", "canelones", "cuscus",
            "quinoa",
            "lentejas", "garbanzos", "alubias", "alubias blancas", "alubias pintas",
            "arroz", "arroz blanco", "arroz redondo", "arroz largo", "arroz integral",
            "arroz basmati", "arroz vaporizado",
        ]),
        ("Conservas de pescado / Encurtidos", 8, [
            "atun", "atun en aceite", "atun al natural", "bonito del norte",
            "sardinas en conserva", "mejillones en escabeche", "berberechos",
            "almejas en conserva", "caballa", "anchoas",
            "aceitunas", "aceitunas verdes", "aceitunas negras", "aceitunas rellenas",
            "pepinillos", "cebollitas", "altramuces", "alcaparras",
        ]),
        ("Pescadería / Snacks / Frutos secos", 9, [
            "salmon", "rodaja de salmon", "filete de salmon", "merluza", "filete de merluza",
            "rodaja de merluza", "pescadilla", "gambas", "gambon", "langostinos",
            "bacalao", "bacalao desalado", "bacalao fresco", "atun fresco", "dorada",
            "lubina", "sardinas frescas", "boquerones", "calamar", "anillas de calamar",
            "chipirones", "sepia", "pulpo", "patas de pulpo", "mejillones frescos",
            "almejas", "chirlas", "berberechos frescos", "palitos de cangrejo", "surimi",
            "trucha", "gallo", "lenguado", "emperador",
            "patatas fritas", "patatas de bolsa", "lays", "pringles", "doritos", "nachos",
            "gusanitos", "palomitas", "grefusa",
            "salsa nachos", "guacamole", "salsa picante mexicana",
            "frutos secos", "pistachos", "cacahuetes fritos", "almendras tostadas",
            "coctel de frutos secos", "pipas", "anacardos",
        ]),
        ("Frutería", 10, [
            "manzana", "manzana golden", "manzana fuji", "pera", "pera conferencia",
            "platano", "platano de canarias", "fresa", "freson", "kiwi", "piña",
            "piña natural", "mango", "sandia", "melon", "melon piel de sapo", "uva",
            "uva blanca", "uva negra", "ciruela", "cereza", "picota", "arandano",
            "frambuesa", "mora", "naranja", "naranja para zumo", "limon", "mandarina",
            "clemenules", "pomelo", "lima", "aguacate", "aguacate hass", "melocoton",
            "albaricoque", "paraguaya", "nectarina", "breva", "higo", "caqui",
            "chirimoya", "granada", "nispero", "coco", "papaya",
            "patata", "patata nueva", "patata para freir", "cebolla", "cebolla dulce",
            "cebolla morada", "ajo", "ajo morado", "tomate", "tomate ensalada",
            "tomate pera", "tomate rama", "tomate cherry", "pepino", "pimiento",
            "pimiento verde", "pimiento rojo", "pimiento amarillo", "pimiento padron",
            "calabacin", "berenjena", "zanahoria", "puerro", "apio", "lechuga",
            "lechuga iceberg", "lechuga romana", "cogollos", "rucula", "canonigos",
            "espinacas", "espinacas baby", "acelgas", "brocoli", "coliflor", "repollo",
            "lombarda", "alcachofa", "esparrago", "esparrago verde", "champiñon",
            "champiñon laminado", "setas", "calabaza", "rabano", "remolacha",
            "judia verde", "judia plana", "guisante fresco", "habas", "maiz mazorca",
            "jengibre", "bimi", "kale", "endivias", "batata", "boniato", "nabo", "hinojo",
        ]),
        ("Charcutería envasada / Platos preparados", 11, [
            "lasaña fresca", "pizza fresca", "ensalada preparada", "canelones frescos",
            "jamon", "jamon york", "jamon cocido", "jamon extra", "jamon serrano",
            "jamon iberico", "paleta", "pavo en lonchas", "pechuga de pavo lonchas",
            "chorizo", "chorizo pamplona", "chorizo sarta", "chorizo dulce",
            "chorizo picante", "salchichon", "fuet", "longaniza", "lomo embuchado",
            "mortadela", "chopped", "chistorra", "morcilla", "morcilla de burgos",
            "bacon", "beicon", "pate", "pate de higado", "foie", "foie gras",
            "sobrasada", "salchichas frankfurt",
        ]),
        ("Carnicería / Charcutería fresca / Huevos", 12, [
            "pollo", "pollo entero", "pechuga de pollo", "filetes de pollo",
            "muslos de pollo", "alitas de pollo", "contramuslos pollo", "pavo",
            "pechuga de pavo", "filetes de pavo", "cerdo", "solomillo de cerdo",
            "lomo de cerdo", "filetes de lomo", "costillas de cerdo", "chuletas de cerdo",
            "panceta", "secreto iberico", "presa iberico", "carne picada",
            "carne picada vacuna", "carne picada pollo", "carne picada mixta", "ternera",
            "filetes de ternera", "entrecot", "chuleton", "redondo de ternera",
            "magro de cerdo", "cordero", "chuletas de cordero", "pierna de cordero",
            "conejo", "higado", "callos", "rabo de toro", "hamburguesa",
            "hamburguesa de ternera", "hamburguesa de pollo", "salchichas frescas",
            "albondigas frescas",
            "jamon cortado", "queso cortado", "ensaladilla rusa fresca", "empanada fresca",
            "huevos", "huevos l", "huevos xl", "huevos m", "huevos camperos",
            "pimienta", "oregano", "perejil", "pimenton", "canela", "comino",
            "colorante", "azafran", "curcuma", "curry", "nuez moscada",
            "hierbas provenzales",
            "carne congelada", "hamburguesas congeladas", "alitas congeladas",
            "filetes congelados",
        ]),
        ("Congelados", 13, [
            "guisantes congelados", "judias congeladas", "ensaladilla congelada",
            "menestra", "verdura congelada", "patatas congeladas",
            "salteado de verduras", "habas congeladas", "espinacas congeladas",
            "hielo", "bolsa de hielo", "pizza congelada", "pizzas congeladas",
            "croquetas", "varitas de pescado", "calamares a la romana", "rabas",
            "nuggets", "empanadillas", "helado", "helados", "tarrina helado",
            "magnum", "cornetto", "lasaña congelada", "canelones congelados",
        ]),
    ]

    total_keywords = 0
    for nombre, orden, palabras in datos:
        pasillo = Pasillo.objects.create(
            supermercado=super_,
            nombre=nombre,
            orden=orden
        )
        kws = [Keyword(pasillo=pasillo, palabra=p) for p in palabras]
        Keyword.objects.bulk_create(kws, ignore_conflicts=True)
        total_keywords += len(palabras)
        print(f"  ✅ {orden}. {nombre} ({len(palabras)} keywords)")

    print(f"\n🎉 Carga completada:")
    print(f"   → 1 supermercado (Mercadona Agustinos)")
    print(f"   → {len(datos)} pasillos")
    print(f"   → {total_keywords} palabras clave")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python cargar_mercadona_agustinos.py email@del-usuario.com")
        sys.exit(1)
    cargar_mercadona_agustinos(sys.argv[1])
