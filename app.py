from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from langgraph_builder import graph, State

app = Flask(__name__)
CORS(app)

@app.route("/api/query", methods=["POST"])
def process_query():
    data = request.get_json()
    nlq = data.get("query", "")

    try:
        state = graph.invoke({"query": nlq})
        print("INTENT:", state["intent"])
        print("SQL:", state["sql"])
        print("RESULT:", state["result"])

        if state["error"]:
            print("ERROR:", state["error"])
            return jsonify({"result": "Internal error, please try again."}), 500

        return jsonify({"result": state["result"]})


    except Exception as e:
        print("LangGraph error:", e)
        return jsonify({"result": "Internal error with the server. Check your internet connection and try again."}), 500

@app.route("/")
def home():
    return render_template('interface.html')

@app.route("/favicon.ico")
def favicon():
    return '', 204

if __name__ == "__main__":
    app.run()
