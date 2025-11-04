from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import sqlite3
import json
import os
from datetime import datetime, timedelta
import csv
import io
import shutil
from pathlib import Path

from pathlib import Path



app = Flask(__name__)

# Configure app paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backup"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOAD_DIR = BASE_DIR / "uploads"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "media").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "sounds").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "icons").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "bootstrap").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "chartjs").mkdir(parents=True, exist_ok=True)

# Database and settings file paths
DB_PATH = DATA_DIR / "peekaboo.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
BACKUP_DB_PATH = BACKUP_DIR / "peekaboo_backup.db"

# App metadata
APP_VERSION = "2.0.0"
APP_NAME = "Peek-a-Boo Boxing Tracker"

# Default settings
DEFAULT_SETTINGS = {
    "training_time": "09:00",
    "timezone": "Africa/Lagos",
    "reminder_enabled": True,
    "sound_enabled": True,
    "theme": "light",
    "auto_backup": True,
    "max_backups": 10
}

def load_settings():
    """Load settings from JSON file"""
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, 'r') as f:
                settings = json.load(f)
                # Merge with defaults in case new settings were added
                return {**DEFAULT_SETTINGS, **settings}
        except (json.JSONDecodeError, Exception):
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to JSON file"""
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=4)

def get_db_connection():
    """Get database connection with proper error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        # Try to restore from backup if available
        restore_from_latest_backup()
        # Try again
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def restore_from_latest_backup():
    """Restore database from latest backup if main DB is corrupted"""
    try:
        backups = sorted(BACKUP_DIR.glob("peekaboo_backup_*.db"))
        if backups:
            latest_backup = backups[-1]
            shutil.copy2(latest_backup, DB_PATH)
            print(f"Restored database from backup: {latest_backup.name}")
    except Exception as e:
        print(f"Failed to restore from backup: {e}")

def init_db():
    """Initialize database with required tables"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Progress table
        c.execute('''CREATE TABLE IF NOT EXISTS progress
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      week INTEGER, 
                      day INTEGER, 
                      fluidity INTEGER, 
                      endurance INTEGER, 
                      power INTEGER, 
                      date TEXT,
                      notes TEXT,
                      duration INTEGER DEFAULT 0,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Sessions table for tracking completion
        c.execute('''CREATE TABLE IF NOT EXISTS sessions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      week INTEGER,
                      day INTEGER,
                      completed_date TEXT,
                      duration INTEGER,
                      UNIQUE(week, day))''')
        
        # Create indexes for better performance
        c.execute('''CREATE INDEX IF NOT EXISTS idx_progress_week_day ON progress(week, day)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_progress_date ON progress(date)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_sessions_week_day ON sessions(week, day)''')
        
        conn.commit()
        conn.close()
        
        # Initialize settings file if it doesn't exist
        if not SETTINGS_PATH.exists():
            save_settings(DEFAULT_SETTINGS)
            
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def backup_database():
    """Create a backup of the database"""
    try:
        if not DB_PATH.exists():
            print("No database file to backup")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"peekaboo_backup_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_file)
        
        # Clean up old backups
        cleanup_old_backups()
        
        print(f"✅ Database backed up: {backup_file.name}")
        return str(backup_file)
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def cleanup_old_backups():
    """Keep only recent backups based on settings"""
    try:
        settings = load_settings()
        max_backups = settings.get('max_backups', 10)
        
        backups = sorted(BACKUP_DIR.glob("peekaboo_backup_*.db"))
        if len(backups) > max_backups:
            for old_backup in backups[:-max_backups]:
                old_backup.unlink()
                print(f"🗑️  Deleted old backup: {old_backup.name}")
    except Exception as e:
        print(f"Backup cleanup error: {e}")

def send_reminder_if_needed():
    """Send reminder if enabled and training time is approaching"""
    try:
        settings = load_settings()
        if not settings.get('reminder_enabled', True):
            return
            
        # Simple reminder logic - you can enhance this with actual notifications
        training_time = settings.get('training_time', '09:00')
        current_time = datetime.now().strftime('%H:%M')
        
        # For demo purposes, just log the reminder check
        print(f"⏰ Reminder check: Current time {current_time}, Training time {training_time}")
        
    except Exception as e:
        print(f"Reminder error: {e}")

# Training program data (MUST BE COMPLETED - This is a placeholder; replace with your full TRAINING_DATA)
TRAINING_DATA = {
    1: {
        1: {
            "focus": "Rhythm & Form",
            "duration": "60-75 minutes",
            "description": "Introduction to peek-a-boo stance, basic head movement, and rhythm development",
            "warmup": ["Jump rope - 3 rounds of 2 minutes", "Arm circles - 2 sets of 20", "Shadow footwork - 3 minutes", "Dynamic stretching - 5 minutes"],
            "technical": ["Peek-a-boo stance hold - 3x1 min", "Slip lines (left/right) - 4 sets of 10", "Double bob & weave - 3 sets of 8", "Guard positioning drills - 5 minutes"],
            "combos": ["Slip Right → Left Hook → Right Uppercut (3x10)", "Bob → Double Jab → Right Hand (3x10)", "Weave Left → Right Hook to Body (3x10)"],
            "bagwork": ["4 rounds of 2 minutes - Focus on form", "Emphasis on tight defense between punches", "Practice peek-a-boo head position"],
            "conditioning": ["Jump squats - 3 sets of 15", "Plank punches - 3 sets of 20", "Russian twists - 3 sets of 30"],
            "recovery": ["Deep breathing - 5 minutes", "Static stretching - 10 minutes", "Foam rolling - 5 minutes"]
        },
        # Add days 2-5 for week 1, and weeks 2-6 here. The code expects weeks 1-6, days 1-5.
        # Example for week 1, day 2 (replace with actual data):
        2: {
            "focus": "Another Focus",
            "duration": "60-75 minutes",
            "description": "Description here",
            "warmup": ["Warmup items"],
            "technical": ["Technical items"],
            "combos": ["Combos"],
            "bagwork": ["Bagwork"],
            "conditioning": ["Conditioning"],
            "recovery": ["Recovery"]
        },
        # ... Continue for all days and weeks. If not provided, the app will 404 for missing sessions.
    },
    # Add weeks 2-6 similarly.
    # 2: { ... },
    # 3: { ... },
    # 4: { ... },
    # 5: { ... },
    # 6: { ... },
}

# Initialize database on startup
if not init_db():
    print("⚠️  Retrying database initialization...")
    init_db()

@app.route('/')
def index():
    """Dashboard view - This is already the default route rendering dashboard.html"""
    try:
        conn = get_db_connection()
        progress_data = conn.execute("SELECT week, day FROM progress ORDER BY week, day").fetchall()
        conn.close()
        
        completed_sessions = {(row['week'], row['day']) for row in progress_data}
        
        return render_template('dashboard.html', 
                             weeks=range(1, 7),
                             completed_sessions=completed_sessions,
                             training_data=TRAINING_DATA)
    except Exception as e:
        return render_template('500.html', error=str(e)), 500



@app.route('/week/<int:week>/day/<int:day>')
def session(week, day):
    """Individual training session view"""
    try:
        if week not in TRAINING_DATA or day not in TRAINING_DATA[week]:
            return render_template('404.html', message="Session not found"), 404
        
        session_data = TRAINING_DATA[week][day]
        
        # Get existing progress
        conn = get_db_connection()
        result = conn.execute(
            "SELECT fluidity, endurance, power, notes, duration FROM progress WHERE week=? AND day=?",
            (week, day)
        ).fetchone()
        conn.close()
        
        existing_progress = None
        if result:
            existing_progress = {
                "fluidity": result['fluidity'],
                "endurance": result['endurance'],
                "power": result['power'],
                "notes": result['notes'],
                "duration": result['duration']
            }
        
        settings = load_settings()
        
        return render_template('session.html', 
                             week=week, 
                             day=day,
                             session=session_data,
                             progress=existing_progress,
                             settings=settings)
    except Exception as e:
        return render_template('500.html', error=str(e)), 500

@app.route('/save_progress', methods=['POST'])
def save_progress():
    """Save training progress"""
    try:
        data = request.json
        week = data['week']
        day = data['day']
        fluidity = data['fluidity']
        endurance = data['endurance']
        power = data['power']
        notes = data.get('notes', '')
        duration = data.get('duration', 0)
        
        conn = get_db_connection()
        conn.execute('''INSERT OR REPLACE INTO progress 
                        (week, day, fluidity, endurance, power, date, notes, duration) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (week, day, fluidity, endurance, power, datetime.now().isoformat(), notes, duration))
        conn.commit()
        conn.close()
        
        # Create automatic backup if enabled
        settings = load_settings()
        if settings.get('auto_backup', True):
            backup_database()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/add_manual_session', methods=['POST'])
def add_manual_session():
    """Add a manual workout session"""
    try:
        data = request.json
        week = data.get('week')
        day = data.get('day')
        fluidity = data.get('fluidity', 0)
        endurance = data.get('endurance', 0)
        power = data.get('power', 0)
        notes = data.get('notes', '')
        duration = data.get('duration', 0)
        custom_date = data.get('date', datetime.now().isoformat())
        
        if not week or not day:
            return jsonify({"success": False, "error": "Week and day are required"}), 400
        
        conn = get_db_connection()
        conn.execute('''INSERT INTO progress 
                        (week, day, fluidity, endurance, power, date, notes, duration) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (week, day, fluidity, endurance, power, custom_date, notes, duration))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/delete_session/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a workout session"""
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM progress WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/progress')
def progress():
    """Progress tracking and analytics view"""
    try:
        conn = get_db_connection()
        
        # Get filter parameters
        week_filter = request.args.get('week', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build query with filters
        query = "SELECT id, week, day, fluidity, endurance, power, date, notes, duration FROM progress"
        params = []
        where_clauses = []
        
        if week_filter:
            where_clauses.append("week = ?")
            params.append(week_filter)
        
        if date_from:
            where_clauses.append("date >= ?")
            params.append(date_from)
            
        if date_to:
            where_clauses.append("date <= ?")
            params.append(date_to)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY date DESC, week DESC, day DESC"
        
        data = conn.execute(query, params).fetchall()
        
        # Calculate statistics
        if data:
            avg_fluidity = sum(row['fluidity'] for row in data) / len(data)
            avg_endurance = sum(row['endurance'] for row in data) / len(data)
            avg_power = sum(row['power'] for row in data) / len(data)
            total_duration = sum(row['duration'] or 0 for row in data)
            total_sessions = len(data)
            
            # Calculate weekly averages
            weekly_stats = {}
            for row in data:
                week = row['week']
                if week not in weekly_stats:
                    weekly_stats[week] = {'fluidity': [], 'endurance': [], 'power': [], 'sessions': 0}
                weekly_stats[week]['fluidity'].append(row['fluidity'])
                weekly_stats[week]['endurance'].append(row['endurance'])
                weekly_stats[week]['power'].append(row['power'])
                weekly_stats[week]['sessions'] += 1
            
            for week in weekly_stats:
                weekly_stats[week] = {
                    'fluidity': round(sum(weekly_stats[week]['fluidity']) / len(weekly_stats[week]['fluidity']), 2),
                    'endurance': round(sum(weekly_stats[week]['endurance']) / len(weekly_stats[week]['endurance']), 2),
                    'power': round(sum(weekly_stats[week]['power']) / len(weekly_stats[week]['power']), 2),
                    'sessions': weekly_stats[week]['sessions']
                }
        else:
            avg_fluidity = avg_endurance = avg_power = total_duration = total_sessions = 0
            weekly_stats = {}
        
        conn.close()
        
        return render_template('progress.html',
                             progress_data=data,
                             avg_fluidity=round(avg_fluidity, 2),
                             avg_endurance=round(avg_endurance, 2),
                             avg_power=round(avg_power, 2),
                             total_duration=total_duration,
                             total_sessions=total_sessions,
                             weekly_stats=weekly_stats,
                             week_filter=week_filter,
                             date_from=date_from,
                             date_to=date_to)
    except Exception as e:
        return render_template('500.html', error=str(e)), 500

@app.route('/export')
def export():
    """Export options view"""
    try:
        backups = sorted(BACKUP_DIR.glob("peekaboo_backup_*.db"), reverse=True)
        backup_list = [{"name": b.name, "date": datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")} for b in backups[:10]]
        
        return render_template('export.html', backups=backup_list)
    except Exception as e:
        return render_template('500.html', error=str(e)), 500

@app.route('/test500')
def test500():
    return render_template('500.html', error="🔥 Custom 500 page test works!"), 500

@app.route('/export/progress_csv')
def export_progress_csv():
    """Export progress data as CSV"""
    try:
        conn = get_db_connection()
        
        # Get filter parameters for export
        week_filter = request.args.get('week', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        query = "SELECT week, day, fluidity, endurance, power, date, notes, duration FROM progress"
        params = []
        where_clauses = []
        
        if week_filter:
            where_clauses.append("week = ?")
            params.append(week_filter)
        
        if date_from:
            where_clauses.append("date >= ?")
            params.append(date_from)
            
        if date_to:
            where_clauses.append("date <= ?")
            params.append(date_to)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY week, day"
        
        data = conn.execute(query, params).fetchall()
        conn.close()

        if not data:
            return jsonify({"error": "No progress data found to export."}), 404

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Week", "Day", "Fluidity", "Endurance", "Power", "Date", "Notes", "Duration (min)"])

        for row in data:
            writer.writerow([
                row["week"],
                row["day"],
                row["fluidity"],
                row["endurance"],
                row["power"],
                row["date"],
                row["notes"] or "",
                row["duration"] or 0
            ])

        output.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"peekaboo_progress_{timestamp}.csv"

        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/export/calendar_csv')
def export_calendar_csv():
    """Export training calendar as CSV for import into calendar apps"""
    try:
        settings = load_settings()
        training_time = settings.get('training_time', '09:00')
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Subject', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Description', 'Location'])
        
        start_date = datetime.now()
        
        for week in range(1, 7):
            for day in range(1, 6):
                if week in TRAINING_DATA and day in TRAINING_DATA[week]:
                    session_date = start_date + timedelta(weeks=week-1, days=day-1)
                    session_data = TRAINING_DATA[week][day]
                    
                    # Parse duration to calculate end time
                    duration_parts = session_data['duration'].split('-')
                    avg_duration = int(duration_parts[0]) if duration_parts else 75
                    
                    date_str = session_date.strftime('%m/%d/%Y')
                    end_time = (datetime.strptime(training_time, '%H:%M') + timedelta(minutes=avg_duration)).strftime('%H:%M')
                    
                    description = f"{session_data['description']}\n\nFocus: {session_data['focus']}"
                    
                    writer.writerow([
                        f'Peek-a-Boo Boxing W{week}D{day}: {session_data["focus"]}',
                        date_str,
                        training_time,
                        date_str,
                        end_time,
                        description,
                        'Training Location'
                    ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'peekaboo_schedule_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/export/full_program_pdf')
def export_full_program():
    """Export complete training program as text file"""
    try:
        output = io.StringIO()
        
        output.write("PEEK-A-BOO BOXING TRAINING PROGRAM\n")
        output.write("=" * 80 + "\n\n")
        
        for week in range(1, 7):
            output.write(f"\n{'='*80}\n")
            output.write(f"WEEK {week}\n")
            output.write(f"{'='*80}\n\n")
            
            for day in range(1, 6):
                if week in TRAINING_DATA and day in TRAINING_DATA[week]:
                    session = TRAINING_DATA[week][day]
                    
                    output.write(f"\nDAY {day}: {session['focus']}\n")
                    output.write(f"{'-'*80}\n")
                    output.write(f"Duration: {session['duration']}\n")
                    output.write(f"Description: {session['description']}\n\n")
                    
                    sections = ['warmup', 'technical', 'combos', 'bagwork', 'conditioning', 'recovery']
                    section_names = ['WARM-UP', 'TECHNICAL WORK', 'COMBINATIONS', 'BAG WORK', 'CONDITIONING', 'RECOVERY']
                    
                    for section, name in zip(sections, section_names):
                        if section in session and session[section]:
                            output.write(f"\n{name}:\n")
                            for item in session[section]:
                                output.write(f"  • {item}\n")
                    
                    output.write("\n" + "="*80 + "\n")
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'peekaboo_complete_program_{datetime.now().strftime("%Y%m%d")}.txt'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings management"""
    try:
        if request.method == 'POST':
            settings_data = load_settings()
            
            # Update settings from form
            settings_data['training_time'] = request.form.get('training_time', '09:00')
            settings_data['timezone'] = request.form.get('timezone', 'Africa/Lagos')
            settings_data['reminder_enabled'] = request.form.get('reminder_enabled') == 'on'
            settings_data['sound_enabled'] = request.form.get('sound_enabled') == 'on'
            settings_data['theme'] = request.form.get('theme', 'light')
            settings_data['auto_backup'] = request.form.get('auto_backup') == 'on'
            settings_data['max_backups'] = int(request.form.get('max_backups', 10))
            
            save_settings(settings_data)
            
            # Clean up backups if max_backups changed
            cleanup_old_backups()
            
            return redirect(url_for('settings'))
        
        settings_data = load_settings()
        
        return render_template('settings.html', settings=settings_data)
    except Exception as e:
        return render_template('500.html', error=str(e)), 500

@app.route('/reset_data', methods=['POST'])
def reset_data():
    """Reset all progress data"""
    try:
        # Create backup before reset
        backup_file = backup_database()
        
        # Clear progress data
        conn = get_db_connection()
        conn.execute("DELETE FROM progress")
        conn.execute("DELETE FROM sessions")
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "backup": backup_file})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/backup/create', methods=['POST'])
def create_backup():
    """Manually create a backup"""
    try:
        backup_file = backup_database()
        if backup_file:
            return jsonify({"success": True, "backup": backup_file})
        else:
            return jsonify({"success": False, "error": "Backup creation failed"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/backup/restore/<filename>', methods=['POST'])
def restore_backup(filename):
    """Restore from a backup file"""
    try:
        backup_file = BACKUP_DIR / filename
        
        if not backup_file.exists():
            return jsonify({"success": False, "error": "Backup file not found"}), 404
        
        # Create a backup of current state before restoring
        backup_database()
        
        # Restore the backup
        shutil.copy2(backup_file, DB_PATH)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/backup/upload', methods=['POST'])
def upload_backup():
    """Upload and restore a backup file"""
    try:
        if 'backup_file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['backup_file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        if not file.filename.endswith('.db'):
            return jsonify({"success": False, "error": "File must be a .db file"}), 400
        
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_path = UPLOAD_DIR / f"uploaded_backup_{timestamp}.db"
        file.save(upload_path)
        
        # Create backup of current database
        backup_database()
        
        # Restore from uploaded file
        shutil.copy2(upload_path, DB_PATH)
        
        # Clean up uploaded file
        upload_path.unlink()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/backup/download/<filename>')
def download_backup(filename):
    """Download a backup file"""
    try:
        backup_file = BACKUP_DIR / filename
        
        if not backup_file.exists():
            return render_template('404.html', message="Backup file not found"), 404
        
        return send_file(backup_file, as_attachment=True)
    except Exception as e:
        return render_template('500.html', error=str(e)), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        conn = get_db_connection()
        
        # Get total sessions completed
        total = conn.execute("SELECT COUNT(*) as count FROM progress").fetchone()['count']
        
        # Get current week progress
        current_week_data = conn.execute(
            "SELECT COUNT(*) as count FROM progress WHERE week = (SELECT MAX(week) FROM progress)"
        ).fetchone()
        current_week = current_week_data['count'] if current_week_data else 0
        
        # Get recent progress
        recent = conn.execute(
            "SELECT week, day, fluidity, endurance, power, date, notes, duration FROM progress ORDER BY date DESC LIMIT 5"
        ).fetchall()
        
        # Get averages
        averages = conn.execute(
            "SELECT AVG(fluidity) as fluidity, AVG(endurance) as endurance, AVG(power) as power FROM progress"
        ).fetchone()
        
        # Get total training time
        total_duration = conn.execute("SELECT SUM(duration) as total FROM progress").fetchone()['total'] or 0
        
        conn.close()
        
        return jsonify({
            "total_sessions": total,
            "current_week_progress": current_week,
            "total_training_minutes": total_duration,
            "recent_sessions": [dict(row) for row in recent],
            "averages": {
                "fluidity": round(averages['fluidity'] or 0, 2),
                "endurance": round(averages['endurance'] or 0, 2),
                "power": round(averages['power'] or 0, 2)
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/progress_chart')
def api_progress_chart():
    """API endpoint for progress chart data"""
    try:
        conn = get_db_connection()
        
        # Get filter parameters
        week_filter = request.args.get('week', type=int)
        
        query = "SELECT week, day, fluidity, endurance, power, date FROM progress"
        params = []
        
        if week_filter:
            query += " WHERE week = ?"
            params.append(week_filter)
            
        query += " ORDER BY week, day"
        
        data = conn.execute(query, params).fetchall()
        conn.close()
        
        chart_data = {
            "labels": [f"W{row['week']}D{row['day']}" for row in data],
            "fluidity": [row['fluidity'] for row in data],
            "endurance": [row['endurance'] for row in data],
            "power": [row['power'] for row in data],
            "dates": [row['date'] for row in data]
        }
        
        return jsonify(chart_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/metadata')
def api_metadata():
    """API endpoint for app metadata"""
    try:
        conn = get_db_connection()
        
        # Get database stats
        total_sessions = conn.execute("SELECT COUNT(*) as count FROM progress").fetchone()['count']
        last_session = conn.execute("SELECT date FROM progress ORDER BY date DESC LIMIT 1").fetchone()
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        
        conn.close()
        
        return jsonify({
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "database": {
                "sessions_count": total_sessions,
                "last_session": last_session['date'] if last_session else None,
                "size_bytes": db_size,
                "size_mb": round(db_size / (1024 * 1024), 2) if db_size > 0 else 0
            },
            "backups": {
                "count": len(list(BACKUP_DIR.glob("peekaboo_backup_*.db"))),
                "location": str(BACKUP_DIR)
            },
            "settings": {
                "file_exists": SETTINGS_PATH.exists(),
                "location": str(SETTINGS_PATH)
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reminders')
def api_reminders():
    """API endpoint for reminder status"""
    try:
        settings = load_settings()
        
        # Simple reminder logic - in a real app, this would check actual training times
        reminder_status = {
            "enabled": settings.get('reminder_enabled', True),
            "training_time": settings.get('training_time', '09:00'),
            "timezone": settings.get('timezone', 'Africa/Lagos'),
            "next_check": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        return jsonify(reminder_status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('500.html'), 500

# Context processor to make settings available in all templates
@app.context_processor
def inject_settings():
    return dict(app_settings=load_settings(), app_version=APP_VERSION, app_name=APP_NAME)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
