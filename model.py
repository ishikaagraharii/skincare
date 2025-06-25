import pandas as pd
import numpy as np
import joblib

# Load saved model pipeline, label encoders, and metadata
pipeline = joblib.load('skincare_recommendation_model.pkl')
le_dict = joblib.load('label_encoders.pkl')
model_metadata = joblib.load('model_metadata.pkl')
feature_cols = model_metadata['features']


def create_skincare_features(df: pd.DataFrame) -> pd.DataFrame:
    df_enhanced = df.copy()

    # Pollution severity categories
    df_enhanced['pollution_level'] = pd.cut(
        df_enhanced['AQI'],
        bins=[0, 50, 100, 150, 200, 300,
              float('inf')],
        labels=[
            'Good', 'Moderate', 'USG', 'Unhealthy', 'Very_Unhealthy',
            'Hazardous'
        ])

    # Humidity categories
    df_enhanced['humidity_category'] = pd.cut(
        df_enhanced['Humidity'],
        bins=[0, 30, 70, 100],
        labels=['Dry', 'Normal', 'Humid'])

    # Temperature categories
    df_enhanced['temp_category'] = pd.cut(
        df_enhanced['Temperature'],
        bins=[0, 10, 25, 35, float('inf')],
        labels=['Cold', 'Cool', 'Warm', 'Hot'])

    # Skin stress score
    df_enhanced['skin_stress_score'] = (
        df_enhanced['AQI'] * 0.4 + df_enhanced['PM2_5'] * 0.3 +
        df_enhanced['PM10'] * 0.2 + abs(df_enhanced['Humidity'] - 50) * 0.1)

    # PM ratio and temp-humidity interaction
    df_enhanced['pm_ratio'] = df_enhanced['PM2_5'] / (df_enhanced['PM10'] +
                                                      1e-6)
    df_enhanced['temp_humidity_interaction'] = (df_enhanced['Temperature'] *
                                                df_enhanced['Humidity'] / 100)

    return df_enhanced


def recommend_product_from_environment(data_dict: dict) -> dict:
    """
    Accepts a dict with keys: 'AQI', 'PM2_5', 'PM10',
    'Temperature', 'Humidity', 'WindSpeed'.
    Returns recommendation + probabilities + analysis.
    """
    input_df = pd.DataFrame([data_dict])
    enhanced = create_skincare_features(input_df)

    # Encode categorical features
    for cat_col, le in le_dict.items():
        col_enc = f"{cat_col}_encoded"
        try:
            enhanced[col_enc] = le.transform(enhanced[cat_col].astype(str))
        except ValueError:
            enhanced[col_enc] = 0

    # Select the same features used during training
    X_input = enhanced[feature_cols]

    # Predict
    pred = pipeline.predict(X_input)[0]
    proba = pipeline.predict_proba(X_input)[0]
    confidence = float(np.max(proba))

    # Build response
    return {
        'recommendation': pred,
        'confidence': confidence,
        'probabilities': dict(zip(pipeline.classes_, proba)),
        'environmental_analysis': {
            'pollution_level': enhanced['pollution_level'].iloc[0],
            'humidity_category': enhanced['humidity_category'].iloc[0],
            'temp_category': enhanced['temp_category'].iloc[0],
            'skin_stress_score': float(enhanced['skin_stress_score'].iloc[0])
        }
    }
