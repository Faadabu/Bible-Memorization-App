# parse_bible.py
import sqlite3
import re
import os

def ensure_data_dir():
    if not os.path.exists("data"):
        os.makedirs("data")

def parse_bible_text(file_path, db_path="data/bible_memory.db"):
    """
    Parse a Bible text file and store verses in SQLite database.
    Expected format: "Book Chapter:Verse Text"
    Example: "Genesis 1:1 In the beginning God created the heaven and the earth."
    """
    ensure_data_dir()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create or clear the table
    cursor.execute('''CREATE TABLE IF NOT EXISTS verses (
                      id INTEGER PRIMARY KEY,
                      book TEXT, 
                      chapter INTEGER, 
                      verse INTEGER, 
                      text TEXT, 
                      progress INTEGER DEFAULT 0)''')
    
    cursor.execute("DELETE FROM verses")  # Clear existing data
    
    verse_id = 1
    skipped_lines = 0
    processed_lines = 0
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            try:
                # Try to match various Bible text formats
                
                # Format 1: "Genesis 1:1 In the beginning..."
                match = re.match(r"^(\w+(?:\s+\w+)*)\s+(\d+):(\d+)\s+(.+)$", line)
                
                if match:
                    book, chapter, verse, text = match.groups()
                    cursor.execute(
                        "INSERT INTO verses (id, book, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
                        (verse_id, book, int(chapter), int(verse), text)
                    )
                    verse_id += 1
                    processed_lines += 1
                else:
                    # Format 2: Try to handle alternative formats
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        reference, text = parts
                        
                        # Try to parse reference like "Genesis1:1" (no space)
                        ref_match = re.match(r"^(\w+(?:\s+\w+)*)(\d+):(\d+)$", reference)
                        if ref_match:
                            book, chapter, verse = ref_match.groups()
                            cursor.execute(
                                "INSERT INTO verses (id, book, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
                                (verse_id, book, int(chapter), int(verse), text)
                            )
                            verse_id += 1
                            processed_lines += 1
                        else:
                            skipped_lines += 1
                    else:
                        skipped_lines += 1
            except Exception as e:
                print(f"Error processing line: {line}")
                print(f"Error: {e}")
                skipped_lines += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Bible parsing complete!")
    print(f"Processed: {processed_lines} verses")
    print(f"Skipped: {skipped_lines} lines")
    return processed_lines, skipped_lines

if __name__ == "__main__":
    file_path = "kjv.txt"
    if os.path.exists(file_path):
        processed, skipped = parse_bible_text(file_path)
        print(f"Bible verses stored in database! Processed {processed} verses, skipped {skipped} lines.")
    else:
        print(f"File not found: {file_path}")
        print("Please provide a valid file path.")
