
from django.contrib import admin
from .models import Insumo, Receta, RecetaInsumo, MovimientoInsumo

admin.site.register(Insumo)
admin.site.register(Receta)
admin.site.register(RecetaInsumo)
admin.site.register(MovimientoInsumo)
