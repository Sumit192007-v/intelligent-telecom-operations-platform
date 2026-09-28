# Intelligent Telecom Operations Platform

An end-to-end telecom operations platform combining real cellular network measurements, complaint management, network monitoring, and machine-learning-based latency prediction.

## Project Overview

The platform provides two main workflows:

### Customer
- Submit network/service complaints
- View submitted complaints
- Track complaint status
- View network information

### Company
- View all customer complaints
- Assign complaints to staff and departments
- Update complaint status
- Monitor network measurements
- Run ML-based latency predictions

## Technology Stack

### Frontend
- React
- React Router
- Vite

### Backend
- FastAPI
- SQLAlchemy
- PyMySQL
- Pydantic
- Python

### Database
- MySQL 8

### Machine Learning
- Python
- Pandas
- NumPy
- Scikit-learn
- Joblib
- Matplotlib
- Seaborn
- Jupyter

## Project Structure

```text
Intelligent-Telecom-Operations-Platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── ml/
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   └── features/
│   ├── models/
│   ├── notebooks/
│   ├── src/
│   └── requirements.txt
│
├── dataset/
│   ├── telecom_real_measurements.csv
│   └── README.md
│
├── database/
│   ├── schema/
│   │   └── schema.sql
│   ├── migrations/
│   └── seed/
│
└── README.md