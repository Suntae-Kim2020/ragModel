import React from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  Box, 
  Chip,
  Menu,
  MenuItem,
  IconButton
} from '@mui/material';
import { Link, useLocation } from 'react-router-dom';
import { AccountCircle, Logout, AdminPanelSettings, Person } from '@mui/icons-material';

function Navigation({ user, onLogout }) {
  const location = useLocation();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleClose();
    onLogout();
  };

  const getRoleDisplay = (role) => {
    switch (role) {
      case 'A': return { text: '시스템 관리자', color: 'error' };
      case 'B': return { text: '기관 관리자', color: 'warning' }; 
      case 'C': return { text: '일반 사용자', color: 'primary' };
      default: return { text: '사용자', color: 'default' };
    }
  };

  const roleInfo = getRoleDisplay(user?.role);

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          RAG 문서 관리 시스템
        </Typography>
        
        {user && (
          <>
            <Box sx={{ mr: 2 }}>
              <Button 
                color="inherit" 
                component={Link} 
                to="/"
                variant={location.pathname === '/' || location.pathname === '/user' ? 'outlined' : 'text'}
                startIcon={<Person />}
              >
                질의응답
              </Button>
              
              {(user.role === 'A' || user.role === 'B') && (
                <Button 
                  color="inherit" 
                  component={Link} 
                  to="/admin"
                  variant={location.pathname === '/admin' ? 'outlined' : 'text'}
                  startIcon={<AdminPanelSettings />}
                  sx={{ ml: 1 }}
                >
                  문서관리
                </Button>
              )}
            </Box>

            <Chip 
              icon={user.role === 'C' ? <Person /> : <AdminPanelSettings />}
              label={roleInfo.text}
              color={roleInfo.color}
              variant="outlined"
              sx={{ 
                color: 'white', 
                borderColor: 'rgba(255,255,255,0.5)',
                mr: 1
              }}
            />

            <IconButton
              size="large"
              aria-label="account menu"
              aria-controls="account-menu"
              aria-haspopup="true"
              onClick={handleMenu}
              color="inherit"
            >
              <AccountCircle />
            </IconButton>
            
            <Menu
              id="account-menu"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              <Box sx={{ px: 2, py: 1, minWidth: 200 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  {user.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {user.email}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {user.organization}
                </Typography>
              </Box>
              <MenuItem onClick={handleLogout}>
                <Logout sx={{ mr: 1 }} />
                로그아웃
              </MenuItem>
            </Menu>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
}

export default Navigation;