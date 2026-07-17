from dominio.excepciones import (
    AppError, ReglaNegocioViolada, TransicionEstadoInvalida,
    MesaConComandaActiva, CajaNoAbierta, ProductoSinStock,
    CapacidadExcedida, StockInsuficiente, PlatoNoDisponible,
    ComandaNoDisponible, MontoInvalido, ReferenciaInvalida,
    UnionInvalida, InsumoAgotado, UnidadConversionInvalida,
    MargenInvalidoError,
)


class RecursoNoEncontrado(AppError):
    pass


class AccesoNoAutorizado(AppError):
    pass
