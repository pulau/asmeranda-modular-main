"""Import helper to handle both Docker and local development import paths."""
import sys
from pathlib import Path

def setup_imports():
    """Setup Python path for both Docker and local development."""
    # Add project root to sys.path (parent of backend folder)
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Add backend directory to sys.path
    backend_dir = Path(__file__).resolve().parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

# Call setup when module is imported
setup_imports()