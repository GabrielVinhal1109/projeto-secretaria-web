# Em: escola/pedagogico/serializers.py (CORRIGIDO)
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import (
    Aluno, Turma, Nota, Disciplina, 
    EventoAcademico, PlanoDeAula, Materia, Falta, Presenca,
    Notificacao, Responsavel # <-- ADICIONADO AQUI
)
from escola.base.models import Usuario
from django.db.models import Avg 
# --- 1. ADICIONADO IMPORTS PARA GERAR SENHA ---
import random 
import string


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo customizado de Usuário.
    """
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'cargo']


class AlunoSerializer(serializers.ModelSerializer):
    """
    Serializer principal para listar e detalhar Alunos.
    """
    usuario = UsuarioSerializer(read_only=True) 
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    
    advertencias_count = serializers.SerializerMethodField()
    suspensoes_count = serializers.SerializerMethodField()
    media_geral = serializers.SerializerMethodField()

    class Meta:
        model = Aluno
        fields = [
            'id', 'usuario', 'turma', 'turma_nome', 'status', 
            'advertencias_count', 'suspensoes_count', 'media_geral'
        ]
        
    def get_media_geral(self, obj):
        media = Nota.objects.filter(aluno=obj).aggregate(media_avg=Avg('valor'))['media_avg']
        if media is None:
            return 0.0
        return round(media, 1)

    def get_advertencias_count(self, obj):
        return obj.advertencias.count()

    def get_suspensoes_count(self, obj):
        return obj.suspensoes.count()


class AlunoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer usado especificamente para CRIAR um novo Aluno.
    Gera uma senha aleatória e a retorna.
    """
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    cpf = serializers.CharField(write_only=True, required=True)
    
    # --- 2. CAMPO DE SENHA REMOVIDO DOS 'fields' OBRIGATÓRIOS ---
    # (Não precisamos mais do 'password' vindo do frontend)

    # --- 3. CAMPO PARA RETORNAR A SENHA GERADA ---
    temp_password = serializers.CharField(read_only=True)

    class Meta:
        model = Aluno
        fields = [
            'cpf', 'first_name', 'last_name', 'email', 
            'turma', 'status', 
            'temp_password' # <-- Adicionado para o retorno
        ]
        # Remove 'password' dos fields

    def validate_cpf(self, value):
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Já existe um usuário com este CPF (username).")
        return value

    def create(self, validated_data):
        # --- 4. LÓGICA DE GERAR SENHA ---
        
        # Gera uma senha aleatória de 8 dígitos (ex: 12345678)
        temp_password = ''.join(random.choices(string.digits, k=8))
        
        user_data = {
            'username': validated_data.pop('cpf'),
            'password': make_password(temp_password), # <-- Usa a senha gerada
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'email': validated_data.pop('email', ''),
            'cargo': 'aluno'
        }
        
        user = Usuario.objects.create(**user_data)
        
        aluno = Aluno.objects.create(usuario=user, **validated_data)
        
        # Anexa a senha temporária ao objeto 'aluno' para o serializer poder lê-la
        aluno.temp_password = temp_password
        
        return aluno


class TurmaSerializer(serializers.ModelSerializer):
    turno_display = serializers.CharField(source='get_turno_display', read_only=True)

    class Meta:
        model = Turma
        fields = ['id', 'nome', 'turno', 'turno_display']
        read_only_fields = ['turno_display']


class NotaCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nota
        fields = ['id', 'aluno', 'disciplina', 'bimestre', 'valor']

    def validate(self, data):
        if not self.instance: 
            if Nota.objects.filter(
                aluno=data['aluno'], 
                disciplina=data['disciplina'], 
                bimestre=data['bimestre']
            ).exists():
                raise serializers.ValidationError("Esta nota já foi lançada para este bimestre.")
        return data


class NotaSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.usuario.get_full_name', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.materia.nome', read_only=True)

    class Meta:
        model = Nota
        fields = [
            'id', 
            'aluno', 'aluno_nome', 
            'disciplina', 'disciplina_nome', 
            'bimestre', 'valor'
        ]
        read_only_fields = ['aluno_nome', 'disciplina_nome']


class EventoAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoAcademico
        fields = '__all__' 


class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = ['id', 'nome']


class DisciplinaSerializer(serializers.ModelSerializer):
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    materia_nome = serializers.CharField(source='materia.nome', read_only=True)
    professores = UsuarioSerializer(many=True, read_only=True) 
    
    class Meta:
        model = Disciplina
        fields = [
            'id', 'materia', 'materia_nome', 'carga_horaria', 
            'professores', 'turma', 'turma_nome'
        ]
        read_only_fields = [
            'materia_nome', 'professores', 'turma_nome'
        ]


class PlanoDeAulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanoDeAula
        fields = '__all__'

class FaltaSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo Falta.
    """
    aluno_nome = serializers.CharField(source='aluno.usuario.get_full_name', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.materia.nome', read_only=True)

    class Meta:
        model = Falta
        fields = [
            'id', 'aluno', 'aluno_nome', 'disciplina', 
            'disciplina_nome', 'data', 'justificada'
        ]
        read_only_fields = ['aluno_nome', 'disciplina_nome']


# --- CLASSES QUE FALTAVAM NO ARQUIVO ---

class NotificacaoSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo Notificacao.
    """
    class Meta:
        model = Notificacao
        fields = ['id', 'mensagem', 'data_envio', 'lida']


class ResponsavelSerializer(serializers.ModelSerializer):
    """
    Serializer para o Responsável, incluindo dados dos seus alunos.
    """
    # Usamos o AlunoSerializer que já existe para mostrar os alunos
    alunos = AlunoSerializer(many=True, read_only=True)
    usuario = UsuarioSerializer(read_only=True)

    class Meta:
        model = Responsavel
        fields = ['id', 'usuario', 'alunos']