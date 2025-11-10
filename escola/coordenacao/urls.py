# Em: escola/coordenacao/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomAuthToken, MaterialDidaticoViewSet, SalaLaboratorioViewSet,
    ColaboradorViewSet, RelatorioGerencialViewSet,
    ReservaSalaViewSet
)

router = DefaultRouter()
router.register(r'materiais', MaterialDidaticoViewSet)
router.register(r'salas', SalaLaboratorioViewSet)
router.register(r'colaboradores', ColaboradorViewSet)
router.register(r'relatorios', RelatorioGerencialViewSet)
router.register(r'reservas', ReservaSalaViewSet, basename='reserva')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api-token-auth/', CustomAuthToken.as_view(), name='api_token_auth'),
]