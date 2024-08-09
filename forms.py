from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, PasswordField 
from wtforms.validators import DataRequired, Length, Email, EqualTo

class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=4, max=320)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=4, max=32)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    department = SelectField('Department', choices=[('mechanical', 'mechanical '), ('electrical', 'electrical'), ('operational', 'operational'),('other', 'none')], validators=[DataRequired()])
    submit = SubmitField('Sign Up')
 

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=4, max=32)])
    submit = SubmitField('Login')

class Csrf(FlaskForm):
    pass
