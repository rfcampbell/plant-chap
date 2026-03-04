"""
API routes - JSON API for charts and CRUD operations
All operations are scoped to the current user's crops
"""
import os
import re
import time
import requests as http_requests
from flask import jsonify, request, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.api import bp
from app.models import db, Crop, PlantParameter, GrowLog, ScheduledTask, Amendment

MEDIA_CROPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'media', 'crops')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB

def get_user_crop(crop_id):
    """Helper to get crop that belongs to current user"""
    return Crop.query.filter_by(id=crop_id, user_id=current_user.id).first()

# Plant Parameters API
@bp.route('/crop/<int:crop_id>/parameters', methods=['GET', 'POST', 'DELETE'])
@login_required
def parameters(crop_id):
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404
    
    if request.method == 'POST':
        data = request.json
        parameter = PlantParameter(
            crop_id=crop_id,
            timestamp=datetime.utcnow(),
            ph_runoff=data.get('ph_runoff'),
            ph_feed=data.get('ph_feed'),
            ec_ppm=data.get('ec_ppm'),
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
            light_hours=data.get('light_hours'),
            vpd=data.get('vpd'),
            ppfd=data.get('ppfd'),
            water_mbars=data.get('water_mbars'),
            notes=data.get('notes')
        )
        try:
            db.session.add(parameter)
            db.session.commit()
            return jsonify({'success': True, 'id': parameter.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        param_id = request.args.get('id', type=int)
        if not param_id:
            return jsonify({'success': False, 'error': 'ID required'}), 400
        parameter = PlantParameter.query.filter_by(id=param_id, crop_id=crop_id).first()
        if not parameter:
            return jsonify({'success': False, 'error': 'Parameter not found'}), 404
        try:
            db.session.delete(parameter)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    else:  # GET
        limit = request.args.get('limit', 50, type=int)
        parameters = PlantParameter.query.filter_by(
            crop_id=crop_id
        ).order_by(PlantParameter.timestamp.desc()).limit(limit).all()
        return jsonify([param.to_dict() for param in parameters])

# Grow Log API
@bp.route('/crop/<int:crop_id>/growlog', methods=['GET', 'POST', 'DELETE'])
@login_required
def grow_log(crop_id):
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404
    
    if request.method == 'POST':
        data = request.json
        entry = GrowLog(
            crop_id=crop_id,
            timestamp=datetime.utcnow(),
            task_type=data.get('task_type'),
            description=data.get('description'),
            completed=data.get('completed', True)
        )
        try:
            db.session.add(entry)
            db.session.commit()
            return jsonify({'success': True, 'id': entry.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        entry_id = request.args.get('id', type=int)
        if not entry_id:
            return jsonify({'success': False, 'error': 'ID required'}), 400
        entry = GrowLog.query.filter_by(id=entry_id, crop_id=crop_id).first()
        if not entry:
            return jsonify({'success': False, 'error': 'Entry not found'}), 404
        try:
            db.session.delete(entry)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    else:  # GET
        limit = request.args.get('limit', 50, type=int)
        entries = GrowLog.query.filter_by(
            crop_id=crop_id
        ).order_by(GrowLog.timestamp.desc()).limit(limit).all()
        return jsonify([entry.to_dict() for entry in entries])

# Scheduled Tasks API
@bp.route('/crop/<int:crop_id>/scheduled', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def scheduled_tasks(crop_id):
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404
    
    if request.method == 'POST':
        data = request.json
        is_recurring = data.get('is_recurring', True)
        
        if is_recurring:
            if not data.get('frequency_days'):
                return jsonify({'success': False, 'error': 'Frequency is required for recurring tasks'}), 400
            next_due = datetime.utcnow() + timedelta(days=int(data['frequency_days']))
            task = ScheduledTask(
                crop_id=crop_id,
                task_name=data['task_name'],
                frequency_days=data['frequency_days'],
                next_due=next_due,
                description=data.get('description'),
                active=True,
                is_recurring=True
            )
        else:
            if not data.get('specific_date'):
                return jsonify({'success': False, 'error': 'Date is required for one-time tasks'}), 400
            try:
                specific_date = datetime.fromisoformat(data['specific_date'])
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format'}), 400
            task = ScheduledTask(
                crop_id=crop_id,
                task_name=data['task_name'],
                next_due=specific_date,
                description=data.get('description'),
                active=True,
                is_recurring=False,
                specific_date=specific_date
            )
        
        try:
            db.session.add(task)
            db.session.commit()
            return jsonify({'success': True, 'id': task.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'PUT':
        data = request.json
        task_id = data.get('id')
        if not task_id:
            return jsonify({'success': False, 'error': 'Task ID required'}), 400
        task = ScheduledTask.query.filter_by(id=task_id, crop_id=crop_id).first()
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        now = datetime.utcnow()
        if task.is_recurring:
            task.last_completed = now
            task.next_due = now + timedelta(days=task.frequency_days)
        else:
            task.last_completed = now
            task.active = False
        
        log_entry = GrowLog(
            crop_id=crop_id,
            timestamp=now,
            task_type=task.task_name,
            description='Completed scheduled task',
            completed=True
        )
        try:
            db.session.add(log_entry)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        task_id = request.args.get('id', type=int)
        if not task_id:
            return jsonify({'success': False, 'error': 'ID required'}), 400
        task = ScheduledTask.query.filter_by(id=task_id, crop_id=crop_id).first()
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        try:
            db.session.delete(task)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    else:  # GET
        tasks = ScheduledTask.query.filter_by(
            crop_id=crop_id,
            active=True
        ).order_by(ScheduledTask.next_due).all()
        return jsonify([task.to_dict() for task in tasks])

# Amendments API
@bp.route('/crop/<int:crop_id>/amendments', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def amendments(crop_id):
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404
    
    if request.method == 'POST':
        data = request.json
        amendment = Amendment(
            crop_id=crop_id,
            name=data['name'],
            type=data.get('type'),
            amount=float(data['amount']) if data.get('amount') else None,
            unit=data.get('unit'),
            notes=data.get('notes')
        )
        try:
            db.session.add(amendment)
            db.session.commit()
            return jsonify({'success': True, 'id': amendment.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        item_id = request.args.get('id', type=int)
        if not item_id:
            return jsonify({'success': False, 'error': 'ID required'}), 400
        amendment = Amendment.query.filter_by(id=item_id, crop_id=crop_id).first()
        if not amendment:
            return jsonify({'success': False, 'error': 'Amendment not found'}), 404
        try:
            db.session.delete(amendment)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    else:  # GET
        items = Amendment.query.filter_by(
            crop_id=crop_id
        ).order_by(Amendment.date_applied.desc()).all()
        return jsonify([item.to_dict() for item in items])

# Charts API
@bp.route('/crop/<int:crop_id>/parameters/chart')
@login_required
def parameters_chart(crop_id):
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404
    
    days = request.args.get('days', 30, type=int)
    since_date = datetime.utcnow() - timedelta(days=days)
    
    parameters = PlantParameter.query.filter(
        PlantParameter.crop_id == crop_id,
        PlantParameter.timestamp >= since_date
    ).order_by(PlantParameter.timestamp.asc()).all()
    
    chart_data = {
        'labels': [],
        'datasets': {
            'ph_runoff': {
                'label': 'pH (Runoff)',
                'data': [],
                'borderColor': '#4ecdc4',
                'backgroundColor': 'rgba(78, 205, 196, 0.1)',
                'yAxisID': 'y1'
            },
            'ph_feed': {
                'label': 'pH (Feed)',
                'data': [],
                'borderColor': '#2d6a4f',
                'backgroundColor': 'rgba(45, 106, 79, 0.1)',
                'yAxisID': 'y1'
            },
            'ec_ppm': {
                'label': 'EC/PPM',
                'data': [],
                'borderColor': '#f7b267',
                'backgroundColor': 'rgba(247, 178, 103, 0.1)',
                'yAxisID': 'y2'
            },
            'temperature': {
                'label': 'Temperature (°F)',
                'data': [],
                'borderColor': '#ff6b9d',
                'backgroundColor': 'rgba(255, 107, 157, 0.1)',
                'yAxisID': 'y'
            },
            'humidity': {
                'label': 'Humidity (%)',
                'data': [],
                'borderColor': '#6b9dff',
                'backgroundColor': 'rgba(107, 157, 255, 0.1)',
                'yAxisID': 'y1'
            },
            'light_hours': {
                'label': 'Light Hours',
                'data': [],
                'borderColor': '#e0e040',
                'backgroundColor': 'rgba(224, 224, 64, 0.1)',
                'yAxisID': 'y1'
            },
            'vpd': {
                'label': 'VPD (kPa)',
                'data': [],
                'borderColor': '#a855f7',
                'backgroundColor': 'rgba(168, 85, 247, 0.1)',
                'yAxisID': 'y1'
            },
            'ppfd': {
                'label': 'PPFD (µmol/m²/s)',
                'data': [],
                'borderColor': '#f59e0b',
                'backgroundColor': 'rgba(245, 158, 11, 0.1)',
                'yAxisID': 'y2'
            },
            'water_mbars': {
                'label': 'Water (mbars)',
                'data': [],
                'borderColor': '#06b6d4',
                'backgroundColor': 'rgba(6, 182, 212, 0.1)',
                'yAxisID': 'y2'
            }
        }
    }
    
    for param in parameters:
        chart_data['labels'].append(param.timestamp.strftime('%m/%d'))
        for field in ['ph_runoff', 'ph_feed', 'ec_ppm', 'temperature', 'humidity', 'light_hours', 'vpd', 'ppfd', 'water_mbars']:
            value = getattr(param, field)
            chart_data['datasets'][field]['data'].append(
                float(value) if value is not None else None
            )
    
    return jsonify(chart_data)

# CSV Import API
@bp.route('/crop/<int:crop_id>/parameters/import', methods=['POST'])
@login_required
def import_parameters(crop_id):
    """Import plant parameters from a CSV file (e.g. sensor exports).
    
    Supports formats:
    - Columns with Temperature_Celsius / Temperature_Fahrenheit
    - Columns with Relative_Humidity or Humidity
    - First column is always timestamp
    - Auto-detects delimiter (comma)
    - Skips duplicate timestamps
    """
    import csv
    import io
    
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404
    
    file = request.files.get('file')
    csv_text = request.form.get('csv_text')
    
    if file:
        content = file.read().decode('utf-8')
    elif csv_text:
        content = csv_text
    else:
        return jsonify({'success': False, 'error': 'No file or CSV text provided'}), 400
    
    lines = content.strip().split('\n')
    if len(lines) < 2:
        return jsonify({'success': False, 'error': 'CSV must have a header and at least one data row'}), 400
    
    # Parse header
    header = lines[0].strip().lower()
    
    # Detect column mapping from header
    temp_is_celsius = 'celsius' in header
    temp_is_fahrenheit = 'fahrenheit' in header
    has_temp = 'temperature' in header or 'temp' in header
    has_humidity = 'humidity' in header
    
    # Parse data rows
    imported = 0
    skipped = 0
    errors = []
    
    # Get existing timestamps for this crop to skip duplicates
    existing_timestamps = set()
    existing = PlantParameter.query.filter_by(crop_id=crop_id).all()
    for p in existing:
        if p.timestamp:
            existing_timestamps.add(p.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
    
    for i, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue
        
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2:
            errors.append(f'Line {i}: not enough columns')
            continue
        
        # Parse timestamp
        try:
            ts = datetime.fromisoformat(parts[0])
        except ValueError:
            try:
                ts = datetime.strptime(parts[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                errors.append(f'Line {i}: invalid timestamp "{parts[0]}"')
                continue
        
        ts_key = ts.strftime('%Y-%m-%d %H:%M:%S')
        if ts_key in existing_timestamps:
            skipped += 1
            continue
        
        # Parse temperature
        temperature = None
        if has_temp and len(parts) > 1 and parts[1]:
            try:
                temp_val = float(parts[1])
                if temp_is_celsius:
                    temperature = round(temp_val * 9/5 + 32, 1)  # Convert C to F
                else:
                    temperature = temp_val
            except ValueError:
                pass
        
        # Parse humidity
        humidity = None
        if has_humidity and len(parts) > 2 and parts[2]:
            try:
                humidity = float(parts[2])
            except ValueError:
                pass
        
        param = PlantParameter(
            crop_id=crop_id,
            timestamp=ts,
            temperature=temperature,
            humidity=humidity
        )
        db.session.add(param)
        existing_timestamps.add(ts_key)
        imported += 1
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'errors': errors[:10]  # Limit error messages
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# Stats API
@bp.route('/crop/<int:crop_id>/stats')
@login_required
def crop_stats(crop_id):
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404
    
    latest_params = PlantParameter.query.filter_by(
        crop_id=crop_id
    ).order_by(PlantParameter.timestamp.desc()).first()
    
    upcoming_tasks = ScheduledTask.query.filter(
        ScheduledTask.crop_id == crop_id,
        ScheduledTask.active == True,
        ScheduledTask.next_due <= datetime.utcnow() + timedelta(days=7)
    ).count()
    
    total_amendments = Amendment.query.filter_by(crop_id=crop_id).count()
    
    recent_logs = GrowLog.query.filter(
        GrowLog.crop_id == crop_id,
        GrowLog.timestamp >= datetime.utcnow() - timedelta(days=30)
    ).count()
    
    return jsonify({
        'latest_parameters': latest_params.to_dict() if latest_params else None,
        'upcoming_tasks': upcoming_tasks,
        'total_amendments': total_amendments,
        'recent_logs': recent_logs
    })

# ── Crop Photo Upload ──────────────────────────────────────────

@bp.route('/media/crops/<path:filename>')
@login_required
def serve_crop_photo(filename):
    """Serve crop photos from media directory"""
    return send_from_directory(MEDIA_CROPS_DIR, filename)

@bp.route('/crop/<int:crop_id>/photo', methods=['POST'])
@login_required
def upload_crop_photo(crop_id):
    """Upload a photo for a crop"""
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404

    file = request.files.get('photo')
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'error': f'File type not allowed. Use: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Check size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_PHOTO_SIZE:
        return jsonify({'success': False, 'error': 'File too large (max 5MB)'}), 400

    filename = f'{crop_id}_{int(time.time())}.{ext}'
    os.makedirs(MEDIA_CROPS_DIR, exist_ok=True)
    file.save(os.path.join(MEDIA_CROPS_DIR, filename))

    crop.photo = filename
    try:
        db.session.commit()
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ── Strain Info ─────────────────────────────────────────────────

@bp.route('/crop/<int:crop_id>/strain-info', methods=['POST'])
@login_required
def save_strain_info(crop_id):
    """Save strain info fields to a crop"""
    crop = get_user_crop(crop_id)
    if not crop:
        return jsonify({'success': False, 'error': 'Crop not found'}), 404

    data = request.json
    if data.get('strain_description') is not None:
        crop.strain_description = data['strain_description']
    if data.get('strain_type') is not None:
        crop.strain_type = data['strain_type']
    if data.get('strain_lineage') is not None:
        crop.strain_lineage = data['strain_lineage']
    if data.get('strain_breeder') is not None:
        crop.strain_breeder = data['strain_breeder']

    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ── Seedfinder.eu Strain Lookup ─────────────────────────────────

def slugify(text):
    """Convert text to URL slug for seedfinder"""
    return re.sub(r'[^a-z0-9-]', '', text.lower().strip().replace(' ', '-').replace('_', '-'))

@bp.route('/strain-lookup')
@login_required
def strain_lookup():
    """Lookup strain info from seedfinder.eu"""
    query = request.args.get('query', '').strip()
    breeder = request.args.get('breeder', '').strip()
    if not query:
        return jsonify({'success': False, 'error': 'Query required'}), 400

    slug = slugify(query)
    urls_to_try = []
    if breeder:
        urls_to_try.append(f'https://seedfinder.eu/en/strain-info/{slug}/{slugify(breeder)}')
    urls_to_try.append(f'https://seedfinder.eu/en/strain-info/{slug}')

    page_text = None
    final_url = None
    for url in urls_to_try:
        try:
            resp = http_requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            })
            if resp.status_code == 200 and 'strain-info' in resp.url:
                page_text = resp.text
                final_url = resp.url
                break
        except Exception:
            continue

    if not page_text:
        return jsonify({'success': False, 'error': 'Strain not found on seedfinder.eu'})

    result = {'success': True, 'url': final_url}

    # Extract breeder from database/breeder link
    breeder_match = re.search(r'href=["\'][^"\']*database/breeder/[^"\']*["\'][^>]*>\s*([A-Z][^<]{2,60}?)\s*</a>', page_text)
    if breeder_match:
        result['breeder'] = breeder_match.group(1).strip()

    # Extract description - look for "StrainName is an indica/sativa..." pattern in page text
    desc_match = re.search(r'([\w][\w\s\'-]{3,60}is an (?:indica|sativa)[^<]*?\.)', page_text, re.IGNORECASE)
    if desc_match:
        result['description'] = desc_match.group(1).strip()

    # Extract type (indica/sativa) from description
    desc_text = result.get('description', '')
    type_match = re.search(r'(indica\s*/?\s*sativa|sativa\s*/?\s*indica|indica|sativa)(?:\s+(?:hybrid|dominant|variety))?',
                           desc_text, re.IGNORECASE)
    if type_match:
        result['type'] = type_match.group(0).strip().title()

    # Extract lineage from description - "crossing X with Y" or "cross of X and Y"
    lineage_match = re.search(r'(?:cross(?:ing)?\s+(?:a\s+)?|bred from\s+|cross of\s+)(.+?)(?:\.|$)',
                              desc_text, re.IGNORECASE)
    if lineage_match:
        result['lineage'] = lineage_match.group(1).strip()

    return jsonify(result)
