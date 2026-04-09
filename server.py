from flask import Flask, request, jsonify

app = Flask(__name__)

@app.before_request
def log_request_info():
    print("Headers:", dict(request.headers))
    print("Data:", request.get_data())
    print("Form:", request.form)
    print("Args:", request.args)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def echo(path):
    return jsonify({
        "headers": dict(request.headers),
        "data": request.get_json(silent=True),
        "form": request.form,
        "args": request.args
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)