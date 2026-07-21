import sqlite3
import csv
import os

def compile_csv_to_room_db(region_prefix, source_csv, output_db_name):
    print(f"--- Starting compilation for: {output_db_name} ---")
    
    if os.path.exists(output_db_name):
        os.remove(output_db_name)
        
    conn = sqlite3.connect(output_db_name)
    cursor = conn.cursor()
    
    # Create target data schema
    cursor.execute("""
        CREATE TABLE GlobalStops (
            `Index Number` TEXT PRIMARY KEY NOT NULL,
            `Country` TEXT NOT NULL,
            `Stop Number` TEXT,
            `Common Stop Name` TEXT NOT NULL,
            `Street Name` TEXT,
            `Town Name` TEXT NOT NULL,
            `Latitude` TEXT NOT NULL,
            `Longitude` TEXT NOT NULL
        )
    """)
    
    # FIX ISSUE 1: Initialize Room's mandatory validation metadata matrix
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_master_table (
            id INTEGER PRIMARY KEY,
            identity_hash TEXT
        )
    """)
    
    # Inject compiled tracking hash key matching version 1 of your TransitStop table schema layout
    room_identity_hash = "c18090b8fcf6eb0ccbc1e619b0b46f5c"
    cursor.execute("""
        INSERT OR REPLACE INTO room_master_table (id, identity_hash) 
        VALUES (42, ?)
    """, (room_identity_hash,))
    
    if not os.path.exists(source_csv):
        print(f"Error: Source file '{source_csv}' not found. Aborting.")
        conn.close()
        return

    print(f"Reading lines from: {source_csv}")
    
    with open(source_csv, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        insert_buffer = []
        total_rows_processed = 0
        
        for count, row in enumerate(reader, start=1):
            # FIX ISSUE 2: Deep trim layout text values, catching structural whitespace issues
            def clean_val(key):
                val = row.get(key)
                if val is None:
                    return ""
                # Strip spaces, tabs, newline commands, and hidden quote structures
                return str(val).strip().replace('"', '').replace("'", "")

            insert_buffer.append((
                clean_val('Index Number'),
                region_prefix.strip(), 
                clean_val('Stop Number'),
                clean_val('Common Stop Name'),
                clean_val('Street Name'),
                clean_val('Town Name'),
                clean_val('Latitude'),
                clean_val('Longitude')
            ))
            total_rows_processed += 1

            if count % 50000 == 0:
                cursor.executemany("""
                    INSERT OR REPLACE INTO GlobalStops 
                    (`Index Number`, `Country`, `Stop Number`, `Common Stop Name`, `Street Name`, `Town Name`, `Latitude`, `Longitude`)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_buffer)
                insert_buffer.clear()
                print(f"   Processed {count} rows...")

        if insert_buffer:
            cursor.executemany("""
                INSERT OR REPLACE INTO GlobalStops 
                (`Index Number`, `Country`, `Stop Number`, `Common Stop Name`, `Street Name`, `Town Name`, `Latitude`, `Longitude`)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, insert_buffer)
            
    if total_rows_processed == 0:
        print("\nBUILD FAILED: 0 entries processed.")
        conn.close()
        if os.path.exists(output_db_name):
            os.remove(output_db_name)
        return

    print(f"Successfully processed {total_rows_processed} total entries.")
    print("Optimizing table performance indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stop_name ON GlobalStops (`Common Stop Name`);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stop_num ON GlobalStops (`Stop Number`);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stop_town ON GlobalStops (`Town Name`);")
    
    conn.commit()
    conn.close()
    print(f"Success! File generated: {output_db_name}\n")

# Change for Country
if __name__ == "__main__":
    TARGET_PREFIX = "IT"
    INPUT_CSV_FILE = "IT\\IT.csv"  # Check your subfolder name pathing
    OUTPUT_DB_FILE = "databases\\transit_IT.db"

    compile_csv_to_room_db(
        region_prefix=TARGET_PREFIX,
        source_csv=INPUT_CSV_FILE,
        output_db_name=OUTPUT_DB_FILE
    )