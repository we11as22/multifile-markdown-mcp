#!/usr/bin/env python3
"""
HTTP transport wrapper for MCP server
This script patches mcp.types before importing FastMCP
"""
import sys
import os
from pathlib import Path

# Fix PYTHONPATH to avoid conflict with local src/mcp/ directory
# We need to import the installed mcp package, not the local src/mcp/
project_root = Path(__file__).parent.parent
if str(project_root / "src") in sys.path:
    # Remove src from path temporarily to import the real mcp package
    src_path = str(project_root / "src")
    if src_path in sys.path:
        sys.path.remove(src_path)

# Fix for FastMCP compatibility - must be done BEFORE importing FastMCP
# This is critical - FastMCP tries to import mcp.types as a module
try:
    # Import the installed mcp package (not local src/mcp/)
    import importlib.util
    import site
    
    # Find the installed mcp package
    for site_package in site.getsitepackages():
        mcp_path = Path(site_package) / "mcp"
        if mcp_path.exists():
            spec = importlib.util.spec_from_file_location("mcp", mcp_path / "__init__.py")
            mcp_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mcp_module)
            
            # Get types from the installed package
            mcp_types_module = mcp_module.types
            
            # Register as a module in sys.modules BEFORE any FastMCP import
            sys.modules['mcp.types'] = mcp_types_module
            sys.modules['mcp'] = mcp_module
            break
    else:
        # Fallback: try direct import
        from mcp import types as mcp_types_module
        sys.modules['mcp.types'] = mcp_types_module
except (ImportError, AttributeError) as e:
    print(f"Warning: Could not patch mcp.types: {e}", file=sys.stderr)

# Restore src to path for our local imports
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Now we can safely import and run the server
if __name__ == "__main__":
    # Set environment to use HTTP transport
    os.environ.setdefault("MCP_TRANSPORT", "http")
    
    # Import and run main
    from src.main import cli_main
    cli_main()

