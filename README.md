# DLT Viewer

A simple and lightweight DLT (Diagnostic Log and Trace) file viewer with search capabilities.

![DLT Viewer Demo](guide.gif)

## Features

- **Multi-file Loading**: Open multiple DLT files at once, automatically sorted by index
- **Structured Display**: View DLT messages in a clean table format with:
  - Index
  - Timestamp
  - ECU ID
  - Application ID
  - Context ID
  - Message Type
  - Payload
  - Source File
- **Read-only Interface**: Select and copy message content
- **Advanced Search**: 
  - Search across all message fields
  - Regular expression support
  - Color highlighting for different search patterns
  - Multiple search patterns simultaneously
- **Status Bar**: Shows current file information and message count

## Installation

1. Make sure you have Python 3.7+ installed

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python main.py
```

### Loading DLT Files

1. Go to **File → Open DLT Files** (or press `Ctrl+O`)
2. Select one or multiple DLT files
3. Files will be automatically sorted by index and loaded
4. Messages will be displayed in the main table

### Searching

1. Go to **Search → Find** (or press `Ctrl+F`)
2. Enter your search pattern
3. Optionally enable "Use Regular Expression" for regex search
4. Select a highlight color
5. Click "Add Pattern" to add the search pattern
6. Add multiple patterns with different colors if needed
7. Click "Search" to highlight matching messages

To clear search highlighting:
- Go to **Search → Clear Search** (or press `Ctrl+Shift+F`)

## File Format

This viewer supports standard DLT files with storage headers. Files are expected to follow the DLT format specification.

## Requirements

- Python 3.7+
- PyQt5 5.15.0+

## Changelog

### Version 0.11 (January 6, 2026)
- **Improved Copy Functionality**: Enhanced clipboard operations for large data sets
  - Added progress dialog for copying >100 rows
  - Implemented 50MB size limit with user warnings
  - Shows data size feedback (KB/MB) in status bar
  - Cancellable operations for better control
  - Better error messages with alternative suggestions
- **UI Enhancement**: Increased default Payload column width from 600 to 1000 pixels for better readability

### Version 0.10
- Initial release with core DLT viewing and search capabilities

## License

This project is open source.
