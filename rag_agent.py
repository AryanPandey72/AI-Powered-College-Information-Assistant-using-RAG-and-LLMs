import os
import chromadb
from chromadb.utils import embedding_functions
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from db_connector import execute_query, get_all_faculty_names

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Replace with your actual Groq API Key
os.environ["GROQ_API_KEY"] = "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"

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# Setup Vector DB Connection
# This connects to the folder created by 'build_vector_db.py'
chroma_client = chromadb.PersistentClient(path="college_chroma_db")
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
vector_collection = chroma_client.get_collection(name="faculty_profiles", embedding_function=embedding_func)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def clean_user_input(user_question):
    """Injects exact names into the prompt (e.g. 'Sunil' -> 'Mr. Sunil Kumar V')."""
    valid_names = get_all_faculty_names()
    words = user_question.split()
    for word in words:
        clean_word = word.strip("?!.,").lower()
        if len(clean_word) < 4: continue
        for db_name in valid_names:
            if clean_word in db_name.lower():
                return f"{user_question} (Note: Strictly refer to '{word}' as '{db_name}')"
    return user_question

def query_vector_db(question):
    """Searches the JSON bio data for relevant text."""
    results = vector_collection.query(query_texts=[question], n_results=2)
    if results['documents']:
        return "\n".join(results['documents'][0])
    return "No bio information found."

# ==========================================
# 3. THE CHAINS (BRAINS)
# ==========================================

# --- ROUTER CHAIN: Decides "SQL" or "VECTOR" ---
router_system = """
Classify the user's question into one of two categories:
1. "SQL" - For questions about Schedules, Classes, Time, Rooms, Subjects, or Student Projects/Guides.
2. "VECTOR" - For questions about Teacher Bio, Research, Experience, Qualification, Date of Joining, or Interests.

Reply ONLY with "SQL" or "VECTOR".
"""
router_prompt = ChatPromptTemplate.from_messages([("system", router_system), ("human", "{question}")])
router_chain = router_prompt | llm | StrOutputParser()

# --- SQL CHAIN: Generates MySQL Queries ---
sql_system = """
You are a SQL Expert. Convert questions to MySQL.
Schema:
1. faculty_schedule (faculty_name, day_of_week, start_time, end_time, room_number, subject_name)
   - For 'now', check `day_of_week=DAYNAME(CURDATE())` AND `CURTIME() BETWEEN start_time AND end_time`.
2. final_year_project (mentor_name, project_title, student_names)
   - student_names uses LIKE.
Return ONLY the SQL.
"""
sql_prompt = ChatPromptTemplate.from_messages([("system", sql_system), ("human", "{question}")])
sql_chain = sql_prompt | llm | StrOutputParser()

# --- FINAL ANSWER CHAIN: Humanizes the result ---
final_system = """
You are a helpful assistant. Answer the user based ONLY on the provided Context.
If the Context is from a Database, summarize it clearly.
If the Context is text (bio/research), summarize the key points.
"""
final_prompt = ChatPromptTemplate.from_messages([
    ("system", final_system), 
    ("human", "Question: {question}\nContext: {context}")
])
final_chain = final_prompt | llm | StrOutputParser()

# ==========================================
# 4. MAIN AGENT LOGIC
# ==========================================
def ask_college_bot(user_question):
    print(f"\nUser Question: {user_question}")
    
    # 1. Clean Input (Name Matching)
    enhanced_question = clean_user_input(user_question)
    
    # 2. Router: SQL or VECTOR?
    category = router_chain.invoke({"question": enhanced_question}).strip()
    print(f"Router Decision: {category}")
    
    context_data = ""
    
    try:
        if "SQL" in category:
            # --- SQL PATH ---
            print("Executing SQL Path...")
            query = sql_chain.invoke({"question": enhanced_question}).replace("```sql", "").replace("```", "").strip()
            print(f"Generated SQL: {query}")
            raw_data = execute_query(query)
            context_data = str(raw_data) if raw_data else "No records found."
            
        else:
            # --- VECTOR PATH ---
            print("Executing Vector Path...")
            context_data = query_vector_db(enhanced_question)

        # 3. Generate Final Answer
        final_answer = final_chain.invoke({
            "question": user_question,
            "context": context_data
        })
        return final_answer
        
    except Exception as e:
        return f"Error: {e}"

# --- TEST ---
if __name__ == "__main__":
    # Test 1: Vector Question (Should work now!)
    print("\n--- TEST VECTOR ---")
    print(ask_college_bot("What are the research works about Piyush Sir?"))