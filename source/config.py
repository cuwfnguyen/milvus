from dotenv import load_dotenv
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
dotenv_path = base_dir / 'data' / '.env'
load_dotenv(dotenv_path)

def get_path_data(file_name):
    file_name = base_dir / 'data' / file_name
    return file_name

def get_config_file(file_name):
    file_name = base_dir / file_name
    return file_name
