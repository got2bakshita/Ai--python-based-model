from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt
import sqlite3
import hashlib

class LoginDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Login")
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 14px;
                color: #333333;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("Welcome to Student Attendance System")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1a237e;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Please login to continue")
        subtitle.setStyleSheet("color: #666666;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)

        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        # Role selection
        role_layout = QHBoxLayout()
        role_label = QLabel("Role:")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Teacher", "Student"])
        role_layout.addWidget(role_label)
        role_layout.addWidget(self.role_combo)
        layout.addLayout(role_layout)

        # Buttons
        button_layout = QHBoxLayout()
        login_button = QPushButton("Login")
        login_button.clicked.connect(self.login)
        signup_button = QPushButton("Sign Up")
        signup_button.clicked.connect(self.show_signup)
        button_layout.addWidget(login_button)
        button_layout.addWidget(signup_button)
        layout.addLayout(button_layout)

    def login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combo.currentText().lower()

        if not email or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields!")
            return

        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Check credentials
        if self.db.verify_user(email, hashed_password, role):
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid email or password!")

    def show_signup(self):
        dialog = SignupDialog(self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            self.email_input.setText(dialog.email_input.text())
            self.password_input.setText(dialog.password_input.text())
            self.role_combo.setCurrentText(dialog.role_combo.currentText())

class SignupDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Sign Up")
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 14px;
                color: #333333;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("Create New Account")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1a237e;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your full name")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)

        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        # Confirm Password
        confirm_layout = QHBoxLayout()
        confirm_label = QLabel("Confirm:")
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        confirm_layout.addWidget(confirm_label)
        confirm_layout.addWidget(self.confirm_input)
        layout.addLayout(confirm_layout)

        # Role selection
        role_layout = QHBoxLayout()
        role_label = QLabel("Role:")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Teacher", "Student"])
        role_layout.addWidget(role_label)
        role_layout.addWidget(self.role_combo)
        layout.addLayout(role_layout)

        # Institution
        institution_layout = QHBoxLayout()
        institution_label = QLabel("Institution:")
        self.institution_input = QLineEdit()
        self.institution_input.setPlaceholderText("Enter your institution name")
        institution_layout.addWidget(institution_label)
        institution_layout.addWidget(self.institution_input)
        layout.addLayout(institution_layout)

        # Buttons
        button_layout = QHBoxLayout()
        signup_button = QPushButton("Sign Up")
        signup_button.clicked.connect(self.signup)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(signup_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def signup(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        confirm = self.confirm_input.text().strip()
        role = self.role_combo.currentText().lower()
        institution = self.institution_input.text().strip()

        if not all([name, email, password, confirm, institution]):
            QMessageBox.warning(self, "Error", "Please fill in all fields!")
            return

        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match!")
            return

        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Add user to database
        if self.db.add_user(name, email, hashed_password, role, institution):
            QMessageBox.information(self, "Success", "Account created successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Email already exists!") 