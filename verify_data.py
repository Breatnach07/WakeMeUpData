import sqlite3

db_name = "databases\\transit_IE.db"
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

print("--- 1. Verification: Metadata Integrity ---")
cursor.execute("SELECT * FROM room_master_table;")
print(f"Room Master Data: {cursor.fetchall()}")

print("\n--- 2. Verification: Total Row Count ---")
cursor.execute("SELECT COUNT(*) FROM GlobalStops;")
count = cursor.fetchone()[0]
print(f"Total rows found in GlobalStops: {count}")

print("\n--- 3. Verification: Inspecting Unique Regions ---")
cursor.execute("SELECT DISTINCT Country FROM GlobalStops;")
print(f"Unique country tags written: {cursor.fetchall()}")

print("\n--- 4. Verification: Targeted Query for '999100' ---")
# Check every single field to see if 999100 exists anywhere at all
cursor.execute("""
    SELECT * FROM GlobalStops 
    WHERE `Index Number` LIKE '%999100%' 
       OR `Stop Number` LIKE '%999100%' 
       OR `Common Stop Name` LIKE '%999100%'
""")
results = cursor.fetchall()
if not results:
    print("ERROR: '999100' does not exist anywhere in this database file!")
else:
    print(f"SUCCESS: Found match!")
    for row in results:
        print(row)

conn.close()