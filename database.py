# database.py
import sqlite3
import os
import random

def ensure_data_dir():
    if not os.path.exists("data"):
        os.makedirs("data")

def init_db():
    ensure_data_dir()
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    
    # Create verses table
    cursor.execute('''CREATE TABLE IF NOT EXISTS verses (
                      id INTEGER PRIMARY KEY, 
                      book TEXT, 
                      chapter INTEGER, 
                      verse INTEGER, 
                      text TEXT, 
                      progress INTEGER DEFAULT 0)''')
    
    # Create memorized verses table
    cursor.execute('''CREATE TABLE IF NOT EXISTS memorized_verses (
                      id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      book TEXT, 
                      chapter INTEGER, 
                      verse INTEGER, 
                      last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      ease_factor REAL DEFAULT 2.5,
                      interval INTEGER DEFAULT 1)''')
    
    conn.commit()
    conn.close()

def import_bible_from_text(file_path):
    """Import Bible verses from a text file into the database"""
    ensure_data_dir()
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    
    # Clear existing verses if any
    cursor.execute("DELETE FROM verses")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            verse_id = 1
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse line format: "Book Chapter:Verse Text"
                    parts = line.split(' ', 1)
                    if len(parts) < 2:
                        continue
                    
                    reference, text = parts
                    
                    # Parse reference
                    book_chapter_verse = reference.split(':')
                    if len(book_chapter_verse) < 2:
                        continue
                    
                    book_chapter = book_chapter_verse[0].rsplit(' ', 1)
                    if len(book_chapter) < 2:
                        continue
                    
                    book = book_chapter[0]
                    chapter = int(book_chapter[1])
                    verse = int(book_chapter_verse[1])
                    
                    cursor.execute(
                        "INSERT INTO verses (id, book, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
                        (verse_id, book, chapter, verse, text)
                    )
                    verse_id += 1
                    
        conn.commit()
        return True
    except Exception as e:
        print(f"Error importing Bible: {e}")
        return False
    finally:
        conn.close()

def count_verses():
    """Count total number of verses in the database"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM verses")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_random_verse():
    """Get a random verse from the database"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    
    # Check if there are any verses in the database
    cursor.execute("SELECT COUNT(*) FROM verses")
    count = cursor.fetchone()[0]
    
    if count == 0:
        conn.close()
        return ("No verses found", 0, 0, "Please import a Bible text file.")
    
    # Get a random verse
    cursor.execute("SELECT book, chapter, verse, text FROM verses ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    
    # Return the verse or a default if none found
    if result:
        return result
    else:
        return ("John", 3, 16, "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.")

def get_verse_by_reference(book, chapter, verse):
    """Get a specific verse by reference"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT book, chapter, verse, text FROM verses WHERE book=? AND chapter=? AND verse=?", 
                  (book, chapter, verse))
    result = cursor.fetchone()
    conn.close()
    return result

def save_memorized_verse(book, chapter, verse):
    """Mark a verse as memorized and schedule it for spaced repetition"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    
    # Check if verse already exists in memorized_verses
    cursor.execute("SELECT id FROM memorized_verses WHERE book=? AND chapter=? AND verse=?",
                  (book, chapter, verse))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing record
        cursor.execute("""
            UPDATE memorized_verses 
            SET last_reviewed=CURRENT_TIMESTAMP, 
                ease_factor=2.5, 
                interval=1 
            WHERE id=?""", (existing[0],))
    else:
        # Insert new record
        cursor.execute("""
            INSERT INTO memorized_verses (book, chapter, verse) 
            VALUES (?, ?, ?)""", (book, chapter, verse))
    
    conn.commit()
    conn.close()

def get_verses_due_for_review(limit=10):
    """Get verses that are due for review based on spaced repetition algorithm"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT mv.book, mv.chapter, mv.verse, v.text, mv.ease_factor, mv.interval
        FROM memorized_verses mv
        JOIN verses v ON mv.book = v.book AND mv.chapter = v.chapter AND mv.verse = v.verse
        WHERE julianday('now') - julianday(mv.last_reviewed) >= mv.interval
        ORDER BY julianday('now') - julianday(mv.last_reviewed) - mv.interval DESC
        LIMIT ?
    """, (limit,))
    
    results = cursor.fetchall()
    conn.close()
    return results

def update_spaced_repetition(book, chapter, verse, quality):
    """Update spaced repetition parameters based on performance quality (0-5)"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    
    # Get current parameters
    cursor.execute("""
        SELECT ease_factor, interval 
        FROM memorized_verses 
        WHERE book=? AND chapter=? AND verse=?
    """, (book, chapter, verse))
    
    result = cursor.fetchone()
    if result:
        ease_factor, interval = result
        
        # Update based on SM-2 algorithm
        ease_factor = max(1.3, ease_factor + (0.1 - (5-quality) * (0.08 + (5-quality) * 0.02)))
        
        if quality < 3:
            interval = 1  # Reset interval if quality is poor
        elif interval == 1:
            interval = 6  # First successful recall
        else:
            interval = int(interval * ease_factor)  # Increase interval based on ease factor
        
        # Update the database
        cursor.execute("""
            UPDATE memorized_verses 
            SET ease_factor=?, interval=?, last_reviewed=CURRENT_TIMESTAMP 
            WHERE book=? AND chapter=? AND verse=?
        """, (ease_factor, interval, book, chapter, verse))
        
        conn.commit()
    
    conn.close()

def get_books():
    """Get list of all books in the Bible"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT book FROM verses ORDER BY id")
    books = [row[0] for row in cursor.fetchall()]
    conn.close()
    return books

def get_chapters_for_book(book):
    """Get all chapters for a specific book"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT chapter FROM verses WHERE book=? ORDER BY chapter", (book,))
    chapters = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chapters

def get_verses_for_chapter(book, chapter):
    """Get all verses for a specific chapter in a book"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT verse, text FROM verses WHERE book=? AND chapter=? ORDER BY verse", 
                  (book, chapter))
    verses = cursor.fetchall()
    conn.close()
    return verses

def get_top_memory_verses():
    """Get one of the top 300 most quoted Bible verses"""
    # Example list - in a real app, these would be stored in the database
    top_memory_verses = [
        ("James", 2, 17, "Faith without works is dead."),
        ("John", 3, 16, "For God so loved the world, that he gave his only begotten Son..."),
        ("Philippians", 4, 13, "I can do all things through Christ which strengtheneth me."),
        ("Romans", 8, 28, "And we know that all things work together for good..."),
        # Add more verses here or load from a file/database
    ]
    
    # Return a random verse from the top memory verses
    import random
    return random.choice(top_memory_verses)

def search_word(word):
    """Search for a word in the Bible and return verses containing it"""
    conn = sqlite3.connect("data/bible_memory.db")
    cursor = conn.cursor()
    
    search_term = f"%{word}%"
    cursor.execute("""
        SELECT book, chapter, verse, text 
        FROM verses 
        WHERE text LIKE ? 
        ORDER BY id
    """, (search_term,))
    
    results = cursor.fetchall()
    
    # Count occurrences (this is simplified - in a real app would count actual word occurrences)
    count = len(results)
    
    conn.close()
    return count, results
