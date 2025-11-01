# F1 Lap Replay Visualizer

A real-time visualization tool for Formula 1 lap telemetry data using FastF1 and an interactive web interface.

## Features

- 🏁 **Visual track rendering** with accurate racing line from real telemetry
- 📊 **Live telemetry display** (speed, throttle, brake, gear, RPM, DRS)
- ⏯️ **Playback controls** with variable speed (0.1x to 5x)
- 🎨 **Modern, responsive UI** with smooth animations
- 📈 **Real FastF1 data** from 2018 onwards

## Quick Start

### 1. Backend Setup

Create a project directory and set up the Python backend:

```bash
# Create project directory
mkdir f1-replay-visualizer
cd f1-replay-visualizer

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the API Server

```bash
# Start the FastAPI server
python main.py

# Or use uvicorn directly for auto-reload during development
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 3. Open the Frontend

Open `index.html` in your web browser (you can simply double-click the file, or use a local server).

If you want to serve it with Python:

```bash
# In a new terminal, in the same directory
python -m http.server 8080
```

Then visit `http://localhost:8080` in your browser.

### 4. Load Lap Data

1. Enter the session details:
   - **Year**: 2018-2024
   - **Round**: GP number (1-24)
   - **Session**: R (Race), Q (Qualifying), S (Sprint), FP1/2/3 (Practice)
   - **Driver**: 3-letter code (VER, HAM, LEC, etc.)

2. Click **"Load Real Lap Data"**

3. Wait for the data to load (30-120 seconds on first load, faster with cache)

4. Click **Play** to start the replay!

## API Endpoints

### `GET /api/lap/{year}/{round}/{session}/{driver}`
Get lap telemetry data for a specific driver (fastest lap by default).

**Example**: `http://localhost:8000/api/lap/2024/1/Q/VER`

**Response**:
```json
{
  "driver": "VER",
  "lap_number": 18,
  "lap_time": "0 days 00:01:29.708000",
  "telemetry": [
    {
      "x": 0.123,
      "y": 0.456,
      "speed": 312.5,
      "throttle": 100.0,
      "brake": 0.0,
      "gear": 8,
      "rpm": 11500.0,
      "drs": 1,
      "distance": 1234.5,
      "time": 5.67
    }
  ],
  "track_info": {
    "name": "Bahrain Grand Prix",
    "location": "Sakhir",
    "country": "Bahrain",
    "total_distance": 5412.0
  }
}
```

### `GET /api/sessions/{year}`
Get all events for a given year.

### `GET /api/drivers/{year}/{round}/{session}`
Get all drivers who participated in a session.

### `GET /health`
Health check endpoint.

## Project Structure

```
f1-replay-visualizer/
├── main.py              # FastAPI backend server
├── requirements.txt     # Python dependencies
├── index.html          # Frontend visualization
├── README.md           # This file
└── f1_cache/           # FastF1 cache directory (auto-created)
```

## Examples

### 2024 Bahrain GP Qualifying - Max Verstappen
```
Year: 2024
Round: 1
Session: Q
Driver: VER
```

### 2024 Monaco GP Race - Charles Leclerc
```
Year: 2024
Round: 8
Session: R
Driver: LEC
```

### 2023 British GP - Lewis Hamilton
```
Year: 2023
Round: 10
Session: Q
Driver: HAM
```

## Troublesho

### "No laps found for driver"
- Check the driver code is correct (3 letters, uppercase)
- Verify the driver participated in that session
- Use the `/api/drivers/{year}/{round}/{session}` endpoint to see available drivers

### "Connection refused" or CORS errors
- Ensure the backend API is running on port 8000
- Check the API URL in the frontend matches your backend
- Verify your firewall isn't blocking the connection

### Data loading is slow
- First load downloads data from F1 servers (30-120 seconds)
- Subsequent loads use cache and are much faster
- Check your internet connection
- Data may not be available for very recent sessions (wait 30-120 minutes after session end)

### "No telemetry data available"
- Telemetry is only available from 2018 onwards
- Some practice sessions may have limited data
- Try a different session (Qualifying/Race typically have complete data)

## Data Availability

- **Telemetry data**: 2018 onwards
- **Historical results**: 1950 onwards (via Ergast API)
- **Update frequency**: Data available 30-120 minutes after session end
- **Cache location**: `f1_cache/` directory

## Tech Stack

**Backend**:
- Python 3.8+
- FastAPI - Modern web framework
- FastF1 - F1 telemetry data library
- Pandas - Data processing
- Uvicorn - ASGI server

**Frontend**:
- HTML5 Canvas - Track rendering
- Vanilla JavaScript - No frameworks needed
- CSS3 - Modern styling with gradients and animations

## Performance Tips

1. **Cache**: FastF1 automatically caches data locally. Keep the `f1_cache` directory to speed up repeated requests.

2. **Playback speed**: Adjust the speed slider to match your preference. Higher speeds work well for long laps.

3. **Data sampling**: The telemetry data is very detailed (multiple points per second). You can modify the backend to sample less frequently if needed.

## Contributing

Ideas for enhancements:
- Compare multiple drivers on the same track
- Show speed heat maps on the track
- Display sector times and mini-sectors
- Add audio (engine sounds based on RPM)
- Export replay as video
- Show tire degradation over stint

## License

This project is for educational purposes. FastF1 and the data it provides are subject to their respective licenses.

**Note**: This is an unofficial project not affiliated with Formula 1, FIA, or any F1 teams.

## Credits

- [FastF1](https://github.com/theOehrly/Fast-F1) - Python library for F1 data
- Formula 1 - For the amazing sport and data
- You - For building cool stuff with F1 data! 🏎️