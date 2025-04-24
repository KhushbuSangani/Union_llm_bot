import os
import PyPDF2
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd
import time,uuid,glob
from datetime import datetime, timedelta
from qdrant_client.http import models



os.environ['HUGGINGFACE_HUB_OFFLINE'] = 'true'
# Initialize Qdrant Client and model
qdrant_client = QdrantClient(host=os.getenv("QDRANT_HOST"), port=6333)
#model_path = "/root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"
model = SentenceTransformer('all-MiniLM-L6-v2')
collection_name = "document_embeddings"
llm_file_dir=os.path.join('llm_files')   
def extract_text_from_pdf(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader= PdfReader(pdf)
        for page in pdf_reader.pages:
            text+= page.extract_text()
    
    return text

def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    text = []
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)
    return '\n'.join(text)


def extract_text_from_csv(csv_file):
    # Read the CSV file
    df = pd.read_csv(csv_file)
    extracted_data = []
    df.columns = df.columns.str.strip()
    if {'title', 'query', 'response'}.issubset(df.columns):
        combined_text = df['query']        
        extracted_data = [{"question": combined_text[i], "answer": df['response'][i]} for i in range(len(df))]
    else:
        combined_text = df.astype(str).agg(' '.join, axis=1)
        extracted_data = [{"question": combined_text[i], "answer": combined_text[i]} for i in range(len(df))]
    return extracted_data
    
def extract_data_from_excel(excel_file):
    sheets = pd.read_excel(excel_file, sheet_name=None)  # Read all sheets
    extracted_data = []
    for _, df in sheets.items():
        df.columns = df.columns.str.strip()     
        if 'query' in df.columns and 'response' in df.columns:
            for _, row in df.iterrows():
                extracted_data.append({'question': row['query'], 'answer': row['response']})
        else:
            for _, row in df.iterrows():
                extracted_data.append(row.to_dict())  # Store each row as a dict
    return extracted_data

def chunk_text(text, chunk_size=500):
    # text_splitter = RecursiveCharacterTextSplitter(
    # # Set a really small chunk size, just to show.
    # chunk_size=chunk_size,
    # chunk_overlap=100,
    # length_function=len,
    # is_separator_regex=False,
    #         )
    # texts = text_splitter.split_text(text)
    qa_pairs = []
    question = ""
    answer = ""
    capturing_answer = False
    lines = text.split('\n')
    collections = qdrant_client.get_collections().collections
    collection_names = [col.name for col in collections]
    
    if collection_name not in collection_names:
        # If collection does not exist, create it
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
 
    for line in lines:
        # Remove extra spaces and check for a question pattern (ends with a ?)
        clean_line = line.strip()

        if clean_line.endswith('?'):
            # If we are already capturing an answer, save the previous QA pair
            if question and answer:
                qa_pairs.append({"question": question, "answer": answer.strip()})
                answer = ""  # Reset for the next answer
            
            question = clean_line  # Set the current line as a question
            capturing_answer = True  # Start capturing the answer in the next lines
        elif capturing_answer:
            # If it's part of the answer (not empty), append it
            answer += clean_line + " "

    # Capture the last QA pair if exists
    if question and answer:
        qa_pairs.append({"question": question, "answer": answer.strip()})
    if not qa_pairs:
        print("No Q&A pairs found. Fallback to normal chunking...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=100,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        qa_pairs = [{"question": chunk.strip(), "answer": chunk.strip()} for chunk in chunks]
    
    return qa_pairs



def process_pdfs(data_folder):
    all_chunks = []
    for filename in os.listdir(data_folder):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(data_folder, filename)
            text = extract_text_from_pdf(pdf_path)
            chunks = chunk_text(text, chunk_size=500)
            all_chunks.extend(chunks)
            
            
            
    for filename in os.listdir(data_folder):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(data_folder, filename)
            text = extract_text_from_pdf(pdf_path)
            chunks = chunk_text(text, chunk_size=500)
            indexing(chunks)  # Line 10: Call indexing directly with extracted chunks
#return None  # Adjust return value if needed
    return all_chunks

def indexing(chunks, filename):
    t1=time.time()   
    collection_name = os.path.splitext(filename)[0]

    try:
        # Check if collection exists
        if not qdrant_client.collection_exists(collection_name):
            qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
            print(f'Collection "{collection_name}" created.')
        else:
            print(f'Collection "{collection_name}" already exists.')
        
        points = []
        for idx, qa_pair in enumerate(chunks):
            question = qa_pair['question']
            answer = qa_pair['answer']
            embedding = model.encode(question).tolist()
            point = PointStruct(id=idx, vector=embedding, payload={"question": question,
        "text_chunk": answer})
            points.append(point)
        # Upsert points to Qdrant
        qdrant_client.upsert(collection_name=collection_name, points=points)
        print(f'Inserted {len(points)} points into Qdrant collection "{collection_name}".')

    except Exception as e:
        print(f"Error indexing chunks: {str(e)}")
    t2=time.time()

    print(f"Time taken by the embedding model: {t2-t1:.2f} seconds")



def cache_qestions(data):
    t1=time.time() 
    collection_name="cache_question"
  
    try:
        # Check if collection exists
        if not qdrant_client.collection_exists(collection_name):
            qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)        )
            print(f'Collection "{collection_name}" created.')
        else:
            print(f'Collection "{collection_name}" already exists.')
        
        points = []
        for idx, qa_pair in enumerate(data):
            question = qa_pair['query']
            answer = qa_pair['response_text']
            embedding = model.encode(question).tolist()
            point = PointStruct(id=str(uuid.uuid4()), vector=embedding, payload={"question": question,
        "text_chunk": answer, "timestamp": datetime.now().isoformat()})
            points.append(point)
        # Upsert points to Qdrant
        qdrant_client.upsert(collection_name=collection_name, points=points)
        t2=time.time()
        print(f"Time taken by the embedding model: {t2-t1:.2f} seconds")

    except Exception as e:
        print(f"Error indexing chunks: {str(e)}")

def query_qdrant_cache(qdrant_client, query_text, embed_model, top_k=2):
    query_embedding = embed_model.encode([query_text])[0].tolist()
    collection_name='cache_question'
    if not qdrant_client.collection_exists(collection_name):
            qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)        )
            print(f'Collection "{collection_name}" created.')
    else:
        print(f'Collection "{collection_name}" already exists.')
    # List all collections
    all_search_results = []
    max_score_result = None
    search_result = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k
    )
    if search_result:
        for result in search_result:
            if result.score > 0.85:  # Filter by minimum score
                all_search_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                })

    # Sort results by score in descending order
    sorted_results = sorted(all_search_results, key=lambda x: x["score"], reverse=True)
    max_score_result = sorted_results[0] if sorted_results else None

    if max_score_result:
        # Return only the 'text_chunk' field from the payload of the max score result
        return max_score_result["payload"].get("text_chunk", None)
def generate_suggestions_qdrant(qdrant_client, question, embed_model, top_k=2):
    """
    Generate follow-up suggestions using Qdrant.

    Args:
        question (str): User's question.
        qdrant_client (QdrantClient): Instance of Qdrant client.
        collection_name (str): The name of the Qdrant collection to query.
        embedding_fn (callable): A function to generate embeddings from a question.
    
    Returns:
        List[str]: List of suggested follow-up questions.
    """
    # Generate embedding for the question

    question_embedding = embed_model.encode([question])[0].tolist()
    collections = qdrant_client.get_collections().collections
    all_search_results = []
    max_score_result = None
    top_results = []

    # Set to track unique questions and avoid duplicates
    seen_questions = set()

    # Iterate over collections
    for collection in collections:
        # Perform search on each collection
        search_result = qdrant_client.search(
            collection_name=collection.name,
            query_vector=question_embedding,
            limit=10  # Limit to top 10 results
        )

        # Skip empty search results
        if not search_result:
            continue

        # Iterate through search results, filtering duplicates and collecting top results
        for result in search_result:
            if result.score < 0.9 and result.score > 0.4:  # Filter by minimum score
                if 'question' in result.payload:  # Ensure the result has the 'question' field
                    question_text = result.payload['question']
                    if question_text not in seen_questions:
                        seen_questions.add(question_text)
                        top_results.append({
                            "question": question_text,
                            "score": result.score
                        })


    # If there are results, sort them by score and get the top 3
    questions_sorted = sorted(top_results, key=lambda x: x['score'], reverse=True)

    # Extract the list of questions (ignoring scores)
    top_questions = [entry["question"] for entry in questions_sorted]
    return top_questions[:3]
def remove_cache_question(data):
    metadata_filter = models.Filter(
    must=[
        models.FieldCondition(
            key="question",  # Replace with the exact metadata field name
            match=models.MatchValue(value=data)
        )
    ]
    )

    # Delete points matching the filter
    qdrant_client.delete(
        collection_name="cache_question",  # Replace with your collection name
        points_selector=models.FilterSelector(filter=metadata_filter)
    )

    print(f"Data with question '{data}' has been removed.")
    
def delete_all_embedded_files(filename_list):
    try:
        all_collections = qdrant_client.get_collections().collections
        for collection in all_collections:
            collection_name = collection.name
            if collection_name in filename_list:
                qdrant_client.delete_collection(collection_name=collection_name)
        print("Operation completed.")
    except Exception as e:
        print(f"An error occurred: {e}")
        
def generate_suggestions_llm(question, model):
    suggestion_prompt = f"""
    Given the following user question:
    
    "{question}"
    
    Generate three related follow-up questions without any additional descriptions or explanations.
    Only return the questions, each on a new line.
    """
    response = model.invoke(suggestion_prompt)  # Using invoke method
    suggestions = response.strip().split("\n")
    return [suggestion.strip() for suggestion in suggestions if suggestion.strip()]


