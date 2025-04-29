import sys
import cv2
import numpy as np
import os
from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                           QMessageBox, QTableWidget, QTableWidgetItem, QInputDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

class AttendanceSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Student Attendance System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize variables
        self.attendance_data = []
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Create left panel for camera and controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Camera display
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.camera_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.start_camera)
        self.stop_button = QPushButton("Stop Camera")
        self.stop_button.clicked.connect(self.stop_camera)
        self.stop_button.setEnabled(False)
        self.mark_attendance_button = QPushButton("Mark Attendance")
        self.mark_attendance_button.clicked.connect(self.mark_attendance)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.mark_attendance_button)
        left_layout.addLayout(button_layout)
        
        # Create right panel for attendance table
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Attendance table
        self.attendance_table = QTableWidget()
        self.attendance_table.setColumnCount(3)
        self.attendance_table.setHorizontalHeaderLabels(["Name", "Time", "Date"])
        right_layout.addWidget(self.attendance_table)
        
        # Export button
        self.export_button = QPushButton("Export Attendance")
        self.export_button.clicked.connect(self.export_attendance)
        right_layout.addWidget(self.export_button)
        
        # Add panels to main layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
    
    def start_camera(self):
        # Try different camera indices
        for camera_index in [0, 1]:
            self.camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # Add CAP_DSHOW for Windows
            if self.camera.isOpened():
                # Set camera properties for better performance
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                
                self.timer.start(30)
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                return
                
        # If we get here, no camera was successfully opened
        QMessageBox.critical(self, "Error", "Could not open any camera! Please check if your camera is connected and not in use by another application.")
        self.camera = None
    
    def stop_camera(self):
        self.timer.stop()
        if self.camera is not None:
            self.camera.release()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def update_frame(self):
        if self.camera is None or not self.camera.isOpened():
            self.stop_camera()
            return
            
        try:
            ret, frame = self.camera.read()
            if ret:
                # Convert frame to RGB for display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert frame to QImage and display
                height, width, channel = rgb_frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                self.camera_label.setPixmap(QPixmap.fromImage(q_image))
            else:
                self.stop_camera()
                QMessageBox.critical(self, "Error", "Failed to grab frame from camera!")
        except Exception as e:
            self.stop_camera()
            QMessageBox.critical(self, "Error", f"Camera error: {str(e)}")
    
    def mark_attendance(self):
        name, ok = QInputDialog.getText(self, "Mark Attendance", "Enter student name:")
        if ok and name:
            now = datetime.now()
            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H:%M:%S")
            
            # Check if attendance already marked for today
            for entry in self.attendance_data:
                if entry["name"] == name and entry["date"] == date:
                    QMessageBox.warning(self, "Warning", f"Attendance already marked for {name} today!")
                    return
            
            # Add new attendance entry
            self.attendance_data.append({
                "name": name,
                "time": time,
                "date": date
            })
            
            # Update table
            self.update_attendance_table()
            
            QMessageBox.information(self, "Success", f"Attendance marked for {name}!")
    
    def update_attendance_table(self):
        self.attendance_table.setRowCount(len(self.attendance_data))
        for i, entry in enumerate(self.attendance_data):
            self.attendance_table.setItem(i, 0, QTableWidgetItem(entry["name"]))
            self.attendance_table.setItem(i, 1, QTableWidgetItem(entry["time"]))
            self.attendance_table.setItem(i, 2, QTableWidgetItem(entry["date"]))
    
    def export_attendance(self):
        if not self.attendance_data:
            QMessageBox.warning(self, "Warning", "No attendance data to export!")
            return
            
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Attendance", "", "CSV Files (*.csv)"
        )
        
        if file_name:
            df = pd.DataFrame(self.attendance_data)
            df.to_csv(file_name, index=False)
            QMessageBox.information(self, "Success", "Attendance data exported successfully!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AttendanceSystem()
    window.show()
    sys.exit(app.exec_()) 