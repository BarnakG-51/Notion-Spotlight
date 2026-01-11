#!/usr/bin/env python3
"""
Main launcher for Notion Agent
Runs the GUI authentication launcher by default
"""
import sys
import os

def main():
    # Check if GUI is available
    try:
        import tkinter
        # Run GUI launcher
        from gui_launcher import main as gui_main
        gui_main()
    except ImportError:
        print("❌ tkinter not available. GUI features require tkinter.")
        print("💡 To install tkinter on Ubuntu/Debian: sudo apt-get install python3-tk")
        print("💡 To install tkinter on macOS: tkinter comes with Python")
        print("💡 To install tkinter on Windows: tkinter comes with Python")
        print()
        print("🔄 Falling back to CLI mode...")
        print("Run: cd notion-spotlight-mvp/backend && python cli.py")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()