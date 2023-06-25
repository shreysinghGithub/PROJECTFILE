'''
This is the main file for the application. 
It contains the routes and views for the application.
'''

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import opendb, DB_URL
from database import User, Profile
from db_helper import *
from validators import *
from logger import log
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from werkzeug.utils import secure_filename
import os
import joblib


def load_data():
    df = pd.read_csv('laptop_data.csv')
    return df

def create_inp_df(company, typename, ram, weight,touchscreen, ips, ppi, cpubrand, hdd, ssd, gpubrand,os):
    df = pd.DataFrame(columns=['Company', 'TypeName', 'Ram', 'Weight', 'Touchscreen', 'Ips', 'ppi', 'Cpu brand', 'HDD', 'SSD', 'Gpu brand', 'os'])
    df.loc[0] = [company, typename, ram, weight, touchscreen, ips, ppi, cpubrand, hdd, ssd, gpubrand, os]
    return df

def load_model(model_file):
    loaded_model = joblib.load(model_file)
    return loaded_model

def predict_price(model,df):
    predictions = model.predict(df)
    return predictions


app = Flask(__name__)
app.secret_key  = '()*(#@!@#)'
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

def session_add(key, value):
    session[key] = value

def save_file(file):
    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    return path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    if not validate_email(email):
        flash('Invalid email', 'danger')
        return redirect(url_for('index'))
    if not validate_password(password):
        flash('Invalid password', 'danger')
        return redirect(url_for('index'))
    db = opendb()
    user = db.query(User).filter_by(email=email).first()
    if user is not None and user.verify_password(password):
        session_add('user_id', user.id)
        session_add('user_name', user.name)
        session_add('user_email', user.email)
        session_add('isauth', True)
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid email or password', 'danger')
        return redirect(url_for('index'))
    
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    cpassword = request.form.get('cpassword')
    db = opendb()
    if not validate_username(name):
        flash('Invalid username', 'danger')
        return redirect(url_for('index'))
    if not validate_email(email):
        flash('Invalid email', 'danger')
        return redirect(url_for('index'))
    if not validate_password(password):
        flash('Invalid password', 'danger')
        return redirect(url_for('index'))
    if password != cpassword:
        flash('Passwords do not match', 'danger')
        return redirect(url_for('index'))
    if db.query(User).filter_by(email=email).first() is not None    :
        flash('Email already exists', 'danger')
        return redirect(url_for('index'))
    elif db.query(User).filter_by(name=name).first() is not None:
        flash('Username already exists', 'danger')
        return redirect(url_for('index'))
    else:
        db_save(User(name=name, email=email, password=password))
        flash('User registered successfully', 'success')
        return redirect(url_for('index'))
    
@app.route('/dashboard')
def dashboard():
    if session.get('isauth'):
        return render_template('dashboard.html')
    else:
        return redirect(url_for('index'))

@app.route('/profile/add', methods=['POST'])
def add_profile():
    if session.get('isauth'):
        user_id = session.get('user_id')
        city = request.form.get('city')
        gender = request.form.get('gender')
        avatar = request.files.get('avatar')
        db = opendb()
        if not validate_city(city):
            flash('Invalid city', 'danger')
            return redirect(url_for('dashboard'))
        if not validate_avatar(avatar):
            flash('Invalid avatar file', 'danger')
            return redirect(url_for('dashboard'))
        if db.query(Profile).filter_by(user_id=user_id).first() is not None:
            flash('Profile already exists', 'danger')
            return redirect(url_for('view_profile'))
        else:
            db_save(Profile(user_id = user_id, city=city, gender=gender, avatar=save_file(avatar)))
            flash('Profile added successfully', 'success')
            return redirect(url_for('dashboard'))
    else:
        flash('Please login to continue', 'danger')
        return redirect(url_for('index'))
        
@app.route('/profile/edit', methods=['POST'])
def edit_profile():
    if session.get('isauth'):
        profile = db_get_by_field(Profile, user_id=session.get('user_id'))
        if profile is not None:
            profile.city = request.form.get('city')
            profile.gender = request.form.get('gender')
            avatar = request.files.get('avatar')
            if avatar is not None:
                profile.avatar = save_file(avatar)
            db_save(profile)
            flash('Profile updated successfully', 'success')
            return redirect(url_for('dashboard'))
    else:
        flash('Please login to continue', 'danger')
        return redirect(url_for('index'))    

@app.route('/profile')
def view_profile():
    if session.get('isauth'):
        profile = db_get_by_field(Profile, user_id=session.get('user_id'))
        if profile is not None:
            return render_template('profile.html', profile=profile)
        else:
            flash(f'<a class="text-danger" href="#" data-bs-toggle="modal" data-bs-target="#profileModal">Create a profile</a>', 'danger')
            return redirect(url_for('dashboard'))
    else:
        flash('Please login to continue', 'danger')
        return redirect(url_for('index'))
    
@app.route('/predict', methods=['GET', 'POST'])
def predict_laptop_price_form():
    companies = ['Apple', 'HP', 'Acer', 'Asus', 'Dell', 'Lenovo', 'Chuwi', 'MSI', 'Microsoft', 'Toshiba', 'Huawei', 'Xiaomi', 'Vero', 'Razer', 'Mediacom', 'Samsung', 'Google', 'Fujitsu', 'LG']
    types = ['Ultrabook', 'Notebook', 'Netbook', 'Gaming', '2 in 1 Convertible', 'Workstation']
    cpu_brands = ['Intel Core i5', 'Intel Core i7', 'AMD Processor', 'Intel Core i3', 'Other Intel Processor']
    oses = ['Mac', 'Others/No OS/Linux', 'Windows']
    gpu_brands = ['Intel', 'AMD', 'Nvidia']
    if request.method == 'POST':
        ram = request.form.get('ram')
        hdd = request.form.get('hdd')
        ssd = request.form.get('ssd')
        ppi = request.form.get('ppi')
        weight = request.form.get('weight')
        ips = request.form.get('ips')
        touchscreen = request.form.get('touchscreen')
        os = request.form.get('os')
        company = request.form.get('company')
        laptop_type = request.form.get('typename')
        brand = request.form.get('brand')
        gpu = request.form.get('gpu')
        try:
            df = create_inp_df(company, laptop_type, ram, weight,touchscreen, ips, ppi, brand, hdd, ssd, gpu,os)
            print(df)
            model = load_model('laptop_price_prediction_model.pkl')
            prediction = predict_price(model,df)
            session['prediction'] = np.exp(prediction[0])
            flash(f'Predicted price is {prediction[0]}', 'success')
            return redirect('result')
        except Exception as e:
            flash(f'Error occured: {e}', 'danger')
            return redirect('predict')
    return render_template('predict.html', 
                        companies=companies,
                        types=types,
                        cpu_brands=cpu_brands,
                        oses=oses,
                        gpu_brands=gpu_brands)

@app.route('/result')
def result():
    if 'prediction' not in session:
        return redirect('predict')
    return render_template('result.html', price=session.get('prediction'))

@app.route('/graph')
def graph():
    df = load_data()
    fig1 = px.area(df['Price'],title='Price',width=800,height=400,color_discrete_sequence=['#F63366'],template='plotly_dark')

    df['Company'].value_counts()
    fig2 = px.histogram(df,x='Company',title='Company',width=800,height=400,template='plotly_dark',color_discrete_sequence=['#F63366'])

    fig3 = px.box(x=df['Company'],y=df['Price'],title='Price vs Company',width=800,height=400,color_discrete_sequence=['#FFC300'],template='plotly_dark')
 
    df['TypeName'].value_counts()
    fig4 = px.pie(df,names='TypeName',title='TypeName',width=800,height=400,template='plotly_dark',color_discrete_sequence=px.colors.sequential.RdBu)

    fig5 = px.violin(x=df['TypeName'],y=df['Price'],title='Price vs TypeName',width=800,height=400,color_discrete_sequence=['#900C3F'],template='plotly_dark')

    fig6 = px.box(df['Inches'])

    fig7 = px.scatter(x=df['Inches'],y=df['Price'],title='Price vs Inches',width=800,height=400,color_discrete_sequence=['#FFC300'],template='plotly_dark')

    return render_template('graph.html', 
                           fig1=fig1.to_html(), 
                           fig2=fig2.to_html(), 
                           fig3=fig3.to_html(), 
                           fig4=fig4.to_html(), 
                           fig5=fig5.to_html(),
                           fig6=fig6.to_html(),
                           fig7=fig7.to_html())
                        
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8000, debug=True)
 