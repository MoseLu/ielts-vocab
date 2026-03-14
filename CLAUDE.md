# IELTS Vocabulary App

An IELTS vocabulary learning web application with 30-day structured learning plan (100 words/day = 3000 words total).

## Project Structure

```
ielts-vocab/
├── index.html          # Main HTML structure
├── css/style.css       # Styling
├── js/main.js          # Application logic
├── database.sql        # Supabase database schema
└── assets/images/logo.png
```

## Technology Stack

- **Frontend**: Vanilla HTML/CSS/JS
- **Backend**: Python Flask + SQLite
- **Authentication**: JWT Token
- **Styling**: Custom CSS with CSS variables
- **Typography**: Inter (Latin), Noto Sans SC (Chinese)
- **Icons**: SVG inline

## Key Features

1. **Authentication**: Login/Register with JWT, localStorage fallback for offline use
2. **Vocabulary Learning**: 30 days × 100 words = 3000 IELTS vocabulary words
3. **Practice Modes**:
   - Meaning Mode: Match English word to Chinese definition
   - Listening Mode: Listen to pronunciation, then match definition
4. **Progress Tracking**: Track correct/wrong answers, save progress to database
5. **Responsive Design**: Mobile-friendly UI

## Backend API

The backend is built with Flask and provides RESTful APIs:

- **Auth API** (`/api/auth`): Register, login, logout, get current user
- **Progress API** (`/api/progress`): Save and retrieve learning progress
- **Vocabulary API** (`/api/vocabulary`): Get vocabulary data

See `backend/` directory for implementation details.

## Development

1. Install backend dependencies:
   ```bash
   cd backend
   pip install flask flask-cors flask-sqlalchemy flask-jwt-extended
   ```

2. Start backend server:
   ```bash
   python app.py
   ```
   Server runs at: http://localhost:5000

3. Open `index.html` in a browser

The backend uses SQLite database (`backend/database.sqlite`) which is automatically created on first run.

## Browser APIs Used

- `speechSynthesis`: For pronunciation in listening mode
- `localStorage`: For offline fallback and session persistence

## License

MIT
