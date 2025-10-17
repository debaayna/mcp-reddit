#!/usr/bin/env python3
"""
Run the Reddit MCP server with HTTPS support
"""
from reddit_mcp_server import app

if __name__ == "__main__":
    # Run with SSL context for HTTPS
    app.run(
        host="0.0.0.0",
        port=8443,  # Standard HTTPS port alternative
        ssl_context=('cert.pem', 'key.pem'),
        debug=False
    )