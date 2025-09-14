import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  Alert,
  LinearProgress,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Autocomplete
} from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

function AdminPage({ user }) {
  const [file, setFile] = useState(null);
  const [documentTitle, setDocumentTitle] = useState('');
  const [tags, setTags] = useState('');
  const [organization, setOrganization] = useState('');
  const [assistantId, setAssistantId] = useState('');
  const [existingAssistants, setExistingAssistants] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchAssistants();
    
    // 로그인한 사용자의 기관명을 자동으로 설정
    if (user?.organization) {
      setOrganization(user.organization);
    }
  }, [user]);

  const fetchAssistants = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/assistants`);
      setExistingAssistants(response.data.assistants || []);
    } catch (error) {
      console.error('Failed to fetch assistants:', error);
    }
  };

  const extractKeywordsFromText = async (text) => {
    // OpenAI API를 사용하여 키워드 추출
    console.log('Extracting keywords using OpenAI API for text:', text);
    
    try {
      const formData = new FormData();
      formData.append('text', text);
      
      const response = await axios.post(`${API_BASE_URL}/extract-keywords`, formData);
      
      const keywords = response.data.keywords || [];
      console.log('Keywords extracted by OpenAI:', keywords);
      return keywords;
      
    } catch (error) {
      console.error('OpenAI keyword extraction failed:', error);
      
      // Fallback to simple extraction
      const fallbackKeywords = [];
      const cleanText = text.replace(/[0-9\._()]/g, '').trim();
      
      // Basic pattern matching for common Korean terms
      if (cleanText.includes('학사운영위원회')) {
        fallbackKeywords.push('학사운영위원회', '학사운영', '운영위원회', '학사', '위원회');
      }
      if (cleanText.includes('규정')) fallbackKeywords.push('규정');
      if (cleanText.includes('개정')) fallbackKeywords.push('개정');
      if (cleanText.includes('제정')) fallbackKeywords.push('제정');
      if (cleanText.includes('전북대')) fallbackKeywords.push('전북대학교');
      
      const uniqueKeywords = [...new Set(fallbackKeywords)];
      console.log('Fallback keywords:', uniqueKeywords);
      return uniqueKeywords;
    }
  };

  const extractKeywordsFromFilename = async (filename) => {
    // 파일명에서 확장자 제거 후 키워드 추출
    const nameWithoutExt = filename.replace('.pdf', '');
    console.log('Filename without extension:', nameWithoutExt);
    const keywords = await extractKeywordsFromText(nameWithoutExt);
    console.log('Keywords from filename processing:', keywords);
    return keywords;
  };

  const handleFileChange = async (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setMessage(null);
      
      // 파일명에서 확장자 제거한 것을 문서 제목으로 자동 입력
      const titleFromFilename = selectedFile.name.replace('.pdf', '');
      setDocumentTitle(titleFromFilename);
      
      // 파일명에서 키워드 추출해서 태그로 자동 입력
      console.log('File selected:', selectedFile.name);
      try {
        const extractedKeywords = await extractKeywordsFromFilename(selectedFile.name);
        console.log('Keywords from filename:', extractedKeywords);
        if (extractedKeywords.length > 0) {
          setTags(extractedKeywords.join(', '));
          console.log('Tags from file:', extractedKeywords.join(', '));
        }
      } catch (error) {
        console.error('Failed to extract keywords from filename:', error);
      }
      
      // 기관명은 로그인한 사용자의 기관명을 사용 (이미 설정됨)
    } else {
      setMessage({ type: 'error', text: 'PDF 파일만 업로드 가능합니다.' });
      setFile(null);
    }
  };

  const handleTagsChange = (event) => {
    setTags(event.target.value);
  };

  const parseTagsToArray = (tagsString) => {
    return tagsString
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!file || !documentTitle || !organization || !assistantId) {
      setMessage({ type: 'error', text: '모든 필수 필드를 입력해주세요.' });
      return;
    }

    setUploading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_title', documentTitle);
    formData.append('tags', JSON.stringify(parseTagsToArray(tags)));
    formData.append('organization', organization);
    formData.append('document_type', '규정'); // 기본값으로 '규정' 설정
    formData.append('assistant_id', assistantId);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload-document`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setMessage({ 
        type: 'success', 
        text: `문서가 성공적으로 업로드되었습니다. (${response.data.total_chunks}개 청크, ${response.data.total_pages}페이지)` 
      });
      
      // Reset form (기관명은 로그인한 사용자 기관명 유지)
      setFile(null);
      setDocumentTitle('');
      setTags('');
      setAssistantId('');
      document.getElementById('file-input').value = '';
      
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: `업로드 실패: ${error.response?.data?.detail || error.message}` 
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Box sx={{ mb: 3, p: 2, bgcolor: 'primary.main', color: 'white', borderRadius: 1 }}>
          <Typography variant="h5">
            문서 업로드 관리
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {user?.name} ({user?.email}) - {user?.organization}
          </Typography>
        </Box>
        
        {message && (
          <Alert severity={message.type} sx={{ mb: 3 }}>
            {message.text}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="기관명"
            value={organization}
            InputProps={{
              readOnly: true,
            }}
            helperText="로그인한 사용자의 기관명이 자동으로 설정됩니다"
            required
            sx={{ mb: 3 }}
          />

          <Autocomplete
            fullWidth
            freeSolo
            options={existingAssistants}
            value={assistantId}
            onInputChange={(event, newValue) => {
              setAssistantId(newValue || '');
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="어시스턴트 ID"
                required
                helperText="기존 어시스턴트를 선택하거나 새로운 ID를 입력하세요"
              />
            )}
            sx={{ mb: 3 }}
          />

          <Box sx={{ mb: 3 }}>
            <input
              accept="application/pdf"
              style={{ display: 'none' }}
              id="file-input"
              type="file"
              onChange={handleFileChange}
            />
            <label htmlFor="file-input">
              <Button
                variant="outlined"
                component="span"
                startIcon={<CloudUpload />}
                fullWidth
                sx={{ p: 2 }}
              >
                PDF 파일 선택
              </Button>
            </label>
            {file && (
              <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                선택된 파일: {file.name}
              </Typography>
            )}
          </Box>

          <TextField
            fullWidth
            label="문서 제목"
            value={documentTitle}
            onChange={async (e) => {
              const newTitle = e.target.value;
              setDocumentTitle(newTitle);
              
              // 문서 제목이 변경될 때마다 키워드 추출해서 태그 자동 업데이트
              console.log('Title changed:', newTitle);
              if (newTitle.trim()) {
                try {
                  const extractedKeywords = await extractKeywordsFromText(newTitle);
                  console.log('Extracted keywords:', extractedKeywords);
                  if (extractedKeywords.length > 0) {
                    setTags(extractedKeywords.join(', '));
                    console.log('Tags set:', extractedKeywords.join(', '));
                  }
                } catch (error) {
                  console.error('Failed to extract keywords from title:', error);
                }
              } else {
                setTags('');
              }
            }}
            required
            sx={{ mb: 3 }}
          />

          <TextField
            fullWidth
            label="태그 (쉼표로 구분)"
            value={tags}
            onChange={handleTagsChange}
            placeholder="법령, 지침, 규정"
            helperText="문서 제목에서 자동으로 키워드가 추출됩니다. 필요시 수정하거나 추가해주세요."
            sx={{ mb: 3 }}
          />
          
          {tags && (
            <Box sx={{ mb: 3 }}>
              {parseTagsToArray(tags).map((tag, index) => (
                <Chip key={index} label={tag} size="small" sx={{ mr: 1, mb: 1 }} />
              ))}
            </Box>
          )}

          {uploading && <LinearProgress sx={{ mb: 3 }} />}

          <Button
            type="submit"
            variant="contained"
            size="large"
            fullWidth
            disabled={uploading || !file}
          >
            {uploading ? '업로드 중...' : '문서 업로드'}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
}

export default AdminPage;