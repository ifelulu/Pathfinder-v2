from PySide6.QtWidgets import QApplication, QMainWindow, QMenuBar, QToolBar, QMenu, QAction, QFileDialog, QMessageBox
from PySide6.QtCore import QTimer
import sys

class TestExportApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Export Menu Test")
        self.resize(800, 600)
        
        # Create menu bar
        self.menu_bar = self.menuBar()
        
        # Add File menu
        file_menu = self.menu_bar.addMenu("&File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Add Export menu
        export_menu = self.menu_bar.addMenu("&Export")
        
        # Export data action
        self.export_data_action = QAction("Export &Data...", self)
        self.export_data_action.triggered.connect(self.handle_export_data)
        export_menu.addAction(self.export_data_action)
        
        # Export image action
        self.export_image_action = QAction("Export &Image...", self)
        self.export_image_action.triggered.connect(self.handle_export_image)
        export_menu.addAction(self.export_image_action)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def handle_export_data(self):
        """Handle export data action"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "data.csv", "CSV (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("Column1,Column2,Column3\n")
                    f.write("Data1,Data2,Data3\n")
                
                self.statusBar().showMessage(f"Data exported to {file_path}", 3000)
                QMessageBox.information(self, "Export Successful", f"Data exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export data: {e}")
    
    def handle_export_image(self):
        """Handle export image action"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", "image.png", "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        
        if file_path:
            try:
                # Create a simple image
                from PySide6.QtGui import QImage, QPainter, QColor, QBrush, QPen
                image = QImage(400, 300, QImage.Format.Format_RGB32)
                image.fill(QColor("white"))
                
                painter = QPainter(image)
                painter.setPen(QPen(QColor("blue"), 2))
                painter.setBrush(QBrush(QColor("lightblue")))
                painter.drawRect(50, 50, 300, 200)
                painter.drawText(100, 150, "Test Export Image")
                painter.end()
                
                # Save the image
                image.save(file_path)
                
                self.statusBar().showMessage(f"Image exported to {file_path}", 3000)
                QMessageBox.information(self, "Export Successful", f"Image exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export image: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestExportApp()
    window.show()
    sys.exit(app.exec())
