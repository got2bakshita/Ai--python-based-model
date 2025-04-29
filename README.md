# Student Attendance Management System

A professional and modern student attendance management system built with Python and PyQt5. The system provides an intuitive interface for managing student records, tracking attendance, and generating reports.

## Features

- Modern and intuitive user interface
- Student management (add, view, edit)
- Attendance tracking with multiple status options (present, absent, late)
- Comprehensive reporting system
- Data visualization with graphs and statistics
- Export functionality for attendance data and reports
- SQLite database for secure data storage

## Requirements

- Python 3.7 or higher
- Required packages listed in requirements.txt

## Installation

1. Clone or download this repository
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```

2. Using the System:

   ### Dashboard
   - View overall attendance statistics
   - See attendance trends through graphs
   - Quick access to key metrics

   ### Student Management
   - Add new students with their details
   - View and manage existing student records
   - Assign students to classes

   ### Attendance
   - Mark attendance by class
   - Multiple attendance status options
   - Bulk attendance marking
   - Edit attendance records

   ### Reports
   - Generate attendance reports by class or date range
   - Export reports to CSV format
   - View attendance statistics and trends

## Database Structure

The system uses SQLite with the following main tables:
- Students: Stores student information
- Attendance: Records daily attendance
- Classes: Manages class information

## Contributing

Feel free to fork this repository and submit pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 