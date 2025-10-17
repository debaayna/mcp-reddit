from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Your Lambda endpoint URL
LAMBDA_URL = "https://9wyawpmjib.execute-api.us-east-1.amazonaws.com/default/reddit-mcp-bot"

# MCP manifest describing commands and params
manifest = {
    "name": "reddit-poster",
    "version": "1.0",
    "description": "MCP server for Reddit posting",
    "domains": [
        {
            "name": "reddit_posting",
            "commands": [
                {
                    "name": "create_post",
                    "description": "Create a Reddit post in a specified subreddit",
                    "parameters": [
                        {"name": "subreddit", "type": "string", "description": "Subreddit name"},
                        {"name": "title", "type": "string", "description": "Post title"},
                        {"name": "selftext", "type": "string", "description": "Post body text"},
                        {"name": "require_approval", "type": "boolean", "description": "Require approval before posting"}
                    ]
                }
            ]
        }
    ]
}

@app.route("/mcp/manifest.json")
def manifest_route():
    return jsonify(manifest)

@app.route("/mcp", methods=["POST"])
def mcp_handler():
    body = request.json

    domain = body.get("domain")
    command = body.get("command")
    params = body.get("parameters", {})

    if domain != "reddit_posting" or command != "create_post":
        return jsonify({"error": "Unsupported domain or command"}), 400

    # Prepare payload for Lambda
    lambda_payload = {
        "action": "post",
        "subreddit": params.get("subreddit", "test"),
        "title": params.get("title", "Default Title"),
        "selftext": params.get("selftext", ""),
        "require_approval": params.get("require_approval", False)
    }

    # Call the Lambda API
    response = requests.post(LAMBDA_URL, json=lambda_payload)
    if response.status_code == 200:
        lambda_response = response.json()
        return jsonify({
            "type": "action_result",
            "result": lambda_response
        })
    else:
        return jsonify({
            "error": "Lambda API call failed",
            "status_code": response.status_code,
            "response": response.text
        }), 500

if __name__ == "__main__":
    import os
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        print("Starting server with HTTPS on port 8443...")
        app.run(host="0.0.0.0", port=8443, ssl_context=('cert.pem', 'key.pem'))
    else:
        print("Starting server with HTTP on port 8282...")
        app.run(host="0.0.0.0", port=8282)
