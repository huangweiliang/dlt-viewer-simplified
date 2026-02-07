"""
DLT file parser using the tested and validated pydlt library
This wrapper maintains compatibility with the DLT Viewer interface
"""
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
import re

# Try multiple paths to find the dlt_parser py3 folder
possible_paths = [
    # Relative to this file (for workspace with dlt_parser as sibling)
    os.path.join(os.path.dirname(__file__), '..', 'dlt_parser', 'py3'),
    # Absolute path to the known location in the workspace
    r'c:\Users\huw6szh\Desktop\QNX\QNX\misc\dlt_parser\py3',
]

dlt_parser_path = None
for path in possible_paths:
    if os.path.exists(path):
        dlt_parser_path = os.path.abspath(path)
        sys.path.insert(0, dlt_parser_path)
        break

try:
    from pydlt import DltFileReader
    from pydlt.message import DltMessage as PydltMessage
    from pydlt.payload import VerbosePayload, NonVerbosePayload, ControlPayload
    PYDLT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import pydlt library: {e}")
    if dlt_parser_path:
        print(f"Attempted path: {dlt_parser_path}")
    # Fallback - we'll handle this gracefully
    DltFileReader = None
    PydltMessage = None
    PYDLT_AVAILABLE = False


class DLTMessage:
    """Represents a single DLT message - compatible with viewer interface"""
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
    """Parser for DLT files using the tested pydlt library"""
    
    def __init__(self, encoding: Optional[str] = 'latin-1'):
        """
        Initialize DLT Parser
        
        Args:
            encoding: Character encoding for non-UTF8 strings (default: latin-1)
        """
        self.messages: List[DLTMessage] = []
        self.encoding = encoding
        
    def parse_file(self, file_path: str, global_index_offset: int = 0) -> List[DLTMessage]:
        """
        Parse a DLT file and return list of messages
        
        Args:
            file_path: Path to the DLT file
            global_index_offset: Starting index for messages (for multi-file parsing)
            
        Returns:
            List of DLTMessage objects
        """
        if not PYDLT_AVAILABLE or DltFileReader is None:
            # Fallback to simple parsing if pydlt not available
            print(f"Error: pydlt library not available, cannot parse {file_path}")
            return []
        
        messages = []
        filename = os.path.basename(file_path)
        
        try:
            # Use DltFileReader from the tested library
            with DltFileReader(file_path, encoding=self.encoding) as reader:
                local_index = 0
                
                for pydlt_msg in reader:
                    try:
                        # Convert pydlt message to our DLTMessage format
                        message = self._convert_message(pydlt_msg, 
                                                       global_index_offset + local_index, 
                                                       filename)
                        if message:
                            messages.append(message)
                            local_index += 1
                    except Exception as e:
                        # Log error but continue parsing
                        print(f"Warning: Error parsing message {local_index} in {file_path}: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error parsing file {file_path}: {str(e)}")
        
        return messages
    
    def _convert_message(self, pydlt_msg: PydltMessage, index: int, filename: str) -> Optional[DLTMessage]:
        """
        Convert a pydlt DltMessage to our DLTMessage format
        
        Args:
            pydlt_msg: Message from pydlt library
            index: Message index
            filename: Source filename
            
        Returns:
            Converted DLTMessage or None on error
        """
        try:
            # Extract timestamp from storage header
            timestamp_str = self._format_timestamp(pydlt_msg)
            
            # Extract ECU ID (note: pydlt uses str_header, not storage_header)
            ecu_id = ""
            if hasattr(pydlt_msg, 'str_header') and pydlt_msg.str_header and pydlt_msg.str_header.ecu_id:
                ecu_id = pydlt_msg.str_header.ecu_id
            elif hasattr(pydlt_msg, 'std_header') and pydlt_msg.std_header and pydlt_msg.std_header.ecu_id:
                ecu_id = pydlt_msg.std_header.ecu_id
            
            # Extract App ID and Context ID from extended header
            app_id = ""
            context_id = ""
            message_type = "LOG"
            
            if hasattr(pydlt_msg, 'ext_header') and pydlt_msg.ext_header:
                app_id = pydlt_msg.ext_header.application_id or ""
                context_id = pydlt_msg.ext_header.context_id or ""
                
                # Get message type
                if hasattr(pydlt_msg.ext_header, 'message_type'):
                    message_type = self._get_message_type_string(pydlt_msg.ext_header.message_type)
            
            # Extract payload as string
            payload_str = self._extract_payload(pydlt_msg)
            
            return DLTMessage(
                index=index,
                timestamp=timestamp_str,
                ecu_id=ecu_id,
                app_id=app_id,
                context_id=context_id,
                message_type=message_type,
                payload=payload_str,
                source_file=filename
            )
            
        except Exception as e:
            print(f"Error converting message: {str(e)}")
            return None
    
    def _format_timestamp(self, pydlt_msg: PydltMessage) -> str:
        """
        Format timestamp from storage header
        
        Args:
            pydlt_msg: pydlt message
            
        Returns:
            Formatted timestamp string
        """
        try:
            # Try storage header first (str_header in pydlt)
            if hasattr(pydlt_msg, 'str_header') and pydlt_msg.str_header:
                if hasattr(pydlt_msg.str_header, 'seconds') and hasattr(pydlt_msg.str_header, 'microseconds'):
                    # Build datetime from seconds and microseconds
                    seconds = pydlt_msg.str_header.seconds
                    microseconds = pydlt_msg.str_header.microseconds
                    dt = datetime.fromtimestamp(seconds)
                    return dt.strftime('%Y-%m-%d %H:%M:%S') + f".{microseconds:06d}"
            
            # Fallback to standard header timestamp
            if hasattr(pydlt_msg, 'std_header') and pydlt_msg.std_header:
                if hasattr(pydlt_msg.std_header, 'timestamp') and pydlt_msg.std_header.timestamp is not None:
                    # Use standard header timestamp (0.1 ms units)
                    timestamp_value = pydlt_msg.std_header.timestamp
                    seconds = timestamp_value / 10000.0
                    return f"{seconds:.4f}"
            
            return "0.0000"
        except Exception as e:
            return "0.0000"
    
    def _get_message_type_string(self, message_type) -> str:
        """
        Get human-readable message type string
        
        Args:
            message_type: Message type from extended header
            
        Returns:
            Message type string
        """
        try:
            # Map message type enum to string
            type_map = {
                0: "LOG",
                1: "APP_TRACE",
                2: "NW_TRACE",
                3: "CONTROL"
            }
            
            if hasattr(message_type, 'value'):
                return type_map.get(message_type.value, "LOG")
            else:
                return type_map.get(int(message_type), "LOG")
        except:
            return "LOG"
    
    def _extract_payload(self, pydlt_msg: PydltMessage) -> str:
        """
        Extract payload as human-readable string
        
        Args:
            pydlt_msg: pydlt message
            
        Returns:
            Payload string
        """
        try:
            if pydlt_msg.payload:
                # The pydlt library's __str__ method handles verbose/non-verbose formatting
                payload_str = str(pydlt_msg.payload)
                
                # Clean up the payload string
                # Remove leading/trailing whitespace
                payload_str = payload_str.strip()
                
                # For non-verbose messages that couldn't be decoded, show a message
                if isinstance(pydlt_msg.payload, NonVerbosePayload):
                    # Non-verbose payload - format with message ID
                    if hasattr(pydlt_msg.payload, 'message_id'):
                        msg_id = pydlt_msg.payload.message_id
                        # If the string representation doesn't include helpful info, add it
                        if not payload_str or payload_str == '':
                            payload_str = f"[Non-Verbose ID: {msg_id}]"
                
                return payload_str
            else:
                return ""
        except Exception as e:
            # Fallback: try to get raw bytes
            try:
                if pydlt_msg.payload:
                    raw_bytes = pydlt_msg.payload.to_bytes()
                    return raw_bytes.hex()[:100]  # Limit length
            except:
                pass
            return f"[Error extracting payload: {str(e)}]"
    
    @staticmethod
    def sort_files_by_index(file_paths: List[str]) -> List[str]:
        """Sort DLT files by numeric index in filename"""
        def extract_index(filepath: str) -> int:
            filename = os.path.basename(filepath)
            numbers = re.findall(r'\d+', filename)
            return int(numbers[0]) if numbers else 0
        
        return sorted(file_paths, key=extract_index)
