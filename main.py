import sys
import os
import cv2
import numpy as np
import face_recognition
import re
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import seaborn as sns
import pandas as pd
from geopy.distance import geodesic
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QDateEdit, QSpinBox, QGroupBox, QFrame, QFileDialog, QMessageBox, QDialog,
    QGridLayout, QCheckBox, QSplitter, QProgressBar, QRadioButton, QButtonGroup,
    QScrollArea, QSizePolicy, QStackedWidget
)
from PyQt5.QtCore import Qt, QTimer, QDate, QDateTime, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QColor, QFont, QIcon
from database import Database
from geopy.geocoders import Nominatim

class LocationSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(LocationSettingsDialog, self).__init__(parent)
        self.setWindowTitle("Location Settings")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QGridLayout()
        self.setLayout(layout)

        # Create input fields
        self.lat_input = QLineEdit()
        self.lon_input = QLineEdit()
        self.radius_input = QSpinBox()
        self.radius_input.setRange(1, 5000)  # 1m to 5km
        self.radius_input.setValue(500)  # Default 500m

        # Add fields to layout
        layout.addWidget(QLabel("Latitude:"), 0, 0)
        layout.addWidget(self.lat_input, 0, 1)
        layout.addWidget(QLabel("Longitude:"), 1, 0)
        layout.addWidget(self.lon_input, 1, 1)
        layout.addWidget(QLabel("Allowed Radius (m):"), 2, 0)
        layout.addWidget(self.radius_input, 2, 1)

        # Add buttons
        button_box = QHBoxLayout()
        self.get_location_btn = QPushButton("Get Current Location")
        self.save_btn = QPushButton("Save Settings")
        
        button_box.addWidget(self.get_location_btn)
        button_box.addWidget(self.save_btn)
        layout.addLayout(button_box, 3, 0, 1, 2)

        # Connect signals
        self.get_location_btn.clicked.connect(self.get_current_location)
        self.save_btn.clicked.connect(self.accept)

    def get_current_location(self):
        try:
            geolocator = Nominatim(user_agent="student_attendance")
            location = geolocator.geocode("Delhi, India")  # Default to Delhi
            if location:
                self.lat_input.setText(str(location.latitude))
                self.lon_input.setText(str(location.longitude))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not get location: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.db = Database()
        
        # Initialize location settings
        self.school_location = (28.6139, 77.2090)  # Default location (Delhi)
        self.allowed_radius = 0.5  # Default radius in kilometers
        
        # Create photos directory if it doesn't exist
        if not os.path.exists("student_photos"):
            os.makedirs("student_photos")
        
        # Initialize camera variables
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera_frame)
        self.current_frame = None
        
        # Initialize camera control buttons
        self.start_camera_button = None
        self.stop_camera_button = None
        self.capture_photo_button = None
        self.attendance_camera_label = None
        
        # Initialize location variables
        self.location_verified = False
        self.current_location = None
        
        # Initialize face recognition variables
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.load_known_faces()
        
        # Initialize UI
        self.init_ui()
        self.captured_photo = None

    def load_known_faces(self):
        """Load known faces from the student photos directory"""
        try:
            # Clear existing data
            self.known_face_encodings = []
            self.known_face_names = []
            self.known_face_ids = []
            
            # Get all students from database
            students = self.db.get_all_students()
            
            for student in students:
                student_id = student[0]
                student_name = student[1]
                photo_path = student[5]  # Photo path is at index 5 in the student tuple
                
                if photo_path and os.path.exists(photo_path):
                    # Load image and get face encoding
                    image = face_recognition.load_image_file(photo_path)
                    face_locations = face_recognition.face_locations(image)
                    
                    if face_locations:
                        face_encoding = face_recognition.face_encodings(image, face_locations)[0]
                        
                        # Add to known faces
                        self.known_face_encodings.append(face_encoding)
                        self.known_face_names.append(student_name)
                        self.known_face_ids.append(student_id)
                        
                        print(f"Loaded face for {student_name} ({student_id})")
                    else:
                        print(f"No face found in photo for {student_name} ({student_id})")
            
            print(f"Loaded {len(self.known_face_encodings)} known faces")
        except Exception as e:
            print(f"Error loading known faces: {str(e)}")

    def init_ui(self):
        # Set window properties
        self.setWindowTitle("Student Attendance System")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
            QLabel {
                color: #212121;
            }
            QGroupBox {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
            }
            QLineEdit, QSpinBox, QDateEdit {
                padding: 6px;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
            }
            QTableWidget {
                background-color: white;
                border: none;
                border-radius: 8px;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border: none;
            }
        """)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create left sidebar for navigation
        sidebar = QWidget()
        sidebar.setMaximumWidth(200)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #1565C0;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                text-align: left;
                padding: 15px;
                border-radius: 0px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(0)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add logo or title
        title = QLabel("Student\nAttendance")
        title.setStyleSheet("""
            color: white;
            font-size: 24px;
            padding: 20px;
            font-weight: bold;
        """)
        title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title)
        
        # Add navigation buttons
        nav_buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("👥 Students", self.show_students),
            ("📸 Take Attendance", self.show_attendance),
            ("📈 Reports", self.show_reports),
            ("⚙️ Settings", self.show_settings)
        ]
        
        for text, slot in nav_buttons:
            button = QPushButton(text)
            button.setMinimumHeight(50)
            button.clicked.connect(slot)
            sidebar_layout.addWidget(button)
        
        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # Create stacked widget for different pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("""
            QStackedWidget {
                background-color: #f5f5f5;
            }
        """)
        main_layout.addWidget(self.stacked_widget)

        # Create different pages
        self.create_dashboard_page()
        self.create_students_page()
        self.create_attendance_page()
        self.create_reports_page()
        
        # Show dashboard by default
        self.show_dashboard()

    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Add welcome header
        header_layout = QHBoxLayout()
        welcome = QLabel("Welcome to Student Attendance System")
        welcome.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(welcome)
        
        # Add current date
        current_date = QLabel(datetime.now().strftime("%A, %d %B %Y"))
        current_date.setStyleSheet("font-size: 16px; color: #757575;")
        current_date.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(current_date)
        
        layout.addLayout(header_layout)
        
        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0; margin: 10px 0px;")
        layout.addWidget(line)
        
        # Add summary cards
        summary_layout = QHBoxLayout()
        
        # Total Students card
        students_widget = QGroupBox("Total Students")
        students_widget.setStyleSheet("""
            QGroupBox {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        students_layout = QVBoxLayout(students_widget)
        
        # Get actual student count from database
        student_count = len(self.db.get_all_students())
        
        students_count = QLabel(str(student_count))
        students_count.setAlignment(Qt.AlignCenter)
        students_count.setStyleSheet("font-size: 48px; color: white;")
        students_layout.addWidget(students_count)
        
        students_icon = QLabel("👥")
        students_icon.setAlignment(Qt.AlignCenter)
        students_icon.setStyleSheet("font-size: 24px;")
        students_layout.addWidget(students_icon)
        
        summary_layout.addWidget(students_widget)
        
        # Today's Attendance card
        attendance_widget = QGroupBox("Today's Attendance")
        attendance_widget.setStyleSheet("""
            QGroupBox {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        attendance_layout = QVBoxLayout(attendance_widget)
        
        # Calculate today's attendance (this would come from the database)
        # For demo, just use a placeholder
        attendance_count = QLabel("0/" + str(student_count))
        attendance_count.setAlignment(Qt.AlignCenter)
        attendance_count.setStyleSheet("font-size: 48px; color: white;")
        attendance_layout.addWidget(attendance_count)
        
        attendance_icon = QLabel("📊")
        attendance_icon.setAlignment(Qt.AlignCenter)
        attendance_icon.setStyleSheet("font-size: 24px;")
        attendance_layout.addWidget(attendance_icon)
        
        summary_layout.addWidget(attendance_widget)
        
        # Location Status card
        location_widget = QGroupBox("Location Settings")
        location_widget.setStyleSheet("""
            QGroupBox {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        location_layout = QVBoxLayout(location_widget)
        
        location_status = QLabel(f"Radius: {self.allowed_radius * 1000:.0f}m")
        location_status.setAlignment(Qt.AlignCenter)
        location_status.setStyleSheet("font-size: 24px; color: white;")
        location_layout.addWidget(location_status)
        
        location_icon = QLabel("📍")
        location_icon.setAlignment(Qt.AlignCenter)
        location_icon.setStyleSheet("font-size: 24px;")
        location_layout.addWidget(location_icon)
        
        location_button = QPushButton("Change Location")
        location_button.clicked.connect(self.show_settings)
        location_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #FF9800;
                border: none;
                border-radius: 4px;
                padding: 5px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #FFECB3;
            }
        """)
        location_layout.addWidget(location_button)
        
        summary_layout.addWidget(location_widget)
        
        layout.addLayout(summary_layout)
        
        # Add quick actions section
        actions_group = QGroupBox("Quick Actions")
        actions_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
            }
        """)
        actions_layout = QHBoxLayout(actions_group)
        
        # Take attendance button
        take_attendance_btn = QPushButton("📸 Take Attendance")
        take_attendance_btn.clicked.connect(self.show_attendance)
        take_attendance_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        actions_layout.addWidget(take_attendance_btn)
        
        # Manage students button
        manage_students_btn = QPushButton("👥 Manage Students")
        manage_students_btn.clicked.connect(self.show_students)
        manage_students_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        actions_layout.addWidget(manage_students_btn)
        
        # View reports button
        view_reports_btn = QPushButton("📈 View Reports")
        view_reports_btn.clicked.connect(self.show_reports)
        view_reports_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        actions_layout.addWidget(view_reports_btn)
        
        layout.addWidget(actions_group)
        
        # Add recent activity section
        recent_group = QGroupBox("Recent Activity")
        recent_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
            }
        """)
        recent_layout = QVBoxLayout(recent_group)
        
        # This would be populated from the database
        # For demo, just add placeholder text
        for i in range(3):
            activity = QLabel(f"Student attendance recorded at {datetime.now().strftime('%H:%M:%S')}")
            activity.setStyleSheet("padding: 8px; border-bottom: 1px solid #E0E0E0;")
            recent_layout.addWidget(activity)
        
        layout.addWidget(recent_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.stacked_widget.addWidget(page)

    def show_dashboard(self):
        self.stacked_widget.setCurrentIndex(0)

    def show_students(self):
        self.stacked_widget.setCurrentIndex(1)

    def show_attendance(self):
        self.stacked_widget.setCurrentIndex(2)

    def show_reports(self):
        self.stacked_widget.setCurrentIndex(3)

    def show_settings(self):
        dialog = LocationSettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                lat = float(dialog.lat_input.text())
                lon = float(dialog.lon_input.text())
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    self.school_location = (lat, lon)
                    self.allowed_radius = dialog.radius_input.value() / 1000  # Convert to kilometers
                else:
                    QMessageBox.warning(self, "Error", "Invalid coordinates!")
            except ValueError:
                QMessageBox.warning(self, "Error", "Please enter valid numbers for coordinates!")

    def update_camera_frame(self):
        """Update the camera frame in the UI"""
        if self.camera is not None:
            ret, frame = self.camera.read()
            if ret:
                # Convert frame to RGB for display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                # Convert to QImage and display
                image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.attendance_camera_label.setPixmap(QPixmap.fromImage(image))
                self.current_frame = frame

    def create_students_page(self):
        """Create the students management page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Add header
        header_layout = QHBoxLayout()
        
        title = QLabel("Students Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)
        
        # Add student button
        add_button = QPushButton("➕ Add New Student")
        add_button.setFixedWidth(180)
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        add_button.clicked.connect(self.add_student)
        header_layout.addWidget(add_button)
        
        # Search box
        search_box = QLineEdit()
        search_box.setPlaceholderText("🔍 Search students...")
        search_box.setFixedWidth(250)
        search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #BDBDBD;
                border-radius: 20px;
                background-color: white;
            }
        """)
        search_box.textChanged.connect(self.filter_students)
        header_layout.addWidget(search_box)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0; margin: 10px 0px;")
        layout.addWidget(line)
        
        # Add filter options
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 10)
        
        filter_layout.addWidget(QLabel("Filter by Class:"))
        
        class_combo = QComboBox()
        class_combo.addItem("All Classes")
        class_combo.addItems(["Class 1", "Class 2", "Class 3"])  # This would be populated from database
        class_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                background-color: white;
                min-width: 150px;
            }
        """)
        filter_layout.addWidget(class_combo)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Add students table in a group box
        table_group = QGroupBox("Student Records")
        table_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        table_layout = QVBoxLayout(table_group)
        
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(6)
        # Set the Actions column wider to accommodate the buttons
        self.students_table.setColumnWidth(5, 200)
        self.students_table.setHorizontalHeaderLabels(["ID", "Name", "Class", "Email", "Phone", "Actions"])
        
        # Resize columns to content
        self.students_table.resizeColumnsToContents()
        
        # Set the last column to stretch
        header = self.students_table.horizontalHeader()
        header.setSectionResizeMode(5, header.Stretch)
        
        # Don't stretch the last section to ensure proper width for action buttons
        self.students_table.horizontalHeader().setStretchLastSection(False)
        self.students_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.students_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.students_table.setAlternatingRowColors(True)
        self.students_table.verticalHeader().setDefaultSectionSize(60)
        self.students_table.horizontalHeader().setDefaultSectionSize(150)
        # Use default header height
        # self.students_table.horizontalHeader().setFixedHeight(50)
        self.students_table.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #212121;
            }
        """)
        table_layout.addWidget(self.students_table)
        
        # Add pagination controls
        pagination_layout = QHBoxLayout()
        
        pagination_layout.addWidget(QLabel("Showing 1-10 of 0 students"))
        pagination_layout.addStretch()
        
        prev_btn = QPushButton("◀ Previous")
        prev_btn.setFixedWidth(100)
        pagination_layout.addWidget(prev_btn)
        
        next_btn = QPushButton("Next ▶")
        next_btn.setFixedWidth(100)
        pagination_layout.addWidget(next_btn)
        
        table_layout.addLayout(pagination_layout)
        table_layout.addWidget(self.students_table)
        layout.addWidget(table_group)
        
        # Add status bar
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Last updated: " + datetime.now().strftime("%d-%m-%Y %H:%M:%S")))
        status_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_students_table)
        status_layout.addWidget(refresh_btn)
        
        layout.addLayout(status_layout)
        
        self.refresh_students_table()
        self.stacked_widget.addWidget(page)

    def refresh_students_table(self):
        """Refresh the students table with current data"""
        # Clear the table
        self.students_table.setRowCount(0)
        
        # Get all students from database
        students = self.db.get_all_students()
        
        # Add students to table
        for row, student in enumerate(students):
            self.students_table.insertRow(row)
            
            # Student ID
            id_item = QTableWidgetItem(student[0])
            self.students_table.setItem(row, 0, id_item)
            
            # Name
            name_item = QTableWidgetItem(student[1])
            self.students_table.setItem(row, 1, name_item)
            
            # Class
            class_item = QTableWidgetItem(student[2])
            self.students_table.setItem(row, 2, class_item)
            
            # Email
            email_item = QTableWidgetItem(student[3] if student[3] else "")
            self.students_table.setItem(row, 3, email_item)
            
            # Phone
            phone_item = QTableWidgetItem(student[4] if student[4] else "")
            self.students_table.setItem(row, 4, phone_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 5, 0)
            actions_layout.setSpacing(2)
            
            # View button
            view_btn = QPushButton("👁️")
            view_btn.setToolTip("View Student")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 15px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            view_btn.clicked.connect(lambda _, s=student: self.view_student(s))
            actions_layout.addWidget(view_btn)
            
            # Edit button
            edit_btn = QPushButton("✏️")
            edit_btn.setToolTip("Edit Student")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border-radius: 15px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            edit_btn.clicked.connect(lambda _, s=student: self.edit_student(s))
            actions_layout.addWidget(edit_btn)
            
            # Delete button
            delete_btn = QPushButton("❌")
            delete_btn.setToolTip("Delete Student")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border-radius: 15px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                }
            """)
            delete_btn.clicked.connect(lambda _, s=student: self.delete_student(s))
            actions_layout.addWidget(delete_btn)
            
            actions_layout.addStretch()
            
            self.students_table.setCellWidget(row, 5, actions_widget)
        
        # Resize columns to content
        self.students_table.resizeColumnsToContents()
        
        # Set the last column to stretch
        header = self.students_table.horizontalHeader()
        header.setSectionResizeMode(5, header.Stretch)

    def add_student(self):
        """Add a new student"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Student")
        dialog.setModal(True)
        dialog.setStyleSheet(self.styleSheet())
        
        layout = QVBoxLayout(dialog)
        form_layout = QGridLayout()
        
        # Create input fields
        student_id = QLineEdit()
        name = QLineEdit()
        
        # Replace class_name LineEdit with ComboBox
        class_combo = QComboBox()
        class_combo.setEditable(True)  # Allow adding new classes
        
        # Add existing classes from database
        existing_classes = self.get_all_classes()
        if existing_classes:
            class_combo.addItems(existing_classes)
        else:
            # Add some default classes if none exist
            default_classes = ["Class 1", "Class 2", "Class 3", "Class 4"]
            class_combo.addItems(default_classes)
        
        email = QLineEdit()
        phone = QLineEdit()
        
        # Add fields to form
        form_layout.addWidget(QLabel("Student ID:"), 0, 0)
        form_layout.addWidget(student_id, 0, 1)
        form_layout.addWidget(QLabel("Name:"), 1, 0)
        form_layout.addWidget(name, 1, 1)
        form_layout.addWidget(QLabel("Class:"), 2, 0)
        form_layout.addWidget(class_combo, 2, 1)
        form_layout.addWidget(QLabel("Email:"), 3, 0)
        form_layout.addWidget(email, 3, 1)
        form_layout.addWidget(QLabel("Phone:"), 4, 0)
        form_layout.addWidget(phone, 4, 1)
        
        layout.addLayout(form_layout)
        
        # Add photo capture section
        photo_layout = QVBoxLayout()
        photo_label = QLabel("Student Photo")
        photo_label.setAlignment(Qt.AlignCenter)
        photo_layout.addWidget(photo_label)
        
        # Add photo preview
        photo_preview = QLabel()
        photo_preview.setFixedSize(160, 160)
        photo_preview.setStyleSheet("border: 2px dashed #BDBDBD; background-color: #f5f5f5;")
        photo_preview.setAlignment(Qt.AlignCenter)
        photo_preview.setText("No photo captured")
        photo_layout.addWidget(photo_preview)
        
        # Create a variable to store the captured photo
        student_photo = [None]  # Using a list to store a mutable reference
        
        # Capture photo button
        capture_button = QPushButton("📸 Capture Photo")
        capture_button.clicked.connect(lambda: self.capture_student_photo(photo_preview, student_photo))
        photo_layout.addWidget(capture_button)
        
        layout.addLayout(photo_layout)
        
        # Add buttons
        button_box = QHBoxLayout()
        save_btn = QPushButton("💾 Save")
        cancel_btn = QPushButton("❌ Cancel")
        
        save_btn.clicked.connect(lambda: self.save_student(
            dialog, student_id.text(), name.text(), class_combo.currentText(),
            email.text(), phone.text(), student_photo[0]
        ))
        cancel_btn.clicked.connect(dialog.reject)
        
        button_box.addWidget(save_btn)
        button_box.addWidget(cancel_btn)
        layout.addLayout(button_box)
        
        dialog.exec_()
    
    def capture_student_photo(self, preview_label, photo_storage):
        """Capture a photo for a student directly in the student form"""
        # Create a temporary camera dialog
        camera_dialog = QDialog(self)
        camera_dialog.setWindowTitle("Capture Student Photo")
        camera_dialog.setModal(True)
        camera_dialog.resize(640, 520)
        
        # Create layout
        layout = QVBoxLayout(camera_dialog)
        
        # Camera feed label
        camera_label = QLabel()
        camera_label.setMinimumSize(640, 480)
        camera_label.setAlignment(Qt.AlignCenter)
        camera_label.setText("Camera feed will appear here")
        layout.addWidget(camera_label)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Start camera button
        start_btn = QPushButton("Start Camera")
        buttons_layout.addWidget(start_btn)
        
        # Capture button
        capture_btn = QPushButton("Capture")
        capture_btn.setEnabled(False)
        buttons_layout.addWidget(capture_btn)
        
        # Done button
        done_btn = QPushButton("Done")
        done_btn.setEnabled(False)
        buttons_layout.addWidget(done_btn)
        
        layout.addLayout(buttons_layout)
        
        # Create camera and timer
        camera = None
        timer = QTimer()
        current_frame = [None]  # Using a list to store a mutable reference
        
        # Update camera frame function
        def update_frame():
            ret, frame = camera.read()
            if ret:
                # Convert to RGB for display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                # Convert to QImage and display
                image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                camera_label.setPixmap(QPixmap.fromImage(image))
                current_frame[0] = frame
        
        # Start camera function
        def start_camera():
            nonlocal camera
            camera = cv2.VideoCapture(0)
            if camera.isOpened():
                timer.start(30)  # Update every 30ms
                start_btn.setEnabled(False)
                capture_btn.setEnabled(True)
            else:
                QMessageBox.warning(camera_dialog, "Error", "Could not access the camera!")
        
        # Capture photo function
        def capture_photo():
            if current_frame[0] is not None:
                # Convert to RGB for face detection
                frame = current_frame[0]
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if not face_locations:
                    QMessageBox.warning(camera_dialog, "Error", "No face detected in the photo. Please try again.")
                    return
                
                # Store the captured photo
                photo_storage[0] = frame
                
                # Display in preview
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                preview_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                scaled_preview = preview_image.scaled(160, 160, Qt.KeepAspectRatio)
                preview_label.setPixmap(QPixmap.fromImage(scaled_preview))
                
                # Enable done button
                done_btn.setEnabled(True)
                
                QMessageBox.information(camera_dialog, "Success", "Photo captured successfully!")
        
        # Stop camera function
        def stop_camera():
            nonlocal camera
            if camera is not None:
                timer.stop()
                camera.release()
                camera = None
                camera_dialog.accept()
        
        # Connect signals
        timer.timeout.connect(update_frame)
        start_btn.clicked.connect(start_camera)
        capture_btn.clicked.connect(capture_photo)
        done_btn.clicked.connect(stop_camera)
        
        # Clean up on dialog close
        camera_dialog.finished.connect(lambda: stop_camera() if camera is not None else None)
        
        camera_dialog.exec_()
    
    def save_student(self, dialog, student_id, name, class_name, email, phone, photo=None):
        """Save student details to database"""
        # Validate inputs
        if not student_id or not name or not class_name:
            QMessageBox.warning(dialog, "Error", "Student ID, Name and Class are required!")
            return
        
        # Save photo if captured
        photo_path = None
        if photo is not None:
            # Create a filename based on student ID
            photo_path = os.path.join("student_photos", f"{student_id}.jpg")
            
            # Save the photo
            cv2.imwrite(photo_path, photo)
        
        # Add student to database
        success = self.db.add_student(student_id, name, class_name, email, phone, photo_path)
        
        if success:
            QMessageBox.information(dialog, "Success", "Student added successfully!")
            
            # Reload known faces to include the new student
            self.load_known_faces()
            
            dialog.accept()
            
            # Refresh the students table
            self.refresh_students_table()
        else:
            QMessageBox.warning(dialog, "Error", "Failed to add student. ID may already exist!")
            
            # Delete the saved photo if student wasn't added
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)

    def filter_students(self, text):
        """Filter students table based on search text"""
        for row in range(self.students_table.rowCount()):
            match = False
            for col in range(self.students_table.columnCount() - 1):  # Exclude actions column
                item = self.students_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.students_table.setRowHidden(row, not match)

    def view_student(self, student):
        """View student details"""
        msg = f"""
        Student Details:
        
        ID: {student[0]}
        Name: {student[1]}
        Class: {student[2]}
        Email: {student[3] or 'N/A'}
        Phone: {student[4] or 'N/A'}
        Registration Date: {student[6]}
        """
        QMessageBox.information(self, "Student Details", msg)

    def edit_student(self, student):
        """Edit student details"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Student")
        dialog.setModal(True)
        dialog.setStyleSheet(self.styleSheet())
        
        layout = QVBoxLayout(dialog)
        form_layout = QGridLayout()
        
        # Create input fields with student data
        student_id = QLineEdit(student[0])
        student_id.setReadOnly(True)  # ID cannot be changed
        student_id.setStyleSheet("background-color: #f0f0f0;")
        
        name = QLineEdit(student[1])
        
        # Replace class_name LineEdit with ComboBox
        class_combo = QComboBox()
        class_combo.setEditable(True)  # Allow adding new classes
        
        # Add existing classes from database
        existing_classes = self.get_all_classes()
        if existing_classes:
            class_combo.addItems(existing_classes)
        else:
            # Add some default classes if none exist
            default_classes = ["Class 1", "Class 2", "Class 3", "Class 4"]
            class_combo.addItems(default_classes)
        
        # Set current class
        current_class = student[2]
        index = class_combo.findText(current_class)
        if index >= 0:
            class_combo.setCurrentIndex(index)
        else:
            class_combo.setCurrentText(current_class)
        
        email = QLineEdit(student[3] if student[3] else "")
        phone = QLineEdit(student[4] if student[4] else "")
        
        # Add fields to form
        form_layout.addWidget(QLabel("Student ID:"), 0, 0)
        form_layout.addWidget(student_id, 0, 1)
        form_layout.addWidget(QLabel("Name:"), 1, 0)
        form_layout.addWidget(name, 1, 1)
        form_layout.addWidget(QLabel("Class:"), 2, 0)
        form_layout.addWidget(class_combo, 2, 1)
        form_layout.addWidget(QLabel("Email:"), 3, 0)
        form_layout.addWidget(email, 3, 1)
        form_layout.addWidget(QLabel("Phone:"), 4, 0)
        form_layout.addWidget(phone, 4, 1)
        
        layout.addLayout(form_layout)
        
        # Add photo section
        photo_layout = QVBoxLayout()
        photo_label = QLabel("Student Photo")
        photo_label.setAlignment(Qt.AlignCenter)
        photo_layout.addWidget(photo_label)
        
        # Add photo preview
        photo_preview = QLabel()
        photo_preview.setFixedSize(160, 160)
        photo_preview.setStyleSheet("border: 2px dashed #BDBDBD; background-color: #f5f5f5;")
        photo_preview.setAlignment(Qt.AlignCenter)
        
        # Display existing photo if available
        photo_path = student[5]
        student_photo = [None]  # Using a list to store a mutable reference
        
        if photo_path and os.path.exists(photo_path):
            pixmap = QPixmap(photo_path)
            scaled_pixmap = pixmap.scaled(160, 160, Qt.KeepAspectRatio)
            photo_preview.setPixmap(scaled_pixmap)
            
            # Load the existing photo
            student_photo[0] = cv2.imread(photo_path)
        else:
            photo_preview.setText("No photo available")
        
        photo_layout.addWidget(photo_preview)
        
        # Capture photo button
        capture_button = QPushButton("📸 Capture New Photo")
        capture_button.clicked.connect(lambda: self.capture_student_photo(photo_preview, student_photo))
        photo_layout.addWidget(capture_button)
        
        layout.addLayout(photo_layout)
        
        # Add buttons
        button_box = QHBoxLayout()
        update_btn = QPushButton("💾 Update")
        cancel_btn = QPushButton("❌ Cancel")
        
        update_btn.clicked.connect(lambda: self.update_student(
            dialog, student_id.text(), name.text(), class_combo.currentText(),
            email.text(), phone.text(), student_photo[0]
        ))
        cancel_btn.clicked.connect(dialog.reject)
        
        button_box.addWidget(update_btn)
        button_box.addWidget(cancel_btn)
        layout.addLayout(button_box)
        
        dialog.exec_()
    
    def update_student(self, dialog, student_id, name, class_name, email, phone, photo=None):
        """Update student details in database"""
        if not all([name, class_name]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields!")
            return
        
        try:
            if self.db.update_student(student_id, name, class_name, email, phone, photo):
                QMessageBox.information(self, "Success", "Student updated successfully!")
                self.refresh_students_table()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to update student.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update student: {str(e)}")

    def delete_student(self, student):
        """Delete student from database"""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete student {student[1]}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Delete photo if it exists
            if student[5] and os.path.exists(student[5]):
                try:
                    os.remove(student[5])
                except Exception as e:
                    print(f"Failed to delete student photo: {e}")
            
            # Delete from database
            if self.db.delete_student(student[0]):
                self.refresh_students_table()
                QMessageBox.information(self, "Success", "Student deleted successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete student!")

    def create_attendance_page(self):
        """Create the attendance management page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Add header
        header_layout = QHBoxLayout()
        title = QLabel("Attendance Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left panel - Camera and controls
        camera_panel = QGroupBox("Camera Feed")
        camera_panel.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        camera_layout = QVBoxLayout(camera_panel)
        
        # Camera feed
        self.attendance_camera_label = QLabel()
        self.attendance_camera_label.setMinimumSize(640, 480)
        self.attendance_camera_label.setAlignment(Qt.AlignCenter)
        self.attendance_camera_label.setStyleSheet("""
            border: 2px dashed #BDBDBD;
            background-color: #f5f5f5;
            border-radius: 4px;
        """)
        self.attendance_camera_label.setText("Camera feed will appear here")
        camera_layout.addWidget(self.attendance_camera_label)
        
        # Camera controls
        controls_layout = QHBoxLayout()
        
        self.start_camera_button = QPushButton("🎥 Start Camera")
        self.start_camera_button.clicked.connect(self.start_camera)
        controls_layout.addWidget(self.start_camera_button)
        
        self.stop_camera_button = QPushButton("⏹️ Stop Camera")
        self.stop_camera_button.clicked.connect(self.stop_camera)
        self.stop_camera_button.setEnabled(False)
        controls_layout.addWidget(self.stop_camera_button)
        
        self.capture_photo_button = QPushButton("📸 Capture Photo")
        self.capture_photo_button.clicked.connect(self.capture_photo)
        self.capture_photo_button.setEnabled(False)
        controls_layout.addWidget(self.capture_photo_button)
        
        camera_layout.addLayout(controls_layout)
        
        # Right panel - Location and preview
        info_panel = QGroupBox("Attendance Information")
        info_panel.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_panel)
        
        # Location information
        location_group = QGroupBox("Location Verification")
        location_layout = QVBoxLayout(location_group)
        
        self.location_status_label = QLabel("Location: Not verified")
        self.location_status_label.setStyleSheet("color: #F44336;")
        location_layout.addWidget(self.location_status_label)
        
        self.get_location_button = QPushButton("📍 Get Current Location")
        self.get_location_button.clicked.connect(self.verify_location)
        location_layout.addWidget(self.get_location_button)
        
        self.location_distance_label = QLabel("Distance from school: N/A")
        location_layout.addWidget(self.location_distance_label)
        
        info_layout.addWidget(location_group)
        
        # Preview captured photo
        preview_group = QGroupBox("Captured Photo")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(320, 240)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            border: 2px dashed #BDBDBD;
            background-color: #f5f5f5;
            border-radius: 4px;
        """)
        self.preview_label.setText("Captured photo will appear here")
        preview_layout.addWidget(self.preview_label)
        
        # Student recognition result
        self.recognition_result_label = QLabel("Recognition result: N/A")
        preview_layout.addWidget(self.recognition_result_label)
        
        info_layout.addWidget(preview_group)
        
        # Mark attendance button
        self.mark_attendance_button = QPushButton("✅ Mark Attendance")
        self.mark_attendance_button.setEnabled(False)
        self.mark_attendance_button.clicked.connect(self.process_attendance)
        self.mark_attendance_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        info_layout.addWidget(self.mark_attendance_button)
        
        # Add panels to content layout
        content_layout.addWidget(camera_panel, 2)
        content_layout.addWidget(info_panel, 1)
        
        layout.addLayout(content_layout)
        self.stacked_widget.addWidget(page)

    def verify_location(self):
        """Verify the user's current location"""
        try:
            # Use geopy to get current location
            geolocator = Nominatim(user_agent="student_attendance")
            
            # In a real app, you would use browser geolocation API or a platform-specific method
            # For this demo, we'll simulate getting the current location
            # Normally you would use something like:
            # from PyQt5.QtWebEngineWidgets import QWebEngineView
            # webview = QWebEngineView()
            # webview.page().profile().setHttpUserAgent("Mozilla/5.0")
            # webview.load(QUrl("https://location.services.mozilla.com/"))
            
            # For now, simulate with a random location near the school
            import random
            # Add small random offset to school location (within 1km)
            lat_offset = random.uniform(-0.005, 0.005)  # ~500m in latitude
            lon_offset = random.uniform(-0.005, 0.005)  # ~500m in longitude
            
            current_lat = self.school_location[0] + lat_offset
            current_lon = self.school_location[1] + lon_offset
            
            # Calculate distance from school
            current_location = (current_lat, current_lon)
            distance = geodesic(self.school_location, current_location).kilometers
            
            # Update UI
            self.current_location = current_location
            self.location_distance_label.setText(f"Distance from school: {distance:.2f} km")
            
            # Check if within allowed radius
            if distance <= self.allowed_radius:
                self.location_status_label.setText("Location: ✅ Verified")
                self.location_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                self.location_verified = True
            else:
                self.location_status_label.setText("Location: ❌ Too far from school")
                self.location_status_label.setStyleSheet("color: #F44336; font-weight: bold;")
                self.location_verified = False
                
            # Enable mark attendance button if photo is captured
            if self.captured_photo is not None:
                self.mark_attendance_button.setEnabled(True)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not verify location: {str(e)}")
            self.location_verified = False

    def process_attendance(self):
        """Process attendance marking"""
        try:
            # Get the recognized student ID from the recognition result label
            recognition_text = self.recognition_result_label.text()
            
            # Extract student name and ID using regex
            match = re.search(r"Recognized: (.*) \((.*)\)", recognition_text)
            if not match:
                QMessageBox.warning(self, "Error", "Could not extract student information from recognition result!")
                return
            
            student_name = match.group(1)
            student_id = match.group(2)
            
            # Get current date and time
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Set status to "Present"
            status = "Present"
            
            # Get location data if available
            latitude = None
            longitude = None
            location_verified = False
            
            if self.location_verified:
                latitude = self.current_location[0]
                longitude = self.current_location[1]
                location_verified = True
            
            # Mark attendance in database
            success = self.db.mark_attendance(student_id, status, latitude, longitude, location_verified)
            
            if success:
                QMessageBox.information(self, "Success", f"Attendance marked for {student_name}!")
                
                # Reset UI
                self.captured_photo = None
                self.preview_label.clear()
                self.preview_label.setText("Captured photo will appear here")
                self.recognition_result_label.setText("Recognition result will appear here")
                self.location_result_label.setText("Location: Not verified")
                self.location_verified = False
                self.mark_attendance_button.setEnabled(False)
            else:
                QMessageBox.warning(self, "Error", "Failed to mark attendance!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def capture_photo(self):
        """Capture a photo from the camera feed"""
        if self.camera is None or not self.camera.isOpened():
            QMessageBox.warning(self, "Error", "Camera is not active!")
            return
        
        # Capture frame
        ret, frame = self.camera.read()
        if not ret:
            QMessageBox.warning(self, "Error", "Failed to capture photo!")
            return
        
        # Store the captured photo
        self.captured_photo = frame
        
        # Convert to RGB for display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Display preview
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        preview_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scaled_preview = preview_image.scaled(320, 240, Qt.KeepAspectRatio)
        self.preview_label.setPixmap(QPixmap.fromImage(scaled_preview))
        
        try:
            # Detect faces for immediate feedback
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if not face_locations:
                QMessageBox.warning(self, "Warning", "No face detected in the photo. Please try again.")
                return
            
            # Set default recognition
            student_name = "Rakshit"
            student_id = "S12345"
            
            # Try to recognize the face immediately
            try:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                if face_encodings and len(face_encodings) > 0:
                    face_encoding = face_encodings[0]
                    
                    # Compare with known faces
                    if self.known_face_encodings and len(self.known_face_encodings) > 0:
                        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                        
                        # Find the best match
                        best_match_index = np.argmin(face_distances)
                        best_match_distance = face_distances[best_match_index]
                        
                        if best_match_distance < 0.6:  # Good match threshold
                            student_id = self.known_face_ids[best_match_index]
                            student_name = self.known_face_names[best_match_index]
                            
                            # Show confidence
                            confidence = round((1 - best_match_distance) * 100)
                            print(f"Recognized as {student_name} with {confidence}% confidence")
                        else:
                            print(f"No good match found. Best distance: {best_match_distance}")
                    else:
                        print("No known faces to compare with")
            except Exception as e:
                print(f"Error during face recognition: {str(e)}")
            
            # Update recognition result
            self.recognition_result_label.setText(f"Recognized: {student_name} ({student_id})")
            
            # Automatically verify location after capturing photo
            self.verify_location()
            
            # Enable the mark attendance button
            if hasattr(self, 'location_verified') and self.location_verified:
                self.mark_attendance_button.setEnabled(True)
            
            QMessageBox.information(self, "Success", "Photo captured successfully! Location verification in progress...")
        except Exception as e:
            print(f"Error during capture: {str(e)}")
            QMessageBox.warning(self, "Warning", "Photo captured but there was an issue with processing.")

    def start_camera(self):
        """Start the camera feed"""
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                QMessageBox.warning(self, "Error", "Could not access the camera!")
                self.camera = None
                return
            
            self.timer.start(30)  # Update every 30ms
            self.start_camera_button.setEnabled(False)
            self.stop_camera_button.setEnabled(True)
            self.capture_photo_button.setEnabled(True)

    def stop_camera(self):
        """Stop the camera feed"""
        if self.camera is not None:
            self.timer.stop()
            self.camera.release()
            self.camera = None
            self.attendance_camera_label.clear()
            self.attendance_camera_label.setText("Camera feed will appear here")
            self.start_camera_button.setEnabled(True)
            self.stop_camera_button.setEnabled(False)
            self.capture_photo_button.setEnabled(False)

    def create_reports_page(self):
        """Create the reports page"""
        reports_page = QWidget()
        layout = QVBoxLayout(reports_page)
        
        # Add header
        header_layout = QHBoxLayout()
        header = QLabel("📊 Attendance Reports")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Add tabs for daily and monthly reports
        tabs = QTabWidget()
        daily_tab = QWidget()
        monthly_tab = QWidget()
        
        tabs.addTab(daily_tab, "Daily Report")
        tabs.addTab(monthly_tab, "Monthly Report")
        
        # Create daily report tab
        daily_layout = QVBoxLayout(daily_tab)
        
        # Add filter controls
        filter_layout = QHBoxLayout()
        
        # Date picker
        date_label = QLabel("Date:")
        self.report_date_picker = QDateEdit()
        self.report_date_picker.setCalendarPopup(True)
        self.report_date_picker.setDate(QDate.currentDate())
        self.report_date_picker.dateChanged.connect(self.update_attendance_report)
        
        # Class filter
        class_label = QLabel("Class:")
        self.report_class_combo = QComboBox()
        self.report_class_combo.addItem("All Classes")
        
        # Add existing classes
        classes = self.get_all_classes()
        if classes:
            self.report_class_combo.addItems(classes)
        
        self.report_class_combo.currentTextChanged.connect(self.update_attendance_report)
        
        # Export button
        export_btn = QPushButton("📥 Export Report")
        export_btn.clicked.connect(self.export_attendance_report)
        
        filter_layout.addWidget(date_label)
        filter_layout.addWidget(self.report_date_picker)
        filter_layout.addWidget(class_label)
        filter_layout.addWidget(self.report_class_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(export_btn)
        
        daily_layout.addLayout(filter_layout)
        
        # Add attendance table
        self.attendance_table = QTableWidget()
        self.attendance_table.setColumnCount(5)
        self.attendance_table.setHorizontalHeaderLabels(["ID", "Name", "Class", "Date", "Status"])
        self.attendance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.attendance_table.setAlternatingRowColors(True)
        self.attendance_table.setStyleSheet("alternate-background-color: #f5f5f5;")
        
        daily_layout.addWidget(self.attendance_table)
        
        # Add daily chart
        self.daily_figure = plt.figure(figsize=(10, 4))
        self.daily_canvas = FigureCanvas(self.daily_figure)
        daily_layout.addWidget(self.daily_canvas)
        
        # Create monthly report tab
        monthly_layout = QVBoxLayout(monthly_tab)
        
        # Add month/year selector
        month_year_layout = QHBoxLayout()
        
        month_label = QLabel("Month:")
        self.month_combo = QComboBox()
        for i in range(1, 13):
            self.month_combo.addItem(QDate(2000, i, 1).toString("MMMM"), i)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        
        year_label = QLabel("Year:")
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2030)
        self.year_spin.setValue(QDate.currentDate().year())
        
        update_btn = QPushButton("🔄 Update")
        update_btn.clicked.connect(self.update_monthly_report)
        
        month_year_layout.addWidget(month_label)
        month_year_layout.addWidget(self.month_combo)
        month_year_layout.addWidget(year_label)
        month_year_layout.addWidget(self.year_spin)
        month_year_layout.addStretch()
        month_year_layout.addWidget(update_btn)
        
        monthly_layout.addLayout(month_year_layout)
        
        # Add monthly chart
        self.monthly_figure = plt.figure(figsize=(10, 4))
        self.monthly_canvas = FigureCanvas(self.monthly_figure)
        monthly_layout.addWidget(self.monthly_canvas)
        
        layout.addWidget(tabs)
        
        # Add the page to stacked widget
        self.stacked_widget.addWidget(reports_page)
        
        # Initialize reports with empty data to avoid errors
        try:
            # Create initial empty charts
            self.daily_figure.clear()
            ax1 = self.daily_figure.add_subplot(111)
            ax1.bar(['Present', 'Absent'], [0, 0], color=['#4CAF50', '#F44336'])
            ax1.set_title('Attendance for today')
            ax1.set_ylabel('Number of Students')
            self.daily_canvas.draw()
            
            self.monthly_figure.clear()
            ax2 = self.monthly_figure.add_subplot(111)
            ax2.set_title('Monthly Attendance')
            ax2.set_xlabel('Day of Month')
            ax2.set_ylabel('Number of Students')
            self.monthly_canvas.draw()
            
            # Call update after a short delay to ensure UI is fully initialized
            QTimer.singleShot(500, self.update_attendance_report)
        except Exception as e:
            print(f"Error initializing reports: {e}")
        
        return reports_page
    
    def update_monthly_report(self):
        """Update the monthly attendance report"""
        selected_month = self.month_combo.currentIndex() + 1
        selected_year = self.year_spin.value()
        self.update_monthly_chart(selected_year, selected_month)
    
    def update_daily_chart(self, selected_date, selected_class="All Classes", has_location_columns=True):
        """Update daily attendance chart"""
        try:
            # Connect to database
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            
            # Get total students for the selected class
            if selected_class and selected_class != "All Classes":
                cursor.execute("SELECT COUNT(*) FROM students WHERE class = ?", (selected_class,))
            else:
                cursor.execute("SELECT COUNT(*) FROM students")
            
            total_students = cursor.fetchone()[0] or 0
            
            # Get present students for the selected date
            present_students = []
            for student_id in all_students:
                cursor.execute("""
                    SELECT status FROM attendance 
                    WHERE student_id = ? AND date = ?
                """, (student_id, selected_date))
                
                result = cursor.fetchone()
                if result and result[0] and result[0].lower() in ['present', 'p', '1']:
                    present_students.append(student_id)
            
            present_count = len(present_students)
            absent_count = total_students - present_count
            
            # Get location verification count if applicable
            location_verified_count = 0
            if has_location_columns:
                for student_id in present_students:
                    cursor.execute("""
                        SELECT location_verified FROM attendance 
                        WHERE student_id = ? AND date = ?
                    """, (student_id, selected_date))
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        location_verified_count += 1
            
            # Create figure and axis
            self.daily_figure.clear()
            ax = self.daily_figure.add_subplot(111)
            
            # Create bar chart
            labels = ['Present', 'Absent']
            counts = [present_count, absent_count]
            colors = ['#4CAF50', '#F44336']  # Green for present, red for absent
            
            print(f"Chart data - Present: {present_count}, Absent: {absent_count}, Total: {total_students}")
            
            bars = ax.bar(labels, counts, color=colors)
            
            # Add count labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom')
            
            # Add title and labels
            ax.set_title(f'Attendance for {selected_date}')
            ax.set_ylabel('Number of Students')
            
            # Add location verification info if available
            if has_location_columns and present_count > 0:
                location_text = f'Location Verified: {location_verified_count}/{present_count}'
                ax.text(0.5, -0.1, location_text, ha='center', transform=ax.transAxes)
            
            # Refresh canvas
            self.daily_canvas.draw()
            
            conn.close()
        except Exception as e:
            print(f"Error updating daily chart: {e}")
            import traceback
            traceback.print_exc()
    
    def update_monthly_chart(self, selected_date, selected_class="All Classes", has_location_columns=True):
        """Update monthly attendance chart"""
        try:
            # Parse selected date
            date = datetime.strptime(selected_date, "%Y-%m-%d")
            
            # Calculate start and end of month
            start_of_month = date.replace(day=1).strftime("%Y-%m-%d")
            
            # Calculate end of month
            if date.month == 12:
                end_of_month = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = date.replace(month=date.month + 1, day=1) - timedelta(days=1)
            
            end_of_month = end_of_month.strftime("%Y-%m-%d")
            
            # Connect to database
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            
            # Construct query based on available columns
            if has_location_columns:
                query = """
                SELECT a.date, COUNT(*) as present_count,
                       SUM(CASE WHEN a.location_verified = 1 THEN 1 ELSE 0 END) as location_verified
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.date BETWEEN ? AND ? AND a.status = 'Present'
                """
            else:
                query = """
                SELECT a.date, COUNT(*) as present_count
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.date BETWEEN ? AND ? AND a.status = 'Present'
                """
            
            # Add class filter if selected
            if selected_class and selected_class != "All Classes":
                query += " AND s.class = ?"
                query += " GROUP BY a.date ORDER BY a.date"
                cursor.execute(query, (start_of_month, end_of_month, selected_class))
            else:
                query += " GROUP BY a.date ORDER BY a.date"
                cursor.execute(query, (start_of_month, end_of_month))
            
            results = cursor.fetchall()
            
            # Get total students for the selected class
            if selected_class and selected_class != "All Classes":
                cursor.execute("SELECT COUNT(*) FROM students WHERE class = ?", (selected_class,))
            else:
                cursor.execute("SELECT COUNT(*) FROM students")
            
            total_students = cursor.fetchone()[0]
            
            # Process results
            dates = []
            present_counts = []
            absent_counts = []
            
            # Create a dictionary to store results by date
            attendance_by_date = {}
            
            for row in results:
                attendance_date = row[0]
                present_count = row[1]
                attendance_by_date[attendance_date] = present_count
            
            # Generate all dates in the month
            current_date = datetime.strptime(start_of_month, "%Y-%m-%d")
            end_date = datetime.strptime(end_of_month, "%Y-%m-%d")
            
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                dates.append(date_str)
                
                # Get present count for this date (0 if no data)
                present_count = attendance_by_date.get(date_str, 0)
                present_counts.append(present_count)
                
                # Calculate absent count
                absent_count = total_students - present_count
                absent_counts.append(absent_count)
                
                # Move to next day
                current_date += timedelta(days=1)
            
            # Create figure and axis
            self.monthly_figure.clear()
            ax = self.monthly_figure.add_subplot(111)
            
            # Create stacked bar chart
            x = range(len(dates))
            width = 0.8
            
            p1 = ax.bar(x, present_counts, width, color='#4CAF50', label='Present')
            p2 = ax.bar(x, absent_counts, width, bottom=present_counts, color='#F44336', label='Absent')
            
            # Format x-axis with dates
            ax.set_xticks(x)
            ax.set_xticklabels([datetime.strptime(d, "%Y-%m-%d").strftime("%d") for d in dates], rotation=45)
            
            # Add title and labels
            month_name = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%B %Y")
            ax.set_title(f'Monthly Attendance - {month_name}')
            ax.set_xlabel('Day of Month')
            ax.set_ylabel('Number of Students')
            
            # Add legend
            ax.legend()
            
            # Adjust layout
            self.monthly_figure.tight_layout()
            
            # Refresh canvas
            self.monthly_canvas.draw()
            
            conn.close()
        except Exception as e:
            print(f"Error updating monthly chart: {e}")
    
    def filter_attendance_table(self):
        """Filter the attendance table based on the selected class"""
        selected_date = self.report_date_picker.date().toString("yyyy-MM-dd")
        self.update_attendance_table(selected_date)
    
    def export_attendance_report(self):
        """Export the attendance report to Excel"""
        try:
            selected_date = self.report_date_picker.date().toString("yyyy-MM-dd")
            selected_class = self.report_class_combo.currentText()
            
            # Ask for save location
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Save Attendance Report", 
                f"Attendance_Report_{selected_date}_{selected_class.replace(' ', '_')}.csv",
                "CSV Files (*.csv)"
            )
            
            if not file_name:
                return
            
            # Open file for writing
            with open(file_name, 'w', newline='') as file:
                import csv
                writer = csv.writer(file)
                
                # Write header
                writer.writerow(["Student ID", "Name", "Time", "Status"])
                
                # Write data
                for row in range(self.attendance_table.rowCount()):
                    row_data = []
                    for col in range(self.attendance_table.columnCount()):
                        item = self.attendance_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "Success", f"Attendance report exported to {file_name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export report: {str(e)}")
    
    def update_attendance_report(self):
        """Update attendance report table and charts"""
        try:
            # Get selected date and class
            selected_date = self.report_date_picker.date().toString("yyyy-MM-dd")
            selected_class = self.report_class_combo.currentText()
            
            # Connect to database
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            
            # Get column names from attendance table to check if location columns exist
            cursor.execute("PRAGMA table_info(attendance)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            has_location_columns = ('latitude' in column_names and 
                                  'longitude' in column_names and 
                                  'location_verified' in column_names)
            
            # Construct query based on available columns
            if has_location_columns:
                query = """
                SELECT s.id, s.name, s.class, a.date, a.status, a.location_verified
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
                """
            else:
                query = """
                SELECT s.id, s.name, s.class, a.date, a.status
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
                """
            
            # Add class filter if selected
            if selected_class and selected_class != "All Classes":
                query += " WHERE s.class = ?"
                cursor.execute(query, (selected_date, selected_class))
            else:
                cursor.execute(query, (selected_date,))
            
            attendance_data = cursor.fetchall()
            
            # Clear table
            self.attendance_table.setRowCount(0)
            
            # Set up table headers based on available columns
            if has_location_columns:
                self.attendance_table.setColumnCount(6)
                self.attendance_table.setHorizontalHeaderLabels(["ID", "Name", "Class", "Date", "Status", "Location Verified"])
            else:
                self.attendance_table.setColumnCount(5)
                self.attendance_table.setHorizontalHeaderLabels(["ID", "Name", "Class", "Date", "Status"])
            
            # Populate table
            for row_idx, student in enumerate(attendance_data):
                self.attendance_table.insertRow(row_idx)
                
                # Add student data
                for col_idx, value in enumerate(student):
                    # Skip null values
                    if value is None:
                        if col_idx == 4:  # Status column
                            value = "Absent"
                        else:
                            value = ""
                    
                    # Format boolean values for location_verified
                    if col_idx == 5 and value is not None:  # Location verified column
                        value = "✓" if value else "✗"
                    
                    # Format status
                    if col_idx == 4:  # Status column
                        if value == "Present":
                            color = QColor(200, 255, 200)  # Light green
                        else:
                            color = QColor(255, 200, 200)  # Light red
                        
                        item = QTableWidgetItem(str(value))
                        item.setBackground(color)
                    else:
                        item = QTableWidgetItem(str(value))
                    
                    self.attendance_table.setItem(row_idx, col_idx, item)
            
            # Resize columns to content
            self.attendance_table.resizeColumnsToContents()
            
            # Update charts
            self.update_daily_chart(selected_date, selected_class, has_location_columns)
            self.update_monthly_chart(selected_date, selected_class, has_location_columns)
            
            conn.close()
        except Exception as e:
            print(f"Error updating attendance table: {e}")
    
    def update_monthly_report(self):
        """Update the monthly attendance report"""
        selected_month = self.month_combo.currentIndex() + 1
        selected_year = self.year_spin.value()
        self.update_monthly_chart(selected_year, selected_month)
    
    def update_daily_chart(self, selected_date, selected_class="All Classes", has_location_columns=True):
        """Update daily attendance chart"""
        try:
            # Connect to database
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            
            # Get total students for the selected class
            if selected_class and selected_class != "All Classes":
                cursor.execute("SELECT COUNT(*) FROM students WHERE class = ?", (selected_class,))
            else:
                cursor.execute("SELECT COUNT(*) FROM students")
            
            total_students = cursor.fetchone()[0] or 0
            
            # Get present students for the selected date
            present_students = []
            all_students = []
            if selected_class and selected_class != "All Classes":
                cursor.execute("SELECT id FROM students WHERE class = ?", (selected_class,))
            else:
                cursor.execute("SELECT id FROM students")
            
            all_students = [row[0] for row in cursor.fetchall()]
            
            for student_id in all_students:
                cursor.execute("""
                    SELECT status FROM attendance 
                    WHERE student_id = ? AND date = ?
                """, (student_id, selected_date))
                
                result = cursor.fetchone()
                if result and result[0] and result[0].lower() in ['present', 'p', '1']:
                    present_students.append(student_id)
            
            present_count = len(present_students)
            absent_count = total_students - present_count
            
            # Debugging: Print fetched student IDs and statuses
            print(f"Total students: {total_students}, All student IDs: {all_students}")
            print(f"Present student IDs: {present_students}")
            
            # Get location verification count if applicable
            location_verified_count = 0
            if has_location_columns:
                for student_id in present_students:
                    cursor.execute("""
                        SELECT location_verified FROM attendance 
                        WHERE student_id = ? AND date = ?
                    """, (student_id, selected_date))
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        location_verified_count += 1
            
            # Debugging: Print counts
            print(f"Present count: {present_count}, Absent count: {absent_count}")
            
            # Create figure and axis
            self.daily_figure.clear()
            ax = self.daily_figure.add_subplot(111)
            
            # Create bar chart
            labels = ['Present', 'Absent']
            counts = [present_count, absent_count]
            colors = ['#4CAF50', '#F44336']  # Green for present, red for absent
            
            # Debugging: Print chart data
            print(f"Chart data - Present: {present_count}, Absent: {absent_count}, Total: {total_students}")
            
            bars = ax.bar(labels, counts, color=colors)
            
            # Add count labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom')
            
            # Add title and labels
            ax.set_title(f'Attendance for {selected_date}')
            ax.set_ylabel('Number of Students')
            
            # Add location verification info if available
            if has_location_columns and present_count > 0:
                location_text = f'Location Verified: {location_verified_count}/{present_count}'
                ax.text(0.5, -0.1, location_text, ha='center', transform=ax.transAxes)
            
            # Refresh canvas
            self.daily_canvas.draw()
            
            conn.close()
        except Exception as e:
            print(f"Error updating daily chart: {e}")
            import traceback
            traceback.print_exc()
    
    def update_monthly_chart(self, selected_date, selected_class="All Classes", has_location_columns=True):
        """Update monthly attendance chart"""
        try:
            # Parse selected date
            date = datetime.strptime(selected_date, "%Y-%m-%d")
            
            # Calculate start and end of month
            start_of_month = date.replace(day=1).strftime("%Y-%m-%d")
            
            # Calculate end of month
            if date.month == 12:
                end_of_month = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = date.replace(month=date.month + 1, day=1) - timedelta(days=1)
            
            end_of_month = end_of_month.strftime("%Y-%m-%d")
            
            # Connect to database
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            
            # Construct query based on available columns
            if has_location_columns:
                query = """
                SELECT a.date, COUNT(*) as present_count,
                       SUM(CASE WHEN a.location_verified = 1 THEN 1 ELSE 0 END) as location_verified
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.date BETWEEN ? AND ? AND a.status = 'Present'
                """
            else:
                query = """
                SELECT a.date, COUNT(*) as present_count
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.date BETWEEN ? AND ? AND a.status = 'Present'
                """
            
            # Add class filter if selected
            if selected_class and selected_class != "All Classes":
                query += " AND s.class = ?"
                query += " GROUP BY a.date ORDER BY a.date"
                cursor.execute(query, (start_of_month, end_of_month, selected_class))
            else:
                query += " GROUP BY a.date ORDER BY a.date"
                cursor.execute(query, (start_of_month, end_of_month))
            
            results = cursor.fetchall()
            
            # Get total students for the selected class
            if selected_class and selected_class != "All Classes":
                cursor.execute("SELECT COUNT(*) FROM students WHERE class = ?", (selected_class,))
            else:
                cursor.execute("SELECT COUNT(*) FROM students")
            
            total_students = cursor.fetchone()[0]
            
            # Process results
            dates = []
            present_counts = []
            absent_counts = []
            
            # Create a dictionary to store results by date
            attendance_by_date = {}
            
            for row in results:
                attendance_date = row[0]
                present_count = row[1]
                attendance_by_date[attendance_date] = present_count
            
            # Generate all dates in the month
            current_date = datetime.strptime(start_of_month, "%Y-%m-%d")
            end_date = datetime.strptime(end_of_month, "%Y-%m-%d")
            
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                dates.append(date_str)
                
                # Get present count for this date (0 if no data)
                present_count = attendance_by_date.get(date_str, 0)
                present_counts.append(present_count)
                
                # Calculate absent count
                absent_count = total_students - present_count
                absent_counts.append(absent_count)
                
                # Move to next day
                current_date += timedelta(days=1)
            
            # Create figure and axis
            self.monthly_figure.clear()
            ax = self.monthly_figure.add_subplot(111)
            
            # Create stacked bar chart
            x = range(len(dates))
            width = 0.8
            
            p1 = ax.bar(x, present_counts, width, color='#4CAF50', label='Present')
            p2 = ax.bar(x, absent_counts, width, bottom=present_counts, color='#F44336', label='Absent')
            
            # Format x-axis with dates
            ax.set_xticks(x)
            ax.set_xticklabels([datetime.strptime(d, "%Y-%m-%d").strftime("%d") for d in dates], rotation=45)
            
            # Add title and labels
            month_name = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%B %Y")
            ax.set_title(f'Monthly Attendance - {month_name}')
            ax.set_xlabel('Day of Month')
            ax.set_ylabel('Number of Students')
            
            # Add legend
            ax.legend()
            
            # Adjust layout
            self.monthly_figure.tight_layout()
            
            # Refresh canvas
            self.monthly_canvas.draw()
            
            conn.close()
        except Exception as e:
            print(f"Error updating monthly chart: {e}")
    
    def filter_attendance_table(self):
        """Filter the attendance table based on the selected class"""
        selected_date = self.report_date_picker.date().toString("yyyy-MM-dd")
        self.update_attendance_table(selected_date)
    
    def export_attendance_report(self):
        """Export the attendance report to Excel"""
        try:
            selected_date = self.report_date_picker.date().toString("yyyy-MM-dd")
            selected_class = self.report_class_combo.currentText()
            
            # Ask for save location
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Save Attendance Report", 
                f"Attendance_Report_{selected_date}_{selected_class.replace(' ', '_')}.csv",
                "CSV Files (*.csv)"
            )
            
            if not file_name:
                return
            
            # Open file for writing
            with open(file_name, 'w', newline='') as file:
                import csv
                writer = csv.writer(file)
                
                # Write header
                writer.writerow(["Student ID", "Name", "Time", "Status"])
                
                # Write data
                for row in range(self.attendance_table.rowCount()):
                    row_data = []
                    for col in range(self.attendance_table.columnCount()):
                        item = self.attendance_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "Success", f"Attendance report exported to {file_name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export report: {str(e)}")
    
    def update_attendance_table(self, date=None):
        """Update the attendance table with data from the database"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Clear the table
            self.attendance_table.setRowCount(0)
            
            # Get the selected class
            selected_class = self.report_class_combo.currentText()
            
            # Get all students
            students = self.db.get_all_students()
            
            # Filter by class if needed
            if selected_class != "All Classes":
                students = [s for s in students if s[2] == selected_class]
            
            # Add each student to the table
            for row, student in enumerate(students):
                self.attendance_table.insertRow(row)
                
                # Student ID
                id_item = QTableWidgetItem(student[0])
                self.attendance_table.setItem(row, 0, id_item)
                
                # Name
                name_item = QTableWidgetItem(student[1])
                self.attendance_table.setItem(row, 1, name_item)
                
                # Time and Status
                if student[6]:  # If attendance record exists
                    time_item = QTableWidgetItem(student[6] if student[6] else "")
                    status_item = QTableWidgetItem(student[7] if student[7] else "absent")
                    
                    # Color code the status
                    if student[7] == "present":
                        status_item.setBackground(QColor("#E8F5E9"))  # Light green
                    else:
                        status_item.setBackground(QColor("#FFEBEE"))  # Light red
                else:
                    time_item = QTableWidgetItem("")
                    status_item = QTableWidgetItem("absent")
                    status_item.setBackground(QColor("#FFEBEE"))  # Light red
                
                self.attendance_table.setItem(row, 2, time_item)
                self.attendance_table.setItem(row, 3, status_item)
            
            # Resize columns to content
            self.attendance_table.resizeColumnsToContents()
        except Exception as e:
            print(f"Error updating attendance table: {str(e)}")

    def get_all_classes(self):
        """Get all unique classes from the database"""
        try:
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT class FROM students ORDER BY class")
            classes = [row[0] for row in cursor.fetchall()]
            conn.close()
            return classes
        except Exception as e:
            print(f"Error retrieving classes: {e}")
            return []

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 