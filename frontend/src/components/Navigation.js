import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link, useLocation } from 'react-router-dom';

function Navigation() {
  const location = useLocation();

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          RAG 문서 관리 시스템
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button 
            color="inherit" 
            component={Link} 
            to="/user"
            variant={location.pathname === '/user' || location.pathname === '/' ? 'outlined' : 'text'}
          >
            사용자
          </Button>
          <Button 
            color="inherit" 
            component={Link} 
            to="/admin"
            variant={location.pathname === '/admin' ? 'outlined' : 'text'}
          >
            관리자
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Navigation;