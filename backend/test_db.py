from app.database import engine

try:
    with engine.connect() as connection:
        print("MySQL connection successful")
except Exception as e:
    print("MySQL connection failed")
    print(e)