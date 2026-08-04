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

    pasillos_existentes = 0
    if not creado:
        pasillos_existentes = Pasillo.objects.filter(supermercado=super_).count()
        if pasillos_existentes > 0:
            print(f"ℹ️  Pasillos ya existían ({pasillos_existentes}), no se recarga")

    if pasillos_existentes == 0:
        _cargar_pasillos_y_keywords(super_)

    migrar_lista_activa(usuario, super_)


def _cargar_pasillos_y_keywords(super_):
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
            "sanex", "dove", "nivea", "loreal", "l'oreal elvive", "garnier",
            "herbal essences", "pantene", "head and shoulders", "gel intimo",
            "jabon intimo", "ausonia", "evax", "tampax", "compresas ausonia",
            "compresas evax", "salvaslip evax", "dodot", "dodot activity",
            "dodot sensitive", "huggies", "huggies pants", "indasec", "axe",
            "rexona", "sanytol", "listerine", "oral b", "colgate", "signal",
            "cepillo electrico", "veet", "crema depilatoria", "cera depilatoria",
            "cuchillas venus", "wilkinson", "nenuco", "johnson baby", "mustela",
            "weleda", "aceite de bebe", "crema culito", "crema pañal",
            "biberon avent", "chicco", "tetina", "esterilizador biberones",
            "toallitas humedas wc", "compresas nocturnas", "protegeslips",
            "crema antiarrugas", "contorno de ojos", "serum facial",
            "mascarilla facial", "exfoliante facial", "agua micelar",
            "desmaquillante de ojos", "aceite corporal", "leche corporal",
            "crema corporal", "talco", "agua de colonia", "gel fijador",
            "fijador de pelo", "champu anticaida", "champu anticaspa",
            "tinte permanente", "decolorante pelo", "guantes de latex",
            "mascarillas higienicas", "gel hidroalcoholico", "jabon en pastilla",
            "esponja de baño", "piedra pomez", "cortaunas", "pinzas de depilar",
            "bastoncillos", "algodon en rama", "friegasuelos con lejia",
            "somat", "calgonit", "cepillo wc", "ambientador wc", "pastillas wc",
            "desatascador", "guantes desechables", "pañales talla 1",
            "pañales talla 2", "pañales talla 3", "pañales talla 4",
            "pañales talla 5", "pañales talla 6", "vitamina c", "vitamina d",
            "hierro complemento", "acido folico", "levadura de cerveza",
            "spirulina", "aloe vera gel", "aloe vera jugo", "aquilea",
            "protector solar niños", "crema solar bebe", "toallitas antibacterianas",
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
            "leche pascual", "leche celta", "leche asturiana", "leche puleva",
            "leche hacendado", "leche de almendras", "leche de avena",
            "leche de soja", "leche de coco bebida", "leche evaporada",
            "leche condensada", "nata montada spray", "batido de vainilla",
            "batido de fresa", "danone", "yogur danone", "yogur griego oikos",
            "yogur natural azucarado", "yogur proteico", "yogur skyr",
            "queso burgos danone", "queso philadelphia light",
            "queso mozzarella bola", "queso parmesano", "queso emmental",
            "queso gouda", "queso manchego", "queso de cabra", "queso azul",
            "queso roquefort", "queso en porciones", "queso el caserio",
            "mantequilla arias", "margarina flora", "zumo don simon",
            "zumo granini", "zumo minute maid", "zumo de tomate",
            "zumo de pomelo", "batido puleva", "cacaolat", "pan bimbo",
            "pan de molde bimbo", "pan artesano", "pan de payes",
            "pan de pueblo", "pan de cristal", "pan de leña", "chapata",
            "focaccia", "pan de nueces", "pan de pasas", "pan de aceitunas",
            "pan de semillas", "regañás", "grissini", "pan candeal", "brioche",
            "roscon", "palmera de chocolate", "palmera", "trenza de hojaldre",
            "berlina", "rosquilla", "bollo suizo", "torrijas",
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
            "cafe marcilla", "cafe saimaza", "cafe bonka", "cafe illy",
            "cafe lavazza", "cafe malaga", "cafe con leche capsulas",
            "cafe solo capsulas", "milka", "kit kat", "cacao valor",
            "chocolate a la taza", "leche condensada para cafe",
            "sacarina liquida", "azucarillos", "te matcha", "te chai",
            "rooibos", "kombucha", "servilletas de tela", "papel de horno silicona",
            "moldes magdalenas", "moldes tarta", "manga pastelera",
            "boquillas reposteria", "colorante alimentario", "perlas de azucar",
            "fideos de chocolate", "obleas", "papel para hornear",
            "bolsas para congelar carne", "bolsas de vacio", "tupperware hermetico",
            "recipiente hermetico", "vasos de papel", "platos de carton",
            "cubiertos de bambu", "pajitas", "palillos", "mondadientes",
            "encendedor", "mechero recargable", "pastillas de barbacoa", "leña",
            "piñas para encender", "velas de cumpleaños", "vela aromatica",
            "incienso", "pañuelos de tela", "pañuelos balsamicos",
            "servilletas de cocktail", "mantel de papel", "papel crepe",
            "galletas oreo rellenas", "cereales especial k", "cereales all bran",
            "muesli crunchy", "porridge", "tortitas de maiz",
            "tortitas de arroz con chocolate",
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
            "detergente skip", "detergente ariel", "detergente wipp express",
            "detergente dixan", "detergente ecologico", "suavizante vernel",
            "suavizante mimosin", "quitamanchas", "vanish", "lejia neutrex",
            "amoniaco perfumado", "limpiador wc", "limpiador baño",
            "limpia hornos", "desengrasante cocina",
            "limpiador de acero inoxidable", "estropajo metalico",
            "estropajo de esparto", "bayeta microfibra", "mopa",
            "cepillo de barrer", "pala recogedora", "papelera de cocina",
            "bolsas aspiradora", "ambientador enchufe", "ambientador spray",
            "vela ambientadora", "insecticida cucarachas", "insecticida hormigas",
            "matamoscas electrico", "trampa para ratones", "veneno para ratones",
            "antipolillas armario", "pienso royal canin", "pienso purina",
            "pienso whiskas", "pienso science plan", "comida humeda gato",
            "comida humeda perro", "snacks dentales perro", "arena aglomerante",
            "arena de silice", "transportin", "correa perro",
            "collar antipulgas", "champu para perros", "comida conejo",
            "heno para conejo", "comida hamster", "comida tortuga",
            "comida peces", "acuario filtro", "jaula pajaros",
            "bebedero animales",
        ]),
        ("Bodega / Agua / Cerveza", 5, [
            "vino", "vino tinto", "vino blanco", "vino rosado", "rioja", "ribera del duero",
            "cava", "sidra", "vermut", "ginebra", "ron", "whisky", "vodka",
            "tinto de verano", "sangria",
            "agua", "agua mineral", "agua con gas", "garrafa de agua",
            "cerveza", "cerveza sin alcohol", "cerveza 00", "mahou", "heineken",
            "estrella", "san miguel", "radler", "shandy",
            "vino verdejo", "vino albariño", "vino tempranillo", "vino garnacha",
            "vino crianza", "vino reserva", "vino gran reserva", "cava brut",
            "cava semiseco", "champagne", "sidra el gaitero", "sidra asturiana",
            "pacharan", "licor 43", "baileys", "brandy", "coñac", "orujo",
            "anis", "tequila", "cerveza sin gluten", "cerveza artesana",
            "cerveza ipa", "cerveza tostada", "cerveza cruzcampo",
            "cerveza alhambra", "cerveza amstel", "cerveza corona",
            "cerveza guinness", "agua con gas font vella", "agua bezoya",
            "agua solan de cabras", "agua fontecelta", "botellin de agua",
            "hielo picado", "mosto",
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
            "sal yodada", "sal maldon", "harina de maiz", "harina de fuerza",
            "harina panificable", "harina sin gluten", "levadura royal",
            "levadura fresca", "aceite hacendado", "aceite carbonell",
            "aceite koipesol", "aceite la española", "aceite de coco",
            "aceite de sesamo", "chocolate valor", "chocolate lindt",
            "chocolate milka", "chocolate nestle", "kinder bueno",
            "kinder sorpresa", "kinder chocolate", "twix", "mars", "snickers",
            "bounty", "toblerone", "haribo", "chuches haribo", "regaliz",
            "piruleta", "chupa chups", "trident", "orbit", "cereales kellogg's",
            "special k", "all bran", "fitness", "smacks", "froot loops",
            "mermelada hero", "mermelada la vieja fabrica", "miel de romero",
            "miel de milflores", "azucar glass", "azucar moreno de caña",
            "panela", "sirope de agave", "sirope de arce", "membrillo",
            "dulce de leche", "turron", "turron de jijona", "turron de alicante",
            "polvorones", "mazapan", "roscon relleno",
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
            "mayonesa hellmanns", "ketchup heinz", "mostaza dijon",
            "salsa perrins", "salsa worcestershire", "salsa teriyaki",
            "salsa agridulce", "salsa curry", "salsa cesar", "salsa yogur",
            "vinagre balsamico", "vinagre de manzana", "vinagre de jerez",
            "tomate frito hacendado", "tomate frito orlando", "tomate frito solis",
            "tomate natural triturado", "pisto manchego lata",
            "menestra de verduras lata", "esparragos verdes lata",
            "corazones de alcachofa lata", "pepinillos en vinagre",
            "cebolletas en vinagre", "coca cola sin cafeina", "pepsi",
            "pepsi max", "nestea", "lipton", "kas naranja", "kas limon",
            "trina", "caldo knorr", "caldo gallina blanca", "caldo starlux",
            "sopa de sobre", "sopa juliana", "pure de patata knorr",
            "pure de calabaza", "gazpacho alvalle", "salmorejo",
            "ensaladilla rusa lata", "macarrones gallo", "espaguetis barilla",
            "pasta de trigo integral", "pasta sin gluten", "pasta al huevo",
            "ñoquis", "arroz sos", "arroz brillante", "arroz bomba",
            "arroz para sushi", "arroz salvaje", "garbanzos cocidos",
            "lentejas cocidas", "alubias cocidas", "hummus", "falafel",
            "cuscus integral", "bulgur", "harina de garbanzo",
        ]),
        ("Conservas de pescado / Encurtidos", 8, [
            "atun", "atun en aceite", "atun al natural", "bonito del norte",
            "sardinas en conserva", "mejillones en escabeche", "berberechos",
            "almejas en conserva", "caballa", "anchoas",
            "aceitunas", "aceitunas verdes", "aceitunas negras", "aceitunas rellenas",
            "pepinillos", "cebollitas", "altramuces", "alcaparras",
            "atun claro hacendado", "atun calvo", "bonito isabel",
            "mejillones escabeche isabel", "sardinillas en aceite",
            "sardinas picantes", "melva", "ventresca de atun", "pate de atun",
            "aceitunas manzanilla", "aceitunas gordal", "aceitunas kalamata",
            "aceitunas hacendado", "aceitunas con hueso", "aceitunas sin hueso",
            "guindillas", "pepinillos hacendado", "cebolletas encurtidas",
            "banderillas", "esparragos en conserva finos", "esparragos gruesos",
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
            "gambas peladas congeladas", "langostinos cocidos",
            "mejillones al vapor", "almejas japonesas", "berberechos al natural",
            "pulpo cocido", "salmon ahumado", "bacalao ahumado",
            "caballa ahumada", "anchoas del cantabrico", "patatas fritas lays max",
            "patatas onduladas", "patatas artesanas", "doritos nacho cheese",
            "cheetos", "ruffles", "matutano", "frito lay",
            "palomitas microondas", "cacahuetes con cascara", "almendras crudas",
            "almendras fritas", "nueces", "avellanas", "pasas", "orejones",
            "dátiles", "higos secos", "mix de frutos secos",
            "mix de frutas desecadas", "salsa guacamole hacendado",
            "nachos con queso", "queso para nachos",
            "tortitas de maiz mexicanas", "burrito", "enchiladas", "jalapeños",
            "chili con carne lata", "tabasco verde",
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
            "manzana reineta", "manzana royal gala", "manzana granny smith",
            "pera limonera", "pera ercolina", "platano ecologico",
            "sandia sin pepitas", "melon galia", "melon cantalupo",
            "uva sin pepitas", "kiwi amarillo", "papaya madura", "guayaba",
            "carambola", "pitahaya", "maracuya", "lichi", "tamarindo", "yuca",
            "malanga", "ñame", "col china", "col rizada", "pak choi", "berza",
            "grelos", "espinacas frescas bolsa", "ensalada mixta bolsa",
            "ensalada cesar bolsa", "brotes de soja", "brotes tiernos",
            "germinados", "cebollino", "eneldo", "cilantro", "albahaca fresca",
            "menta fresca", "romero fresco", "tomillo fresco", "laurel fresco",
            "perejil fresco", "guindilla fresca", "pimiento italiano",
            "pimiento morron", "champiñon portobello", "seta shiitake",
            "seta ostra", "trufa fresca", "castañas", "piñones",
            "cacahuete fresco", "coco fresco",
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
            "jamon el pozo", "jamon campofrio", "jamon navidul",
            "pavo campofrio", "chorizo revilla", "chorizo palacios",
            "salchichon campofrio", "fuet palacios", "lomo embuchado navidul",
            "mortadela campofrio", "bacon oscar mayer", "salchichas oscar mayer",
            "salchichas frankfurt el pozo", "pate la piara", "pate campofrio",
            "sobrasada mallorquina", "queso de untar con jamon",
            "pizza casa tarradellas", "pizza buitoni", "lasaña findus",
            "canelones la cocinera", "empanadillas la cocinera",
            "croquetas la cocinera", "croquetas findus",
            "ensalada de pasta preparada", "wok de verduras preparado",
            "poke bowl", "sushi preparado", "tartar de atun preparado",
            "gazpacho preparado", "hummus preparado",
            "guacamole preparado envasado",
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
            "pollo campero", "pollo ecologico", "pechuga de pollo fileteada",
            "alitas de pollo adobadas", "solomillo de pollo",
            "jamoncitos de pollo", "muslos deshuesados", "pavo fileteado",
            "secreto de cerdo adobado", "presa de cerdo", "cinta de lomo",
            "chuletero de cerdo", "costillar de cerdo bbq",
            "carrilleras de cerdo", "morcillo de ternera", "aguja de ternera",
            "falda de ternera", "solomillo de ternera", "picaña",
            "vacio de ternera", "cordero lechal", "paletilla de cordero",
            "costillar de cordero", "pato", "codorniz", "faisan",
            "morcilla de arroz", "huevos ecologicos", "huevos de codorniz",
            "clara de huevo pasteurizada", "huevo liquido",
            "pimenton de la vera", "sal de ajo", "sal de apio",
            "adobo para carne", "especias para asar", "romero seco",
            "tomillo seco", "laurel seco", "eneldo seco",
            "hamburguesa de cerdo congelada", "salchichas congeladas",
            "solomillo congelado", "costillas congeladas",
        ]),
        ("Congelados", 13, [
            "guisantes congelados", "judias congeladas", "ensaladilla congelada",
            "menestra", "verdura congelada", "patatas congeladas",
            "salteado de verduras", "habas congeladas", "espinacas congeladas",
            "hielo", "bolsa de hielo", "pizza congelada", "pizzas congeladas",
            "croquetas", "varitas de pescado", "calamares a la romana", "rabas",
            "nuggets", "empanadillas", "helado", "helados", "tarrina helado",
            "magnum", "cornetto", "lasaña congelada", "canelones congelados",
            "guisantes findus", "menestra findus", "verduras salteadas congeladas",
            "brocoli congelado", "coliflor congelada",
            "espinacas en porciones congeladas", "patatas gajo congeladas",
            "patatas rusticas congeladas", "aros de cebolla congelados",
            "pizza casera congelada", "pizza margarita congelada",
            "pizza cuatro quesos congelada", "canelones congelados la cocinera",
            "lasaña boloñesa congelada", "nuggets de pollo findus",
            "varitas merluza pescanova", "gambas congeladas pescanova",
            "calamares congelados", "rabas congeladas", "sepia congelada",
            "pulpo congelado", "helado ben and jerrys", "helado haagen dazs",
            "polo frigo", "helado de nata", "helado de chocolate",
            "helado de vainilla", "tarta helada", "sorbete de limon",
            "hielo para copas",
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
    print(f"   → {len(datos)} pasillos")
    print(f"   → {total_keywords} palabras clave")


def migrar_lista_activa(usuario, super_nuevo):
    """
    Copia los productos de la lista activa del usuario (en cualquier otro
    supermercado) a una lista activa de Mercadona Agustinos, reasignando
    el pasillo de cada producto con las keywords del nuevo supermercado.
    """
    from compra.models import Lista, ListaItem
    from compra.views import inferir_pasillo

    lista_origen = Lista.objects.filter(
        usuario=usuario, activa=True
    ).exclude(supermercado=super_nuevo).order_by('-fecha').first()

    if not lista_origen:
        print("\nℹ️  No hay ninguna otra lista activa que migrar.")
        return

    lista_nueva, _ = Lista.objects.get_or_create(
        supermercado=super_nuevo,
        usuario=usuario,
        activa=True,
        defaults={}
    )

    copiados = 0
    for item in lista_origen.items.all():
        pasillo = inferir_pasillo(item.nombre, super_nuevo)
        _, creado = ListaItem.objects.get_or_create(
            lista=lista_nueva,
            nombre=item.nombre,
            defaults={'pasillo': pasillo, 'en_carro': item.en_carro}
        )
        if creado:
            copiados += 1

    print(f"\n🛒 Migración de lista:")
    print(f"   → Origen: '{lista_origen.supermercado.nombre}' ({lista_origen.items.count()} productos)")
    print(f"   → {copiados} productos copiados y reclasificados a Mercadona Agustinos")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python cargar_mercadona_agustinos.py email@del-usuario.com")
        sys.exit(1)
    cargar_mercadona_agustinos(sys.argv[1])
