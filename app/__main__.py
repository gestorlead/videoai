"""
VideoAI Entry Point
Allows running the application with: python -m videoai
"""

import sys
import uvicorn
from app.main import app


def main():
    """Main entry point for VideoAI application"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
🎬 VideoAI - AI Video Creation & Social Media Platform

Usage:
  python -m videoai [options]
  
Options:
  --help          Show this help message
  --host HOST     Host to bind (default: 0.0.0.0)
  --port PORT     Port to bind (default: 8000)
  --reload        Enable auto-reload for development
  --workers N     Number of worker processes
  
Examples:
  python -m videoai
  python -m videoai --host localhost --port 8080 --reload
  
For more information, visit: https://github.com/gestorlead/videoai
""")
        return
    
    # Parse basic arguments
    host = "0.0.0.0"
    port = 8000
    reload = False
    workers = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--reload":
            reload = True
            i += 1
        elif args[i] == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])
            i += 2
        else:
            i += 1
    
    print(f"🚀 Starting VideoAI on {host}:{port}")
    if reload:
        print("🔄 Auto-reload enabled")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers
    )


if __name__ == "__main__":
    main()
