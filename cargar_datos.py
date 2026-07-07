import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from compra.models import Supermercado, Pasillo, Keyword


def cargar_datos():
    from usuarios.models import Usuario

    try:
        admin = Usuario.objects.filter(is_superuser=True).first()
        if not admin:
            print("❌ No hay superusuario.")
            return
    except Exception as e:
        print(f"❌ Error al obtener usuario: {e}")
        return

    print(f"ℹ️  Cargando datos para el usuario: {admin.username}")

    super_, creado = Supermercado.objects.get_or_create(
        nombre="Mi Super del Barrio",
        usuario=admin,
        defaults={'direccion': '', 'activo': True}
    )
    if creado:
        print("✅ Supermercado creado")
    else:
        print("ℹ️  Supermercado ya existía")

    # Solo carga datos si el supermercado es nuevo
    if not creado:
        pasillos_existentes = Pasillo.objects.filter(supermercado=super_).count()
        if pasillos_existentes > 0:
            print(f"ℹ️  Pasillos ya existían ({pasillos_existentes}), no se recarga")
            return

    datos = [
        ("Perfumería", 1, [
            "champu","gel","gel de baño","gel de ducha","gel de manos","jabon de manos",
            "desodorante","desodorante spray","desodorante rollon","pasta de dientes",
            "dentifrico","colutorio","enjuague bucal","cepillo de dientes","hilo dental",
            "compresas","tampones","salvaslips","pañuelos","pañuelos de papel","algodon",
            "discos desmaquillantes","crema de afeitar","espuma de afeitar","cuchillas afeitar",
            "gillette","preservativos","tiritas","alcohol 96","acondicionador","mascarilla pelo",
            "gomina","laca","espuma pelo","tinte","tinte de pelo","crema hidratante",
            "crema de manos","crema de la cara","protector solar","crema solar","aftersun",
            "toallitas desmaquillantes","colonia","perfume"
        ]),
        ("Droguería / Animales", 2, [
            "detergente","detergente liquido","detergente capsulas","detergente polvo",
            "suavizante","lejia","lejia ropa","amoniaco","lavavajillas","lavavajillas mano",
            "fairy","pastillas lavavajillas","finish","limpiacristales","multiusos",
            "desengrasante","kh7","friegasuelos","limpiador hogar","don limpio",
            "bolsas basura","bolsas de basura","papel cocina","papel de cocina",
            "papel higienico","servilletas","bayetas","estropajo","papel aluminio",
            "film transparente","insecticida","ambientador",
            "pienso","pienso perro","pienso gato","comida perro","comida gato",
            "premios perro","snacks perro","premios gato","arena gato","arena para gatos",
            "comida pajaros","alpiste",
            "pañales","toallitas bebe","leche bebe","potito","papilla","cereales bebe"
        ]),
        ("Encurtidos / Pastas", 3, [
            "macarrones","espaguetis","tallarines","fideos","espirales","lazos",
            "pasta integral","raviolis","tortellini","lasaña","canelones","cuscus",
            "quinoa","lentejas","garbanzos","alubias","alubias blancas","alubias pintas",
            "pure de patatas","arroz","arroz blanco","arroz redondo","arroz largo",
            "arroz integral","arroz basmati","arroz vaporizado",
            "aceitunas","aceitunas verdes","aceitunas negras","aceitunas rellenas",
            "pepinillos","cebollitas","altramuces","alcaparras","fabada asturiana",
            "atun","atun en aceite","atun al natural","bonito del norte",
            "sardinas en conserva","mejillones en escabeche","berberechos",
            "almejas en conserva","caballa","anchoas","tomate triturado","tomate frito",
            "tomate pelado","esparragos blancos","pimientos del piquillo",
            "guisantes en conserva","maiz dulce","champiñones en conserva",
            "aceite","aceite de oliva","aceite virgen extra","aceite de girasol",
            "vinagre","vinagre de vino","vinagre de modena",
            "sal","sal fina","sal gorda","mayonesa","ketchup","mostaza","salsa barbacoa",
            "alioli","salsa de soja","salsa rosa","tabasco","salsa carbonara",
            "salsa boloñesa","salsa pesto","guacamole",
            "pimienta","oregano","perejil","pimenton","canela","comino","colorante",
            "azafran","curcuma","curry","nuez moscada","hierbas provenzales"
        ]),
        ("Bodega", 4, [
            "vino","vino tinto","vino blanco","vino rosado","rioja","ribera del duero",
            "cava","sidra","vermut","ginebra","ron","whisky","vodka",
            "tinto de verano","sangria"
        ]),
        ("Refrescos", 5, [
            "agua","agua mineral","agua con gas","garrafa de agua",
            "coca-cola","cocacola","coca cola zero","coca cola light",
            "fanta","fanta naranja","fanta limon","sprite","seven up",
            "schweppes","tonica","aquarius","gatorade","monster","red bull",
            "zumo","zumo de naranja","zumo de piña","zumo de melocoton","zumo de manzana",
            "nectar","horchata",
            "cerveza","cerveza sin alcohol","cerveza 00","mahou","heineken",
            "estrella","san miguel","radler","shandy"
        ]),
        ("Patatas Fritas / Snacks", 6, [
            "patatas fritas","patatas de bolsa","lays","pringles","doritos","nachos",
            "gusanitos","palomitas","grefusa","frutos secos","pistachos",
            "cacahuetes fritos","almendras tostadas","coctel de frutos secos",
            "pipas","anacardos"
        ]),
        ("Café / Leche", 7, [
            "leche","leche entera","leche desnatada","leche semidesnatada",
            "leche sin lactosa","leche con calcio","leche de cabra",
            "nata","nata para cocinar","nata para montar","batido","batido chocolate",
            "mantequilla","mantequilla con sal","mantequilla sin sal","margarina",
            "huevos","huevos l","huevos xl","huevos m","huevos camperos",
            "cafe","cafe molido","cafe en grano","cafe soluble","cafe descafeinado",
            "cafe capsulas","capsulas nespresso","capsulas dolce gusto",
            "cola cao","nesquik","cacao","cacao puro","cacao en polvo",
            "te","te verde","te negro","te rojo","manzanilla","poleo menta",
            "tila","infusion","valeriana"
        ]),
        ("Galletas / Bollería", 8, [
            "cereales","cereales integrales","corn flakes","chocapic","muesli",
            "avena","copos de avena","galletas","galletas maria","galletas tostadas",
            "galletas con chocolate","cookies","principe","oreo","barritas de cereales",
            "digestive","azucar","azucar blanco","azucar moreno","sacarina",
            "edulcorante","stevia","miel","mermelada","mermelada de fresa",
            "crema de cacao","nutella","nocilla","chocolate","chocolate con leche",
            "chocolate negro","tableta de chocolate","bombones","gominolas","chuches",
            "caramelos","chicles","lacasitos","conguitos"
        ]),
        ("Panadería", 9, [
            "pan","barra de pan","pistola","baguette","pan integral","pan de centeno",
            "pan de molde","pan de molde blanco","pan de molde integral",
            "pan de molde sin corteza","pan de hamburguesa","pan de perrito",
            "pan pita","pan tostado","biscotes","picos","colines",
            "pan rallado","croissant","napolitana","napolitana de chocolate",
            "ensaimada","magdalenas","donuts","berlinesas","sobaos","bizcocho",
            "plumcake","tortitas de arroz","masa de hojaldre","masa de pizza",
            "masa quebrada","churros","porras"
        ]),
        ("Yogures / Lácteos frescos", 10, [
            "yogur","yogur natural","yogur griego","yogur bifidus","yogur desnatado",
            "yogur de fresa","yogur de limon","actimel","bifidus","petit suisse",
            "flan","flan de huevo","natillas","natillas de chocolate","arroz con leche",
            "cuajada","kefir",
            "queso","queso tierno","queso semicurado","queso curado","queso viejo",
            "queso en lonchas","queso rallado","queso mozzarella","mozzarella fresca",
            "queso fresco","queso de burgos","queso crema","philadelphia","queso mascarpone"
        ]),
        ("Pescadería", 11, [
            "salmon","rodaja de salmon","filete de salmon","merluza","filete de merluza",
            "rodaja de merluza","pescadilla","gambas","gambon","langostinos",
            "bacalao","bacalao desalado","bacalao fresco","atun fresco","dorada","lubina",
            "sardinas frescas","boquerones","calamar","anillas de calamar","chipirones",
            "sepia","pulpo","patas de pulpo","mejillones frescos","almejas","chirlas",
            "berberechos frescos","palitos de cangrejo","surimi","trucha","gallo",
            "lenguado","emperador"
        ]),
        ("Carnicería", 12, [
            "pollo","pollo entero","pechuga de pollo","filetes de pollo","muslos de pollo",
            "alitas de pollo","contramuslos pollo","pavo","pechuga de pavo",
            "filetes de pavo","cerdo","solomillo de cerdo","lomo de cerdo",
            "filetes de lomo","costillas de cerdo","chuletas de cerdo","panceta",
            "secreto iberico","presa iberico","carne picada","carne picada vacuna",
            "carne picada pollo","carne picada mixta","ternera","filetes de ternera",
            "entrecot","chuleton","redondo de ternera","magro de cerdo","cordero",
            "chuletas de cordero","pierna de cordero","conejo","higado","callos",
            "rabo de toro","hamburguesa","hamburguesa de ternera","hamburguesa de pollo",
            "salchichas frescas","albondigas frescas"
        ]),
        ("Charcutería", 13, [
            "jamon","jamon york","jamon cocido","jamon extra","jamon serrano",
            "jamon iberico","paleta","pavo en lonchas","pechuga de pavo lonchas",
            "chorizo","chorizo pamplona","chorizo sarta","chorizo dulce","chorizo picante",
            "salchichon","fuet","longaniza","lomo embuchado","mortadela","chopped",
            "chistorra","morcilla","morcilla de burgos","bacon","beicon",
            "pate","pate de higado","foie","foie gras","sobrasada","salchichas frankfurt"
        ]),
        ("Frutería", 14, [
            "manzana","manzana golden","manzana fuji","pera","pera conferencia",
            "platano","platano de canarias","fresa","freson","kiwi","piña","piña natural",
            "mango","sandia","melon","melon piel de sapo","uva","uva blanca","uva negra",
            "ciruela","cereza","picota","arandano","frambuesa","mora","naranja",
            "naranja para zumo","limon","mandarina","clemenules","pomelo","lima",
            "aguacate","aguacate hass","melocoton","albaricoque","paraguaya","nectarina",
            "breva","higo","caqui","chirimoya","granada","nispero","coco","papaya",
            "patata","patata nueva","patata para freir","cebolla","cebolla dulce",
            "cebolla morada","ajo","ajo morado","tomate","tomate ensalada","tomate pera",
            "tomate rama","tomate cherry","pepino","pimiento","pimiento verde",
            "pimiento rojo","pimiento amarillo","pimiento padron","calabacin","berenjena",
            "zanahoria","puerro","apio","lechuga","lechuga iceberg","lechuga romana",
            "cogollos","rucula","canonigos","espinacas","espinacas baby","acelgas",
            "brocoli","coliflor","repollo","lombarda","alcachofa","esparrago",
            "esparrago verde","champiñon","champiñon laminado","setas","calabaza",
            "rabano","remolacha","judia verde","judia plana","guisante fresco","habas",
            "maiz mazorca","jengibre","bimi","kale","endivias","batata","boniato",
            "nabo","hinojo"
        ]),
        ("Congelados Verdura", 15, [
            "guisantes congelados","judias congeladas","ensaladilla congelada","menestra",
            "verdura congelada","patatas congeladas","salteado de verduras",
            "habas congeladas","espinacas congeladas"
        ]),
        ("Congelados Pescado / Listos para comer", 16, [
            "hielo","bolsa de hielo","pizza congelada","pizzas congeladas","croquetas",
            "varitas de pescado","calamares a la romana","rabas","nuggets","empanadillas",
            "helado","helados","tarrina helado","magnum","cornetto",
            "hamburguesas congeladas","lasaña congelada","canelones congelados"
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
    print(f"   → 1 supermercado")
    print(f"   → {len(datos)} pasillos")
    print(f"   → {total_keywords} palabras clave")


if __name__ == '__main__':
    cargar_datos()