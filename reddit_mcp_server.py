from flask import Flask, request, jsonify
import requests
import secrets
import base64
from datetime import datetime, timedelta

app = Flask(__name__)

# Your Lambda endpoint URL
LAMBDA_URL = "https://9wyawpmjib.execute-api.us-east-1.amazonaws.com/default/reddit-mcp-bot"

# MCP Server Metadata
server_metadata = {
    "name": "reddit-poster",
    "version": "1.0.0",
    "description": "MCP server for Reddit posting",
    "tools": [
        {
            "name": "create_reddit_post",
            "description": "Create a Reddit post in a specified subreddit",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "subreddit": {
                        "type": "string",
                        "description": "Subreddit name"
                    },
                    "title": {
                        "type": "string",
                        "description": "Post title"
                    },
                    "selftext": {
                        "type": "string",
                        "description": "Post body text"
                    },
                    "require_approval": {
                        "type": "boolean",
                        "description": "Require approval before posting",
                        "default": False
                    }
                },
                "required": ["subreddit", "title"]
            }
        }
    ]
}

# OAuth 2.1 Configuration
oauth_config = {
    "issuer": "https://mcp-reddit.onrender.com",
    "authorization_endpoint": "https://mcp-reddit.onrender.com/oauth/authorize",
    "token_endpoint": "https://mcp-reddit.onrender.com/oauth/token",
    "userinfo_endpoint": "https://mcp-reddit.onrender.com/oauth/userinfo",
    "registration_endpoint": "https://mcp-reddit.onrender.com/oauth/register",
    "response_types_supported": ["code"],
    "grant_types_supported": ["authorization_code"],
    "scopes_supported": ["reddit:post"]
}

# Simple in-memory storage (use database in production)
tokens = {}
auth_codes = {}

# OAuth 2.1 Authorization Server Metadata
@app.route("/.well-known/oauth-authorization-server")
def oauth_metadata():
    response = jsonify(oauth_config)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# MCP Server Root - Returns server capabilities
@app.route("/")
def root():
    print("Root endpoint called!")  # Debug
    response = jsonify({
        "status": "MCP Reddit Server is running",
        "server": server_metadata,
        "endpoints": {
            "oauth_metadata": "/.well-known/oauth-authorization-server",
            "tools": "/tools",
            "manifest": "/mcp/manifest.json"
        }
    })
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# Legacy manifest endpoint (keeping for compatibility)
@app.route("/mcp/manifest.json")
def manifest_route():
    response = jsonify(server_metadata)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# OAuth Authorization endpoint
@app.route("/oauth/authorize")
def oauth_authorize():
    # Simple auth for demo - in production, implement proper OAuth flow
    auth_code = secrets.token_urlsafe(32)
    auth_codes[auth_code] = {
        "created": datetime.now(),
        "expires": datetime.now() + timedelta(minutes=10)
    }

    response = jsonify({"code": auth_code})
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# OAuth Token endpoint
@app.route("/oauth/token", methods=["POST"])
def oauth_token():
    grant_type = request.form.get('grant_type') or request.json.get('grant_type')
    code = request.form.get('code') or request.json.get('code')

    if grant_type != 'authorization_code' or not code or code not in auth_codes:
        return jsonify({"error": "invalid_grant"}), 400

    # Generate access token
    access_token = secrets.token_urlsafe(32)
    tokens[access_token] = {
        "created": datetime.now(),
        "expires": datetime.now() + timedelta(hours=1),
        "scope": "reddit:post"
    }

    # Clean up auth code
    del auth_codes[code]

    response = jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "reddit:post"
    })
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# OAuth User Info endpoint
@app.route("/oauth/userinfo")
def oauth_userinfo():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "unauthorized"}), 401

    token = auth_header.split(' ')[1]
    if token not in tokens:
        return jsonify({"error": "invalid_token"}), 401

    response = jsonify({
        "sub": "reddit_user",
        "name": "Reddit MCP User",
        "scope": "reddit:post"
    })
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# MCP Tools endpoint
@app.route("/tools", methods=["GET", "POST", "OPTIONS"])
def tools_handler():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    if request.method == "GET":
        # Return available tools
        response = jsonify({"tools": server_metadata["tools"]})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    # POST - Execute tool
    body = request.json
    tool_name = body.get("name")
    arguments = body.get("arguments", {})

    if tool_name != "create_reddit_post":
        error_result = jsonify({"error": "Unknown tool"})
        error_result.headers['Access-Control-Allow-Origin'] = '*'
        return error_result, 400

    # Prepare payload for Lambda
    lambda_payload = {
        "action": "post",
        "subreddit": arguments.get("subreddit", "test"),
        "title": arguments.get("title", "Default Title"),
        "selftext": arguments.get("selftext", ""),
        "require_approval": arguments.get("require_approval", False)
    }

    # Call the Lambda API
    response = requests.post(LAMBDA_URL, json=lambda_payload)
    if response.status_code == 200:
        lambda_response = response.json()
        result = jsonify({
            "content": [{
                "type": "text",
                "text": f"Successfully created Reddit post: {lambda_response}"
            }]
        })
        result.headers['Access-Control-Allow-Origin'] = '*'
        return result
    else:
        error_result = jsonify({
            "content": [{
                "type": "text",
                "text": f"Failed to create Reddit post. Status: {response.status_code}, Error: {response.text}"
            }],
            "isError": True
        })
        error_result.headers['Access-Control-Allow-Origin'] = '*'
        return error_result, 500

if __name__ == "__main__":
    import os
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        print("Starting server with HTTPS on port 8443...")
        app.run(host="0.0.0.0", port=8443, ssl_context=('cert.pem', 'key.pem'), debug=True)
    else:
        print("Starting server with HTTP on port 8080...")
        app.run(host="0.0.0.0", port=8080, debug=True)
