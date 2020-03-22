import os
from flask import Flask, render_template, url_for, json, request,current_app as app, jsonify
import pandas as pd
from geopy.geocoders import Nominatim
from Forms import Locations


app = Flask(__name__)
app.config['SECRET_KEY'] = 'fba483ff5f287007f4994b0b7ec9366c'


@app.route('/', methods=['GET','POST'])
def home():
    nom = Nominatim(user_agent="ICT1008")
    form = Locations()

    if form.validate_on_submit():
        n = nom.geocode(form.start_point.data, "Singapore")
        start_lat = n.latitude
        start_long = n.longitude
        n = nom.geocode(form.end_point.data, "Singapore")
        end_lat = n.latitude
        end_long = n.longitude
        return render_template("gui.html", start_lat=start_lat, start_long=start_long, end_lat=end_lat, end_long=end_long, form=form)
    else:
        return render_template("gui.html", form=form)


@app.route('/map')
def map():
    return render_template("Algo.html", title="About")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

