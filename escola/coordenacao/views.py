# Em: escola/coordenacao/views.py
from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import (
    MaterialDidatico, SalaLaboratorio, Colaborador, 
    RelatorioGerencial, ReservaSala
)
from .serializers import (
    MaterialDidaticoSerializer, SalaLaboratorioSerializer, 
    ColaboradorSerializer, RelatorioGerencialSerializer,
    ReservaSalaReadSerializer, ReservaSalaWriteSerializer
)
from escola.base.permissions import IsCoordenacao
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

# --- VIEWSETS DA API ---

class MaterialDidaticoViewSet(viewsets.ModelViewSet):
    queryset = MaterialDidatico.objects.all()
    serializer_class = MaterialDidaticoSerializer
    permission_classes = [IsCoordenacao]

class SalaLaboratorioViewSet(viewsets.ModelViewSet):
    queryset = SalaLaboratorio.objects.all()
    serializer_class = SalaLaboratorioSerializer
    permission_classes = [permissions.IsAuthenticated] # Todos autenticados podem ver

# --- VIEWSETS QUE FALTAVAM (CORREÇÃO DO ERRO) ---
class ColaboradorViewSet(viewsets.ModelViewSet):
    queryset = Colaborador.objects.all()
    serializer_class = ColaboradorSerializer
    permission_classes = [IsCoordenacao]

class RelatorioGerencialViewSet(viewsets.ModelViewSet):
    queryset = RelatorioGerencial.objects.all()
    serializer_class = RelatorioGerencialSerializer
    permission_classes = [IsCoordenacao]

# --- VIEWSET NOVA PARA RESERVAS ---
class ReservaSalaViewSet(viewsets.ModelViewSet):
    """
    API para criar, ver, e deletar reservas de sala.
    """
    queryset = ReservaSala.objects.all().order_by('-data_inicio')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ReservaSalaReadSerializer
        return ReservaSalaWriteSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'cargo'):
            return ReservaSala.objects.none()

        admin_roles = ['administrador', 'coordenador', 'diretor', 'ti']
        if user.cargo in admin_roles or user.is_superuser:
            return ReservaSala.objects.all().order_by('-data_inicio')
        
        return ReservaSala.objects.filter(usuario=user).order_by('-data_inicio')

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsCoordenacao] # Só admin pode alterar/deletar
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

# --- VIEW DE LOGIN (JÁ EXISTIA) ---
class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })