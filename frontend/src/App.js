import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import AdminPage from './components/AdminPage';
import UserPage from './components/UserPage';
import Navigation from './components/Navigation';
import LoginPage from './components/LoginPage';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [user, setUser] = useState(null); // null means not logged in

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    setUser(null);
  };

  // Protected route component
  const ProtectedRoute = ({ children, allowedRoles = [] }) => {
    if (!user) {
      return <Navigate to="/login" replace />;
    }

    if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
      return <Navigate to="/" replace />;
    }

    return children;
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        {user && <Navigation user={user} onLogout={handleLogout} />}
        <Routes>
          <Route 
            path="/login" 
            element={
              user ? <Navigate to="/" replace /> : <LoginPage onLogin={handleLogin} />
            } 
          />
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <UserPage user={user} />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin" 
            element={
              <ProtectedRoute allowedRoles={['A', 'B']}>
                <AdminPage user={user} />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/user" 
            element={
              <ProtectedRoute>
                <UserPage user={user} />
              </ProtectedRoute>
            } 
          />
          {/* Redirect to login if no route matches and not logged in */}
          <Route 
            path="*" 
            element={
              user ? <Navigate to="/" replace /> : <Navigate to="/login" replace />
            } 
          />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;