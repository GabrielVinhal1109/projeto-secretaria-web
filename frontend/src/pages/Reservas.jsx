// Em: frontend/src/pages/Reservas.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box, Typography, Button, Container, Paper,
  CircularProgress, Alert, List, ListItem, ListItemText,
  Select, MenuItem, FormControl, InputLabel, TextField, Grid
} from '@mui/material';

const token = localStorage.getItem('authToken');
const apiUrl = 'http://127.0.0.1:8000/coordenacao/api';

function Reservas() {
  const [salas, setSalas] = useState([]);
  const [reservas, setReservas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Estado do formulário
  const [selectedSala, setSelectedSala] = useState('');
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');

  const fetchData = () => {
    setLoading(true);
    setError('');
    const headers = { 'Authorization': `Token ${token}` };

    Promise.all([
      axios.get(`${apiUrl}/salas/`, { headers }),
      axios.get(`${apiUrl}/reservas/`, { headers })
    ]).then(([salasRes, reservasRes]) => {
      setSalas(salasRes.data);
      setReservas(reservasRes.data); // O backend já filtra (só admin vê todas)
      setLoading(false);
    }).catch(err => {
      console.error("Erro ao buscar dados:", err);
      setError('Não foi possível carregar os dados. Você tem permissão?');
      setLoading(false);
    });
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!selectedSala || !dataInicio || !dataFim) {
      setError('Por favor, preencha todos os campos.');
      return;
    }
    
    const payload = {
      sala: selectedSala,
      data_inicio: new Date(dataInicio).toISOString(),
      data_fim: new Date(dataFim).toISOString(),
    };

    try {
      await axios.post(`${apiUrl}/reservas/`, payload, {
        headers: { 'Authorization': `Token ${token}` }
      });
      setSuccess('Sala reservada com sucesso!');
      // Limpa o formulário e recarrega os dados
      setSelectedSala('');
      setDataInicio('');
      setDataFim('');
      fetchData();
    } catch (err) {
      console.error("Erro ao reservar:", err);
      if (err.response && err.response.data && err.response.data.non_field_errors) {
          setError(err.response.data.non_field_errors[0]); // Mostra erro de conflito
      } else {
          setError('Não foi possível fazer a reserva. Verifique os dados.');
      }
    }
  };

  const formatarData = (isoString) => {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Reserva de Salas e Laboratórios
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Grid container spacing={3}>
        {/* Coluna do Formulário */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Fazer nova reserva</Typography>
            <Box component="form" onSubmit={handleSubmit} noValidate>
              <FormControl fullWidth margin="normal" required>
                <InputLabel id="sala-label">Sala</InputLabel>
                <Select
                  labelId="sala-label"
                  value={selectedSala}
                  label="Sala"
                  onChange={(e) => setSelectedSala(e.target.value)}
                >
                  <MenuItem value=""><em>Selecione...</em></MenuItem>
                  {salas.map((sala) => (
                    <MenuItem key={sala.id} value={sala.id}>
                      {sala.nome} ({sala.tipo})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                label="Início da Reserva"
                type="datetime-local"
                value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)}
                required fullWidth margin="normal"
                InputLabelProps={{ shrink: true }}
              />

              <TextField
                label="Fim da Reserva"
                type="datetime-local"
                value={dataFim}
                onChange={(e) => setDataFim(e.target.value)}
                required fullWidth margin="normal"
                InputLabelProps={{ shrink: true }}
              />
              
              <Button type="submit" variant="contained" color="primary" fullWidth sx={{ mt: 2 }}>
                Reservar
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* Coluna das Reservas */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Minhas Reservas</Typography>
            {loading ? <CircularProgress /> : (
              <List>
                {reservas.length === 0 && <Typography>Nenhuma reserva encontrada.</Typography>}
                {reservas.map(reserva => (
                  <ListItem key={reserva.id} divider>
                    <ListItemText
                      primary={
                        <>
                          <Typography component="span" fontWeight="bold">
                            {reserva.sala.nome}
                          </Typography>
                          <Typography component="span" color="text.secondary" sx={{ ml: 1 }}>
                            (por: {reserva.usuario.first_name || reserva.usuario.username})
                          </Typography>
                        </>
                      }
                      secondary={`De: ${formatarData(reserva.data_inicio)} | Até: ${formatarData(reserva.data_fim)}`}
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

export default Reservas;