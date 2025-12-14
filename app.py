from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import numpy as np
import random # For generating OTP

# Import our custom modules
from config import Config
from models import db, User, History
# Note: We imported the new functions here
from utils import get_soil_profile, get_weather_data,validate_location_hierarchy
from utils import process_voice_command
# ---------------------------------------------------
# SETUP
# ---------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Load the AI Model ONCE
with open('crop_recommendation.pkl', 'rb') as f:
    model = pickle.load(f)

# ---------------------------------------------------
# ROUTES
# ---------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('login'))

# --- AUTHENTICATION: REGISTER -> OTP -> LOGIN ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        # 1. Check if user already exists
        if User.query.filter_by(phone=phone).first():
            flash('Phone number already registered. Please Login.')
            return redirect(url_for('login'))
        
        # 2. Generate OTP (Random 4 digit number)
        otp = str(random.randint(1000, 9999))
        
        # 3. Store data in SESSION (Temporary Memory)
        # We do NOT save to Database yet. We wait for OTP verification.
        session['temp_user'] = {
            'username': username,
            'phone': phone,
            'password': password, # Will be hashed later
            'otp': otp
        }
        
        # 4. Simulate SMS Sending (For Demo Purpose)
        print("----------------------------------------------------")
        print(f" [SMS GATEWAY] OTP sent to {phone}: {otp}")
        print("----------------------------------------------------")
        flash(f"OTP sent to your mobile: {otp}") # Shown on screen for demo
        
        return redirect(url_for('verify_otp'))
        
    return render_template('register.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    # Security: If no temp user in session, go back to register
    if 'temp_user' not in session:
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        stored_data = session['temp_user']
        
        if entered_otp == stored_data['otp']:
            # 5. OTP Verified! Now create the account.
            
            # Secure Hashing (Encryption)
            hashed_pw = generate_password_hash(stored_data['password'], method='pbkdf2:sha256')
            
            new_user = User(
                username=stored_data['username'],
                phone=stored_data['phone'],
                password_hash=hashed_pw # Storing Hash, not plain text
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            # Login the user and clear the session
            login_user(new_user)
            session.pop('temp_user', None)
            
            flash('Registration Successful! Welcome to Smart Kisan.')
            return redirect(url_for('home'))
        else:
            flash('Invalid OTP. Please try again.')
            
    return render_template('verify_otp.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        user = User.query.filter_by(phone=phone).first()
        
        # Security: Check Hash instead of plain text
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid Phone or Password')
            
    return render_template('login.html')


@app.route('/ask_agent', methods=['POST'])
def ask_agent():
    data = request.get_json()
    user_text = data.get('text')
    lang_code = data.get('language')
    
    # Get context from screen (might be empty)
    district = data.get('district')
    
    # CRITICAL CHANGE: Do NOT default to "Nagpur" here. 
    # Pass 'None' if district is empty so utils.py knows it's missing.
    target_city = district if district and district != "Select District" else None

    response_data = process_voice_command(user_text, lang_code, target_city)
    
    return {
        'answer': response_data['text'],
        'audio_url': url_for('static', filename='audio/' + response_data['audio'])
    }
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- THE MAIN PREDICTION LOGIC (UPDATED) ---
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    # 1. Get New Detailed Inputs from Form
    district = request.form.get('district')
    village = request.form.get('village')
    pincode = request.form.get('pincode')
    terrain = request.form.get('terrain') # river, mountain, plain
    soil_color = request.form.get('soil_color')
    
    # 2. Get OPTIONAL Inputs (N, P, K, pH)
    val_n = request.form.get('N')
    val_p = request.form.get('P')
    val_k = request.form.get('K')
    val_ph = request.form.get('ph')
    
    # --- NEW VALIDATION STEP ---
    # Check if Village actually belongs to District (roughly)
    is_valid_location = validate_location_hierarchy(district, village)
    
    # Basic Validation
    if not pincode.isdigit() or len(pincode) != 6:
        flash("Invalid Pincode. Please enter 6 digits.")
        return redirect(url_for('home'))

    # 2. Get Logic Data (Using updated utils.py)
    # Note: We now pass 'terrain' to adjust soil nutrients!
    # 3. Get Logic Data (Passing ALL inputs now)
    # The function will prioritize user values (val_n) if they exist!
    soil_data = get_soil_profile(soil_color, terrain, val_n, val_p, val_k, val_ph)
    
    # We use District for weather now (more accurate than generic city)
    weather = get_weather_data(district)
    
    # 3. Prepare Data for AI [N, P, K, Temp, Hum, pH, Rain]
    input_features = [
        soil_data['N'], 
        soil_data['P'], 
        soil_data['K'],
        weather['temp'],
        weather['humidity'],
        soil_data['ph'],
        weather['rainfall']
    ]
    
    features_array = np.array([input_features])
    
    # 4. Make Prediction
    prediction = model.predict(features_array)
    final_crop = prediction[0]
    
    # 5. Save Detailed History to Database
    new_report = History(
        district=district,
        village=village,
        pincode=pincode,
        terrain=terrain,
        soil_color=soil_color,
        predicted_crop=final_crop,
        farmer=current_user
    )
    db.session.add(new_report)
    db.session.commit()
    
    # --- ADDED FEATURES ---
    # 6. Generate Voice Report & Roadmap
    # audio_filename = generate_voice_report(final_crop, weather)
    # farming_plan = get_crop_plan(final_crop)

    # 7. Show Result
    return render_template('result.html', 
                           crop=final_crop, 
                           weather=weather, 
                           soil=soil_color,
                        #    audio_file=audio_filename,
                        #    plan=farming_plan
                        )

@app.route('/history')
@login_required
def history():
    # 1. Fetch data for the CURRENT USER only
    # 2. Sort by 'timestamp' descending (Newest first)
    # We changed 'History.timestamp' to 'History.created_at' here:
    user_reports = History.query.filter_by(farmer=current_user)\
                                .order_by(History.created_at.desc())\
                                .all()
    
    # Debugging: Print to terminal to see if data exists
    print(f"--- FETCHING HISTORY FOR {current_user.username} ---")
    print(f"Found {len(user_reports)} reports.")

    # 3. Pass it to the template as 'history' variable
    return render_template('history.html', history=user_reports)

@app.route('/report/<int:report_id>')
@login_required
def view_report(report_id):
    # 1. Fetch the specific report
    report = History.query.get_or_404(report_id)
    
    # 2. Re-generate necessary data (Plan & Audio)
    # farming_plan = get_crop_plan(report.predicted_crop)
    # We fetch current weather again since we didn't save historical weather
    # (Or you can pass a dummy weather object if you prefer)
    weather = get_weather_data(report.district) 
    
    # 3. Render the Result Page with this data
    return render_template('result.html', 
                           crop=report.predicted_crop, 
                           weather=weather, 
                           soil=report.soil_color,
                        #    plan=farming_plan,
                           # Pass None for audio to skip generating a new file unnecessarily
                           audio_file=None)
    
# In app.py

#---- for indian time data retrival ---#
from datetime import timedelta
@app.template_filter('ist_date')
def ist_date_filter(dt):
    """Just formats the date since DB already has IST time"""
    if dt is None:
        return ""
    # We REMOVED the line: ist_time = dt + timedelta(...)
    # Now we just format the existing time
    return dt.strftime('%d %b %Y, %I:%M %p')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)