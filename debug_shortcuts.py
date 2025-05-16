#!/usr/bin/env python
"""
Debug script to show all defined shortcuts in the MainWindow
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QAction

from main import MainWindow

def debug_shortcuts():
    app = QApplication(sys.argv)
    window = MainWindow()
    
    # Find all actions with shortcuts
    actions_with_shortcuts = []
    
    for attr_name in dir(window):
        attr = getattr(window, attr_name)
        if isinstance(attr, QAction):
            shortcut = attr.shortcut()
            if not shortcut.isEmpty():
                actions_with_shortcuts.append((attr_name, attr.text(), shortcut.toString()))
    
    # Sort and print
    actions_with_shortcuts.sort(key=lambda x: x[0])
    
    print("\n=== Defined Shortcuts ===")
    for name, text, shortcut in actions_with_shortcuts:
        print(f"{name:30} | {text:30} | {shortcut}")
    
    return app.quit()

if __name__ == "__main__":
    debug_shortcuts() 