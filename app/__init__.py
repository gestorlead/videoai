"""
VideoAI - AI Video Creation & Social Media Platform

A complete AI-powered video creation pipeline from concept to social media publishing.
"""

__version__ = "1.0.0"
__title__ = "VideoAI" 
__description__ = "AI-powered video creation and social media publishing platform"
__author__ = "VideoAI Team"
__email__ = "dev@videoai.com"
__license__ = "MIT"
__url__ = "https://github.com/gestorlead/videoai"

# Public API exports
try:
    from .main import app
    from .core.config import settings
    
    __all__ = [
        "__version__",
        "__title__", 
        "__description__",
        "__author__",
        "__email__",
        "__license__",
        "__url__",
        "app",
        "settings"
    ]
except ImportError:
    # Handle import errors gracefully during development
    __all__ = [
        "__version__",
        "__title__", 
        "__description__",
        "__author__",
        "__email__",
        "__license__",
        "__url__"
    ]
