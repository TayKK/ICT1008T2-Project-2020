import os
from flask import Flask, render_template, url_for, json, request,current_app as app, jsonify
import pandas as pd
from geopy.geocoders import Nominatim
from Forms import Locations
from subprocess import Popen

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fba483ff5f287007f4994b0b7ec9366c'

@app.route('/', methods=['GET','POST'])
def home():
    nom = Nominatim(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36")
    form = Locations()

    refresh_count = 0 # to check times refreshed 

    if form.validate_on_submit():
        refresh_count += 1
        #get start lat and long from location name using geocoder
        n = nom.geocode(form.start_point.data, "Singapore")
        start_lat = n.latitude
        start_long = n.longitude

        #get end lat and long from location name using geocoder
        n = nom.geocode(form.end_point.data, "Singapore")
        end_lat = n.latitude
        end_long = n.longitude

        #define shell commands to run python code generating maps 
        walk_command = "python walkonly.py " + str(start_lat) + " " + str(start_long) + " " + str(end_lat) + " " + str(end_long)
        transport_command = "python main.py " + str(start_lat) + " " + str(start_long) + " " + str(end_lat) + " " + str(end_long)

        #run shell commands
        commands = [walk_command, transport_command]
        procs = [ Popen(i) for i in commands ]
        for p in procs:
            p.wait()

        return render_template("gui.html", start_lat=start_lat, start_long=start_long, end_lat=end_lat, end_long=end_long, form=form, refresh_count=refresh_count)
    else:
        return render_template("gui.html", form=form, refresh_count=refresh_count)

@app.route('/walk')
def walking_map():
    return render_template("walkonly.html", title="walk")

@app.route('/transport')
def transport_map():
    return render_template("transport.html", title="transport")

@app.route('/clean')
def clean_map():
    return render_template("clean.html", title="clean_map")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
