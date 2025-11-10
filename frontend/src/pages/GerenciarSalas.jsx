// Em: frontend/src/pages/GerenciarSalas.jsx
import React, { useState, useEffect } from 'react'; // <-- Imports atualizados
import axios from 'axios';
import { 
    Container, 
    Typography, 
    Paper, 
    Box, 
    CircularProgress, 
    Alert,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Button // <-- Importado
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom'; // <-- Importado

const token = localStorage.getItem('authToken');

// --- ADICIONADO: Lógica de permissão ---
const getUserRole = () => {
  try {
    const userData = localStorage.getItem('userData');
    if (!userData) return null;
    const user = JSON.parse(userData);
    return user.cargo; // <-- Verifica o 'cargo'
  } catch (e) { return null; }
};
const adminRoles = ['administrador', 'coordenador', 'diretor', 'ti'];
// ------------------------------------

function GerenciarSalas() {
  const [salas, setSalas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [userRole, setUserRole] = useState(null); // <-- Adicionado

  useEffect(() => {
    setUserRole(getUserRole()); // <-- Adicionado

    const fetchSalas = async () => {
      setLoading(true);
      try {
        const headers = { 'Authorization': `Token ${token}` };
        const res = await axios.get('http://127.0.0.1:8000/coordenacao/api/salas/', { headers });
        setSalas(res.data);
      } catch (err) {
        setError('Erro ao buscar salas.');
      } finally {
        setLoading(false);
      }
    };
    fetchSalas();
  }, []);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  if (error) return <Container><Alert severity="error">{error}</Alert></Container>;

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        
        {/* --- ADICIONADO: Cabeçalho com Botão --- */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" gutterBottom sx={{ mb: 0 }}>
            Gerenciar Salas e Laboratórios
          </Typography>
          {adminRoles.includes(userRole) && (
            <Button
              component={RouterLink}
              to="/salas/adicionar" // <-- (Precisaremos criar esta página depois)
              variant="contained"
              color="primary"
            >
              Adicionar Sala
            </Button>
          )}
        </Box>
        {/* ------------------------------------- */}

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Nome</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell align="right">Capacidade</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {salas.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.nome}</TableCell>
                  <TableCell>{item.tipo}</TableCell>
                  <TableCell align="right">{item.capacidade}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Container>
  );
}

export default GerenciarSalas;