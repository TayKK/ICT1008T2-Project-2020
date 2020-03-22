from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

class Locations(FlaskForm):
    start_point = StringField('Start Point')
    end_point = StringField('End Point')
    submit = SubmitField('Find Way')