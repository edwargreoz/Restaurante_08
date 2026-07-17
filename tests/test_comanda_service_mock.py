from unittest.mock import MagicMock, patch
import pytest
from pedidos.services import ComandaService


class TestComandaServiceConMock:

    def test_init_repos(self):
        comanda_repo = MagicMock()
        mesa_repo = MagicMock()
        service = ComandaService(
            comanda_repo=comanda_repo, mesa_repo=mesa_repo
        )
        assert service.comanda_repo == comanda_repo
        assert service.mesa_repo == mesa_repo

    def test_init_repos_instancias_diferentes(self):
        comanda_repo = MagicMock()
        mesa_repo = MagicMock()
        service = ComandaService(
            comanda_repo=comanda_repo, mesa_repo=mesa_repo
        )
        assert service.comanda_repo is not service.mesa_repo

    def test_comanda_service_tiene_metodos_principales(self):
        comanda_repo = MagicMock()
        mesa_repo = MagicMock()
        service = ComandaService(
            comanda_repo=comanda_repo, mesa_repo=mesa_repo
        )
        assert hasattr(service, 'abrir')
        assert hasattr(service, 'agregar_platos')
        assert hasattr(service, 'fusionar')
        assert hasattr(service, 'anular')
        assert hasattr(service, 'pagar')
        assert hasattr(service, 'pagar_split')
