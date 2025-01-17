import json
import psycopg2
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector
import os

# Define the embedding function
class HuggingFaceEmbeddings:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-l6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed(self, texts):
        return self.model.encode(texts, convert_to_tensor=False).tolist()

embedding_function = HuggingFaceEmbeddings()

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "user_questions",
    "user": "postgres",
    "password": "test"
}
#USER_DB_POSTGRES_URL="postgresql://postgres:test@localhost:5432/user_questions"
#Function to create the questions table if it doesn't exist
POSTGRES_URL=os.getenv("POSTGRES_URL")
class PromptQuestion:
    def __init__(self):
        self.create_table_if_not_exists()
    def create_table_if_not_exists(self):
        #conn = psycopg2.connect(**DB_CONFIG)
        #conn=psycopg2.connect(USER_DB_POSTGRES_URL)
        conn=psycopg2.connect(POSTGRES_URL)

        register_vector(conn)
        cur = conn.cursor()
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,          -- Auto-incremented unique identifier
            persona VARCHAR(50),            -- Persona identifier (e.g., 'OP', 'ESP')
            question TEXT,                  -- The question text
            embedding VECTOR(384)           -- Vector for question embeddings
        );
        
        -- Create index for similarity search if it doesn't exist
        CREATE INDEX IF NOT EXISTS idx_embedding ON questions USING ivfflat (embedding) WITH (lists = 100);

        -- Create index for persona filtering if it doesn't exist
        CREATE INDEX IF NOT EXISTS idx_persona ON questions (persona);
        """
        cur.execute(create_table_query)
        conn.commit()
        cur.close()
        conn.close()
        print("Table `questions` checked or created successfully.")

    # Function to insert questions and embeddings into the database
    def insert_questions_from_json(json_file, persona):
        # Ensure the table exists
        #self.create_table_if_not_exists()

        with open(json_file, "r") as f:
            questions = json.load(f)
        
        # Generate embeddings
        embeddings = embedding_function.embed(questions)
        
        # Insert into PostgreSQL
        #conn = psycopg2.connect(**DB_CONFIG)
        conn=psycopg2.connect(POSTGRES_URL)
        register_vector(conn)
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO questions (persona, question, embedding)
            VALUES (%s, %s, %s)
        """
        for question, embedding in zip(questions, embeddings):
            cur.execute(insert_query, (persona, question, embedding))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"Inserted {len(questions)} questions for persona: {persona}")


    def get_similar_question(user_question, persona="ESP"):
        # Generate embedding for the user question
        user_embedding = embedding_function.embed([user_question])[0]
        
        # Convert Python list to PostgreSQL array format
        user_embedding_str = "ARRAY[" + ", ".join(map(str, user_embedding)) + "]"
        
        # Query the database for similar questions
        #conn = psycopg2.connect(**DB_CONFIG)
        conn=psycopg2.connect(POSTGRES_URL)
        register_vector(conn)
        cur = conn.cursor()
        
        # First, get the most similar question's index
        similar_query = f"""
            SELECT id, question, 
                1 - (embedding <=> {user_embedding_str}::VECTOR) AS similarity
            FROM questions
            WHERE persona = %s
            ORDER BY embedding <=> {user_embedding_str}::VECTOR
            LIMIT 1
        """
        cur.execute(similar_query, (persona,))
        most_similar = cur.fetchone()
        
        if not most_similar:
            cur.close()
            conn.close()
            return None
        
        most_similar_id = most_similar[0]
        
        # Get the next question in index order
        next_query = """
            SELECT question 
            FROM questions 
            WHERE persona = %s 
            AND id > %s 
            ORDER BY id 
            LIMIT 1
        """
        cur.execute(next_query, (persona, most_similar_id))
        next_question = cur.fetchone()
        
        # If no next question exists (we're at the end), get the first question
        if not next_question:
            first_query = """
                SELECT question 
                FROM questions 
                WHERE persona = %s 
                ORDER BY id 
                LIMIT 1
            """
            cur.execute(first_query, (persona,))
            next_question = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return next_question[0] if next_question else None



# promt_question=PromptQuestion
# print("Suggested next question : ",promt_question.get_similar_question("What if I select best","DP"))



