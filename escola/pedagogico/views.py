# Em: escola/pedagogico/views.py (CORRIGIDO)

import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Avg, F
from django.template.loader import render_to_string 
from django.http import HttpResponse 

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action 
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response 

# --- IMPORTAÇÕES DE PDF ATUALIZADAS ---
from io import BytesIO
from xhtml2pdf import pisa
# --- FIM DAS IMPORTAÇÕES DE PDF ---

from .serializers import (
    NotaSerializer, EventoAcademicoSerializer, 
    AlunoSerializer, TurmaSerializer, AlunoCreateSerializer,
    PlanoDeAulaSerializer, DisciplinaSerializer,
    NotaCreateUpdateSerializer, MateriaSerializer,
    FaltaSerializer, NotificacaoSerializer,
    ResponsavelSerializer
)
from escola.base.permissions import IsProfessor, IsAluno, IsCoordenacao, IsResponsavel

from .models import (
    Aluno, 
    Nota, 
    Falta,
    Presenca, 
    Turma, 
    Disciplina,
    EventoAcademico, 
    PlanoDeAula,
    Materia,
    Notificacao, 
    Responsavel
)
from escola.disciplinar.models import Advertencia, Suspensao

# --- Bloco do WeasyPrint REMOVIDO ---

# ===================================================================
# VIEWSETS
# ===================================================================

class DisciplinaViewSet(viewsets.ModelViewSet):
    """
    API para Disciplinas.
    Professores podem ver apenas suas próprias disciplinas.
    Coordenação pode ver todas.
    """
    serializer_class = DisciplinaSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Começa com o queryset correto de Disciplina
        queryset = Disciplina.objects.all().order_by('materia__nome') 

        if not hasattr(user, 'cargo'):
            return Disciplina.objects.none() 

        # Filtra por turma (para o modal de notas)
        turma_id = self.request.query_params.get('turma_id')
        if turma_id:
            queryset = queryset.filter(turma_id=turma_id)

        # Professor só vê as suas
        if user.cargo == 'professor':
            return queryset.filter(professores=user)
        
        # Aluno só vê as da sua turma
        if user.cargo == 'aluno': 
            if hasattr(user, 'aluno_profile'):
                return queryset.filter(turma=user.aluno_profile.turma)
            else:
                return Disciplina.objects.none() 

        # Admin/Coord vê tudo (respeitando o filtro de turma)
        admin_roles = ['administrador', 'coordenador', 'diretor', 'ti']
        if user.cargo in admin_roles or user.is_superuser:
            return queryset
            
        return Disciplina.objects.none() 

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsCoordenacao]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]


class EventoAcademicoViewSet(viewsets.ModelViewSet):
    queryset = EventoAcademico.objects.all()
    serializer_class = EventoAcademicoSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsCoordenacao]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

class AlunoViewSet(viewsets.ModelViewSet): 

    serializer_class = AlunoSerializer
    permission_classes = [IsCoordenacao] # Permissão base

    def get_queryset(self):
        user = self.request.user

        if not hasattr(user, 'cargo'):
            return Aluno.objects.none()
        
        admin_roles = ['administrador', 'coordenador', 'diretor', 'ti']
        # Corrigido para incluir superuser
        if user.cargo not in admin_roles and not user.is_superuser: 
            return Aluno.objects.none()
            
        # Corrigido (removido o .annotate que causava erro 500)
        queryset = Aluno.objects.all().order_by('usuario__first_name')

        turma_id = self.request.query_params.get('turma_id')
        if turma_id:
            queryset = queryset.filter(turma_id=turma_id)
            
        return queryset # Retorna o queryset para Admins
            
    def get_serializer_class(self):
        # Lógica para usar um serializer diferente ao criar
        if self.action == 'create' or self.action == 'update':
            return AlunoCreateSerializer
        return AlunoSerializer 

    def get_permissions(self):
        # Define permissões por ação
        if self.action in ['list', 'retrieve', 'create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsCoordenacao()]
        return [permissions.IsAuthenticated()]

class TurmaViewSet(viewsets.ModelViewSet):
    queryset = Turma.objects.all().order_by('nome')
    serializer_class = TurmaSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsCoordenacao]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'])
    def detalhe_com_alunos(self, request, pk=None):
        turma = self.get_object()
        alunos_da_turma = Aluno.objects.filter(
            turma=turma, 
            status='ativo'
        ).order_by('usuario__first_name', 'usuario__last_name')
        
        turma_data = TurmaSerializer(turma).data
        # Usamos o AlunoSerializer (que é read-only)
        alunos_data = AlunoSerializer(alunos_da_turma, many=True).data 
        
        return Response({
            'turma': turma_data,
            'alunos': alunos_data
        })

class NotaViewSet(viewsets.ModelViewSet):
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return NotaCreateUpdateSerializer
        return NotaSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'bulk_update_notas']:
            permission_classes = [permissions.IsAuthenticated, (IsProfessor | IsCoordenacao)]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        queryset = Nota.objects.all()

        if not hasattr(user, 'cargo'):
            return Nota.objects.none()

        disciplina_id = self.request.query_params.get('disciplina_id')
        aluno_id = self.request.query_params.get('aluno_id')

        if disciplina_id:
            queryset = queryset.filter(disciplina_id=disciplina_id)
        if aluno_id:
             queryset = queryset.filter(aluno_id=aluno_id)

        if user.cargo == 'aluno':
            if hasattr(user, 'aluno_profile'):
                return queryset.filter(aluno=user.aluno_profile)
            else:
                return Nota.objects.none() 
        
        if user.cargo == 'professor':
            return queryset.filter(disciplina__professores=user)
        
        admin_roles = ['administrador', 'coordenador', 'diretor', 'ti']
        if user.cargo in admin_roles or user.is_superuser:
            return queryset 
            
        return Nota.objects.none()

    @action(detail=False, methods=['post'], permission_classes=[IsProfessor | IsCoordenacao])
    def bulk_update_notas(self, request):
        """
        Ação customizada para o professor salvar várias notas de uma vez.
        """
        notas_data = request.data
        if not isinstance(notas_data, list):
            return Response({"erro": "O payload deve ser uma lista."}, status=status.HTTP_400_BAD_REQUEST)

        resultados = []
        erros = []
        
        user_is_admin = (hasattr(request.user, 'cargo') and 
                         request.user.cargo in ['administrador', 'coordenador', 'diretor', 'ti'])

        for nota_data in notas_data:
            nota_id = nota_data.get('id')
            valor = nota_data.get('valor')
            disciplina_id = nota_data.get('disciplina')

            if not user_is_admin:
                if not Disciplina.objects.filter(id=disciplina_id, professores=request.user).exists():
                    erros.append(f"ID {nota_id or 'novo'}: Você não tem permissão para esta disciplina.")
                    continue

            if valor is None or valor == '': 
                continue

            try:
                if nota_id:
                    if user_is_admin:
                         nota = Nota.objects.get(id=nota_id)
                    else:
                         nota = Nota.objects.get(id=nota_id, disciplina__professores=request.user)
                         
                    serializer = NotaCreateUpdateSerializer(nota, data=nota_data, partial=True)
                else:
                    serializer = NotaCreateUpdateSerializer(data=nota_data)
                
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    resultados.append(serializer.data)
                
            except Nota.DoesNotExist:
                erros.append(f"Nota ID {nota_id} não encontrada ou não pertence a você.")
            except Exception as e:
                if 'UNIQUE constraint' in str(e):
                    erros.append(f"Erro na Disc. {disciplina_id}: Esta nota já foi lançada para este bimestre.")
                else:
                    erros.append(f"ID {nota_id or 'novo'}: {str(e)}")

        if erros:
            return Response({"sucesso": resultados, "erros": erros}, status=status.HTTP_207_MULTI_STATUS) 
            
        return Response(resultados, status=status.HTTP_200_OK)

class MateriaViewSet(viewsets.ModelViewSet):
    """
    API endpoint para Matérias (ex: Matemática, Português).
    """
    queryset = Materia.objects.all().order_by('nome')
    serializer_class = MateriaSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsCoordenacao]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


class FaltaViewSet(viewsets.ModelViewSet):
    """
    API endpoint para Faltas.
    """
    serializer_class = FaltaSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsProfessor]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        queryset = Falta.objects.all()

        if not hasattr(user, 'cargo'):
            return Falta.objects.none()

        disciplina_id = self.request.query_params.get('disciplina_id')
        aluno_id = self.request.query_params.get('aluno_id')

        if disciplina_id:
            queryset = queryset.filter(disciplina_id=disciplina_id)
        if aluno_id:
             queryset = queryset.filter(aluno_id=aluno_id)

        if user.cargo == 'aluno':
            if hasattr(user, 'aluno_profile'):
                return queryset.filter(aluno=user.aluno_profile)
            else:
                return Falta.objects.none() 
        
        if user.cargo == 'professor':
            return queryset.filter(disciplina__professores=user)
        
        admin_roles = ['administrador', 'coordenador', 'diretor', 'ti']
        if user.cargo in admin_roles or user.is_superuser:
            return queryset 
            
        return Falta.objects.none()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def relatorio_desempenho_aluno(request, aluno_id):
    """
    Gera relatório com notas, faltas e evolução do aluno.
    Retorna JSON.
    """
    aluno = get_object_or_404(Aluno, id=aluno_id)

    admin_roles = ['administrador', 'coordenador', 'diretor', 'ti']
    user_cargo = getattr(request.user, 'cargo', None) 

    if user_cargo == 'aluno':
        if not (hasattr(request.user, 'aluno_profile') and request.user.aluno_profile.id == aluno.id):
            return Response({'erro': 'Acesso negado. Alunos só podem ver o próprio relatório.'}, status=status.HTTP_403_FORBIDDEN)
    
    # --- CORREÇÃO AQUI ---
    # Permitir que Responsáveis também vejam o relatório
    elif user_cargo not in admin_roles and user_cargo != 'professor' and user_cargo != 'responsavel':
         return Response({'erro': 'Você não tem permissão para ver este relatório.'}, status=status.HTTP_403_FORBIDDEN)
    
    # --- (Bônus) Verificação de Responsável ---
    # Se for um responsável, verifica se ele é responsável por ESTE aluno
    if user_cargo == 'responsavel':
        if not (hasattr(request.user, 'responsavel_profile') and 
                request.user.responsavel_profile.alunos.filter(id=aluno.id).exists()):
            return Response({'erro': 'Acesso negado. Você só pode ver relatórios de alunos pelos quais é responsável.'}, status=status.HTTP_403_FORBIDDEN)


    notas = Nota.objects.filter(aluno=aluno)
    faltas = Falta.objects.filter(aluno=aluno)
    presencas = Presenca.objects.filter(aluno=aluno)

    medias_disciplinas = notas.values('disciplina__materia__nome').annotate(
        media=Avg('valor')
    )

    context = {
        'aluno': {
            'nome': aluno.usuario.get_full_name() or aluno.usuario.username,
            'turma': {
                'id': aluno.turma.id if aluno.turma else None,
                'nome': aluno.turma.nome if aluno.turma else 'Sem turma'
            },
            'status': aluno.get_status_display()
        },
        'medias_disciplinas': list(medias_disciplinas), 
        'faltas': {
            'count': faltas.count()
        },
        'presencas': {
            'count': presencas.count()
        }
    }

    return Response(context)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCoordenacao]) 
def relatorio_geral_faltas(request):
    relatorio_faltas = Falta.objects.values('aluno__usuario__username', 'disciplina__materia__nome') \
                                   .annotate(total_faltas=Count('id')) \
                                   .order_by('aluno__usuario__username')
    
    return Response(list(relatorio_faltas))

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCoordenacao]) 
def relatorio_gerencial(request):
    turmas = Turma.objects.all()
    dados_turmas = []

    for turma in turmas:
        total_alunos_considerados = Aluno.objects.filter(turma=turma, status__in=['ativo', 'evadido', 'transferido', 'concluido']).count()
        evadidos_turma = Aluno.objects.filter(turma=turma, status='evadido').count()
        
        taxa_evasao = 0
        if total_alunos_considerados > 0:
            taxa_evasao = (evadidos_turma / total_alunos_considerados) * 100

        alunos_aprovados = 0
        alunos_ativos_turma = turma.alunos.filter(status__in=['ativo', 'concluido'])
        
        taxa_aprovacao = 0
        if alunos_ativos_turma.count() > 0:
            for aluno in alunos_ativos_turma:
                media_final_aluno = Nota.objects.filter(aluno=aluno).aggregate(media=Avg('valor'))['media']
                
                if media_final_aluno is not None and media_final_aluno >= 6.0:
                    alunos_aprovados += 1
            
            taxa_aprovacao = (alunos_aprovados / alunos_ativos_turma.count()) * 100

        dados_turmas.append({
            'turma': TurmaSerializer(turma).data, 
            'taxa_evasao': f"{taxa_evasao:.2f}%",
            'taxa_aprovacao': f"{taxa_aprovacao:.2f}%",
        })

    return Response(dados_turmas) 

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendario_academico(request):
    eventos = EventoAcademico.objects.all()

    eventos_formatados = []
    for evento in eventos:
        eventos_formatados.append({
            'id': evento.id,
            'title': f"({evento.get_tipo_display()}) {evento.titulo}",
            'start': evento.data_inicio.isoformat(),
            'end': evento.data_fim.isoformat() if evento.data_fim else None,
            'description': evento.descricao,
        })

    return Response(eventos_formatados)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsProfessor]) 
def planos_de_aula_professor(request):
    try:
        # A consulta correta
        disciplinas_professor = Disciplina.objects.filter(professores=request.user)
        planos = PlanoDeAula.objects.filter(disciplina__in=disciplinas_professor).order_by('data')
    
    except (Disciplina.DoesNotExist, TypeError, AttributeError):
        return Response(
            {'erro': 'Usuário não é professor ou não possui disciplinas.'}, 
            status=status.HTTP_403_FORBIDDEN
        )

    planos_data = PlanoDeAulaSerializer(planos, many=True).data
    disciplinas_data = DisciplinaSerializer(disciplinas_professor, many=True).data

    context = {
        'planos_de_aula': planos_data,
        'disciplinas': disciplinas_data
    }
    return Response(context)

# --- FUNÇÃO DO PDF ATUALIZADA PARA Xhtml2pdf ---
@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def download_boletim_pdf(request, aluno_id):
    """
    Gera e baixa um PDF do boletim completo do aluno (usando xhtml2pdf).
    """
    aluno = get_object_or_404(Aluno, id=aluno_id)

    # --- Lógica de permissão (permanece a mesma) ---
    admin_roles = ['administrador', 'coordenador', 'diretor', 'ti']
    user_cargo = getattr(request.user, 'cargo', None) 

    if user_cargo == 'aluno':
        if not (hasattr(request.user, 'aluno_profile') and request.user.aluno_profile.id == aluno.id):
            return Response({'erro': 'Acesso negado. Alunos só podem ver o próprio relatório.'}, status=status.HTTP_403_FORBIDDEN)
    
    # --- CORREÇÃO AQUI ---
    # Permitir que Responsáveis também baixem o PDF
    elif user_cargo not in admin_roles and user_cargo != 'professor' and user_cargo != 'responsavel':
         return Response({'erro': 'Você não tem permissão para ver este relatório.'}, status=status.HTTP_403_FORBIDDEN)

    # --- (Bônus) Verificação de Responsável ---
    if user_cargo == 'responsavel':
        if not (hasattr(request.user, 'responsavel_profile') and 
                request.user.responsavel_profile.alunos.filter(id=aluno.id).exists()):
            return Response({'erro': 'Acesso negado. Você só pode baixar relatórios de alunos pelos quais é responsável.'}, status=status.HTTP_403_FORBIDDEN)


    # Busca os dados para o template (permanece o mesmo)
    notas_disciplinas = Nota.objects.filter(aluno=aluno).values('disciplina__materia__nome').annotate(
        media=Avg('valor')
    ).order_by('disciplina__materia__nome')
    
    total_faltas = Falta.objects.filter(aluno=aluno).count()
    advertencias = Advertencia.objects.filter(aluno=aluno).order_by('-data')
    suspensoes = Suspensao.objects.filter(aluno=aluno).order_by('-data_inicio')

    context = {
        'aluno': aluno,
        'notas_disciplinas': notas_disciplinas,
        'total_faltas': total_faltas,
        'advertencias': advertencias,
        'suspensoes': suspensoes,
    }

    # Renderiza o template HTML (permanece o mesmo)
    html_string = render_to_string(
        'pedagogico/boletim_pdf.html', # Template que você já tem
        context
    )
    
    # --- NOVA LÓGICA DE GERAÇÃO DE PDF ---
    # Cria um buffer de memória para o PDF
    result = BytesIO()
    
    # Converte o HTML para PDF
    pdf = pisa.CreatePDF(
        html_string,                # o HTML renderizado
        dest=result                 # o buffer de destino
    )

    # Se não houver erro na geração
    if not pdf.err:
        # Cria a resposta HTTP
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="boletim_{aluno.usuario.username}.pdf"'
        return response
    
    # Se houver um erro
    return HttpResponse(f"Erro ao gerar o PDF: {pdf.err}", status=500)

# ... (outros ViewSets)

class NotificacaoViewSet(viewsets.ModelViewSet):
    """
    API para Notificações.
    Filtra automaticamente para mostrar apenas as do usuário logado.
    """
    serializer_class = NotificacaoSerializer
    permission_classes = [IsAuthenticated] # Só precisa estar logado

    def get_queryset(self):
        # Retorna apenas as notificações para o usuário que fez a request
        return Notificacao.objects.filter(destinatario=self.request.user).order_by('-data_envio')

    @action(detail=True, methods=['post'])
    def marcar_como_lida(self, request, pk=None):
        """ Ação para marcar uma notificação como lida """
        try:
            notificacao = Notificacao.objects.get(pk=pk, destinatario=request.user)
            notificacao.lida = True
            notificacao.save()
            return Response(NotificacaoSerializer(notificacao).data)
        except Notificacao.DoesNotExist:
            return Response({'erro': 'Notificação não encontrada.'}, status=status.HTTP_404_NOT_FOUND)


# --- VIEWSET DO RESPONSÁVEL CORRIGIDA ---
class ResponsavelViewSet(viewsets.ModelViewSet):
    """
    API para o Portal do Responsável.
    """
    queryset = Responsavel.objects.all()
    serializer_class = ResponsavelSerializer
    # 1. Permissão base: Apenas estar logado
    permission_classes = [IsAuthenticated] 

    # 2. Adicione este método para definir permissões por ação
    def get_permissions(self):
        # Ações de Admin (listar todos, criar, editar, deletar)
        if self.action in ['list', 'create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsCoordenacao]
        # A ação 'me' usará a permissão do seu @action
        elif self.action == 'me':
            self.permission_classes = [IsResponsavel]
        # Ação 'retrieve' (ver um por ID) só precisa estar logado
        else:
            self.permission_classes = [IsAuthenticated]
            
        return super().get_permissions()

    @action(detail=False, methods=['get'], permission_classes=[IsResponsavel])
    def me(self, request):
        """
        Endpoint especial (/api/responsaveis/me/)
        Retorna o perfil do responsável logado e seus alunos vinculados.
        """
        try:
            responsavel = request.user.responsavel_profile
            serializer = self.get_serializer(responsavel)
            return Response(serializer.data)
        except Responsavel.DoesNotExist:
            return Response({'erro': 'Este usuário não possui um perfil de responsável.'}, status=status.HTTP_404_NOT_FOUND)