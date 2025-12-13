"""
DLT file parser
Parses DLT (Diagnostic Log and Trace) files and extracts message information
"""
import struct
import os
from datetime import datetime
from typing import List, Dict, Optional


class DLTMessage:
    """Represents a single DLT message"""
    def __init__(self, index: int, timestamp: str, ecu_id: str, app_id: str, 
                 context_id: str, message_type: str, payload: str, source_file: str = ""):
        self.index = index
        self.timestamp = timestamp
        self.ecu_id = ecu_id
        self.app_id = app_id
        self.context_id = context_id
        self.message_type = message_type
        self.payload = payload
        self.source_file = source_file
    
    def to_dict(self) -> Dict:
        return {
            'Index': self.index,
            'Timestamp': self.timestamp,
            'ECU ID': self.ecu_id,
            'App ID': self.app_id,
            'Context ID': self.context_id,
            'Type': self.message_type,
            'Payload': self.payload,
            'Source': self.source_file
        }


class DLTParser:
    """Parser for DLT files"""
    
    # DLT Standard Header pattern
    DLT_PATTERN = b'DLT\x01'
    
    def __init__(self):
        self.messages: List[DLTMessage] = []
        
    def parse_file(self, file_path: str, global_index_offset: int = 0) -> List[DLTMessage]:
        """
        Parse a DLT file and return list of messages
        
        Args:
            file_path: Path to the DLT file
            global_index_offset: Starting index for messages (for multi-file loading)
        
        Returns:
            List of DLTMessage objects
        """
        messages = []
        
        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                local_index = 0
                
                while f.tell() < file_size:
                    try:
                        message = self._parse_message(f, global_index_offset + local_index, filename)
                        if message:
                            messages.append(message)
                            local_index += 1
                    except Exception as e:
                        # Skip malformed messages and try to find next valid message
                        if not self._find_next_message(f):
                            break
                            
        except Exception as e:
            print(f"Error parsing file {file_path}: {str(e)}")
        
        return messages
    
    def _parse_message(self, f, index: int, filename: str) -> Optional[DLTMessage]:
        """Parse a single DLT message from file"""
        
        # Read storage header (if present) - 16 bytes
        start_pos = f.tell()
        header_bytes = f.read(4)
        
        if len(header_bytes) < 4:
            return None
        
        # Check for DLT pattern
        if header_bytes != self.DLT_PATTERN:
            # Try to find DLT pattern
            f.seek(start_pos)
            if not self._find_next_message(f):
                return None
            header_bytes = f.read(4)
        
        # Read storage header timestamp (seconds + microseconds)
        storage_header = f.read(12)
        if len(storage_header) < 12:
            return None
            
        seconds = struct.unpack('<I', storage_header[0:4])[0]
        microseconds = struct.unpack('<I', storage_header[4:8])[0]
        
        # Create timestamp
        try:
            timestamp = datetime.fromtimestamp(seconds).strftime('%Y-%m-%d %H:%M:%S')
            timestamp += f".{microseconds:06d}"
        except:
            timestamp = f"{seconds}.{microseconds}"
        
        # Read ECU ID
        ecu_id = storage_header[8:12].decode('ascii', errors='ignore').strip('\x00')
        
        # Read standard header
        standard_header = f.read(4)
        if len(standard_header) < 4:
            return None
        
        htyp = standard_header[0]
        message_counter = standard_header[1]
        length = struct.unpack('>H', standard_header[2:4])[0]
        
        # Read remaining message (length includes standard header)
        remaining_length = length - 4
        if remaining_length < 0:
            return None
            
        message_data = f.read(remaining_length)
        if len(message_data) < remaining_length:
            return None
        
        # Parse optional standard header fields
        payload_offset = 0
        
        # Check for ECU ID in standard header (WEID flag, bit 2)
        if htyp & 0x04:
            if len(message_data) < payload_offset + 4:
                return None
            # ECU ID is optional in standard header, skip it
            payload_offset += 4
        
        # Check for Session ID (WSID flag, bit 3)
        if htyp & 0x08:
            if len(message_data) < payload_offset + 4:
                return None
            payload_offset += 4
        
        # Check for Timestamp (WTMS flag, bit 4)
        if htyp & 0x10:
            if len(message_data) < payload_offset + 4:
                return None
            payload_offset += 4
        
        # Parse extended header if present
        app_id = ""
        context_id = ""
        message_type = "LOG"
        noar = 0  # Number of arguments
        
        if htyp & 0x01:  # UEH - Use Extended Header (bit 0)
            if len(message_data) >= payload_offset + 10:
                ext_header_start = payload_offset
                message_info = message_data[ext_header_start]
                noar = message_data[ext_header_start + 1]  # Number of arguments
                app_id = message_data[ext_header_start + 2:ext_header_start + 6].decode('ascii', errors='ignore').strip('\x00').strip()
                context_id = message_data[ext_header_start + 6:ext_header_start + 10].decode('ascii', errors='ignore').strip('\x00').strip()
                payload_offset += 10
                
                # Determine message type
                mtin = (message_info >> 1) & 0x07
                if mtin == 0:
                    message_type = "LOG"
                elif mtin == 1:
                    message_type = "TRACE"
                elif mtin == 2:
                    message_type = "NW_TRACE"
                elif mtin == 3:
                    message_type = "CONTROL"
        
        # Extract payload
        payload_data = message_data[payload_offset:]
        
        # Try to decode payload as text
        try:
            # DLT payload often contains type information, try to extract readable text
            # Pass app_id and context_id to filter them out from payload
            payload = self._extract_payload_text(payload_data, app_id, context_id)
        except:
            payload = payload_data.hex()
        
        return DLTMessage(
            index=index,
            timestamp=timestamp,
            ecu_id=ecu_id,
            app_id=app_id,
            context_id=context_id,
            message_type=message_type,
            payload=payload,
            source_file=filename
        )
    
    def _extract_payload_text(self, payload_data: bytes, app_id: str = "", context_id: str = "") -> str:
        """Extract readable text from DLT payload"""
        if len(payload_data) == 0:
            return ""
        
        if len(payload_data) < 4:
            return payload_data.decode('ascii', errors='ignore').strip('\x00')
        
        result = []
        offset = 0
        
        try:
            # Check if this is a verbose mode message (has argument type info)
            # In verbose mode, each argument has type info (4 bytes) followed by data
            
            # Try to parse as verbose mode
            arg_count = 0
            while offset < len(payload_data) - 4 and arg_count < 100:  # Safety limit
                # Read type info (4 bytes)
                type_info = struct.unpack('>I', payload_data[offset:offset+4])[0]
                offset += 4
                arg_count += 1
                
                # Extract type information from type_info
                # Bit 0: BOOL, Bit 1-3: Type length, Bit 4-7: Type (String=0x00, Int, etc.)
                type_code = (type_info >> 4) & 0x0F
                
                # Type 0x00 = String
                if type_code == 0x00 or type_code == 0x08:  # String or UTF8 string
                    # Read string length (2 bytes)
                    if offset + 2 > len(payload_data):
                        break
                    
                    str_len = struct.unpack('>H', payload_data[offset:offset+2])[0]
                    offset += 2
                    
                    if offset + str_len > len(payload_data) or str_len > 4096:
                        break
                    
                    # Read string data
                    string_data = payload_data[offset:offset+str_len]
                    offset += str_len
                    
                    # Decode and clean string
                    text = string_data.decode('ascii', errors='ignore').strip('\x00').strip()
                    if text and len(text) > 1:
                        # Skip if it matches the app_id or context_id we already extracted
                        if app_id and text.startswith(app_id):
                            # Check if it's exactly app_id+context_id concatenated
                            if context_id and text == app_id + context_id:
                                continue
                            # Or if it starts with app_id, try to remove it
                            if len(text) > len(app_id):
                                remaining = text[len(app_id):]
                                # Check if remaining starts with context_id
                                if context_id and remaining.startswith(context_id):
                                    remaining = remaining[len(context_id):]
                                if remaining and len(remaining) > 1:
                                    text = remaining.strip()
                                else:
                                    continue
                            else:
                                continue
                        elif context_id and text == context_id:
                            continue
                        
                        # Skip single characters or very short uppercase strings (likely metadata)
                        if len(text) == 1:
                            continue
                        # Skip if it's just whitespace-separated single chars like "B A N"
                        if len(text) <= 5 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ ' for c in text) and ' ' in text:
                            continue
                        # Skip short uppercase codes at the beginning
                        if arg_count <= 3 and len(text) <= 4 and text.isupper():
                            continue
                        result.append(text)
                else:
                    # For non-string types, skip based on type length
                    type_length_code = (type_info >> 1) & 0x07
                    if type_length_code <= 6:
                        type_length = 1 << type_length_code
                    else:
                        type_length = 16  # Max
                    offset += type_length
                    if offset > len(payload_data):
                        break
            
            if result:
                return ' '.join(result)
                
        except Exception:
            pass
        
        # Fallback: extract printable ASCII sequences (non-verbose mode or parsing failed)
        result = []
        current_str = []
        skip_count = 0
        
        for i, byte in enumerate(payload_data):
            if 32 <= byte <= 126:  # Printable ASCII
                current_str.append(chr(byte))
            elif byte == 0:  # Null terminator
                if current_str:
                    text = ''.join(current_str)
                    
                    # Skip if it matches app_id or context_id
                    if (app_id and app_id in text) or (context_id and context_id in text):
                        if i < 50:  # Only filter near the beginning
                            current_str = []
                            continue
                    
                    # Skip first few short uppercase strings
                    if skip_count < 3 and len(text) <= 4 and text.isupper() and i < 50:
                        skip_count += 1
                    # Skip patterns like "B A N" (single chars with spaces)
                    elif len(text) <= 5 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ ' for c in text) and ' ' in text:
                        pass
                    elif len(text) > 1:
                        result.append(text)
                current_str = []
            else:
                if current_str and len(current_str) > 1:
                    text = ''.join(current_str)
                    
                    # Skip if it matches app_id or context_id
                    if (app_id and app_id in text) or (context_id and context_id in text):
                        if i < 50:
                            current_str = []
                            continue
                    
                    if skip_count < 3 and len(text) <= 4 and text.isupper() and i < 50:
                        skip_count += 1
                    elif len(text) <= 5 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ ' for c in text) and ' ' in text:
                        pass
                    elif len(text) > 1:
                        result.append(text)
                current_str = []
        
        if current_str and len(current_str) > 1:
            text = ''.join(current_str)
            if not (len(text) <= 4 and text.isupper()):
                result.append(text)
        
        if result:
            return ' '.join(result)
        else:
            # Last fallback
            return payload_data.decode('ascii', errors='ignore').strip('\x00')
    
    def _find_next_message(self, f) -> bool:
        """Find the next DLT message pattern in file"""
        chunk_size = 4096
        pattern = self.DLT_PATTERN
        
        # Read chunks and search for pattern
        overlap = len(pattern) - 1
        previous_chunk = b''
        
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                return False
            
            search_data = previous_chunk + chunk
            pos = search_data.find(pattern)
            
            if pos != -1:
                # Found pattern, seek to start of message
                f.seek(f.tell() - len(chunk) - len(previous_chunk) + pos)
                return True
            
            # Keep overlap for pattern that might span chunks
            previous_chunk = chunk[-overlap:] if len(chunk) >= overlap else chunk
            
            if len(chunk) < chunk_size:
                return False
    
    @staticmethod
    def sort_files_by_index(file_paths: List[str]) -> List[str]:
        """
        Sort DLT files by numeric index in filename
        Assumes files are named like: file_0.dlt, file_1.dlt, etc.
        """
        def extract_index(filepath: str) -> int:
            filename = os.path.basename(filepath)
            # Try to extract number from filename
            import re
            numbers = re.findall(r'\d+', filename)
            return int(numbers[0]) if numbers else 0
        
        return sorted(file_paths, key=extract_index)
