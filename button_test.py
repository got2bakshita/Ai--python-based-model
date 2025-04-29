import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

class CircularButtonDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circular Button Demo")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Class", "Email", "Phone", "Actions"])
        
        # Important: Set row height for header
        self.table.horizontalHeader().setFixedHeight(100)
        
        # Style the table
        self.table.setStyleSheet("""
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
            QTableWidget {
                border: none;
                gridline-color: #E0E0E0;
            }
        """)
        
        # Add some sample data
        self.table.setRowCount(5)
        for row in range(5):
            for col in range(5):
                self.table.setItem(row, col, QTableWidgetItem(f"Item {row},{col}"))
            
            # Add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(10, 10, 10, 10)
            actions_layout.setSpacing(10)
            
            # Create circular buttons
            view_btn = self.create_circular_button("👁️", "#2196F3")
            edit_btn = self.create_circular_button("✏️", "#FF9800")
            delete_btn = self.create_circular_button("❌", "#F44336")
            
            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch()
            
            self.table.setCellWidget(row, 5, actions_widget)
        
        # Create custom header widget for Actions column
        header = self.table.horizontalHeader()
        
        # Set the Actions column wider
        self.table.setColumnWidth(5, 200)
        
        # Add the table to the main layout
        main_layout.addWidget(self.table)
        
        # Add header buttons demo
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create label
        header_label = QLabel("Actions Header Example")
        header_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(header_label)
        
        # Create circular buttons for the header
        view_btn = self.create_circular_button("👁️", "#2196F3")
        edit_btn = self.create_circular_button("✏️", "#FF9800")
        delete_btn = self.create_circular_button("❌", "#F44336")
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addWidget(view_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        
        header_layout.addLayout(button_layout)
        header_layout.addStretch()
        
        main_layout.addWidget(header_widget)
    
    def create_circular_button(self, text, color):
        """Create a circular button with the given text and color"""
        button = QPushButton(text)
        button.setFixedSize(40, 40)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 20px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {color};
                border: 2px solid white;
            }}
        """)
        return button

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CircularButtonDemo()
    window.show()
    sys.exit(app.exec_())
