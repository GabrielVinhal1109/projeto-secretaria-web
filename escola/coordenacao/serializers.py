# Em: escola/coordenacao/serializers.py
from rest_framework import serializers
from .models import SalaLaboratorio, ReservaSala, MaterialDidatico, Colaborador, RelatorioGerencial
from escola.base.models import Usuario
from django.db.models import Q

# Serializers que você já tinha
class MaterialDidaticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialDidatico
        fields = '__all__'

class ColaboradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Colaborador
        fields = '__all__'

class RelatorioGerencialSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelatorioGerencial
        fields = '__all__'

# --- NOVOS SERIALIZERS PARA RESERVA DE SALA ---

class SalaLaboratorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaLaboratorio
        fields = ['id', 'nome', 'tipo', 'capacidade']

class UsuarioReservaSerializer(serializers.ModelSerializer):
    """ Serializer simplificado para mostrar quem reservou """
    class Meta:
        model = Usuario
        fields = ['id', 'first_name', 'last_name', 'username']

class ReservaSalaReadSerializer(serializers.ModelSerializer):
    """ Serializer para LER reservas, mostrando detalhes """
    usuario = UsuarioReservaSerializer(read_only=True)
    sala = SalaLaboratorioSerializer(read_only=True)

    class Meta:
        model = ReservaSala
        fields = ['id', 'sala', 'usuario', 'data_inicio', 'data_fim']

class ReservaSalaWriteSerializer(serializers.ModelSerializer):
    """ Serializer para CRIAR/ATUALIZAR reservas """
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = ReservaSala
        fields = ['id', 'sala', 'usuario', 'data_inicio', 'data_fim']
    
    def validate(self, data):
        """
        Garante que não há reservas sobrepostas.
        """
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')
        sala = data.get('sala')

        if data_inicio >= data_fim:
            raise serializers.ValidationError("A data de término deve ser posterior à data de início.")

        conflitos = ReservaSala.objects.filter(
            sala=sala,
            data_inicio__lt=data_fim,
            data_fim__gt=data_inicio
        )

        if self.instance:
            conflitos = conflitos.exclude(pk=self.instance.pk)

        if conflitos.exists():
            raise serializers.ValidationError(
                "Esta sala já está reservada para este horário. Por favor, escolha outro."
            )

        return data