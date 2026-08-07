from django.contrib import admin
from .models import Supermercado, Pasillo, Keyword, Lista, ListaItem, Categoria, CategoriaKeyword


class PasilloInline(admin.TabularInline):
    model = Pasillo
    extra = 1
    ordering = ['orden']


class CategoriaKeywordInline(admin.TabularInline):
    model = CategoriaKeyword
    extra = 3


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']
    inlines = [CategoriaKeywordInline]


@admin.register(CategoriaKeyword)
class CategoriaKeywordAdmin(admin.ModelAdmin):
    list_display = ['palabra', 'categoria']
    list_filter = ['categoria']
    search_fields = ['palabra']


class KeywordInline(admin.TabularInline):
    model = Keyword
    extra = 3


class ListaItemInline(admin.TabularInline):
    model = ListaItem
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Supermercado)
class SupermercadoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'usuario', 'direccion', 'activo', 'publico', 'total_likes', 'created_at']
    list_filter = ['activo', 'publico']
    search_fields = ['nombre']
    inlines = [PasilloInline]


@admin.register(Pasillo)
class PasilloAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'supermercado', 'orden']
    list_filter = ['supermercado']
    search_fields = ['nombre']
    ordering = ['supermercado', 'orden']
    filter_horizontal = ['categorias']
    inlines = [KeywordInline]


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['palabra', 'pasillo']
    list_filter = ['pasillo__supermercado']
    search_fields = ['palabra']


@admin.register(Lista)
class ListaAdmin(admin.ModelAdmin):
    list_display = ['supermercado', 'fecha', 'activa', 'total_productos']
    list_filter = ['supermercado', 'activa']
    inlines = [ListaItemInline]


@admin.register(ListaItem)
class ListaItemAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'lista', 'pasillo', 'en_carro']
    list_filter = ['en_carro', 'lista__supermercado']
    search_fields = ['nombre']
