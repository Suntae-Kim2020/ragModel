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
  ListItemText,
  RadioGroup,
  FormControlLabel,
  Radio,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import { Send, Source, ExpandMore } from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// HTML 태그 정리 함수
const cleanHtml = (html) => {
  if (!html) return '';
  
  return html
    // 빈 텍스트 태그 제거: <text></text> 또는 <text> </text>
    .replace(/<text[^>]*>\s*<\/text>/g, '')
    // 빈 태그들 제거
    .replace(/<(\w+)[^>]*>\s*<\/\1>/g, '')
    // 연속된 공백 정리
    .replace(/\s+/g, ' ')
    .trim();
};

function UserPage({ user }) {
  const [assistants, setAssistants] = useState([]);
  const [selectedAssistant, setSelectedAssistant] = useState([]);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [selectedSourceIndex, setSelectedSourceIndex] = useState(0);
  const [responseMode, setResponseMode] = useState('individual');
  const [individualResponses, setIndividualResponses] = useState([]);
  const [comparisonTable, setComparisonTable] = useState('');
  const [comparisonLoading, setComparisonLoading] = useState(false);

  useEffect(() => {
    fetchAssistants();
  }, []);

  const fetchAssistants = async () => {
    try {
      // 질의응답에서는 모든 어시스턴트 목록 가져오기 (organization 필터 제거)
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
    await handleSubmitQuery();
  };

  const handleSourceClick = (index) => {
    setSelectedSourceIndex(index);
  };

  const handleResponseModeChange = (event) => {
    const newMode = event.target.value;
    setResponseMode(newMode);
    
    // Clear previous responses immediately when mode changes
    setAnswer('');
    setSources([]);
    setIndividualResponses([]);
    setSelectedSourceIndex(0);
    
    // If there's a question and multiple assistants selected, auto-submit with new mode
    if (question.trim() && selectedAssistant.length >= 2) {
      // Use the new mode directly in the API call
      setTimeout(() => {
        handleSubmitQueryWithMode(newMode);
      }, 100); // Small delay to ensure state is updated
    }
  };

  const handleSubmitQueryWithMode = async (mode = null) => {
    const actualMode = mode || responseMode;
    
    if (!question.trim()) {
      setMessage({ type: 'error', text: '질문을 입력해주세요.' });
      return;
    }

    setLoading(true);
    setMessage(null);
    setAnswer('');
    setSources([]);
    setIndividualResponses([]);
    setComparisonTable('');
    setComparisonLoading(false);

    const formData = new FormData();
    formData.append('question', question);
    formData.append('response_mode', actualMode);
    formData.append('summary_mode', actualMode === 'integrated');
    if (selectedAssistant.length > 0) {
      formData.append('assistant_ids', JSON.stringify(selectedAssistant));
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/query`, formData);
      
      console.log('Response type:', response.data.response_type);
      console.log('Actual mode used:', actualMode);
      
      if (response.data.response_type === 'individual') {
        // Individual responses
        setIndividualResponses(response.data.individual_responses || []);
        setAnswer(''); // Clear integrated answer
        setSources([]); // Clear integrated sources
        
        // Check if comparison keywords exist and multiple assistants selected
        const comparison_keywords = ["비교", "차이", "다른점", "구별", "표", "분석", "대조", "vs", "versus", "비교분석"];
        const hasComparisonKeyword = comparison_keywords.some(keyword => question.includes(keyword));
        
        // Set comparison table if available
        if (response.data.comparison_table) {
          setComparisonTable(response.data.comparison_table);
          setComparisonLoading(false);
        } else if (hasComparisonKeyword && selectedAssistant.length >= 2) {
          // Show loading message if comparison should be generated but not yet available
          setComparisonLoading(true);
        }
        
        if (response.data.individual_responses?.length === 0) {
          setMessage({ type: 'warning', text: '관련된 문서를 찾을 수 없습니다.' });
        }
      } else {
        // Integrated response (current behavior)
        setAnswer(response.data.answer);
        setSources(response.data.sources || []);
        setSelectedSourceIndex(0);
        setIndividualResponses([]); // Clear individual responses
        
        if (response.data.sources?.length === 0) {
          setMessage({ type: 'warning', text: '관련된 문서를 찾을 수 없습니다.' });
        }
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

  const handleSubmitQuery = async () => {
    await handleSubmitQueryWithMode();
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

              {/* 비교 안내 (어시스턴트가 2개 이상 선택된 경우에만 표시) */}
              {selectedAssistant.length >= 2 && (
                <Box sx={{ mb: 2, p: 2, backgroundColor: '#e3f2fd', borderRadius: 1 }}>
                  <Typography variant="body2" color="primary">
                    💡 여러 어시스턴트가 선택되었습니다. 질의 내용에 '비교', '분석', '차이' 등의 키워드가 포함되면 자동으로 비교표가 제공됩니다.
                  </Typography>
                </Box>
              )}

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
              {/* Individual Responses */}
              {individualResponses.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    각 Assistant별 답변
                  </Typography>
                  {individualResponses.map((response, index) => (
                    <Accordion key={index} defaultExpanded={true}>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                            {response.assistant_name || response.assistant_id}
                          </Typography>
                          <Chip 
                            label={`신뢰도: ${Math.round(response.confidence * 100)}%`} 
                            size="small" 
                            color={response.confidence > 0.7 ? "success" : response.confidence > 0.4 ? "warning" : "error"}
                          />
                          {response.sources && response.sources.length > 0 && (
                            <Chip 
                              label={`출처: ${response.sources.length}개`} 
                              size="small" 
                              variant="outlined"
                            />
                          )}
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box 
                          sx={{ 
                            whiteSpace: 'pre-wrap', 
                            lineHeight: 1.6, 
                            mb: 2,
                            '& table': {
                              borderCollapse: 'collapse',
                              width: '100%',
                              marginTop: 1,
                              marginBottom: 1,
                              border: '1px solid #ddd'
                            },
                            '& th, & td': {
                              border: '1px solid #ddd',
                              padding: '6px 10px',
                              textAlign: 'left',
                              fontSize: '0.875rem'
                            },
                            '& th': {
                              backgroundColor: '#f0f0f0',
                              fontWeight: 'bold'
                            }
                          }}
                          dangerouslySetInnerHTML={{ __html: cleanHtml(response.answer) }}
                        />
                        
                        {response.sources && response.sources.length > 0 && (
                          <Box sx={{ mt: 2 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              출처 ({response.sources.length}개):
                            </Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                              {response.sources.map((source, sourceIndex) => (
                                <Chip
                                  key={sourceIndex}
                                  label={`${source.document_title} (p.${source.page_number})`}
                                  onClick={() => {
                                    setSources(response.sources);
                                    handleSourceClick(sourceIndex);
                                  }}
                                  clickable
                                  size="small"
                                  icon={<Source />}
                                />
                              ))}
                            </Box>
                          </Box>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </Box>
              )}

              {/* Comparison Table Loading */}
              {comparisonLoading && (
                <Box sx={{ mb: 3, textAlign: 'center', p: 3, backgroundColor: '#f0f7ff', borderRadius: 1 }}>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  <Typography variant="body1" color="primary" sx={{ display: 'inline' }}>
                    비교표 생성중입니다...
                  </Typography>
                </Box>
              )}

              {/* Comparison Table */}
              {comparisonTable && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    비교 분석표
                  </Typography>
                  <Box 
                    sx={{ 
                      '& table': {
                        borderCollapse: 'collapse',
                        width: '100%',
                        marginTop: 1,
                        marginBottom: 1,
                        border: '1px solid #ddd',
                        fontSize: '0.875rem'
                      },
                      '& th, & td': {
                        border: '1px solid #ddd',
                        padding: '8px 12px',
                        textAlign: 'left',
                        verticalAlign: 'top'
                      },
                      '& th': {
                        backgroundColor: '#e3f2fd',
                        fontWeight: 'bold',
                        color: '#1565c0'
                      },
                      '& tr:nth-of-type(even)': {
                        backgroundColor: '#f8f9fa'
                      }
                    }}
                    dangerouslySetInnerHTML={{ __html: cleanHtml(comparisonTable) }}
                  />
                </Box>
              )}

              {/* Integrated Response */}
              {answer && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    통합 답변
                  </Typography>
                  <Box 
                    sx={{ 
                      whiteSpace: 'pre-wrap', 
                      lineHeight: 1.6,
                      '& table': {
                        borderCollapse: 'collapse',
                        width: '100%',
                        marginTop: 2,
                        marginBottom: 2,
                        border: '1px solid #ddd'
                      },
                      '& th, & td': {
                        border: '1px solid #ddd',
                        padding: '8px 12px',
                        textAlign: 'left'
                      },
                      '& th': {
                        backgroundColor: '#f5f5f5',
                        fontWeight: 'bold'
                      },
                      '& tr:nth-of-type(even)': {
                        backgroundColor: '#f9f9f9'
                      }
                    }}
                    dangerouslySetInnerHTML={{ __html: cleanHtml(answer) }}
                  />
                  
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