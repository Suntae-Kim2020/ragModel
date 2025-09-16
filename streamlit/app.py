import streamlit as st
import tempfile
import os
import json
import pandas as pd
from dotenv import load_dotenv
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go

# 백엔드 모듈들 임포트
from opensearch_client import OpenSearchClient
from pdf_processor import PDFProcessor
from rag_service import RAGService

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="RAG 문서 관리 시스템",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바에 CSS 스타일 추가
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton > button {
        width: 100%;
    }
    .stSelectbox > div > div > select {
        background-color: #f0f2f6;
    }
    .comparison-table {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'services_initialized' not in st.session_state:
    st.session_state.services_initialized = False
    st.session_state.osearch_client = None
    st.session_state.pdf_processor = None
    st.session_state.rag_service = None

def initialize_services():
    """서비스 초기화"""
    if not st.session_state.services_initialized:
        try:
            with st.spinner("서비스 초기화 중..."):
                st.session_state.osearch_client = OpenSearchClient()
                st.session_state.pdf_processor = PDFProcessor()
                st.session_state.rag_service = RAGService()
                st.session_state.services_initialized = True
                st.success("✅ 모든 서비스가 성공적으로 초기화되었습니다!")
        except Exception as e:
            st.error(f"❌ 서비스 초기화 실패: {str(e)}")
            st.warning("일부 기능이 제한될 수 있습니다.")

def get_assistants(organization: str = None) -> List[str]:
    """어시스턴트 목록 조회"""
    if st.session_state.osearch_client:
        try:
            assistants = st.session_state.osearch_client.get_assistants(organization)
            return assistants
        except:
            return ["General", "Technical", "Academic", "Business"]
    return ["General", "Technical", "Academic", "Business"]

def upload_document_page():
    """문서 업로드 페이지"""
    st.header("📄 문서 업로드")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 파일 업로드
        uploaded_file = st.file_uploader(
            "PDF 문서를 선택하세요",
            type=['pdf'],
            help="PDF 파일만 업로드 가능합니다."
        )
        
        if uploaded_file is not None:
            st.success(f"선택된 파일: {uploaded_file.name}")
            
            # 문서 정보 입력
            st.subheader("📋 문서 정보")
            
            document_title = st.text_input(
                "문서 제목",
                value=uploaded_file.name.replace('.pdf', ''),
                help="문서의 제목을 입력하세요"
            )
            
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                organization = st.selectbox(
                    "조직",
                    ["개인", "회사", "학교", "기타"],
                    help="문서가 속한 조직을 선택하세요"
                )
                
                document_type = st.selectbox(
                    "문서 유형",
                    ["보고서", "논문", "매뉴얼", "계약서", "기타"],
                    help="문서의 유형을 선택하세요"
                )
            
            with col_info2:
                assistant_id = st.selectbox(
                    "담당 어시스턴트",
                    get_assistants(organization),
                    help="문서를 처리할 어시스턴트를 선택하세요"
                )
            
            # 태그 입력
            tags_input = st.text_input(
                "태그 (쉼표로 구분)",
                placeholder="예: 기술문서, 설계, 개발",
                help="문서를 분류할 태그들을 쉼표로 구분하여 입력하세요"
            )
            
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            
            # 업로드 버튼
            if st.button("📤 문서 업로드", type="primary"):
                if not st.session_state.services_initialized:
                    st.error("서비스가 초기화되지 않았습니다. 페이지를 새로고침하세요.")
                    return
                
                try:
                    with st.spinner("문서 처리 중..."):
                        # 임시 파일로 저장
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_file_path = tmp_file.name
                        
                        # 문서 처리
                        processed_data = st.session_state.pdf_processor.process_pdf_for_storage(
                            tmp_file_path,
                            document_title,
                            tags,
                            organization,
                            document_type,
                            assistant_id
                        )
                        
                        # OpenSearch에 저장
                        stored_chunks = []
                        progress_bar = st.progress(0)
                        
                        for i, chunk in enumerate(processed_data['chunks']):
                            chunk_id = st.session_state.osearch_client.add_document_chunk(chunk)
                            stored_chunks.append(chunk_id)
                            progress_bar.progress((i + 1) / len(processed_data['chunks']))
                        
                        # 임시 파일 삭제
                        os.unlink(tmp_file_path)
                        
                        st.success("✅ 문서 업로드 완료!")
                        
                        # 결과 표시
                        col_result1, col_result2, col_result3 = st.columns(3)
                        with col_result1:
                            st.metric("총 페이지", processed_data['total_pages'])
                        with col_result2:
                            st.metric("생성된 청크", processed_data['total_chunks'])
                        with col_result3:
                            st.metric("저장된 청크", len(stored_chunks))
                        
                except Exception as e:
                    st.error(f"❌ 문서 업로드 실패: {str(e)}")
    
    with col2:
        st.subheader("📊 업로드 통계")
        if st.session_state.osearch_client:
            try:
                # 어시스턴트별 문서 수 (더미 데이터로 시각화)
                assistants = get_assistants()
                doc_counts = [10, 15, 8, 12]  # 실제로는 OpenSearch에서 조회
                
                fig = px.bar(
                    x=assistants,
                    y=doc_counts,
                    title="어시스턴트별 문서 수",
                    labels={'x': '어시스턴트', 'y': '문서 수'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            except:
                st.info("통계 데이터를 불러올 수 없습니다.")

def query_page():
    """질의응답 페이지"""
    st.header("🤖 RAG 질의응답")
    
    # 어시스턴트 선택
    st.subheader("🎯 어시스턴트 선택")
    available_assistants = get_assistants()
    
    selected_assistants = st.multiselect(
        "질의할 어시스턴트를 선택하세요 (다중 선택 가능)",
        available_assistants,
        default=[available_assistants[0]] if available_assistants else [],
        help="여러 어시스턴트를 선택하면 각각의 답변을 비교할 수 있습니다"
    )
    
    if len(selected_assistants) >= 2:
        st.info("💡 여러 어시스턴트가 선택되었습니다. 질의 내용에 '비교', '분석', '차이' 등의 키워드가 포함되면 자동으로 비교표가 제공됩니다.")
    
    # 질문 입력
    st.subheader("❓ 질문 입력")
    question = st.text_area(
        "질문을 입력하세요",
        height=100,
        placeholder="예: 인공지능의 발전 전망에 대해 설명해주세요.",
        help="문서 내용을 기반으로 답변드립니다"
    )
    
    col_query1, col_query2 = st.columns([3, 1])
    
    with col_query1:
        summary_mode = st.checkbox(
            "📝 요약 모드",
            help="체크하면 더 간결한 답변을 제공합니다"
        )
    
    with col_query2:
        query_button = st.button("🔍 질의 실행", type="primary")
    
    if query_button and question.strip():
        if not selected_assistants:
            st.warning("⚠️ 어시스턴트를 선택해주세요.")
            return
        
        if not st.session_state.services_initialized:
            st.error("❌ 서비스가 초기화되지 않았습니다. 페이지를 새로고침하세요.")
            return
        
        try:
            # 비교 키워드 검사
            comparison_keywords = ['비교', '분석', '차이', '대비', '비교분석', '차이점', '공통점']
            has_comparison = any(keyword in question for keyword in comparison_keywords)
            
            if len(selected_assistants) > 1:
                with st.spinner("🤖 여러 어시스턴트가 답변을 생성 중입니다..."):
                    # 개별 답변 생성
                    response = st.session_state.rag_service.get_individual_answers(
                        question, selected_assistants, summary_mode
                    )
                
                st.subheader("📝 어시스턴트 답변")
                
                # 각 어시스턴트 답변 표시 (확장된 상태로)
                for assistant_data in response['individual_answers']:
                    with st.expander(f"🤖 {assistant_data['assistant_id']} 답변", expanded=True):
                        st.write(assistant_data['answer'])
                        
                        if assistant_data.get('sources'):
                            st.write("**📚 참조 문서:**")
                            for source in assistant_data['sources']:
                                st.write(f"- {source.get('title', '알 수 없는 문서')}")
                
                # 비교표 생성 및 표시
                if has_comparison and 'comparison_table' in response and response['comparison_table']:
                    st.subheader("📊 비교 분석표")
                    with st.container():
                        st.markdown(
                            f'<div class="comparison-table">{response["comparison_table"]}</div>',
                            unsafe_allow_html=True
                        )
                
            else:
                # 단일 어시스턴트 답변
                with st.spinner(f"🤖 {selected_assistants[0]}가 답변을 생성 중입니다..."):
                    response = st.session_state.rag_service.get_answer(
                        question, selected_assistants[0], summary_mode
                    )
                
                st.subheader("📝 답변")
                st.write(response['answer'])
                
                if response.get('sources'):
                    st.subheader("📚 참조 문서")
                    for source in response['sources']:
                        st.write(f"- {source.get('title', '알 수 없는 문서')}")
        
        except Exception as e:
            st.error(f"❌ 질의 처리 실패: {str(e)}")
            st.info("기본 검색 결과를 제공합니다.")

def keyword_extraction_page():
    """키워드 추출 페이지"""
    st.header("🏷️ 키워드 추출")
    
    st.subheader("📝 텍스트 입력")
    text_input = st.text_area(
        "키워드를 추출할 텍스트를 입력하세요",
        height=200,
        placeholder="여기에 텍스트를 입력하면 자동으로 주요 키워드를 추출해드립니다...",
        help="OpenAI API를 사용하여 주요 키워드를 추출합니다"
    )
    
    if st.button("🔍 키워드 추출", type="primary"):
        if not text_input.strip():
            st.warning("⚠️ 텍스트를 입력해주세요.")
            return
        
        if not st.session_state.services_initialized:
            st.error("❌ 서비스가 초기화되지 않았습니다.")
            return
        
        try:
            with st.spinner("🤖 키워드 추출 중..."):
                keywords = st.session_state.rag_service.extract_keywords_with_openai(text_input)
            
            st.subheader("🏷️ 추출된 키워드")
            
            if keywords:
                # 키워드를 태그 형태로 표시
                cols = st.columns(4)
                for i, keyword in enumerate(keywords):
                    with cols[i % 4]:
                        st.markdown(f"<span style='background-color: #e1f5fe; padding: 4px 8px; border-radius: 12px; margin: 2px; display: inline-block;'>{keyword}</span>", unsafe_allow_html=True)
                
                # 키워드 분석 차트
                if len(keywords) > 1:
                    st.subheader("📊 키워드 분석")
                    # 키워드 길이 분석
                    keyword_lengths = [len(keyword) for keyword in keywords]
                    fig = px.bar(
                        x=keywords,
                        y=keyword_lengths,
                        title="키워드별 글자 수",
                        labels={'x': '키워드', 'y': '글자 수'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ 키워드를 추출할 수 없습니다.")
        
        except Exception as e:
            st.error(f"❌ 키워드 추출 실패: {str(e)}")

def main():
    """메인 함수"""
    st.title("📚 RAG 문서 관리 시스템")
    st.markdown("---")
    
    # 사이드바 메뉴
    with st.sidebar:
        st.title("🧭 메뉴")
        
        page = st.selectbox(
            "페이지 선택",
            ["🏠 홈", "📄 문서 업로드", "🤖 질의응답", "🏷️ 키워드 추출"],
            help="원하는 기능을 선택하세요"
        )
        
        st.markdown("---")
        
        # 서비스 상태 표시
        st.subheader("🔧 서비스 상태")
        if st.session_state.services_initialized:
            st.success("✅ 모든 서비스 정상")
        else:
            st.warning("⚠️ 서비스 초기화 필요")
            if st.button("🔄 서비스 초기화"):
                initialize_services()
        
        st.markdown("---")
        
        # 환경 정보
        st.subheader("ℹ️ 환경 정보")
        st.info(f"OpenAI API: {'✅ 설정됨' if os.getenv('OPENAI_API_KEY') else '❌ 미설정'}")
        st.info(f"OpenSearch: {'✅ 연결됨' if st.session_state.services_initialized else '❌ 연결 안됨'}")
    
    # 서비스 초기화 (첫 방문시)
    if not st.session_state.services_initialized:
        initialize_services()
    
    # 페이지 라우팅
    if page == "🏠 홈":
        st.subheader("🏠 RAG 문서 관리 시스템에 오신 것을 환영합니다!")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("""
            ### 📄 문서 업로드
            - PDF 문서 업로드
            - 자동 텍스트 추출
            - 벡터 임베딩 생성
            - OpenSearch 저장
            """)
        
        with col2:
            st.info("""
            ### 🤖 질의응답
            - 다중 어시스턴트 지원
            - 자동 비교표 생성
            - 문서 기반 답변
            - 참조 문서 제공
            """)
        
        with col3:
            st.info("""
            ### 🏷️ 키워드 추출
            - OpenAI API 활용
            - 자동 키워드 분석
            - 시각화 제공
            - 태그 형태 출력
            """)
        
        st.markdown("---")
        st.subheader("📊 시스템 개요")
        
        # 시스템 아키텍처 다이어그램 (텍스트로)
        st.code("""
        📄 PDF 업로드 → 🔍 텍스트 추출 → 🧠 임베딩 변환 → 💾 OpenSearch 저장
                                                    ↓
        🤖 질의 입력 → 🔍 유사도 검색 → 📚 문서 검색 → 🤖 GPT-4 답변 생성
        """, language="text")
    
    elif page == "📄 문서 업로드":
        upload_document_page()
    
    elif page == "🤖 질의응답":
        query_page()
    
    elif page == "🏷️ 키워드 추출":
        keyword_extraction_page()

if __name__ == "__main__":
    main()