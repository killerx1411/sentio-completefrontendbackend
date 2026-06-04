from flask import jsonify

def success_response(data=None, message="Success", status_code=200):
    """
    Returns a standardized JSON success response.
    """
    response = {
        "status": "success",
        "message": message
    }
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code

def error_response(message="An error occurred", status_code=400):
    """
    Returns a standardized JSON error response.
    """
    return jsonify({
        "status": "error",
        "message": message
    }), status_code
