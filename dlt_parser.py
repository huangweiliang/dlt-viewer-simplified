"""
Improved DLT file parser based on COVESA DLT Viewer implementation
Properly handles DLT binary format and verbose mode arguments
"""
import struct
import os
from datetime import datetime
from typing import List, Dict, Optional


# DLT Type Info Constants (from dlt_common.h)
DLT_TYPE_INFO_TYLE = 0x0000000f  # Length info
DLT_TYPE_INFO_BOOL = 0x00000010  # Boolean
DLT_TYPE_INFO_SINT = 0x00000020  # Signed integer
DLT_TYPE_INFO_UINT = 0x00000040  # Unsigned integer
DLT_TYPE_INFO_FLOA = 0x00000080  # Float
DLT_TYPE_INFO_RAWD = 0x00000100  # Raw data
DLT_TYPE_INFO_STRG = 0x00000200  # String
DLT_TYPE_INFO_TRAI = 0x00000400  # Trace info
DLT_TYPE_INFO_STRU = 0x00000800  # Struct
DLT_TYPE_INFO_VARI = 0x00001000  # Variable info
DLT_TYPE_INFO_FIXP = 0x00002000  # Fixed point
DLT_TYPE_INFO_SCOD = 0x00038000  # String coding

DLT_TYLE_8BIT = 0x00000001
DLT_TYLE_16BIT = 0x00000002
DLT_TYLE_32BIT = 0x00000003
DLT_TYLE_64BIT = 0x00000004
DLT_TYLE_128BIT = 0x00000005

DLT_SCOD_ASCII = 0x00000000
DLT_SCOD_UTF8 = 0x00008000


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
    """Parser for DLT files based on COVESA implementation"""
    
    DLT_PATTERN = b'DLT\x01'
    
    def __init__(self):
        self.messages: List[DLTMessage] = []
        
    def parse_file(self, file_path: str, global_index_offset: int = 0) -> List[DLTMessage]:
        """Parse a DLT file and return list of messages"""
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
                        if not self._find_next_message(f):
                            break
                            
        except Exception as e:
            print(f"Error parsing file {file_path}: {str(e)}")
        
        return messages
    
    def _parse_message(self, f, index: int, filename: str) -> Optional[DLTMessage]:
        """Parse a single DLT message"""
        
        start_pos = f.tell()
        header_bytes = f.read(4)
        
        if len(header_bytes) < 4 or header_bytes != self.DLT_PATTERN:
            f.seek(start_pos)
            if not self._find_next_message(f):
                return None
            header_bytes = f.read(4)
        
        # Read storage header (12 more bytes after DLT\x01)
        storage_header = f.read(12)
        if len(storage_header) < 12:
            return None
            
        seconds = struct.unpack('<I', storage_header[0:4])[0]
        microseconds = struct.unpack('<I', storage_header[4:8])[0]
        ecu_id = storage_header[8:12].decode('ascii', errors='ignore').strip('\x00').strip()
        
        # Create timestamp
        try:
            timestamp = datetime.fromtimestamp(seconds).strftime('%Y-%m-%d %H:%M:%S')
            timestamp += f".{microseconds:06d}"
        except:
            timestamp = f"{seconds}.{microseconds}"
        
        # Read standard header (4 bytes)
        standard_header = f.read(4)
        if len(standard_header) < 4:
            return None
        
        htyp = standard_header[0]
        message_counter = standard_header[1]
        length = struct.unpack('>H', standard_header[2:4])[0]
        
        # Read remaining message
        remaining_length = length - 4
        if remaining_length < 0:
            return None
            
        message_data = f.read(remaining_length)
        if len(message_data) < remaining_length:
            return None
        
        # Parse optional fields in standard header
        offset = 0
        
        # Check for ECU ID in standard header (WEID, bit 2)
        if htyp & 0x04:
            if len(message_data) < offset + 4:
                return None
            offset += 4
        
        # Check for Session ID (WSID, bit 3)
        if htyp & 0x08:
            if len(message_data) < offset + 4:
                return None
            offset += 4
        
        # Check for Timestamp (WTMS, bit 4)
        if htyp & 0x10:
            if len(message_data) < offset + 4:
                return None
            offset += 4
        
        # Parse extended header if present (UEH, bit 0)
        app_id = ""
        context_id = ""
        message_type = "LOG"
        noar = 0
        
        if htyp & 0x01:  # UEH flag
            if len(message_data) < offset + 10:
                return None
            
            message_info = message_data[offset]
            noar = message_data[offset + 1]
            app_id = message_data[offset + 2:offset + 6].decode('ascii', errors='ignore').strip('\x00').strip()
            context_id = message_data[offset + 6:offset + 10].decode('ascii', errors='ignore').strip('\x00').strip()
            offset += 10
            
            # Determine message type from MTIN (bits 4-7 of message_info)
            mtin = (message_info >> 1) & 0x07
            if mtin == 0:
                message_type = "LOG"
            elif mtin == 1:
                message_type = "TRACE"
            elif mtin == 2:
                message_type = "NW_TRACE"
            elif mtin == 3:
                message_type = "CONTROL"
            
            # Check if verbose mode (VERB bit, bit 0 of message_info)
            is_verbose = (message_info & 0x01) != 0
        else:
            is_verbose = False
        
        # Extract payload
        payload_data = message_data[offset:]
        
        # Parse payload
        try:
            if is_verbose and noar > 0:
                payload = self._parse_verbose_payload(payload_data, noar)
            else:
                # Non-verbose mode - just show as hex/ascii
                payload = self._parse_nonverbose_payload(payload_data)
        except Exception as e:
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
    
    def _parse_verbose_payload(self, payload_data: bytes, num_args: int) -> str:
        """Parse verbose mode payload with type information"""
        result = []
        offset = 0
        
        for arg_num in range(num_args):
            if offset + 4 > len(payload_data):
                break
            
            # Read 4-byte type info (little endian)
            type_info = struct.unpack('<I', payload_data[offset:offset+4])[0]
            offset += 4
            
            # Parse argument based on type
            try:
                arg_text = self._parse_argument(payload_data, offset, type_info)
                if arg_text is not None:
                    arg_value, arg_size = arg_text
                    # Add all values, even empty ones that represent actual empty strings
                    result.append(arg_value if arg_value else "")
                    offset += arg_size
                else:
                    # Try to continue with next argument instead of breaking
                    offset += 1
            except Exception as e:
                # Try to continue
                offset += 1
        
        # If no results from verbose parsing, fallback to simple text extraction
        if not result and len(payload_data) > 0:
            return self._parse_nonverbose_payload(payload_data)
        
        return ' '.join(result)
    
    def _parse_argument(self, payload_data: bytes, offset: int, type_info: int):
        """Parse a single argument based on type info"""
        
        # Check for string types
        if type_info & DLT_TYPE_INFO_STRG:
            return self._parse_string_argument(payload_data, offset, type_info)
        
        # Check for boolean
        elif type_info & DLT_TYPE_INFO_BOOL:
            if offset + 1 > len(payload_data):
                return None
            value = payload_data[offset]
            return ("true" if value else "false", 1)
        
        # Check for signed integer
        elif type_info & DLT_TYPE_INFO_SINT:
            return self._parse_int_argument(payload_data, offset, type_info, signed=True)
        
        # Check for unsigned integer
        elif type_info & DLT_TYPE_INFO_UINT:
            return self._parse_int_argument(payload_data, offset, type_info, signed=False)
        
        # Check for float
        elif type_info & DLT_TYPE_INFO_FLOA:
            return self._parse_float_argument(payload_data, offset, type_info)
        
        # Check for raw data
        elif type_info & DLT_TYPE_INFO_RAWD:
            return self._parse_raw_argument(payload_data, offset)
        
        return None
    
    def _parse_string_argument(self, payload_data: bytes, offset: int, type_info: int):
        """Parse string argument"""
        # Read string length (2 bytes, little endian)
        if offset + 2 > len(payload_data):
            return None
        
        str_len = struct.unpack('<H', payload_data[offset:offset+2])[0]
        offset += 2
        
        # Validate string length
        if str_len > 4096 or offset + str_len > len(payload_data):
            return None
        
        # Read string data
        string_data = payload_data[offset:offset+str_len]
        
        # Decode based on encoding
        if (type_info & DLT_TYPE_INFO_SCOD) == DLT_SCOD_UTF8:
            text = string_data.decode('utf-8', errors='ignore')
        else:
            text = string_data.decode('ascii', errors='ignore')
        
        # Clean up the string (remove null terminators but keep content)
        text = text.rstrip('\x00')
        
        return (text, str_len + 2)
    
    def _parse_int_argument(self, payload_data: bytes, offset: int, type_info: int, signed: bool):
        """Parse integer argument"""
        type_len = type_info & DLT_TYPE_INFO_TYLE
        
        if type_len == DLT_TYLE_8BIT:
            size = 1
            fmt = 'b' if signed else 'B'
        elif type_len == DLT_TYLE_16BIT:
            size = 2
            fmt = '<h' if signed else '<H'
        elif type_len == DLT_TYLE_32BIT:
            size = 4
            fmt = '<i' if signed else '<I'
        elif type_len == DLT_TYLE_64BIT:
            size = 8
            fmt = '<q' if signed else '<Q'
        else:
            return None
        
        if offset + size > len(payload_data):
            return None
        
        value = struct.unpack(fmt, payload_data[offset:offset+size])[0]
        return (str(value), size)
    
    def _parse_float_argument(self, payload_data: bytes, offset: int, type_info: int):
        """Parse float argument"""
        type_len = type_info & DLT_TYPE_INFO_TYLE
        
        if type_len == DLT_TYLE_32BIT:
            size = 4
            fmt = '<f'
        elif type_len == DLT_TYLE_64BIT:
            size = 8
            fmt = '<d'
        else:
            return None
        
        if offset + size > len(payload_data):
            return None
        
        value = struct.unpack(fmt, payload_data[offset:offset+size])[0]
        return (f"{value:.6f}", size)
    
    def _parse_raw_argument(self, payload_data: bytes, offset: int):
        """Parse raw data argument"""
        # Read length (2 bytes, little endian)
        if offset + 2 > len(payload_data):
            return None
        
        data_len = struct.unpack('<H', payload_data[offset:offset+2])[0]
        offset += 2
        
        if data_len > 4096 or offset + data_len > len(payload_data):
            return None
        
        raw_data = payload_data[offset:offset+data_len]
        # Convert to hex string
        hex_str = raw_data.hex()
        
        return (hex_str, data_len + 2)
    
    def _parse_nonverbose_payload(self, payload_data: bytes) -> str:
        """Parse non-verbose payload - just extract readable text"""
        # Try to extract printable text
        result = []
        current_str = []
        
        for byte in payload_data:
            if 32 <= byte <= 126:  # Printable ASCII
                current_str.append(chr(byte))
            elif byte == 0:  # Null terminator
                if current_str and len(current_str) > 2:
                    result.append(''.join(current_str))
                current_str = []
            else:
                if current_str and len(current_str) > 2:
                    result.append(''.join(current_str))
                current_str = []
        
        if current_str and len(current_str) > 2:
            result.append(''.join(current_str))
        
        if result:
            return ' '.join(result)
        else:
            # Fallback to hex
            return payload_data.hex()
    
    def _find_next_message(self, f) -> bool:
        """Find the next DLT message pattern in file"""
        chunk_size = 4096
        pattern = self.DLT_PATTERN
        overlap = len(pattern) - 1
        previous_chunk = b''
        
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                return False
            
            search_data = previous_chunk + chunk
            pos = search_data.find(pattern)
            
            if pos != -1:
                f.seek(f.tell() - len(chunk) - len(previous_chunk) + pos)
                return True
            
            previous_chunk = chunk[-overlap:] if len(chunk) >= overlap else chunk
            
            if len(chunk) < chunk_size:
                return False
    
    @staticmethod
    def sort_files_by_index(file_paths: List[str]) -> List[str]:
        """Sort DLT files by numeric index in filename"""
        def extract_index(filepath: str) -> int:
            filename = os.path.basename(filepath)
            import re
            numbers = re.findall(r'\d+', filename)
            return int(numbers[0]) if numbers else 0
        
        return sorted(file_paths, key=extract_index)
