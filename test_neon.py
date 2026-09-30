import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("DATABASE_URL not found in .env")

conn = psycopg2.connect(database_url)

cursor = conn.cursor()

cursor.execute("SELECT version();")
result = cursor.fetchone()

print("Connected successfully!")
print(result[0])

cursor.close()
conn.close()