# main.py
import sys
import os
import sqlite3
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                            QTextEdit, QLabel, QHBoxLayout, QSplitter, 
                            QComboBox, QScrollArea, QFileDialog, QMessageBox,
                            QSpinBox, QGroupBox, QSlider, QLineEdit)
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtCore import Qt, QTimer
from database import (init_db, get_random_verse, save_memorized_verse, 
                     import_bible_from_text, get_books, get_chapters_for_book,
                     get_verses_for_chapter, get_verse_by_reference,
                     count_verses, get_verses_due_for_review)
import pyttsx3

class TextToSpeech:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        
    def speak(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"TTS Error: {e}")

class BibleMemoryApp(QWidget):
    def __init__(self):
        super().__init__()
        self.tts = TextToSpeech()
        self.current_book = None
        self.current_chapter = None
        self.current_verse = None
        self.current_text = None
        self.test_mode = False
        self.attempts = 0
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Bible Memorization App")
        self.setGeometry(100, 100, 1000, 600)
        
        # Create main layout with splitter
        main_layout = QHBoxLayout()
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel (Bible display)
        self.left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Navigation controls
        nav_layout = QHBoxLayout()
        
        self.book_selector = QComboBox()
        self.book_selector.currentTextChanged.connect(self.book_selected)
        
        self.chapter_selector = QComboBox()
        self.chapter_selector.currentTextChanged.connect(self.chapter_selected)
        
        self.verse_selector = QComboBox()
        self.verse_selector.currentTextChanged.connect(self.verse_selected)
        
        nav_layout.addWidget(QLabel("Book:"))
        nav_layout.addWidget(self.book_selector)
        nav_layout.addWidget(QLabel("Chapter:"))
        nav_layout.addWidget(self.chapter_selector)
        nav_layout.addWidget(QLabel("Verse:"))
        nav_layout.addWidget(self.verse_selector)
        
        left_layout.addLayout(nav_layout)
        
        # Search controls
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search word...")
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_word)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        left_layout.addLayout(search_layout)

        # Search results area
        self.search_results = QTextEdit()
        self.search_results.setReadOnly(True)
        self.search_results.setMaximumHeight(150)
        self.search_results.setVisible(False)
        left_layout.addWidget(self.search_results)
        
        # Add dark/light mode toggle
        self.is_dark_mode = False
        self.theme_toggle_btn = QPushButton("🌙 Dark Mode")
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        main_layout.addWidget(self.theme_toggle_btn, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
        # Bible text area with scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.bible_display = QTextEdit()
        self.bible_display.setFont(QFont("Times New Roman", 12))
        self.bible_display.setReadOnly(True)
        self.scroll_area.setWidget(self.bible_display)
        left_layout.addWidget(self.scroll_area)
        
        # Import button
        import_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import Bible Text")
        self.import_btn.clicked.connect(self.import_bible)
        self.read_aloud_btn = QPushButton("Read Aloud")
        self.read_aloud_btn.clicked.connect(self.read_current_verse)
        import_layout.addWidget(self.import_btn)
        import_layout.addWidget(self.read_aloud_btn)
        left_layout.addLayout(import_layout)
        
        self.left_panel.setLayout(left_layout)
        
        # Right panel (Memory test)
        self.right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Test controls
        self.verse_ref_label = QLabel("Verse Reference")
        self.verse_ref_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.verse_ref_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.verse_ref_label)
        
        self.test_verse_label = QLabel("Click 'Start Memory Test' to begin")
        self.test_verse_label.setFont(QFont("Arial", 12))
        self.test_verse_label.setWordWrap(True)
        self.test_verse_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.test_verse_label)
        
        # Memory test controls
        test_controls = QHBoxLayout()
        self.memory_test_btn = QPushButton("Start Memory Test")
        self.memory_test_btn.clicked.connect(self.start_test)
        self.random_verse_btn = QPushButton("Random Verse")
        self.random_verse_btn.clicked.connect(self.load_random_verse)
        self.review_due_btn = QPushButton("Review Due Verses")
        self.review_due_btn.clicked.connect(self.review_due_verses)
        test_controls.addWidget(self.memory_test_btn)
        test_controls.addWidget(self.random_verse_btn)
        test_controls.addWidget(self.review_due_btn)
        right_layout.addLayout(test_controls)
        
        self.memory_verse_btn = QPushButton("Top Memory Verse")
        self.memory_verse_btn.clicked.connect(self.load_memory_verse)
        test_controls.addWidget(self.memory_verse_btn)
        
        # User input area
        self.user_input = QTextEdit()
        self.user_input.setFont(QFont("Arial", 12))
        self.user_input.setPlaceholderText("Type the verse here when in test mode...")
        right_layout.addWidget(self.user_input)
       
        
        # Submit and feedback
        self.submit_btn = QPushButton("Submit")
        self.submit_btn.clicked.connect(self.check_answer)
        right_layout.addWidget(self.submit_btn)
        
        self.feedback_label = QLabel("")
        self.feedback_label.setWordWrap(True)
        right_layout.addWidget(self.feedback_label)
        
        # Next verse button
        self.next_btn = QPushButton("Next Verse")
        self.next_btn.clicked.connect(self.load_random_verse)
        self.next_btn.setVisible(False)
        right_layout.addWidget(self.next_btn)
        
        self.right_panel.setLayout(right_layout)
        
        # Add panels to splitter
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([500, 500])  # Equal initial sizes
        
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)
        
        # Initialize and load data
        init_db()
        self.update_book_selector()
        self.load_random_verse()
    
    def update_book_selector(self):
        """Update the book selector dropdown with available books"""
        books = get_books()
        if books:
            self.book_selector.clear()
            self.book_selector.addItems(books)
            
    def load_memory_verse(self):
        """Load a verse from the top memory verses collection"""
        from database import get_top_memory_verses
        self.test_mode = False
        self.current_book, self.current_chapter, self.current_verse, self.current_text = get_top_memory_verses()
        self.display_verse()
        self.reset_test_ui()
        
    
    def search_word(self):
        """Search for a word in the Bible"""
        from database import search_word
        
        search_term = self.search_input.text().strip()
        if not search_term:
            return
            
        count, results = search_word(search_term)
        
        if count == 0:
            self.search_results.setText(f"No occurrences of '{search_term}' found.")
        else:
            output = f"'{search_term}' appears {count} times in the Bible:\n\n"
            
            for book, chapter, verse, text in results[:20]:  # Limit to first 20 results
                reference = f"{book} {chapter}:{verse}"
                # Make each result clickable by formatting as HTML
                output += f"<a href=\"{book},{chapter},{verse}\">{reference}</a> - {text[:50]}...\n"
                
            if count > 20:
                output += f"\n... and {count-20} more occurrences."
                
            self.search_results.setHtml(output)
            self.search_results.setVisible(True)
            
            # Connect linkClicked signal if not already connected
            if not hasattr(self, 'search_results_connected'):
                self.search_results.anchorClicked.connect(self.load_verse_from_search)
                self.search_results_connected = True
            
    def load_verse_from_search(self, url):
        """Load a verse when clicked in search results"""
        parts = url.toString().split(',')
        if len(parts) == 3:
            book = parts[0]
            chapter = int(parts[1])
            verse = int(parts[2])
            
            result = get_verse_by_reference(book, chapter, verse)
            if result:
                self.current_book, self.current_chapter, self.current_verse, self.current_text = result
                self.display_verse()
                self.reset_test_ui()
            
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
    
        if self.is_dark_mode:
            self.theme_toggle_btn.setText("☀️ Light Mode")
            self.setStyleSheet("""
                QWidget { background-color: #2b2b2b; color: #e0e0e0; }
                QTextEdit, QComboBox, QSpinBox { background-color: #3b3b3b; color: #e0e0e0; border: 1px solid #555; }
                QPushButton { background-color: #444; color: #e0e0e0; border: 1px solid #666; padding: 5px; }
                QPushButton:hover { background-color: #555; }
                QLabel { color: #e0e0e0; }
            """)
        else:
            self.theme_toggle_btn.setText("🌙 Dark Mode")
            self.setStyleSheet("")  # Reset to default theme
    
    def book_selected(self):
        """Handle book selection"""
        if self.book_selector.currentText():
            self.current_book = self.book_selector.currentText()
            chapters = get_chapters_for_book(self.current_book)
            
            self.chapter_selector.clear()
            self.chapter_selector.addItems([str(ch) for ch in chapters])
    
    def chapter_selected(self):
        """Handle chapter selection"""
        if self.chapter_selector.currentText():
            self.current_chapter = int(self.chapter_selector.currentText())
            verses = get_verses_for_chapter(self.current_book, self.current_chapter)
            
            self.verse_selector.clear()
            self.verse_selector.addItems([str(v[0]) for v in verses])
    
    def verse_selected(self):
        """Handle verse selection"""
        if self.verse_selector.currentText():
            self.current_verse = int(self.verse_selector.currentText())
            self.load_selected_verse()
    
    def load_selected_verse(self):
        """Load the selected verse"""
        if self.current_book and self.current_chapter and self.current_verse:
            result = get_verse_by_reference(self.current_book, self.current_chapter, self.current_verse)
            if result:
                self.current_book, self.current_chapter, self.current_verse, self.current_text = result
                self.display_verse()
    
    def load_random_verse(self):
        """Load a random verse from the database"""
        self.test_mode = False
        self.current_book, self.current_chapter, self.current_verse, self.current_text = get_random_verse()
        
        # Update the selectors to match the current verse
        if self.current_book in [self.book_selector.itemText(i) for i in range(self.book_selector.count())]:
            self.book_selector.setCurrentText(self.current_book)
            
            # Update chapter selector
            chapters = get_chapters_for_book(self.current_book)
            self.chapter_selector.clear()
            self.chapter_selector.addItems([str(ch) for ch in chapters])
            if str(self.current_chapter) in [self.chapter_selector.itemText(i) for i in range(self.chapter_selector.count())]:
                self.chapter_selector.setCurrentText(str(self.current_chapter))
            
            # Update verse selector
            verses = get_verses_for_chapter(self.current_book, self.current_chapter)
            self.verse_selector.clear()
            self.verse_selector.addItems([str(v[0]) for v in verses])
            if str(self.current_verse) in [self.verse_selector.itemText(i) for i in range(self.verse_selector.count())]:
                self.verse_selector.setCurrentText(str(self.current_verse))
        
        self.display_verse()
        self.reset_test_ui()
    
    def display_verse(self):
        """Display the current verse in the UI"""
        reference = f"{self.current_book} {self.current_chapter}:{self.current_verse}"
        self.verse_ref_label.setText(reference)
        
        if self.test_mode:
            self.bible_display.setText(f"{reference}\n\n[HIDDEN DURING TEST]")
            self.test_verse_label.setText("Type the verse from memory")
        else:
            full_text = f"{reference}\n\n{self.current_text}"
            self.bible_display.setText(full_text)
            self.test_verse_label.setText(self.current_text)
    
    def start_test(self):
        """Start the memory test for the current verse"""
        self.test_mode = True
        self.attempts = 0
        self.user_input.clear()
        self.feedback_label.setText("Try to recall the verse!")
        self.next_btn.setVisible(False)
        self.display_verse()
    
    def check_answer(self):
        """Check the user's answer against the verse"""
        if not self.test_mode:
            self.feedback_label.setText("Click 'Start Memory Test' first!")
            return
        
        user_text = self.user_input.toPlainText().strip()
        # Simple normalization for comparison - remove punctuation and case
        normalized_user = ''.join(c.lower() for c in user_text if c.isalnum() or c.isspace())
        normalized_verse = ''.join(c.lower() for c in self.current_text if c.isalnum() or c.isspace())
        
        if normalized_user == normalized_verse:
            self.feedback_label.setText("Correct! Well done!")
            save_memorized_verse(self.current_book, self.current_chapter, self.current_verse)
            self.next_btn.setVisible(True)
            self.test_mode = False
            self.display_verse()  # Show the full verse again
        else:
            self.attempts += 1
            if self.attempts < 5:
                # Generate hint by showing first N letters of each word
                words = self.current_text.split()
                hint_level = min(self.attempts, 3)  # Maximum 3 letters per word
                
                hint_words = []
                for word in words:
                    visible_chars = min(hint_level, len(word))
                    hint_word = word[:visible_chars] + "_" * (len(word) - visible_chars)
                    hint_words.append(hint_word)
                
                hint_text = " ".join(hint_words)
                self.feedback_label.setText(f"Attempt {self.attempts}/5. Hint: {hint_text}")
            else:
                self.feedback_label.setText(f"Out of attempts! The correct verse is:\n{self.current_text}")
                self.next_btn.setVisible(True)
                self.test_mode = False
                self.display_verse()  # Show the full verse again
    
    def reset_test_ui(self):
        """Reset the test UI components"""
        self.test_mode = False
        self.user_input.clear()
        self.feedback_label.setText("")
        self.next_btn.setVisible(False)
        self.attempts = 0
    
    def import_bible(self):
        """Import Bible text from a file"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Open Bible Text File", "", "Text Files (*.txt)")
        
        if file_path:
            success = import_bible_from_text(file_path)
            if success:
                verses_count = count_verses()
                QMessageBox.information(self, "Import Successful", 
                                       f"Successfully imported {verses_count} verses into the database.")
                self.update_book_selector()
                self.load_random_verse()
            else:
                QMessageBox.critical(self, "Import Failed", 
                                    "Failed to import Bible text. Check file format.")
    
    def read_current_verse(self):
        """Read the current verse aloud using TTS"""
        if self.current_text:
            self.tts.speak(self.current_text)
    
    def review_due_verses(self):
        """Load verses that are due for review based on spaced repetition"""
        due_verses = get_verses_due_for_review()
        if due_verses:
            # Get the first due verse
            book, chapter, verse, text, ease_factor, interval = due_verses[0]
            self.current_book = book
            self.current_chapter = chapter
            self.current_verse = verse
            self.current_text = text
            
            self.display_verse()
            self.reset_test_ui()
            QMessageBox.information(self, "Review Mode", 
                                   f"Reviewing verse due for repetition. Next review in {interval} days.")
        else:
            QMessageBox.information(self, "No Reviews Due", 
                                   "No verses are currently due for review.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BibleMemoryApp()
    window.show()
    sys.exit(app.exec())

