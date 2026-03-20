"""Test hex format CAN ID in DBC"""
from src.parsers.dbc_parser import DBCParser
import tempfile
from pathlib import Path

# Test hex format CAN ID
dbc_content = '''
VERSION "1.0"
NS_ :
BS_:
BU_: ECU1 ECU2
BO_ 0x100 Message1: 8 ECU1
 SG_ Signal1 : 0|8@1+ (1,0) [0|255] "" ECU2
'''
dbc_path = Path(tempfile.mktemp(suffix='.dbc'))
dbc_path.write_text(dbc_content.strip())

parser = DBCParser(dbc_path)
result = parser.parse()
print(f'Status: {result.status}')
print(f'Error: {result.error_message}')
print(f'Messages: {parser.get_all_messages()}')
