from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Plant Growth Visualization Service")

def get_db_engine():
    try:
        db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.get("/growth-data/{lot_id}", response_class=HTMLResponse)
async def get_growth_chart(lot_id: int):
    try:
        engine = get_db_engine()

        query = text("""
            SELECT log_date, height_mm 
            FROM growth_logs 
            WHERE lot_id = :lot_id
            ORDER BY log_date
        """)
        
        # SQLAlchemy connection
        with engine.connect() as connection:
            df = pd.read_sql_query(query, connection, params={'lot_id': lot_id})
        
        if df.empty:
            return HTMLResponse(content="<h2>No data found for this lot ID</h2>", status_code=404)
        
        # height from mm to cm 
        df['height_cm'] = df['height_mm'] / 10
        df['log_date'] = pd.to_datetime(df['log_date'])
        
        fig = px.line(
            df,
            x='log_date',
            y='height_cm',
            title=f'Tomato Growth - Lot {lot_id}',
            labels={'height_cm': 'Height (cm)', 'log_date': 'Date'},
            markers=True,
            color_discrete_sequence=['green']
        )
        
        # Customize the layout
        fig.update_layout(
            xaxis=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(count=7, label="1w", step="day", stepmode="backward"),
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(step="all")
                    ])
                ),
                rangeslider=dict(visible=True),
                type="date"
            ),
            hovermode="x unified"
        )
        
        # Customize hover information
        fig.update_traces(
            hovertemplate=(
                "<b>Date:</b> %{x|%Y-%m-%d}<br>"
                "<b>Height:</b> %{y:.1f} cm<br>"
                "<extra></extra>"
            )
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Plant Growth Visualization Service - Access /growth-data/{lot_id} for charts"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070)