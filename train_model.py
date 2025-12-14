import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

# =============================================================================
# PHASE 2: TRAINING THE AI MODEL
# This script is run ONLY ONCE to create the 'brain' of the system.
# =============================================================================

def train():
    print("1. Loading the dataset...")
    try:
        # Load the CSV file into a pandas DataFrame
        df = pd.read_csv('Crop_recommendation.csv')
        print(f"   Success! Dataset loaded with {len(df)} records.")
    except FileNotFoundError:
        print("   ERROR: 'Crop_recommendation.csv' not found. Please download it first.")
        return

    # ---------------------------------------------------------
    # STEP A: Preparing the Data
    # The dataset has columns: N, P, K, temperature, humidity, ph, rainfall, label
    # We split it into 'Inputs' (X) and 'Answers' (y)
    # ---------------------------------------------------------
    
    # X = All columns EXCEPT the label (The ingredients)
    X = df.drop('label', axis=1)
    
    # y = The label column (The target crop we want to predict)
    y = df['label']

    # Split data: 80% for training (learning), 20% for testing (exam)
    # random_state=42 ensures we get the same split every time we run this
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # ---------------------------------------------------------
    # STEP B: The Algorithm (Random Forest)
    # Question: "Why Random Forest?"
    # Answer: "It uses multiple Decision Trees (voting mechanism) which gives 
    # higher accuracy and reduces overfitting compared to a single Decision Tree."
    # ---------------------------------------------------------
    print("2. Training the Random Forest model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train) # This is where the learning happens

    # ---------------------------------------------------------
    # STEP C: Evaluation
    # We test the model to see how smart it is
    # ---------------------------------------------------------
    accuracy = model.score(X_test, y_test)
    print(f"   Model Accuracy: {accuracy * 100:.2f}%")

    # ---------------------------------------------------------
    # STEP D: Saving the Brain
    # We use 'pickle' to save the trained model to a file.
    # The website will load this file later to make predictions.
    # ---------------------------------------------------------
    filename = 'crop_recommendation.pkl'
    with open(filename, 'wb') as file:
        pickle.dump(model, file)
    
    print(f"3. Success! Model saved as '{filename}'.")
    print("   You can now delete this script if you want, but keep the .pkl file.")

if __name__ == '__main__':
    train()