import React, { useState } from 'react';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  Alert,
  Divider
} from '@mui/material';
import { Login, AdminPanelSettings, Person } from '@mui/icons-material';

// Test accounts from the documentation
const TEST_ACCOUNTS = {
  // System Admin
  'admin@ragp.system': {
    password: 'Admin123!',
    role: 'A',
    name: 'System Administrator',
    organization: 'RAGP System',
    permissions: ['전체 시스템 관리', '조직 관리', '사용자 승인/거부', '모든 문서 접근']
  },
  // Organization Admin - 전북대학교
  'admin@jbnu.ac.kr': {
    password: 'Admin123!',
    role: 'B', 
    name: 'Organization Administrator',
    organization: '전북대학교',
    permissions: ['소속 기관 사용자 관리', '소속 기관 문서 관리', '소속 기관 설정 관리']
  },
  // Organization User - 전북대학교
  'user@jbnu.ac.kr': {
    password: 'User123!',
    role: 'C',
    name: 'Organization User', 
    organization: '전북대학교',
    permissions: ['소속 기관 문서 조회', '본인 업로드 문서 관리']
  },
  // Organization Admin - 고려대학교
  'admin@korea.ac.kr': {
    password: 'Admin123!',
    role: 'B', 
    name: 'Korea University Administrator',
    organization: '고려대학교',
    permissions: ['소속 기관 사용자 관리', '소속 기관 문서 관리', '소속 기관 설정 관리']
  },
  // Organization User - 고려대학교
  'user@korea.ac.kr': {
    password: 'User123!',
    role: 'C',
    name: 'Korea University User', 
    organization: '고려대학교',
    permissions: ['소속 기관 문서 조회', '본인 업로드 문서 관리']
  }
};

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState(null);
  const [loginType, setLoginType] = useState(null); // 'admin' or 'user'

  const handleLogin = (event) => {
    event.preventDefault();
    
    if (!email || !password) {
      setMessage({ type: 'error', text: '이메일과 비밀번호를 입력해주세요.' });
      return;
    }

    const account = TEST_ACCOUNTS[email];
    
    if (!account) {
      setMessage({ type: 'error', text: '존재하지 않는 계정입니다.' });
      return;
    }

    if (account.password !== password) {
      setMessage({ type: 'error', text: '비밀번호가 올바르지 않습니다.' });
      return;
    }

    // Check if login type matches account role
    if (loginType === 'admin' && account.role === 'C') {
      setMessage({ type: 'error', text: '일반 사용자는 관리자 로그인을 사용할 수 없습니다.' });
      return;
    }

    if (loginType === 'user' && (account.role === 'A' || account.role === 'B')) {
      setMessage({ type: 'error', text: '관리자는 사용자 로그인을 사용할 수 없습니다.' });
      return;
    }

    // Successful login
    setMessage({ type: 'success', text: `로그인 성공! ${account.name}님 환영합니다.` });
    
    // Call parent login handler
    setTimeout(() => {
      onLogin({
        email,
        role: account.role,
        name: account.name,
        organization: account.organization,
        permissions: account.permissions,
        loginType: loginType
      });
    }, 1000);
  };

  const handleQuickLogin = (accountEmail, type) => {
    const account = TEST_ACCOUNTS[accountEmail];
    setEmail(accountEmail);
    setPassword(account.password);
    setLoginType(type);
  };

  if (loginType) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Paper sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            {loginType === 'admin' ? 
              <AdminPanelSettings sx={{ mr: 1, color: 'primary.main' }} /> : 
              <Person sx={{ mr: 1, color: 'primary.main' }} />
            }
            <Typography variant="h4">
              {loginType === 'admin' ? '관리자 로그인' : '사용자 로그인'}
            </Typography>
          </Box>

          {message && (
            <Alert severity={message.type} sx={{ mb: 3 }}>
              {message.text}
            </Alert>
          )}

          <Box component="form" onSubmit={handleLogin}>
            <TextField
              fullWidth
              label="이메일"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              label="비밀번호"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              sx={{ mb: 3 }}
            />

            <Button
              type="submit"
              variant="contained"
              size="large"
              fullWidth
              startIcon={<Login />}
              sx={{ mb: 2 }}
            >
              로그인
            </Button>

            <Button
              variant="text"
              fullWidth
              onClick={() => {
                setLoginType(null);
                setEmail('');
                setPassword('');
                setMessage(null);
              }}
            >
              뒤로 가기
            </Button>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            테스트 계정 (클릭시 자동 입력)
          </Typography>
          
          {loginType === 'admin' ? (
            <Box>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                sx={{ mb: 1 }}
                onClick={() => handleQuickLogin('admin@ragp.system', 'admin')}
              >
                시스템 관리자 (admin@ragp.system)
              </Button>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                sx={{ mb: 1 }}
                onClick={() => handleQuickLogin('admin@jbnu.ac.kr', 'admin')}
              >
                전북대 관리자 (admin@jbnu.ac.kr)
              </Button>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                sx={{ mb: 1 }}
                onClick={() => handleQuickLogin('admin@korea.ac.kr', 'admin')}
              >
                고려대 관리자 (admin@korea.ac.kr)
              </Button>
            </Box>
          ) : (
            <Box>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                sx={{ mb: 1 }}
                onClick={() => handleQuickLogin('user@jbnu.ac.kr', 'user')}
              >
                전북대 사용자 (user@jbnu.ac.kr)
              </Button>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                onClick={() => handleQuickLogin('user@korea.ac.kr', 'user')}
              >
                고려대 사용자 (user@korea.ac.kr)
              </Button>
            </Box>
          )}
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 8 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h3" align="center" gutterBottom>
          RAG Document Management System
        </Typography>
        <Typography variant="h6" align="center" color="text.secondary" sx={{ mb: 4 }}>
          역할을 선택하여 로그인해주세요
        </Typography>

        <Box sx={{ display: 'flex', gap: 3, justifyContent: 'center' }}>
          <Button
            variant="contained"
            size="large"
            startIcon={<AdminPanelSettings />}
            onClick={() => setLoginType('admin')}
            sx={{ minWidth: 200, py: 2 }}
          >
            관리자 로그인
          </Button>

          <Button
            variant="contained"
            size="large"
            startIcon={<Person />}
            onClick={() => setLoginType('user')}
            sx={{ minWidth: 200, py: 2 }}
          >
            사용자 로그인
          </Button>
        </Box>

        <Box sx={{ mt: 4, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            테스트 계정 정보:
          </Typography>
          <Typography variant="body2">
            • 시스템 관리자: admin@ragp.system / Admin123!<br/>
            • 전북대 관리자: admin@jbnu.ac.kr / Admin123!<br/>
            • 전북대 사용자: user@jbnu.ac.kr / User123!<br/>
            • 고려대 관리자: admin@korea.ac.kr / Admin123!<br/>
            • 고려대 사용자: user@korea.ac.kr / User123!
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}

export default LoginPage;