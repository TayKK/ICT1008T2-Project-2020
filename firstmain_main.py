import os
from flask import Flask, render_template, url_for, json, request,current_app as app, jsonify
import pandas as pd

app = Flask(__name__)

@app.route('/')
def map():
    return render_template('gui.html')
    #return render_template("algo.html", title="About") 

@app.route("/results.html", methods=["GET", "POST"])
def process():
    data = request.form
    return render_template("results.html", data=data)

@app.route('/map')
def map2():
    return render_template("Algo.html", title="About")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

