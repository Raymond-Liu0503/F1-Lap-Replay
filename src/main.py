from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import fastf1
import pandas as pd
from typing import List, Optional
import logging
import os

# Create cache directory if it doesn't exist
cache_dir = 'f1_cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
    
# Enable FastF1 cache for better performance
fastf1.Cache.enable_cache(cache_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="F1 Lap Replay API", version="1.0.0")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TelemetryPoint(BaseModel):
    x: float
    y: float
    speed: float
    throttle: float
    brake: float
    gear: int
    rpm: float
    drs: int
    distance: float
    time: float


class LapDataResponse(BaseModel):
    driver: str
    lap_number: int
    lap_time: str
    telemetry: List[TelemetryPoint]
    track_info: dict


@app.get("/")
async def root():
    return {
        "message": "F1 Lap Replay API",
        "endpoints": {
            "/api/lap": "Get lap data with telemetry",
            "/api/sessions": "Get available sessions for a year",
            "/api/drivers": "Get drivers for a specific session"
        }
    }


@app.get("/api/sessions/{year}")
async def get_sessions(year: int):
    """Get all available sessions for a given year"""
    try:
        schedule = fastf1.get_event_schedule(year)
        events = []
        
        for idx, event in schedule.iterrows():
            events.append({
                "round": event['RoundNumber'],
                "name": event['EventName'],
                "location": event['Location'],
                "country": event['Country'],
                "date": str(event['EventDate'])
            })
        
        return {"year": year, "events": events}
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/drivers/{year}/{round}/{session}")
async def get_drivers(year: int, round: int, session: str):
    """Get all drivers who participated in a specific session"""
    try:
        logger.info(f"Fetching drivers for {year}, Round {round}, Session {session}")
        
        # Load session
        f1_session = fastf1.get_session(year, round, session)
        f1_session.load()
        
        # Get unique drivers
        drivers = []
        for driver in f1_session.laps['Driver'].unique():
            driver_laps = f1_session.laps.pick_drivers(driver)
            if not driver_laps.empty:
                fastest_lap = driver_laps.pick_fastest()
                if pd.notna(fastest_lap['LapTime']):
                    drivers.append({
                        "code": driver,
                        "fastest_lap": str(fastest_lap['LapTime']),
                        "team": fastest_lap['Team']
                    })
        
        return {
            "year": year,
            "round": round,
            "session": session,
            "drivers": drivers
        }
    except Exception as e:
        logger.error(f"Error fetching drivers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lap/{year}/{round}/{session}/{driver}", response_model=LapDataResponse)
async def get_lap_data(
    year: int,
    round: int,
    session: str,
    driver: str,
    lap_number: Optional[int] = None
):
    """
    Get lap data with telemetry for a specific driver.
    If lap_number is not provided, returns the fastest lap.
    """
    try:
        logger.info(f"Loading session: {year}, Round {round}, Session {session}")
        
        # Load the session with extended timeout and error handling
        try:
            f1_session = fastf1.get_session(year, round, session)
            f1_session.load(telemetry=True, laps=True, weather=False, messages=False)
        except Exception as e:
            if "ergast" in str(e).lower() or "timeout" in str(e).lower():
                logger.error(f"Connection issue, retrying with alternative method: {str(e)}")
                # Try loading with minimal data first
                f1_session = fastf1.get_session(year, round, session)
                f1_session.load(telemetry=True, laps=True)
            else:
                raise
        
        # Get driver's laps (using pick_drivers which returns a list)
        driver_laps = f1_session.laps.pick_drivers(driver)
        
        if driver_laps.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No laps found for driver {driver}"
            )
        
        # Select lap
        if lap_number:
            lap = driver_laps[driver_laps['LapNumber'] == lap_number].iloc[0]
        else:
            lap = driver_laps.pick_fastest()
        
        if pd.isna(lap['LapTime']):
            raise HTTPException(
                status_code=404,
                detail="Selected lap has no valid lap time"
            )
        
        logger.info(f"Getting telemetry for lap {lap['LapNumber']}")
        
        # Get telemetry data
        telemetry = lap.get_telemetry()
        
        if telemetry.empty:
            raise HTTPException(
                status_code=404,
                detail="No telemetry data available for this lap"
            )
        
        logger.info(f"Telemetry columns: {list(telemetry.columns)}")
        
        # Check if telemetry already has position data (X, Y, Z)
        if 'X' in telemetry.columns and 'Y' in telemetry.columns:
            logger.info("Position data already in telemetry, using directly")
            merged_data = telemetry
        else:
            # Get position data separately
            try:
                pos_data = lap.get_pos_data()
                logger.info(f"Position data columns: {list(pos_data.columns) if not pos_data.empty else 'empty'}")
            except Exception as e:
                logger.error(f"Error getting position data: {str(e)}")
                raise HTTPException(
                    status_code=404,
                    detail="No position data available for this lap"
                )
            
            # Check if we have X, Y coordinates
            has_pos_data = not pos_data.empty and 'X' in pos_data.columns and 'Y' in pos_data.columns
            
            if not has_pos_data:
                # Try to get car data which has position info
                try:
                    car_data = lap.get_car_data()
                    logger.info(f"Car data columns: {list(car_data.columns) if not car_data.empty else 'empty'}")
                    if not car_data.empty and 'X' in car_data.columns and 'Y' in car_data.columns:
                        pos_data = car_data
                        has_pos_data = True
                except Exception as e:
                    logger.error(f"Error getting car data: {str(e)}")
            
            if not has_pos_data:
                raise HTTPException(
                    status_code=404,
                    detail="No position data (X, Y coordinates) available for this lap. Try a different session (Qualifying often has better data)."
                )
            
            # Merge telemetry with position data
            pos_columns = ['X', 'Y', 'Z']
            if 'Distance' in pos_data.columns and 'Distance' not in telemetry.columns:
                pos_columns.append('Distance')
            
            merged_data = telemetry.merge(
                pos_data[pos_columns],
                left_index=True,
                right_index=True,
                how='inner'
            )
        
        if merged_data.empty:
            raise HTTPException(
                status_code=404,
                detail="Could not merge telemetry with position data"
            )
        
        # Prepare telemetry points
        telemetry_points = []
        
        # Normalize coordinates for visualization
        x_coords = merged_data['X'].values
        y_coords = merged_data['Y'].values
        
        # Calculate bounds for normalization
        x_min, x_max = x_coords.min(), x_coords.max()
        y_min, y_max = y_coords.min(), y_coords.max()
        x_range = x_max - x_min if x_max != x_min else 1
        y_range = y_max - y_min if y_max != y_min else 1
        
        for idx, row in merged_data.iterrows():
            # Normalize coordinates to 0-1 range (frontend will scale to canvas)
            x_norm = (row['X'] - x_min) / x_range
            y_norm = (row['Y'] - y_min) / y_range
            
            # Get Distance from either column (pos_data or telemetry)
            distance_val = 0.0
            if 'Distance' in row.index and pd.notna(row['Distance']):
                distance_val = float(row['Distance'])
            elif 'Distance' in merged_data.columns:
                distance_val = float(row['Distance'])
            
            point = TelemetryPoint(
                x=float(x_norm),
                y=float(y_norm),
                speed=float(row['Speed']) if pd.notna(row['Speed']) else 0.0,
                throttle=float(row['Throttle']) if pd.notna(row['Throttle']) else 0.0,
                brake=float(row['Brake']) if pd.notna(row['Brake']) else 0.0,
                gear=int(row['nGear']) if pd.notna(row['nGear']) else 0,
                rpm=float(row['RPM']) if pd.notna(row['RPM']) else 0.0,
                drs=int(row['DRS']) if pd.notna(row['DRS']) else 0,
                distance=distance_val,
                time=float(row['Time'].total_seconds()) if pd.notna(row['Time']) else 0.0
            )
            telemetry_points.append(point)
        
        # Get track information
        total_distance = 0.0
        if 'Distance' in merged_data.columns:
            total_distance = float(merged_data['Distance'].max())
        
        track_info = {
            "name": f1_session.event['EventName'],
            "location": f1_session.event['Location'],
            "country": f1_session.event['Country'],
            "x_bounds": {"min": float(x_min), "max": float(x_max)},
            "y_bounds": {"min": float(y_min), "max": float(y_max)},
            "total_distance": total_distance
        }
        
        response = LapDataResponse(
            driver=driver,
            lap_number=int(lap['LapNumber']),
            lap_time=str(lap['LapTime']),
            telemetry=telemetry_points,
            track_info=track_info
        )
        
        logger.info(f"Successfully processed {len(telemetry_points)} telemetry points")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing lap data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "cache_enabled": fastf1.Cache._CACHE_DIR is not None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)