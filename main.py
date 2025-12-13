"""
DLT Viewer - A simple DLT file viewer with search capabilities
"""
import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DLT Viewer - SoC DLT parser")
    app.setOrganizationName("DLTViewer")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
