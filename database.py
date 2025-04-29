import sqlite3
from datetime import datetime
import os
import cv2

class Database:
    def __init__(self, db_file="attendance.db"):
        self.db_file = db_file
        self.create_tables()

    def create_tables(self):
        """Create necessary tables if they don't exist"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Create students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                class TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                photo_path TEXT,
                registration_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create attendance table with location fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                date TEXT,
                time TEXT,
                status TEXT,
                latitude REAL,
                longitude REAL,
                location_verified BOOLEAN,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        ''')

        # Create classes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                class_name TEXT PRIMARY KEY
            )
        ''')

        conn.commit()
        conn.close()

    def add_student(self, student_id, name, class_name, email=None, phone=None, photo_path=None):
        """Add a new student to the database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Check if student ID already exists
            cursor.execute("SELECT id FROM students WHERE id=?", (student_id,))
            if cursor.fetchone():
                return False
            
            cursor.execute('''
                INSERT INTO students (id, name, class, email, phone, photo_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, name, class_name, email, phone, photo_path))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding student: {e}")
            return False
        finally:
            conn.close()

    def get_all_students(self):
        """Get all students from the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        conn.close()
        return students

    def get_student_attendance(self, student_id, start_date=None, end_date=None):
        """Get attendance records for a specific student"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if start_date and end_date:
            cursor.execute('''
                SELECT s.id, s.name, a.date, a.time, a.status, a.latitude, a.longitude, a.location_verified
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id
                WHERE s.id = ? AND a.date BETWEEN ? AND ?
                ORDER BY a.date DESC, a.time DESC
            ''', (student_id, start_date, end_date))
        else:
            cursor.execute('''
                SELECT s.id, s.name, a.date, a.time, a.status, a.latitude, a.longitude, a.location_verified
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id
                WHERE s.id = ?
                ORDER BY a.date DESC, a.time DESC
            ''', (student_id,))
        
        attendance = cursor.fetchall()
        conn.close()
        return attendance

    def mark_attendance(self, student_id, status, latitude=None, longitude=None, location_verified=False):
        """Mark attendance for a student"""
        try:
            # Standardize status to lowercase
            status = status.lower() if status else "present"
            
            # Get current date and time
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Connect to database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Check if attendance table has location columns
            cursor.execute("PRAGMA table_info(attendance)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            has_location_columns = ('latitude' in column_names and 
                                  'longitude' in column_names and 
                                  'location_verified' in column_names)
            
            # Check if attendance already exists for this student on this date
            cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date = ?", 
                         (student_id, current_date))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing attendance
                if has_location_columns:
                    cursor.execute("""
                        UPDATE attendance 
                        SET status = ?, time = ?, latitude = ?, longitude = ?, location_verified = ?
                        WHERE student_id = ? AND date = ?
                    """, (status, current_time, latitude, longitude, location_verified, 
                          student_id, current_date))
                else:
                    cursor.execute("""
                        UPDATE attendance 
                        SET status = ?, time = ?
                        WHERE student_id = ? AND date = ?
                    """, (status, current_time, student_id, current_date))
            else:
                # Insert new attendance
                if has_location_columns:
                    cursor.execute("""
                        INSERT INTO attendance (student_id, date, time, status, latitude, longitude, location_verified)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (student_id, current_date, current_time, status, 
                          latitude, longitude, location_verified))
                else:
                    cursor.execute("""
                        INSERT INTO attendance (student_id, date, time, status)
                        VALUES (?, ?, ?, ?)
                    """, (student_id, current_date, current_time, status))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking attendance: {e}")
            return False

    def get_class_attendance(self, class_name, date=None):
        """Get attendance for a specific class"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if date:
            cursor.execute('''
                SELECT s.id, s.name, a.status, a.time
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
                WHERE s.class = ?
                ORDER BY s.name
            ''', (date, class_name))
        else:
            cursor.execute('''
                SELECT s.id, s.name, NULL as status, NULL as time
                FROM students s
                WHERE s.class = ?
                ORDER BY s.name
            ''', (class_name,))
        
        attendance = cursor.fetchall()
        conn.close()
        return attendance

    def get_attendance_stats(self, start_date, end_date):
        """Get attendance statistics for the date range"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                s.class,
                COUNT(DISTINCT CASE WHEN a.status = 'present' THEN s.id END) as present,
                COUNT(DISTINCT s.id) as total,
                (CAST(COUNT(DISTINCT CASE WHEN a.status = 'present' THEN s.id END) AS FLOAT) / 
                 CAST(COUNT(DISTINCT s.id) AS FLOAT) * 100) as rate
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id 
                AND a.date BETWEEN ? AND ?
            GROUP BY s.class
        ''', (start_date, end_date))
        
        stats = cursor.fetchall()
        conn.close()
        return stats

    def add_class(self, class_name):
        """Add a new class"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO classes (class_name) VALUES (?)", (class_name,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_all_classes(self):
        """Get all classes"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT class_name FROM classes")
        classes = [row[0] for row in cursor.fetchall()]
        conn.close()
        return classes

    def delete_student(self, student_id):
        """Delete a student and their attendance records"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Delete attendance records first (due to foreign key constraint)
            cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
            
            # Delete student
            cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting student: {e}")
            return False
        finally:
            conn.close()

    def get_student_by_user_id(self, user_id):
        """Get student information by user ID"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id = ?", (user_id,))
        student = cursor.fetchone()
        conn.close()
        return student

    def update_student(self, student_id, name, class_name, email, phone, photo=None):
        """Update student details in database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Check if we need to update the photo
            if photo is not None:
                # Create photos directory if it doesn't exist
                if not os.path.exists('photos'):
                    os.makedirs('photos')
                
                # Save photo to file
                photo_path = f'photos/{student_id}.jpg'
                cv2.imwrite(photo_path, photo)
                
                # Update student with photo
                cursor.execute(
                    "UPDATE students SET name=?, class=?, email=?, phone=?, photo_path=? WHERE id=?",
                    (name, class_name, email, phone, photo_path, student_id)
                )
            else:
                # Update student without changing photo
                cursor.execute(
                    "UPDATE students SET name=?, class=?, email=?, phone=? WHERE id=?",
                    (name, class_name, email, phone, student_id)
                )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating student: {e}")
            return False