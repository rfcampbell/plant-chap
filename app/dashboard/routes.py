"""
Dashboard routes - main UI and crop management
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app.dashboard import bp
from app.models import db, Crop, PlantParameter, GrowLog, ScheduledTask, Amendment

@bp.route('/')
@login_required
def index():
    """Main dashboard - shows crop selector and dashboard"""
    crops = Crop.query.filter_by(user_id=current_user.id).order_by(Crop.name).all()
    
    if not crops:
        flash('Welcome! Let\'s set up your first crop.', 'info')
        return redirect(url_for('dashboard.create_crop'))
    
    selected_id = request.args.get('crop_id', type=int)
    if selected_id:
        selected_crop = Crop.query.filter_by(id=selected_id, user_id=current_user.id).first()
        if not selected_crop:
            selected_crop = crops[0]
    else:
        selected_crop = crops[0]
    
    recent_parameters = PlantParameter.query.filter_by(
        crop_id=selected_crop.id
    ).order_by(PlantParameter.timestamp.desc()).limit(10).all()
    
    upcoming_tasks = ScheduledTask.query.filter_by(
        crop_id=selected_crop.id,
        active=True
    ).order_by(ScheduledTask.next_due).limit(5).all()
    
    recent_grow_logs = GrowLog.query.filter_by(
        crop_id=selected_crop.id
    ).order_by(GrowLog.timestamp.desc()).limit(10).all()
    
    amendment_count = Amendment.query.filter_by(crop_id=selected_crop.id).count()
    
    return render_template('dashboard/index.html',
                         crops=crops,
                         selected_crop=selected_crop,
                         recent_parameters=recent_parameters,
                         upcoming_tasks=upcoming_tasks,
                         recent_grow_logs=recent_grow_logs,
                         amendment_count=amendment_count)

@bp.route('/create-crop', methods=['GET', 'POST'])
@login_required
def create_crop():
    """Create a new crop"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        date_planted = None
        if data.get('date_planted'):
            try:
                date_planted = datetime.fromisoformat(data['date_planted'])
            except ValueError:
                pass
        
        crop = Crop(
            user_id=current_user.id,
            name=data.get('name'),
            strain=data.get('strain'),
            medium=data.get('medium'),
            grow_space=data.get('grow_space'),
            date_planted=date_planted,
            status=data.get('status', 'vegetative'),
            notes=data.get('notes')
        )
        
        try:
            db.session.add(crop)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'id': crop.id})
            else:
                flash(f'Crop "{crop.name}" created successfully!', 'success')
                return redirect(url_for('dashboard.index', crop_id=crop.id))
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 400
            else:
                flash('Failed to create crop. Please try again.', 'danger')
    
    return render_template('dashboard/create_crop.html')

@bp.route('/crop/<int:crop_id>/edit', methods=['POST'])
@login_required
def edit_crop(crop_id):
    """Edit an existing crop"""
    crop = Crop.query.filter_by(id=crop_id, user_id=current_user.id).first_or_404()
    data = request.get_json() if request.is_json else request.form
    
    crop.name = data.get('name', crop.name)
    crop.strain = data.get('strain', crop.strain)
    crop.medium = data.get('medium', crop.medium)
    crop.grow_space = data.get('grow_space', crop.grow_space)
    crop.status = data.get('status', crop.status)
    crop.notes = data.get('notes', crop.notes)
    
    for date_field in ['date_planted', 'date_flipped', 'harvest_date']:
        if data.get(date_field):
            try:
                setattr(crop, date_field, datetime.fromisoformat(data[date_field]))
            except ValueError:
                pass
    
    try:
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True})
        else:
            flash('Crop updated successfully!', 'success')
            return redirect(url_for('dashboard.index', crop_id=crop_id))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        else:
            flash('Failed to update crop.', 'danger')
            return redirect(url_for('dashboard.index', crop_id=crop_id))

@bp.route('/crop/<int:crop_id>/delete', methods=['POST'])
@login_required
def delete_crop(crop_id):
    """Delete a crop and all its data"""
    crop = Crop.query.filter_by(id=crop_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(crop)
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True})
        else:
            flash(f'Crop "{crop.name}" deleted successfully.', 'success')
            return redirect(url_for('dashboard.index'))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        else:
            flash('Failed to delete crop.', 'danger')
            return redirect(url_for('dashboard.index'))
