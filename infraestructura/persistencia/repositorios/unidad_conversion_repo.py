from typing import Optional
from inventario.models import UnidadConversion as UnidadModel
from dominio.entidades.unidad_conversion import UnidadConversion

class UnidadConversionRepository:
    def obtener_por_id(self, unidad_id: int) -> Optional[UnidadConversion]:
        try:
            u = UnidadModel.objects.get(id=unidad_id)
            return UnidadConversion(id=u.id, nombre=u.nombre, abreviatura=u.abreviatura, factor_conversion=u.factor_conversion, unidad_base_id=u.unidad_base_id)
        except UnidadModel.DoesNotExist:
            return None

    def guardar(self, unidad: UnidadConversion) -> UnidadConversion:
        u, _ = UnidadModel.objects.update_or_create(
            id=unidad.id,
            defaults={'nombre': unidad.nombre, 'abreviatura': unidad.abreviatura, 'factor_conversion': unidad.factor_conversion, 'unidad_base_id': unidad.unidad_base_id}
        )
        return UnidadConversion(id=u.id, nombre=u.nombre, abreviatura=u.abreviatura, factor_conversion=u.factor_conversion, unidad_base_id=u.unidad_base_id)

    def listar(self) -> list:
        return [
            UnidadConversion(id=u.id, nombre=u.nombre, abreviatura=u.abreviatura, factor_conversion=u.factor_conversion, unidad_base_id=u.unidad_base_id)
            for u in UnidadModel.objects.all()
        ]
