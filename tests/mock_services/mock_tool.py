from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Store the last received request for potential inspection in tests
last_request_data = None

@app.route('/invoke', methods=['POST'])
def invoke_tool():
    """Simulates a tool being invoked."""
    global last_request_data
    print("Mock Tool Service: Received invocation request.")
    try:
        data = request.get_json()
        if not data:
            print("Mock Tool Service: Received empty or non-JSON data.")
            return jsonify({"error": "Invalid input"}), 400

        print(f"Mock Tool Service: Received data: {data}")
        last_request_data = data # Store for inspection

        # Simulate processing and return a result
        tool_result = {
            "status": "success",
            "message": "Mock tool executed successfully.",
            "input_received": data,
            "output": f"Processed arguments: {data.get('arguments', {})}"
        }
        print(f"Mock Tool Service: Returning result: {tool_result}")
        return jsonify(tool_result), 200
    except Exception as e:
        print(f"Mock Tool Service: Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/last_request', methods=['GET'])
def get_last_request():
    """Endpoint to retrieve the last request data received by /invoke (for testing)."""
    if last_request_data:
        return jsonify(last_request_data), 200
    else:
        return jsonify({"message": "No request data stored yet."}), 404

if __name__ == '__main__':
    # Use port 9001 for the mock tool service to avoid conflict with AgentKit API (8000)
    port = int(os.environ.get('PORT', 9001))
    print(f"Starting Mock Tool Service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False) # Set debug=False for production/testing