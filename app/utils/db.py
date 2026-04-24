import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

@st.cache_resource
def get_engine():
    password = quote_plus(os.getenv('DB_PASSWORD'))
    return create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{password}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )

@st.cache_data(ttl=60)
def query(sql, params=None):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)
