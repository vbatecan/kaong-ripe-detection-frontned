import mysql.connector
from mysql.connector import Error

def get_db_connection(use_database=True):
    try:
        connection_params = {
            'host': 'localhost',
            'user': 'root',
            'password': '1234',
            'port': 33306
        }
        
        if use_database:
            connection_params['database'] = 'kaong_assessment'
            
        connection = mysql.connector.connect(**connection_params)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    # First connect without database
    connection = get_db_connection(use_database=False)
    if connection:
        try:
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS kaong_assessment")
            cursor.execute("USE kaong_assessment")
            
            # Create assessments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assessments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    image_url VARCHAR(255) NOT NULL,
                    assessment VARCHAR(50) NOT NULL,
                    confidence FLOAT NOT NULL,
                    source VARCHAR(50) NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)
            
            connection.commit()
            print("Database initialized successfully")
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close() 