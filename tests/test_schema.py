"""Test script to validate all schema tables can be created."""
import sqlite3
import tempfile
import os

# Import the schema
from src.database.schema import SCHEMAS

def test_schema_creation():
    """Test that all 57 tables can be created without errors."""
    # Create a temporary database
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as tmp:
        tmp_db = tmp.name

    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        errors = []
        success_count = 0

        # Try to create each table
        for table_name, schema_sql in SCHEMAS.items():
            try:
                cursor.execute(schema_sql)
                success_count += 1
                print(f'[OK] {table_name}')
            except Exception as e:
                errors.append((table_name, str(e)))
                print(f'[FAIL] {table_name}: {e}')

        conn.commit()

        # Report results
        print(f'\n{"="*60}')
        print(f'RESULTS:')
        print(f'  Total tables: {len(SCHEMAS)}')
        print(f'  Successfully created: {success_count}')
        print(f'  Failed: {len(errors)}')

        if errors:
            print(f'\nERRORS:')
            for table, error in errors:
                print(f'  {table}: {error}')
            return False
        else:
            print(f'\n[SUCCESS] All {success_count} tables created successfully!')
            return True

    finally:
        # Close connection before deleting
        if conn:
            conn.close()
        # Clean up temporary database
        if os.path.exists(tmp_db):
            try:
                os.unlink(tmp_db)
            except:
                pass  # Ignore cleanup errors

if __name__ == '__main__':
    success = test_schema_creation()
    exit(0 if success else 1)
