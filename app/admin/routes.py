"""
Admin routes - user management
"""
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from itsdangerous import URLSafeTimedSerializer

from app.admin import bp
from app.models import db, User, Crop
from app.email import send_email


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@bp.route('/')
@admin_required
def index():
    """Admin dashboard - list all users"""
    users = User.query.order_by(User.created_at.desc()).all()

    # Get crop counts per user
    user_data = []
    for user in users:
        crop_count = Crop.query.filter_by(user_id=user.id).count()
        user_data.append({
            'user': user,
            'crop_count': crop_count
        })

    return render_template('admin/index.html', user_data=user_data)


@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user and all their data"""
    if user_id == current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
        flash('Cannot delete your own account.', 'danger')
        return redirect(url_for('admin.index'))

    user = User.query.get_or_404(user_id)

    try:
        db.session.delete(user)
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True})
        flash(f'User "{user.display_name}" ({user.email}) deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        flash('Failed to delete user.', 'danger')

    return redirect(url_for('admin.index'))


@bp.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    if user_id == current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Cannot change your own admin status'}), 400
        flash('Cannot change your own admin status.', 'danger')
        return redirect(url_for('admin.index'))

    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin

    try:
        db.session.commit()
        status = 'granted' if user.is_admin else 'revoked'
        if request.is_json:
            return jsonify({'success': True, 'is_admin': user.is_admin})
        flash(f'Admin access {status} for {user.display_name}.', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        flash('Failed to update user.', 'danger')

    return redirect(url_for('admin.index'))


@bp.route('/user/<int:user_id>/send-reset', methods=['POST'])
@admin_required
def send_reset(user_id):
    """Send a password reset email to a user"""
    from flask import current_app
    user = User.query.get_or_404(user_id)
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = s.dumps(user.email, salt='password-reset')

    reset_url = url_for('auth.reset_password', token=token, _external=True)

    # Try sending email, fall back to showing the link directly
    success = send_email(
        user.email,
        'Plant Chap - Password Reset',
        f'Hi {user.display_name},\n\n'
        f'An admin has requested a password reset for your account.\n\n'
        f'To reset your password, visit the following link:\n\n{reset_url}\n\n'
        f'This link expires in 1 hour.\n\n'
        f'— Plant Chap'
    )

    if success:
        flash(f'Reset email sent to {user.email}.', 'success')
    else:
        flash(f'Could not send email. Copy this reset link (expires in 1 hour): {reset_url}', 'warning')

    return redirect(url_for('admin.index'))
