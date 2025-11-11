// Em: frontend/src/pages/PortalResponsavel.jsx (NOVO ARQUIVO)

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
    Container, 
    Typography, 
    Paper, 
    Box, 
    CircularProgress, 
    Alert,
    Grid,
    List,
    ListItem,
    ListItemText,
    Button,
    Divider,
    ListItemIcon,
    Chip
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import NotificationsIcon from '@mui/icons-material/Notifications';
import FaceIcon from '@mui/icons-material/Face';

const token = localStorage.getItem('authToken');
const apiUrl = 'http://127.0.0.1:8000/pedagogico/api';

function PortalResponsavel() {
  const [alunos, setAlunos] = useState([]);
  const [notificacoes, setNotificacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError('');
      const headers = { 'Authorization': `Token ${token}` };

      try {
        const responsavelRes = await axios.get(`${apiUrl}/responsaveis/me/`, { headers });
        setAlunos(responsavelRes.data.alunos || []);

        const notificacoesRes = await axios.get(`${apiUrl}/notificacoes/`, { headers });
        setNotificacoes(notificacoesRes.data || []);

      } catch (err) {
        console.error("Erro ao buscar dados do portal:", err);
        setError('Não foi possível carregar os dados. Verifique se sua conta é de um responsável.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  if (error) return <Container><Alert severity="error">{error}</Alert></Container>;

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Portal do Responsável
      </Typography>

      <Grid container spacing={3}>
        
        {/* Coluna dos Alunos */}
        <Grid item xs={12} md={7}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>Meus Alunos</Typography>
            {alunos.length === 0 ? (
                <Typography>Nenhum aluno vinculado a esta conta.</Typography>
            ) : (
                <List>
                    {alunos.map((aluno) => (
                    <ListItem 
                        key={aluno.id}
                        divider
                        secondaryAction={
                        <Button 
                            variant="contained" 
                            size="small"
                            component={RouterLink}
                            to={`/relatorio/aluno/${aluno.id}`}
                        >
                            Ver Relatório
                        </Button>
                        }
                    >
                        <ListItemIcon>
                            <FaceIcon />
                        </ListItemIcon>
                        <ListItemText 
                            primary={aluno.nome}
                            secondary={`Turma: ${aluno.turma_nome || 'N/A'} | Status: ${aluno.status}`}
                        />
                    </ListItem>
                    ))}
                </List>
            )}
          </Paper>
        </Grid>

        {/* Coluna de Notificações */}
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 3, maxHeight: '60vh', overflowY: 'auto' }}>
            <Typography variant="h5" gutterBottom>Notificações</Typography>
            {notificacoes.length === 0 ? (
                <Typography>Nenhuma notificação.</Typography>
            ) : (
                <List>
                    {notificacoes.map((notif) => (
                    <ListItem key={notif.id} divider>
                        <ListItemIcon sx={{ mt: 1, alignSelf: 'flex-start' }}>
                            <NotificationsIcon color={notif.lida ? 'disabled' : 'primary'}/>
                        </ListItemIcon>
                        <ListItemText 
                            primary={notif.mensagem}
                            secondary={new Date(notif.data_envio).toLocaleString('pt-BR')}
                            primaryTypographyProps={{ 
                                fontWeight: notif.lida ? 'normal' : 'bold',
                                color: notif.lida ? 'text.secondary' : 'text.primary'
                            }}
                        />
                    </ListItem>
                    ))}
                </List>
            )}
          </Paper>
        </Grid>

      </Grid>
    </Container>
  );
}

export default PortalResponsavel;