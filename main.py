#!/usr/bin/env python3
"""
Main entry point for the CLIA Report File Generator.

This script can be used to launch either the GUI or CLI version of the application.
"""
import sys
import argparse


def main():
    """Main entry point that can launch GUI or CLI mode."""
    parser = argparse.ArgumentParser(
        description="CLIA Laboratory Report Generator - Automated PDF Report Generation",
        epilog="For GUI mode, run without arguments or use --gui flag."
    )
    parser.add_argument(
        '--gui',
        action='store_true',
        help="Launch the graphical user interface (default if no args provided)"
    )
    parser.add_argument(
        '-i', '--input',
        help="Path to the input CSV file (CLI mode)"
    )
    parser.add_argument(
        '-o', '--output',
        help="Directory to save the generated PDF reports (CLI mode)"
    )
    parser.add_argument(
        '--organize-by',
        choices=['collection-date', 'tested-date', 'mrn'],
        help="Organize PDFs into subdirectories (CLI mode)"
    )

    args = parser.parse_args()

    # If no arguments provided or --gui flag, launch GUI
    if len(sys.argv) == 1 or args.gui:
        try:
            from src.gui import QApplication, MainWindow
            app = QApplication(sys.argv)
            window = MainWindow()
            window.show()
            sys.exit(app.exec())
        except ImportError as e:
            print(f"Error: Could not launch GUI. Make sure PySide6 is installed.")
            print(f"Details: {e}")
            sys.exit(1)
    # Otherwise, use CLI mode
    elif args.input and args.output:
        from src.main import main as cli_main
        cli_main(args.input, args.output, args.organize_by)
    else:
        parser.print_help()
        print("\nError: For CLI mode, both --input and --output are required.")
        sys.exit(1)


if __name__ == "__main__":
    main()
