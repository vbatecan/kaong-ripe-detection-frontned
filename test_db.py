from db_config import get_db_connection, init_db
from datetime import datetime

def test_database():
    print("Testing database connection...")
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Test connection
    print("\n2. Testing connection...")
    connection = get_db_connection()
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Successfully connected to database")
    
    try:
        cursor = connection.cursor()
        
        # Test inserting data
        print("\n3. Testing data insertion...")
        test_data = {
            'image_url': '/static/uploads/test_image.jpg',
            'assessment': 'Ready for Harvesting',
            'confidence': 0.95,
            'source': 'test',
            'timestamp': datetime.now()
        }
        
        sql = """INSERT INTO assessments 
                (image_url, assessment, confidence, source, timestamp) 
                VALUES (%s, %s, %s, %s, %s)"""
        values = (
            test_data['image_url'],
            test_data['assessment'],
            test_data['confidence'],
            test_data['source'],
            test_data['timestamp']
        )
        
        cursor.execute(sql, values)
        connection.commit()
        print("✅ Successfully inserted test data")
        
        # Test retrieving data
        print("\n4. Testing data retrieval...")
        cursor.execute("SELECT * FROM assessments ORDER BY timestamp DESC LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            print("✅ Successfully retrieved data:")
            print(f"Assessment: {result[2]}")
            print(f"Confidence: {result[3]}")
            print(f"Source: {result[4]}")
            print(f"Timestamp: {result[5]}")
        else:
            print("❌ No data found in database")
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("\n✅ Database connection closed properly")

if __name__ == "__main__":
    test_database() 