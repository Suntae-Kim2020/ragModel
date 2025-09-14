import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Divider,
  Chip,
  Checkbox,
  ListItemText
} from '@mui/material';
import { Send, Source } from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

function UserPage({ user }) {
  const [assistants, setAssistants] = useState([]);
  const [selectedAssistant, setSelectedAssistant] = useState([]);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [selectedSourceIndex, setSelectedSourceIndex] = useState(0);

  useEffect(() => {
    fetchAssistants();
  }, []);

  const fetchAssistants = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/assistants`);
      setAssistants(response.data.assistants);
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: `어시스턴트 목록을 가져오는데 실패했습니다: ${error.message}` 
      });
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!question.trim()) {
      setMessage({ type: 'error', text: '질문을 입력해주세요.' });
      return;
    }

    setLoading(true);
    setMessage(null);
    setAnswer('');
    setSources([]);

    const formData = new FormData();
    formData.append('question', question);
    if (selectedAssistant.length > 0) {
      formData.append('assistant_ids', JSON.stringify(selectedAssistant));
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/query`, formData);
      
      setAnswer(response.data.answer);
      setSources(response.data.sources || []);
      setSelectedSourceIndex(0);
      
      if (response.data.sources?.length === 0) {
        setMessage({ type: 'warning', text: '관련된 문서를 찾을 수 없습니다.' });
      }
      
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: `질의 처리 실패: ${error.response?.data?.detail || error.message}` 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSourceClick = (index) => {
    setSelectedSourceIndex(index);
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Grid container spacing={3}>
        {/* 좌측: 질의응답 영역 */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 'calc(100vh - 150px)', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ mb: 2, p: 2, bgcolor: 'primary.main', color: 'white', borderRadius: 1 }}>
              <Typography variant="h6">
                질의응답 시스템
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {user?.name} ({user?.email}) - {user?.organization}
              </Typography>
            </Box>
            
            {message && (
              <Alert severity={message.type} sx={{ mb: 2 }}>
                {message.text}
              </Alert>
            )}

            {/* 어시스턴트 선택 및 질문 입력 */}
            <Box component="form" onSubmit={handleSubmit} sx={{ mb: 3 }}>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>어시스턴트 선택 (선택사항)</InputLabel>
                <Select
                  multiple
                  value={selectedAssistant || []}
                  label="어시스턴트 선택 (선택사항)"
                  onChange={(e) => setSelectedAssistant(e.target.value)}
                  renderValue={(selected) => {
                    if (selected.length === 0) {
                      return '전체 문서';
                    }
                    return (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    );
                  }}
                >
                  {assistants.map((assistant) => (
                    <MenuItem key={assistant} value={assistant}>
                      <Checkbox checked={selectedAssistant.indexOf(assistant) > -1} />
                      <ListItemText primary={assistant} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  multiline
                  rows={2}
                  label="질문을 입력하세요"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  disabled={loading}
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading || !question.trim()}
                  sx={{ minWidth: 100 }}
                  startIcon={loading ? <CircularProgress size={20} /> : <Send />}
                >
                  {loading ? '' : '질의'}
                </Button>
              </Box>
            </Box>

            <Divider sx={{ mb: 2 }} />

            {/* 답변 영역 */}
            <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
              {answer && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    답변
                  </Typography>
                  <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                    {answer}
                  </Typography>
                  
                  {sources.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        출처 ({sources.length}개):
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {sources.map((source, index) => (
                          <Chip
                            key={index}
                            label={`${source.document_title} (p.${source.page_number})`}
                            variant={selectedSourceIndex === index ? "filled" : "outlined"}
                            color={selectedSourceIndex === index ? "primary" : "default"}
                            onClick={() => handleSourceClick(index)}
                            clickable
                            size="small"
                            icon={<Source />}
                          />
                        ))}
                      </Box>
                    </Box>
                  )}
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* 우측: 출처 원본 내용 */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 'calc(100vh - 150px)', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom>
              출처 원본
            </Typography>
            
            {sources.length > 0 && sources[selectedSourceIndex] ? (
              <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    {sources[selectedSourceIndex].document_title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    페이지: {sources[selectedSourceIndex].page_number} | 
                    기관: {sources[selectedSourceIndex].organization} | 
                    유형: {sources[selectedSourceIndex].document_type}
                  </Typography>
                  
                  <Box sx={{ mb: 2 }}>
                    {sources[selectedSourceIndex].tags?.map((tag, index) => (
                      <Chip key={index} label={tag} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                    ))}
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    관련도: {Math.round(sources[selectedSourceIndex].relevance_score * 100)}%
                  </Typography>
                </Box>
                
                <Divider sx={{ mb: 2 }} />
                
                <Box sx={{ 
                  whiteSpace: 'pre-wrap', 
                  lineHeight: 1.5,
                  backgroundColor: '#f5f5f5',
                  p: 2,
                  borderRadius: 1,
                  fontSize: '0.875rem',
                  fontFamily: 'Roboto, sans-serif',
                  '& mark': {
                    backgroundColor: '#ffeb3b',
                    color: '#000',
                    padding: '0 2px',
                    borderRadius: '2px',
                    fontWeight: 'bold'
                  }
                }}
                dangerouslySetInnerHTML={{
                  __html: sources[selectedSourceIndex].highlighted_content || sources[selectedSourceIndex].content
                }}
                />
              </Box>
            ) : (
              <Box sx={{ 
                flexGrow: 1, 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: 'text.secondary'
              }}>
                <Typography variant="body2">
                  질의 후 출처 정보가 여기에 표시됩니다.
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default UserPage;