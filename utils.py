import os
import uuid
from gtts import gTTS
import requests
import random
import math 
from googletrans import Translator
from datetime import datetime


# =============================================================================
# HELPER 1: SOIL TRANSLATOR (Visual -> Scientific)
# Farmers know color, not N-P-K values. We map them here.
# =============================================================================
# --- ADD THIS NEW FUNCTION ---
def analyze_weather_impact(temp, humidity, rainfall):
    desc = ""
    tip = ""
    
    # 1. Temperature Check
    if temp > 35:
        desc += "It is very hot. "
        tip += "Irrigate crops in the evening to avoid evaporation. "
    elif temp < 15:
        desc += "It is cold. "
        tip += "Cover young crops to protect from frost. "
    else:
        desc += "Temperature is good for growth. "
        # If temp is normal, we didn't have a tip before. Now we do:
        tip += "Maintain regular field observation. "

    # 2. Rainfall Check
    if rainfall > 5:
        desc += "Rain is expected. "
        tip += "Do not spray fertilizers today as they will wash away. "
    else:
        desc += "Sky is clear. "
        if humidity < 40:
            tip += "Soil moisture is low, apply light irrigation. "
        else:
            tip += "Weather is favorable for farm work. "

    return desc, tip

def get_soil_profile(soil_color, terrain, user_n=None, user_p=None, user_k=None, user_ph=None):
    
    if not soil_color:
        soil_color = 'black' # Default fallback if user selects nothing
        
    # 1. Base Values from Soil Color
    base_map = {
        'black': {'N': 50, 'P': 50, 'K': 50, 'ph': 7.0},
        'red':   {'N': 40, 'P': 30, 'K': 20, 'ph': 5.5},
        'clay':  {'N': 60, 'P': 40, 'K': 30, 'ph': 6.0},
        'sandy': {'N': 20, 'P': 20, 'K': 20, 'ph': 6.5},
    }
    data = base_map.get(soil_color.lower(), {'N': 40, 'P': 40, 'K': 40, 'ph': 6.5})

    # 2. ADJUSTMENT: Logic based on Terrain (The "Real World" factor)
    if terrain == 'river':
        # River banks have fertile alluvial soil
        data['N'] += 20  # More Nitrogen
        data['ph'] -= 0.5 # Slightly more acidic due to organic matter
    elif terrain == 'mountain':
        # Mountain soil leaches nutrients
        data['N'] -= 10
        data['K'] -= 10
    
    # Ensure values don't go below zero
    for key in data:
        if data[key] < 0: data[key] = 5
        
    # 3. OVERWRITE WITH REAL DATA (The "Accuracy" Layer)
    # If user provided a number, use it. Otherwise, keep the estimate.
    if user_n and user_n.strip(): 
        data['N'] = float(user_n)
        
    if user_p and user_p.strip(): 
        data['P'] = float(user_p)
        
    if user_k and user_k.strip(): 
        data['K'] = float(user_k)
        
    if user_ph and user_ph.strip(): 
        data['ph'] = float(user_ph)
        
    return data

# ... (Keep existing get_weather_data and voice functions) ...

# =============================================================================
# HELPER 2: WEATHER FETCHING (Robust)
# Fetches live weather or uses historical averages if API fails.
# =============================================================================
# utils.py

# ... (Keep get_soil_profile as is) ...

def get_weather_data(city):
    try:
        # 1. Get Coordinates
        geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_response = requests.get(geocoding_url, timeout=5).json()
        
        if 'results' in geo_response:
            lat = geo_response['results'][0]['latitude']
            lon = geo_response['results'][0]['longitude']
            
            # 2. FETCH REAL RAINFALL DATA (The Fix)
            # We added '&daily=precipitation_sum' to the URL
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&"
                f"current_weather=true&"
                f"daily=precipitation_sum&"  # <--- Asking for Rain Amount
                f"timezone=auto"
            )
            
            weather_data = requests.get(weather_url, timeout=5).json()
            
            # 3. Extract the Data
            # Temperature comes from 'current_weather'
            temp = weather_data['current_weather']['temperature']
            
            # Rainfall comes from 'daily' (Index 0 is Today)
            rainfall = weather_data['daily']['precipitation_sum'][0]
            
            # Humidity is not in this specific API call, so we estimate it based on rain
            # (If it's raining, humidity is high. If dry, humidity is lower)
            if rainfall > 5.0:
                humidity = 85.0
            else:
                humidity = 40.0 # Winter/Dry default
            
            return {'temp': temp, 'humidity': humidity, 'rainfall': rainfall}
            
    except Exception as e:
        print(f"API Error: {e}")
    
    # Fallback only if Internet is totally dead
    return {'temp': 25.0, 'humidity': 50.0, 'rainfall': 10.0}


# ... (keep other functions) ...

def validate_location_hierarchy(district, village):
    """
    Advanced Logic: Checks if the Village is roughly near the District.
    Uses Haversine Distance Formula.
    """
    try:
        # 1. Get Coordinates of District
        url_d = f"https://geocoding-api.open-meteo.com/v1/search?name={district}&count=1"
        res_d = requests.get(url_d).json()
        
        # 2. Get Coordinates of Village
        url_v = f"https://geocoding-api.open-meteo.com/v1/search?name={village}&count=1"
        res_v = requests.get(url_v).json()
        
        if 'results' in res_d and 'results' in res_v:
            lat1 = res_d['results'][0]['latitude']
            lon1 = res_d['results'][0]['longitude']
            
            lat2 = res_v['results'][0]['latitude']
            lon2 = res_v['results'][0]['longitude']
            
            # 3. Calculate Distance (Haversine Formula)
            R = 6371 # Earth radius in km
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat/2) * math.sin(dLat/2) + \
                math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
                math.sin(dLon/2) * math.sin(dLon/2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = R * c # Distance in KM
            
            print(f"DEBUG: Distance between {village} and {district} is {distance:.2f} km")
            
            # If Village is more than 150km away from District center, flag it!
            if distance > 150:
                return False # Invalid
            return True # Valid
            
        # If API can't find them, we assume it's valid to be safe (Benefit of doubt)
        return True
        
    except Exception as e:
        print(f"Validation Error: {e}")
        return True
    

# Initialize Translator
import requests
import random
import os
import uuid  # <--- THIS WAS LIKELY MISSING
from gtts import gTTS
from googletrans import Translator
from datetime import datetime
import math

# Initialize Translator
# robust: If googletrans fails, we handle it in the try-except block
try:
    translator = Translator()
except:
    translator = None

# =============================================================================
# 1. SOIL & LOCATION LOGIC
# =============================================================================
def validate_location_hierarchy(district, village):
    try:
        url_d = f"https://geocoding-api.open-meteo.com/v1/search?name={district}&count=1"
        res_d = requests.get(url_d, timeout=5).json()
        
        url_v = f"https://geocoding-api.open-meteo.com/v1/search?name={village}&count=1"
        res_v = requests.get(url_v, timeout=5).json()
        
        if 'results' in res_d and 'results' in res_v:
            lat1 = res_d['results'][0]['latitude']
            lon1 = res_d['results'][0]['longitude']
            lat2 = res_v['results'][0]['latitude']
            lon2 = res_v['results'][0]['longitude']
            
            # Haversine Distance
            R = 6371
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat/2) * math.sin(dLat/2) + \
                math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
                math.sin(dLon/2) * math.sin(dLon/2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = R * c
            
            if distance > 150: return False
            return True
        return True # Default valid if API fails
    except:
        return True

def get_soil_profile(soil_color, terrain, user_n=None, user_p=None, user_k=None, user_ph=None):
    if not soil_color: soil_color = 'black'
    
    base_map = {
        'black': {'N': 50, 'P': 50, 'K': 50, 'ph': 7.0},
        'red':   {'N': 40, 'P': 30, 'K': 20, 'ph': 5.5},
        'clay':  {'N': 60, 'P': 40, 'K': 30, 'ph': 6.0},
        'sandy': {'N': 20, 'P': 20, 'K': 20, 'ph': 6.5},
    }
    data = base_map.get(soil_color.lower(), {'N': 40, 'P': 40, 'K': 40, 'ph': 6.5})

    if terrain == 'river':
        data['N'] += 20
        data['ph'] -= 0.5
    elif terrain == 'mountain':
        data['N'] -= 10
        data['K'] -= 10

    if user_n and str(user_n).strip(): data['N'] = float(user_n)
    if user_p and str(user_p).strip(): data['P'] = float(user_p)
    if user_k and str(user_k).strip(): data['K'] = float(user_k)
    if user_ph and str(user_ph).strip(): data['ph'] = float(user_ph)

    return data

def get_weather_data(city):
    try:
        # Geocoding
        geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_response = requests.get(geocoding_url, timeout=5).json()
        
        if 'results' in geo_response:
            lat = geo_response['results'][0]['latitude']
            lon = geo_response['results'][0]['longitude']
            
            # Weather
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&"
                f"current_weather=true&daily=precipitation_sum&timezone=auto"
            )
            weather_data = requests.get(weather_url, timeout=5).json()
            
            temp = weather_data['current_weather']['temperature']
            rainfall = weather_data['daily']['precipitation_sum'][0]
            
            humidity = 85.0 if rainfall > 5.0 else 40.0
            
            return {'temp': temp, 'humidity': humidity, 'rainfall': rainfall}
            
    except Exception as e:
        print(f"Weather API Error: {e}")
    
    return {'temp': 25.0, 'humidity': 50.0, 'rainfall': 10.0}

# =============================================================================
# 2. VOICE & REPORT FEATURES
# =============================================================================

def generate_voice_report(crop_name, weather, language='en'):
    # Ensure folder exists
    os.makedirs(os.path.join('static', 'audio'), exist_ok=True)
    
    text = f"Namaste. The best crop is {crop_name}. Temperature is {weather['temp']} degrees."
    filename = f"report_{uuid.uuid4().hex}.mp3"
    save_path = os.path.join('static', 'audio', filename)
    
    try:
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(save_path)
        return filename
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def get_crop_plan(crop_name):
    plans = {
        'rice': [{'day': 1, 'task': 'Sowing', 'detail': 'Prepare Nursery'}],
        'cotton': [{'day': 1, 'task': 'Sowing', 'detail': 'Plant at 2cm depth'}],
        # Add more defaults as needed
    }
    return plans.get(crop_name.lower(), [{'day': 1, 'task': 'Soil Test', 'detail': 'Check NPK'}])

# =============================================================================
# 3. AI VOICE ASSISTANT (The Deep Feature)
# =============================================================================

# --- REPLACE YOUR EXISTING process_voice_command WITH THIS ---

def process_voice_command(user_text, user_language, user_city):
    os.makedirs(os.path.join('static', 'audio'), exist_ok=True)
    
    try:
        # 1. Translate User Input to English
        english_command = user_text
        if 'en' not in user_language:
            try:
                translated = translator.translate(user_text, src=user_language, dest='en')
                english_command = translated.text
            except:
                english_command = user_text 
        
        english_command = english_command.lower()
        
        # 2. INTENT RECOGNITION & NATIVE RESPONSES
        answer_english = ""
        is_marathi = 'mr' in user_language
        is_hindi = 'hi' in user_language

        # [FEATURE 1: SMART GREETING]
        if 'hello' in english_command or 'namaste' in english_command or 'hi' in english_command:
            if is_marathi:
                # "Hello Farmer Friend! I am Smart Kisan..."
                answer_english = "Namaskar Shetkari Mitra! Mi Smart Kisan ahe. Mi tumhala pikanchi mahiti ani havamanachi mahiti deu shakto. Bola, kay madad karu?"
            elif is_hindi:
                answer_english = "Namaste Kisan Bhai! Main Smart Kisan hoon. Main mausam aur fasal ki jaankari de sakta hoon. Boliye, aaj kya madad karoon?"
            else:
                answer_english = "Namaste Farmer! I am Smart Kisan. I can help you with Weather and Crop advice. How can I help you today?"

        # [FEATURE 2: HELP / GUIDE]
        elif 'help' in english_command or 'how' in english_command or 'use' in english_command:
            if is_marathi:
                answer_english = "Shetkari Mitra, pik salla ghenyasathi, screen var tumcha Jilha nivda, ani 'Predict' button daba. Jar havaman vicharayche asel tar 'Havaaman kase ahe' ashe vichara."
            else:
                answer_english = "To get a crop recommendation, select your District on the screen and click Predict. You can also ask me about the weather."

        # [FEATURE 3: DETAILED WEATHER + TIPS]
        # [FEATURE 3: DETAILED WEATHER + TRANSLATED TIPS]
        elif 'weather' in english_command or 'rain' in english_command or 'temperature' in english_command:
            
            if user_city and user_city != "Select District":
                weather = get_weather_data(user_city)
                
                # Get the Expert Advice (in English)
                desc, tip = analyze_weather_impact(weather['temp'], weather['humidity'], weather['rainfall'])
                
                # --- TRANSLATION LOGIC FOR TIPS ---
                translated_tip = tip # Default to English
                
                if is_marathi:
                    try:
                        # Translate ONLY the advice part to Marathi
                        translated_tip = translator.translate(tip, src='en', dest='mr').text
                    except:
                        pass # Keep English if fails
                    
                    # Construct Marathi Sentence
                    answer_english = f"Sadhya {user_city} madhe taapman {weather['temp']} degree ahe. " \
                                     f"Paus padnyache praman {weather['rainfall']} millimeter ahe. " \
                                     f"Shetkari Salla: {translated_tip}" 

                elif is_hindi:
                    try:
                        # Translate ONLY the advice part to Hindi
                        translated_tip = translator.translate(tip, src='en', dest='hi').text
                    except:
                        pass 
                    
                    # Construct Hindi Sentence
                    answer_english = f"{user_city} mein abhi taapman {weather['temp']} degree hai. " \
                                     f"Baarish {weather['rainfall']} millimeter hai. " \
                                     f"Visheshagya ki Salaah: {translated_tip}"

                else:
                    # English (Default)
                    answer_english = f"In {user_city}, Temperature is {weather['temp']} degrees, Rainfall is {weather['rainfall']} mm. Humidity is {weather['humidity']}." \
                                     f"{desc} Expert Advice: {tip}"
            else:
                answer_english = "Please select a District first so I can tell you the weather."
                
        # [FEATURE 4: IDENTITY]
        elif 'who are you' in english_command:
            answer_english = "I am your Farming Assistant."

        # Fallback
        else:
            answer_english = "I did not understand. Please ask about Weather or Help."

        # 3. TRANSLATION (Skip if we used Native Strings)
        final_answer = answer_english
        # Only translate if we didn't use a native string (Simple check for 'Namaskar')
        if "Namaskar" not in answer_english and "Sadhya" not in answer_english:
            if 'en' not in user_language:
                try:
                    translated_ans = translator.translate(answer_english, src='en', dest=user_language)
                    final_answer = translated_ans.text
                except:
                    pass

        # 4. GENERATE AUDIO
        filename = f"answer_{uuid.uuid4().hex}.mp3"
        save_path = os.path.join('static', 'audio', filename)
        
        tts = gTTS(text=final_answer, lang=user_language, slow=False)
        tts.save(save_path)
        
        return {'text': final_answer, 'audio': filename}

    except Exception as e:
        print(f"VOICE ERROR: {e}")
        return {'text': "Error processing request.", 'audio': None}