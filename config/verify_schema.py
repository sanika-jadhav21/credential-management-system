
from config.database import get_connection


def verify_tables():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SHOW TABLES")

        tables = cursor.fetchall()

        print("\nDATABASE SCHEMA VERIFICATION")
        print("-" * 40)
        print(f"Database: {connection.database}")
        print(f"Total tables found: {len(tables)}")

        for index, table in enumerate(tables, start=1):
            print(f"{index}. {table[0]}")

        if not tables:
            print("WARNING: No tables found in the database.")

    except Exception as error:
        print("Schema verification failed:", error)

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
            print("\nDatabase connection closed.")



def verify_foreign_keys():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        query = """
            SELECT
                TABLE_NAME,
                CONSTRAINT_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, CONSTRAINT_NAME
        """

        cursor.execute(query, (connection.database,))
        foreign_keys = cursor.fetchall()

        print("\nFOREIGN KEY VERIFICATION")
        print("-" * 50)
        print(f"Total foreign keys found: {len(foreign_keys)}")

        for fk in foreign_keys:
            print(
                f"{fk[0]}.{fk[2]} -> "
                f"{fk[3]}.{fk[4]} "
                f"({fk[1]})"
            )

    except Exception as error:
        print("Foreign key verification failed:", error)

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
            print("\nDatabase connection closed.")


if __name__ == "__main__":
    verify_tables()
    verify_foreign_keys()
