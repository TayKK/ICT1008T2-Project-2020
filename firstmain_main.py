import os
from flask import Flask, render_template, url_for, json, request,current_app as app, jsonify
import pandas as pd
from geopy.geocoders import Nominatim
from Forms import Locations


app = Flask(__name__)
app.config['SECRET_KEY'] = 'fba483ff5f287007f4994b0b7ec9366c'


@app.route('/', methods=['GET','POST'])
def home():
    nom = Nominatim(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36")
    form = Locations()

    if form.validate_on_submit():
        n = nom.geocode(form.start_point.data, "Singapore")
        start_lat = n.latitude
        start_long = n.longitude
        n = nom.geocode(form.end_point.data, "Singapore")
        end_lat = n.latitude
        end_long = n.longitude
        command = "python walk.py " + str(start_lat) + " " + str(start_long) + " " + str(end_lat) + " " + str(end_long)
        os.system(command)
        return render_template("gui.html", start_lat=start_lat, start_long=start_long, end_lat=end_lat, end_long=end_long, form=form)
    else:
        return render_template("gui.html", form=form)

@app.route('/walk')
def map():
    return render_template("walk.html", title="walk")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

