"""
app.py - التطبيق الرئيسي لنظام إدارة المحروقات
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
import sqlite3
import os
from datetime import datetime
import functools

# تهيئة التطبيق
app = Flask(__name__)
app.secret_key = 'fuel-management-system-secret-key-2024'
app.config['SESSION_TYPE'] = 'filesystem'
bcrypt = Bcrypt(app)


# فلتر escapejs مخصص
@app.template_filter('escapejs')
def escapejs_filter(value):
    """فلتر لتهريب النصوص لاستخدامها في JavaScript"""
    if value is None:
        return ''
    # تحويل القيمة إلى سلسلة نصية
    value = str(value)
    # تهريب الأحرف الخاصة
    value = value.replace('\\', '\\\\')
    value = value.replace("'", r"\'")
    value = value.replace('"', r'\"')
    value = value.replace('\n', r'\n')
    value = value.replace('\r', r'\r')
    value = value.replace('\t', r'\t')
    value = value.replace('\f', r'\f')
    return value

# دالة للاتصال بقاعدة البيانات
def get_db_connection():
    """الحصول على اتصال بقاعدة البيانات"""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ديكورات الصلاحيات
def login_required(f):
    """تأكد من تسجيل الدخول"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('الرجاء تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """تأكد من صلاحية الدور"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session:
                flash('غير مصرح بالدخول', 'danger')
                return redirect(url_for('login'))

            # المدير يمكنه الوصول لكل شيء
            if session['user_role'] == 'مدير النظام':
                return f(*args, **kwargs)

            if session['user_role'] != required_role:
                flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# دوال مساعدة
def log_activity(user_id, action, table_name=None, record_id=None, details=None):
    """تسجيل نشاط المستخدم"""
    try:
        conn = get_db_connection()
        ip_address = request.remote_addr if request else '127.0.0.1'

        conn.execute(
            """
            INSERT INTO activity_logs 
            (user_id, action, table_name, record_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, action, table_name, record_id, details, ip_address)
        )

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"خطأ في تسجيل النشاط: {e}")

def get_dashboard_route():
    """الحصول على مسار لوحة التحكم حسب الدور"""
    if 'user_role' not in session:
        return 'login'

    routes = {
        'مدير النظام': 'admin_dashboard',
        'مسؤول النظام': 'system_manager_dashboard',
        'المناوب بالعمليات': 'operations_dashboard',
        'المناوب بالمحروقات': 'fuel_dashboard'
    }
    return routes.get(session['user_role'], 'index')

# ============================================
# المسارات العامة
# ============================================

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    if 'user_id' in session:
        return redirect(url_for(get_dashboard_route()))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """تسجيل الدخول"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember') == 'on'

        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND is_active = 1',
            (username,)
        ).fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            # حفظ بيانات الجلسة
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            session['unit_id'] = user['unit_id']
            session['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # إذا تم اختيار "تذكرني"
            # if remember:
            #     session.permanent = True
            #     app.permanent_session_lifetime = timedelta(days=30)

            # تسجيل النشاط
            log_activity(user['id'], 'تسجيل دخول', details=f'الدور: {user["role"]}')

            flash(f'مرحباً بك {user["name"]}! تم تسجيل الدخول بنجاح', 'success')

            # توجيه إلى لوحة التحكم المناسبة
            return redirect_to_dashboard(user['role'])
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
            log_activity(None, 'محاولة دخول فاشلة', details=f'المستخدم: {username}')

    return render_template('auth/login.html', current_year=datetime.now().year)


def redirect_to_dashboard(role):
    """توجيه المستخدم إلى لوحة التحكم المناسبة"""
    dashboard_routes = {
        'مدير النظام': 'admin_dashboard',
        'مسؤول النظام': 'system_manager_dashboard',
        'المناوب بالعمليات': 'operations_dashboard',
        'المناوب بالمحروقات': 'fuel_dashboard'
    }

    route = dashboard_routes.get(role, 'index')
    return redirect(url_for(route))


@app.route('/check-session')
@login_required
def check_session():
    """فحص حالة الجلسة وإرجاع الدور"""
    return jsonify({
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'name': session.get('user_name'),
        'role': session.get('user_role'),
        'unit_id': session.get('unit_id'),
        'last_login': session.get('last_login')
    })

@app.route('/logout')
def logout():
    """تسجيل الخروج"""
    if 'user_id' in session:
        log_activity(session['user_id'], 'تسجيل خروج')
        session.clear()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """لوحة التحكم الرئيسية"""
    return redirect(url_for(get_dashboard_route()))

# ============================================
# مسارات مدير النظام
# ============================================

@app.route('/admin/dashboard')
@login_required
@role_required('مدير النظام')
def admin_dashboard():
    """لوحة تحكم مدير النظام"""
    conn = get_db_connection()

    # الإحصائيات العامة
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_units = conn.execute('SELECT COUNT(*) FROM units WHERE is_active = 1').fetchone()[0]

    # إحصائيات العمليات
    total_operations = conn.execute('SELECT COUNT(*) FROM fuel_operations').fetchone()[0]
    total_petrol = conn.execute('SELECT COALESCE(SUM(petrol_quantity), 0) FROM fuel_operations').fetchone()[0]
    total_diesel = conn.execute('SELECT COALESCE(SUM(diesel_quantity), 0) FROM fuel_operations').fetchone()[0]

    # العمليات الأخيرة
    recent_operations = conn.execute('''
        SELECT f.*, u.name as unit_name, r.name as status_name, r.color_code as status_color
        FROM fuel_operations f
        JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        ORDER BY f.created_at DESC LIMIT 10
    ''').fetchall()

    # النشاطات الأخيرة
    recent_activities = conn.execute('''
        SELECT a.*, u.name as user_name
        FROM activity_logs a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC LIMIT 10
    ''').fetchall()

    conn.close()

    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_units=total_units,
                         total_operations=total_operations,
                         total_petrol=total_petrol,
                         total_diesel=total_diesel,
                         recent_operations=recent_operations,
                         recent_activities=recent_activities)

@app.route('/admin/users')
@login_required
@role_required('مدير النظام')
def admin_users():
    """إدارة المستخدمين"""
    conn = get_db_connection()
    users = conn.execute('''
        SELECT u.*, un.name as unit_name 
        FROM users u 
        LEFT JOIN units un ON u.unit_id = un.id 
        ORDER BY u.created_at DESC
    ''').fetchall()

    units = conn.execute('SELECT * FROM units WHERE is_active = 1').fetchall()
    conn.close()

    return render_template('admin/users.html', users=users, units=units)

@app.route('/admin/operations')
@login_required
@role_required('مدير النظام')
def admin_operations():
    """عرض جميع العمليات"""
    conn = get_db_connection()

    # البحث والتصفية
    search = request.args.get('search', '')
    unit_id = request.args.get('unit_id', '')
    status_id = request.args.get('status_id', '')
    month = request.args.get('month', '')

    query = '''
        SELECT f.*, u.name as unit_name, r.name as status_name, 
               d.name as dispense_type, us.name as user_name
        FROM fuel_operations f
        JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        JOIN users us ON f.user_id = us.id
        WHERE 1=1
    '''
    params = []

    if search:
        query += " AND (f.driver_name LIKE ? OR f.vehicle_type LIKE ? OR f.receipt_number LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

    if unit_id:
        query += " AND f.unit_id = ?"
        params.append(unit_id)

    if status_id:
        query += " AND f.receipt_status_id = ?"
        params.append(status_id)

    if month:
        query += " AND f.month = ?"
        params.append(month)

    query += " ORDER BY f.operation_date DESC"

    operations = conn.execute(query, params).fetchall()
    units = conn.execute('SELECT * FROM units WHERE is_active = 1').fetchall()
    statuses = conn.execute('SELECT * FROM receipt_statuses').fetchall()

    # الأشهر المتاحة
    months = conn.execute('SELECT DISTINCT month FROM fuel_operations ORDER BY month DESC').fetchall()

    conn.close()

    return render_template('admin/operations.html',
                         operations=operations,
                         units=units,
                         statuses=statuses,
                         months=months)

@app.route('/admin/reports')
@login_required
@role_required('مدير النظام')
def admin_reports():
    """التقارير والإحصائيات"""
    conn = get_db_connection()

    # استهلاك شهري
    monthly_consumption = conn.execute('''
        SELECT month, 
               COALESCE(SUM(petrol_quantity), 0) as total_petrol,
               COALESCE(SUM(diesel_quantity), 0) as total_diesel
        FROM fuel_operations
        WHERE month IS NOT NULL
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    ''').fetchall()

    # استهلاك الوحدات
    unit_consumption = conn.execute('''
        SELECT u.name as unit_name,
               COALESCE(SUM(f.petrol_quantity), 0) as total_petrol,
               COALESCE(SUM(f.diesel_quantity), 0) as total_diesel
        FROM units u
        LEFT JOIN fuel_operations f ON u.id = f.unit_id
        WHERE u.is_active = 1
        GROUP BY u.id
        ORDER BY total_petrol + total_diesel DESC
    ''').fetchall()

    # أنواع الصرف
    dispense_stats = conn.execute('''
        SELECT d.name as type_name,
               COUNT(f.id) as operation_count,
               COALESCE(SUM(f.petrol_quantity), 0) as total_petrol,
               COALESCE(SUM(f.diesel_quantity), 0) as total_diesel
        FROM dispense_types d
        LEFT JOIN fuel_operations f ON d.id = f.dispense_type_id
        GROUP BY d.id
        ORDER BY operation_count DESC
    ''').fetchall()

    conn.close()

    return render_template('admin/reports.html',
                         monthly_consumption=monthly_consumption,
                         unit_consumption=unit_consumption,
                         dispense_stats=dispense_stats)

# ============================================
# مسارات مسؤول النظام
# ============================================

# ============================================
# API Routes for System Manager
# ============================================

@app.route('/api/system-manager/stats')
@login_required
@role_required('مسؤول النظام')
def system_manager_stats():
    """الحصول على إحصائيات لوحة تحكم مسؤول النظام"""
    try:
        conn = get_db_connection()

        # تاريخ اليوم
        today = datetime.now().strftime('%Y-%m-%d')

        # إحصائيات اليوم
        today_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_operations,
                SUM(CASE WHEN receipt_status_id = 1 THEN 1 ELSE 0 END) as dispensed_receipts,
                SUM(CASE WHEN receipt_status_id != 1 THEN 1 ELSE 0 END) as non_dispensed_receipts,
                COALESCE(SUM(petrol_quantity), 0) as total_petrol,
                COALESCE(SUM(diesel_quantity), 0) as total_diesel
            FROM fuel_operations 
            WHERE operation_date = ?
        ''', (today,)).fetchone()

        # حساب النسب المئوية
        total_ops = today_stats['total_operations'] or 0
        dispensed = today_stats['dispensed_receipts'] or 0
        non_dispensed = today_stats['non_dispensed_receipts'] or 0

        dispensed_percentage = (dispensed / total_ops * 100) if total_ops > 0 else 0
        non_dispensed_percentage = (non_dispensed / total_ops * 100) if total_ops > 0 else 0

        # المستخدمين النشطين اليوم
        active_users = conn.execute('''
            SELECT DISTINCT u.id, u.name 
            FROM users u
            JOIN activity_logs a ON u.id = a.user_id
            WHERE DATE(a.created_at) = DATE('now')
            AND a.action LIKE '%تسجيل دخول%'
        ''').fetchall()

        # السندات المنصرفة اليوم
        today_dispensed_receipts = conn.execute('''
            SELECT f.*, u.name as unit_name, r.name as status_name, r.color_code
            FROM fuel_operations f
            JOIN units u ON f.unit_id = u.id
            JOIN receipt_statuses r ON f.receipt_status_id = r.id
            WHERE f.operation_date = ? 
            AND f.receipt_status_id = 1
            ORDER BY f.created_at DESC
        ''', (today,)).fetchall()

        # جميع العمليات مع تفاصيل إضافية
        operations = conn.execute('''
            SELECT 
                f.*,
                u.name as unit_name,
                r.name as status_name,
                r.color_code as status_color,
                d.name as dispense_name,
                us.name as user_name,
                us.role as user_role,
                (SELECT name FROM users WHERE id = (
                    SELECT user_id FROM activity_logs 
                    WHERE table_name = 'fuel_operations' 
                    AND record_id = f.id 
                    AND action = 'تعديل عملية'
                    ORDER BY created_at DESC LIMIT 1
                )) as last_updated_by
            FROM fuel_operations f
            JOIN units u ON f.unit_id = u.id
            JOIN receipt_statuses r ON f.receipt_status_id = r.id
            JOIN dispense_types d ON f.dispense_type_id = d.id
            JOIN users us ON f.user_id = us.id
            ORDER BY f.created_at DESC
            LIMIT 100
        ''').fetchall()

        # بيانات الرسوم البيانية
        # توزيع العمليات حسب الحالة
        status_distribution = conn.execute('''
            SELECT 
                r.name as status_name,
                COUNT(f.id) as count,
                r.color_code
            FROM receipt_statuses r
            LEFT JOIN fuel_operations f ON r.id = f.receipt_status_id
            GROUP BY r.id, r.name, r.color_code
            ORDER BY r.id
        ''').fetchall()

        # الاستهلاك اليومي لآخر 7 أيام
        daily_consumption = conn.execute('''
            SELECT 
                operation_date,
                COALESCE(SUM(petrol_quantity), 0) as total_petrol,
                COALESCE(SUM(diesel_quantity), 0) as total_diesel
            FROM fuel_operations
            WHERE operation_date >= DATE('now', '-7 days')
            GROUP BY operation_date
            ORDER BY operation_date
        ''').fetchall()

        # النشاطات الأخيرة
        recent_activity_logs = conn.execute('''
            SELECT 
                a.*,
                u.name as user_name
            FROM activity_logs a
            JOIN users u ON a.user_id = u.id
            WHERE a.table_name = 'fuel_operations'
            ORDER BY a.created_at DESC
            LIMIT 20
        ''').fetchall()

        # جميع المستخدمين
        all_users = conn.execute('''
            SELECT id, name, role FROM users WHERE is_active = 1
        ''').fetchall()

        conn.close()

        # تحضير بيانات الرسوم البيانية
        chart_data = {
            'statusData': [s['count'] for s in status_distribution],
            'dailyLabels': [d['operation_date'] for d in daily_consumption],
            'dailyPetrol': [float(d['total_petrol']) for d in daily_consumption],
            'dailyDiesel': [float(d['total_diesel']) for d in daily_consumption]
        }

        return jsonify({
            'success': True,
            'stats': {
                'total_operations': total_ops,
                'dispensed_receipts': dispensed,
                'non_dispensed_receipts': non_dispensed,
                'total_petrol': float(today_stats['total_petrol'] or 0),
                'total_diesel': float(today_stats['total_diesel'] or 0),
                'dispensed_percentage': dispensed_percentage,
                'non_dispensed_percentage': non_dispensed_percentage,
                'operations_change': 12.5,  # يمكن حسابها من البيانات السابقة
                'active_users': len(active_users)
            },
            'today_dispensed_receipts': [dict(r) for r in today_dispensed_receipts],
            'operations': [dict(o) for o in operations],
            'today_active_users': [dict(u) for u in active_users],
            'recent_activity_logs': [dict(l) for l in recent_activity_logs],
            'all_users': [dict(u) for u in all_users],
            'charts': chart_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في الحصول على الإحصائيات: {str(e)}'
        }), 500

#
# @app.route('/api/operation/<int:operation_id>')
# @login_required
# def get_operation_details(operation_id):
#     """الحصول على تفاصيل عملية معينة"""
#     try:
#         conn = get_db_connection()
#
#         operation = conn.execute('''
#             SELECT
#                 f.*,
#                 u.name as unit_name,
#                 r.name as status_name,
#                 r.color_code,
#                 d.name as dispense_name,
#                 us.name as user_name,
#                 us.role as user_role,
#                 (SELECT name FROM users WHERE id = (
#                     SELECT user_id FROM activity_logs
#                     WHERE table_name = 'fuel_operations'
#                     AND record_id = f.id
#                     AND action = 'تعديل عملية'
#                     ORDER BY created_at DESC LIMIT 1
#                 )) as last_updated_by
#             FROM fuel_operations f
#             JOIN units u ON f.unit_id = u.id
#             JOIN receipt_statuses r ON f.receipt_status_id = r.id
#             JOIN dispense_types d ON f.dispense_type_id = d.id
#             JOIN users us ON f.user_id = us.id
#             WHERE f.id = ?
#         ''', (operation_id,)).fetchone()
#
#         conn.close()
#
#         if operation:
#             return jsonify({
#                 'success': True,
#                 'operation': dict(operation)
#             })
#         else:
#             return jsonify({
#                 'success': False,
#                 'message': 'العملية غير موجودة'
#             }), 404
#
#     except Exception as e:
#         return jsonify({
#             'success': False,
#             'message': f'خطأ في الحصول على التفاصيل: {str(e)}'
#         }), 500


# ============================================
# تحديث مسار مسؤول النظام
# ============================================

@app.route('/system-manager/dashboard')
@login_required
@role_required('مسؤول النظام')
def system_manager_dashboard():
    """لوحة تحكم مسؤول النظام"""
    conn = get_db_connection()

    # تاريخ اليوم
    today = datetime.now().strftime('%Y-%m-%d')
    today_date_ar = datetime.now().strftime('%Y/%m/%d')

    # إحصائيات اليوم
    today_stats = conn.execute('''
        SELECT 
            COUNT(*) as total_operations,
            SUM(CASE WHEN receipt_status_id = 1 THEN 1 ELSE 0 END) as dispensed_receipts,
            SUM(CASE WHEN receipt_status_id != 1 THEN 1 ELSE 0 END) as non_dispensed_receipts,
            COALESCE(SUM(petrol_quantity), 0) as total_petrol,
            COALESCE(SUM(diesel_quantity), 0) as total_diesel
        FROM fuel_operations 
        WHERE operation_date = ?
    ''', (today,)).fetchone()

    # حساب النسب المئوية
    total_ops = today_stats['total_operations'] or 0
    dispensed = today_stats['dispensed_receipts'] or 0
    non_dispensed = today_stats['non_dispensed_receipts'] or 0

    dispensed_percentage = (dispensed / total_ops * 100) if total_ops > 0 else 0
    non_dispensed_percentage = (non_dispensed / total_ops * 100) if total_ops > 0 else 0

    # السندات المنصرفة اليوم
    today_dispensed_receipts = conn.execute('''
        SELECT f.*, u.name as unit_name, r.name as status_name, r.color_code
        FROM fuel_operations f
        JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        WHERE f.operation_date = ? 
        AND f.receipt_status_id = 1
        ORDER BY f.created_at DESC
        LIMIT 20
    ''', (today,)).fetchall()

    # جميع العمليات مع تفاصيل إضافية
    operations = conn.execute('''
        SELECT 
            f.*,
            u.name as unit_name,
            r.name as status_name,
            r.color_code as status_color,
            d.name as dispense_name,
            us.name as user_name,
            us.role as user_role,
            (SELECT name FROM users WHERE id = (
                SELECT user_id FROM activity_logs 
                WHERE table_name = 'fuel_operations' 
                AND record_id = f.id 
                AND action = 'تعديل عملية'
                ORDER BY created_at DESC LIMIT 1
            )) as last_updated_by
        FROM fuel_operations f
        JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        JOIN users us ON f.user_id = us.id
        ORDER BY f.created_at DESC
        LIMIT 100
    ''').fetchall()

    # المستخدمين النشطين اليوم
    active_users = conn.execute('''
        SELECT DISTINCT u.id, u.name 
        FROM users u
        JOIN activity_logs a ON u.id = a.user_id
        WHERE DATE(a.created_at) = DATE('now')
        AND a.action LIKE '%تسجيل دخول%'
    ''').fetchall()

    # النشاطات الأخيرة
    recent_activity_logs = conn.execute('''
        SELECT 
            a.*,
            u.name as user_name
        FROM activity_logs a
        JOIN users u ON a.user_id = u.id
        WHERE a.table_name = 'fuel_operations'
        ORDER BY a.created_at DESC
        LIMIT 10
    ''').fetchall()

    # البيانات للفلترة
    receipt_statuses = conn.execute('SELECT * FROM receipt_statuses').fetchall()
    dispense_types = conn.execute('SELECT * FROM dispense_types').fetchall()
    all_users = conn.execute('SELECT id, name, role FROM users WHERE is_active = 1').fetchall()

    conn.close()

    return render_template('system_manager/dashboard.html',
                           today_date=today_date_ar,
                           today_stats={
                               'total_operations': total_ops,
                               'dispensed_receipts': dispensed,
                               'non_dispensed_receipts': non_dispensed,
                               'total_petrol': float(today_stats['total_petrol'] or 0),
                               'total_diesel': float(today_stats['total_diesel'] or 0),
                               'dispensed_percentage': dispensed_percentage,
                               'non_dispensed_percentage': non_dispensed_percentage,
                               'petrol_percentage': 60,  # يمكن حسابها من البيانات
                               'diesel_percentage': 40,  # يمكن حسابها من البيانات
                               'operations_change': 12.5,
                               'active_users': len(active_users)
                           },
                           today_dispensed_receipts=today_dispensed_receipts,
                           today_active_users=active_users,
                           operations=operations,
                           recent_activity_logs=recent_activity_logs,
                           receipt_statuses=receipt_statuses,
                           dispense_types=dispense_types,
                           all_users=all_users,
                           now=datetime.now())


# ============================================
# مسارات المناوب بالعمليات
# ============================================
@app.route('/operations/dashboard')
@login_required
@role_required('المناوب بالعمليات')
def operations_dashboard():
    """لوحة تحكم مناوب العمليات"""
    conn = get_db_connection()

    # تاريخ اليوم والشهر
    today = datetime.now().strftime('%Y-%m-%d')
    current_month = datetime.now().strftime('%Y-%m')

    # الوحدة التابع لها (إذا كان مرتبط بوحدة)
    current_unit = None
    if session.get('unit_id'):
        current_unit = conn.execute(
            'SELECT * FROM units WHERE id = ?',
            (session['unit_id'],)
        ).fetchone()

    # تحويل current_unit إلى dict إذا كان موجوداً
    current_unit_dict = dict(current_unit) if current_unit else None

    # الحصول على أعلى رقم سند
    max_receipt_result = conn.execute(
        'SELECT COALESCE(MAX(receipt_number), 1000) FROM fuel_operations'
    ).fetchone()
    max_receipt_number = max_receipt_result[0] if max_receipt_result else 1000

    # إحصائيات الوحدة
    unit_stats = conn.execute('''
        SELECT 
            COUNT(*) as total_operations,
            SUM(CASE WHEN receipt_status_id = 1 THEN 1 ELSE 0 END) as dispensed_operations,
            SUM(CASE WHEN receipt_status_id != 1 THEN 1 ELSE 0 END) as non_dispensed_operations
        FROM fuel_operations 
        WHERE unit_id = ?
    ''', (session.get('unit_id'),)).fetchone() or {'total_operations': 0, 'dispensed_operations': 0,
                                                   'non_dispensed_operations': 0}

    # تحويل إلى dict
    unit_stats_dict = dict(unit_stats)

    # إحصائيات اليوم
    today_stats = conn.execute('''
        SELECT 
            COUNT(*) as today_operations,
            SUM(CASE WHEN receipt_status_id = 2 THEN 1 ELSE 0 END) as pending_operations,
            COALESCE(SUM(petrol_quantity), 0) as today_petrol,
            COALESCE(SUM(diesel_quantity), 0) as today_diesel
        FROM fuel_operations 
        WHERE operation_date = ? AND user_id = ?
    ''', (today, session['user_id'])).fetchone() or {'today_operations': 0, 'pending_operations': 0, 'today_petrol': 0,
                                                     'today_diesel': 0}

    # تحويل إلى dict
    today_stats_dict = dict(today_stats)

    # جميع السجلات المدخلة من قبل المستخدم
    all_operations_rows = conn.execute('''
        SELECT 
            f.*,
            u.name as unit_name,
            r.name as status_name,
            d.name as dispense_name,
            (
                SELECT a.created_at 
                FROM activity_logs a 
                WHERE a.table_name = 'fuel_operations' 
                AND a.record_id = f.id 
                AND a.action = 'تعديل حالة السند'
                ORDER BY a.created_at DESC LIMIT 1
            ) as dispensed_at,
            (
                SELECT us.name 
                FROM activity_logs a 
                JOIN users us ON a.user_id = us.id 
                WHERE a.table_name = 'fuel_operations' 
                AND a.record_id = f.id 
                AND a.action = 'تعديل حالة السند'
                ORDER BY a.created_at DESC LIMIT 1
            ) as dispensed_by,
            (
                SELECT a.details 
                FROM activity_logs a 
                WHERE a.table_name = 'fuel_operations' 
                AND a.record_id = f.id 
                AND a.action = 'تعديل حالة السند'
                ORDER BY a.created_at DESC LIMIT 1
            ) as dispense_notes
        FROM fuel_operations f
        LEFT JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
    ''', (session['user_id'],)).fetchall()

    # تحويل جميع الصفوف إلى قواميس
    all_operations = [dict(row) for row in all_operations_rows]

    # السجلات التي تم صرفها
    dispensed_operations_rows = conn.execute('''
        SELECT 
            f.*,
            u.name as unit_name,
            r.name as status_name,
            d.name as dispense_name,
            a.created_at as dispensed_at,
            us.name as dispensed_by,
            a.details as dispense_notes
        FROM fuel_operations f
        LEFT JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        JOIN activity_logs a ON f.id = a.record_id
        JOIN users us ON a.user_id = us.id
        WHERE f.user_id = ? 
        AND a.table_name = 'fuel_operations'
        AND a.action = 'تعديل حالة السند'
        AND f.receipt_status_id = 1
        ORDER BY a.created_at DESC
    ''', (session['user_id'],)).fetchall()

    # تحويل إلى قواميس
    dispensed_operations = [dict(row) for row in dispensed_operations_rows]

    # البيانات اللازمة للنموذج
    units_rows = conn.execute('SELECT * FROM units WHERE is_active = 1 ORDER BY name').fetchall()
    units = [dict(row) for row in units_rows]

    dispense_types_rows = conn.execute('SELECT * FROM dispense_types ORDER BY id').fetchall()
    dispense_types = [dict(row) for row in dispense_types_rows]

    conn.close()

    return render_template('operations/dashboard.html',
                           current_unit=current_unit_dict,
                           unit_stats=unit_stats_dict,
                           today_stats=today_stats_dict,
                           all_operations=all_operations,
                           dispensed_operations=dispensed_operations,
                           units=units,
                           dispense_types=dispense_types,
                           today=today,
                           current_month=current_month,
                           max_receipt_number=max_receipt_number)  # إضافة هذا المتغير

# ============================================
# API لتحديث العملية
# ============================================

@app.route('/api/update-operation/<int:operation_id>', methods=['PUT'])
@login_required
@role_required('المناوب بالعمليات')
def update_operation(operation_id):
    """تحديث عملية"""
    try:
        data = request.get_json()

        conn = get_db_connection()

        # التحقق من ملكية العملية
        operation = conn.execute(
            'SELECT * FROM fuel_operations WHERE id = ? AND user_id = ?',
            (operation_id, session['user_id'])
        ).fetchone()

        if not operation:
            return jsonify({
                'success': False,
                'message': 'العملية غير موجودة أو لا تملك صلاحية التعديل'
            }), 403

        # التحقق من حالة السند (لا يمكن تعديل المنصرف)
        if operation['receipt_status_id'] == 1:
            return jsonify({
                'success': False,
                'message': 'لا يمكن تعديل العملية المنصرفة'
            }), 400

        # استخراج الشهر من التاريخ
        operation_date = data.get('operation_date', '')
        month = operation_date[:7] if operation_date else datetime.now().strftime('%Y-%m')[:7]

        # تحديث البيانات
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE fuel_operations 
            SET operation_date = ?,
                driver_name = ?,
                vehicle_type = ?,
                petrol_quantity = ?,
                diesel_quantity = ?,
                unit_id = ?,
                dispense_type_id = ?,
                purpose = ?,
                notes = ?,
                month = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data.get('operation_date'),
            data.get('driver_name', ''),
            data.get('vehicle_type', ''),
            float(data.get('petrol_quantity', 0)),
            float(data.get('diesel_quantity', 0)),
            data.get('unit_id') or None,
            data.get('dispense_type_id', 1),
            data.get('purpose', ''),
            data.get('notes', ''),
            month,
            operation_id
        ))

        # تسجيل النشاط
        log_activity(
            session['user_id'],
            'تعديل عملية',
            'fuel_operations',
            operation_id,
            f'تعديل بيانات العملية #{operation["receipt_number"]}'
        )

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'تم تحديث العملية بنجاح'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تحديث العملية: {str(e)}'
        }), 500

# ============================================
# مسارات المناوب بالمحروقات
# ============================================

# ============================================
# مسار عمليات المحروقات
# ============================================

@app.route('/fuel/operations')
@login_required
@role_required('المناوب بالمحروقات')
def fuel_operations():
    """صفحة جميع عمليات المحروقات"""
    conn = get_db_connection()

    # تاريخ اليوم
    today = datetime.now().strftime('%Y-%m-%d')

    # البحث والتصفية
    search = request.args.get('search', '')
    unit_id = request.args.get('unit_id', '')
    status_id = request.args.get('status_id', '')
    month = request.args.get('month', '')

    query = '''
        SELECT 
            f.*,
            u.name as unit_name,
            r.name as status_name,
            r.color_code,
            d.name as dispense_name,
            us.name as user_name,
            us.role as user_role,
            (
                SELECT a.created_at 
                FROM activity_logs a 
                WHERE a.table_name = 'fuel_operations' 
                AND a.record_id = f.id 
                AND a.action = 'تعديل حالة السند'
                ORDER BY a.created_at DESC LIMIT 1
            ) as dispensed_at,
            (
                SELECT us2.name 
                FROM activity_logs a 
                JOIN users us2 ON a.user_id = us2.id 
                WHERE a.table_name = 'fuel_operations' 
                AND a.record_id = f.id 
                AND a.action = 'تعديل حالة السند'
                ORDER BY a.created_at DESC LIMIT 1
            ) as dispensed_by
        FROM fuel_operations f
        LEFT JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        JOIN users us ON f.user_id = us.id
        WHERE 1=1
    '''
    params = []

    if search:
        query += " AND (f.driver_name LIKE ? OR f.vehicle_type LIKE ? OR f.receipt_number LIKE ? OR f.purpose LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])

    if unit_id and unit_id != 'all':
        query += " AND f.unit_id = ?"
        params.append(unit_id)

    if status_id and status_id != 'all':
        query += " AND f.receipt_status_id = ?"
        params.append(status_id)

    if month and month != 'all':
        query += " AND f.month = ?"
        params.append(month)

    query += " ORDER BY f.operation_date DESC, f.created_at DESC"

    operations = conn.execute(query, params).fetchall()
    units = conn.execute('SELECT * FROM units WHERE is_active = 1 ORDER BY name').fetchall()
    statuses = conn.execute('SELECT * FROM receipt_statuses ORDER BY id').fetchall()

    # الأشهر المتاحة
    months = conn.execute(
        'SELECT DISTINCT month FROM fuel_operations WHERE month IS NOT NULL ORDER BY month DESC').fetchall()

    # إحصائيات سريعة
    stats = {
        'total': len(operations),
        'dispensed': len([op for op in operations if op['receipt_status_id'] == 1]),
        'pending': len([op for op in operations if op['receipt_status_id'] == 2]),
        'total_petrol': sum(float(op['petrol_quantity']) for op in operations),
        'total_diesel': sum(float(op['diesel_quantity']) for op in operations)
    }

    conn.close()

    return render_template('fuel/operations.html',
                           operations=operations,
                           units=units,
                           statuses=statuses,
                           months=months,
                           stats=stats,
                           today=today,
                           search=search,
                           unit_id=unit_id,
                           status_id=status_id,
                           month=month)


# ============================================
# API لتعديل حالة السند
# ============================================

# ============================================
# مسارات المناوب بالمحروقات
# ============================================
#
# @app.route('/fuel/dashboard')
# @login_required
# @role_required('المناوب بالمحروقات')
# def fuel_dashboard():
#     """لوحة تحكم المناوب بالمحروقات"""
#     conn = get_db_connection()
#
#     # تاريخ اليوم والشهر
#     today = datetime.now().strftime('%Y-%m-%d')
#     current_month = datetime.now().strftime('%Y-%m')
#
#     # الوحدة التابع لها (إذا كان مرتبط بوحدة)
#     current_unit = None
#     if session.get('unit_id'):
#         current_unit = conn.execute(
#             'SELECT * FROM units WHERE id = ?',
#             (session['unit_id'],)
#         ).fetchone()
#
#     # العمليات قيد الانتظار (غير المنصرفة)
#     pending_operations = conn.execute('''
#         SELECT f.*, u.name as unit_name, r.name as status_name, d.name as dispense_name,
#                us.name as user_name, us.role as user_role
#         FROM fuel_operations f
#         LEFT JOIN units u ON f.unit_id = u.id
#         JOIN receipt_statuses r ON f.receipt_status_id = r.id
#         JOIN dispense_types d ON f.dispense_type_id = d.id
#         JOIN users us ON f.user_id = us.id
#         WHERE f.receipt_status_id = 2  -- غير منصرف فقط
#         ORDER BY f.operation_date DESC, f.created_at DESC
#     ''').fetchall()
#
#     # العمليات المنصرفة اليوم
#     today_dispensed = conn.execute('''
#         SELECT f.*, u.name as unit_name, r.name as status_name, d.name as dispense_name,
#                us.name as user_name, us.role as user_role,
#                (
#                    SELECT a.created_at
#                    FROM activity_logs a
#                    WHERE a.table_name = 'fuel_operations'
#                    AND a.record_id = f.id
#                    AND a.action = 'تعديل حالة السند'
#                    ORDER BY a.created_at DESC LIMIT 1
#                ) as dispensed_at,
#                (
#                    SELECT us2.name
#                    FROM activity_logs a
#                    JOIN users us2 ON a.user_id = us2.id
#                    WHERE a.table_name = 'fuel_operations'
#                    AND a.record_id = f.id
#                    AND a.action = 'تعديل حالة السند'
#                    ORDER BY a.created_at DESC LIMIT 1
#                ) as dispensed_by
#         FROM fuel_operations f
#         LEFT JOIN units u ON f.unit_id = u.id
#         JOIN receipt_statuses r ON f.receipt_status_id = r.id
#         JOIN dispense_types d ON f.dispense_type_id = d.id
#         JOIN users us ON f.user_id = us.id
#         WHERE f.receipt_status_id = 1  -- منصرف فقط
#         AND DATE(f.operation_date) = DATE('now')
#         ORDER BY f.operation_date DESC
#     ''').fetchall()
#
#     # جميع العمليات مع تفاصيل إضافية
#     all_operations = conn.execute('''
#         SELECT
#             f.*,
#             u.name as unit_name,
#             r.name as status_name,
#             d.name as dispense_name,
#             us.name as user_name,
#             us.role as user_role,
#             (
#                 SELECT a.created_at
#                 FROM activity_logs a
#                 WHERE a.table_name = 'fuel_operations'
#                 AND a.record_id = f.id
#                 AND a.action = 'تعديل حالة السند'
#                 ORDER BY a.created_at DESC LIMIT 1
#             ) as dispensed_at,
#             (
#                 SELECT us2.name
#                 FROM activity_logs a
#                 JOIN users us2 ON a.user_id = us2.id
#                 WHERE a.table_name = 'fuel_operations'
#                 AND a.record_id = f.id
#                 AND a.action = 'تعديل حالة السند'
#                 ORDER BY a.created_at DESC LIMIT 1
#             ) as dispensed_by,
#             (
#                 SELECT us3.name
#                 FROM activity_logs a
#                 JOIN users us3 ON a.user_id = us3.id
#                 WHERE a.table_name = 'fuel_operations'
#                 AND a.record_id = f.id
#                 AND a.action LIKE '%تعديل%'
#                 AND a.action != 'تعديل حالة السند'
#                 ORDER BY a.created_at DESC LIMIT 1
#             ) as last_updater
#         FROM fuel_operations f
#         LEFT JOIN units u ON f.unit_id = u.id
#         JOIN receipt_statuses r ON f.receipt_status_id = r.id
#         JOIN dispense_types d ON f.dispense_type_id = d.id
#         JOIN users us ON f.user_id = us.id
#         ORDER BY f.operation_date DESC, f.created_at DESC
#         LIMIT 500
#     ''').fetchall()
#
#     # الإحصائيات
#     today_stats = conn.execute('''
#         SELECT
#             COUNT(*) as total_operations,
#             SUM(CASE WHEN receipt_status_id = 1 THEN 1 ELSE 0 END) as dispensed_operations,
#             SUM(CASE WHEN receipt_status_id = 2 THEN 1 ELSE 0 END) as pending_operations,
#             COALESCE(SUM(petrol_quantity), 0) as today_petrol,
#             COALESCE(SUM(diesel_quantity), 0) as today_diesel
#         FROM fuel_operations
#         WHERE operation_date = ?
#     ''', (today,)).fetchone() or {'total_operations': 0, 'dispensed_operations': 0, 'pending_operations': 0,
#                                   'today_petrol': 0, 'today_diesel': 0}
#
#     # إحصائيات الشهر
#     month_stats = conn.execute('''
#         SELECT
#             COALESCE(SUM(petrol_quantity), 0) as month_petrol,
#             COALESCE(SUM(diesel_quantity), 0) as month_diesel,
#             COUNT(DISTINCT unit_id) as active_units
#         FROM fuel_operations
#         WHERE month = ?
#     ''', (current_month,)).fetchone() or {'month_petrol': 0, 'month_diesel': 0, 'active_units': 0}
#
#     # البيانات للفلترة
#     units = conn.execute('SELECT * FROM units WHERE is_active = 1 ORDER BY name').fetchall()
#     dispense_types = conn.execute('SELECT * FROM dispense_types ORDER BY id').fetchall()
#
#     conn.close()
#
#     return render_template('fuel/dashboard.html',
#                            current_unit=current_unit,
#                            pending_operations=pending_operations,
#                            today_dispensed=today_dispensed,
#                            all_operations=all_operations,
#                            stats={
#                                'pending_operations': len(pending_operations),
#                                'today_dispensed': len(today_dispensed),
#                                'today_petrol': float(today_stats['today_petrol'] or 0),
#                                'today_diesel': float(today_stats['today_diesel'] or 0),
#                                'month_petrol': float(month_stats['month_petrol'] or 0),
#                                'month_diesel': float(month_stats['month_diesel'] or 0),
#                                'active_units': month_stats['active_units'] or 0
#                            },
#                            units=units,
#                            dispense_types=dispense_types,
#                            today=today,
#                            today_petrol=float(today_stats['today_petrol'] or 0),
#                            today_diesel=float(today_stats['today_diesel'] or 0))

@app.route('/fuel/dashboard')
@login_required
@role_required('المناوب بالمحروقات')
def fuel_dashboard():
    """لوحة تحكم المناوب بالمحروقات"""
    conn = get_db_connection()

    # تاريخ اليوم والشهر
    today = datetime.now().strftime('%Y-%m-%d')
    current_month = datetime.now().strftime('%Y-%m')

    # الوحدة التابع لها (إذا كان مرتبط بوحدة)
    current_unit = None
    if session.get('unit_id'):
        current_unit = conn.execute(
            'SELECT * FROM units WHERE id = ?',
            (session['unit_id'],)
        ).fetchone()
        # تحويل Row إلى dict إذا كان موجوداً
        if current_unit:
            current_unit = dict(current_unit)

    # العمليات قيد الانتظار (غير المنصرفة)
    pending_operations_rows = conn.execute('''
        SELECT f.*, u.name as unit_name, r.name as status_name, d.name as dispense_name,
               us.name as user_name, us.role as user_role
        FROM fuel_operations f
        LEFT JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        JOIN users us ON f.user_id = us.id
        WHERE f.receipt_status_id = 2  -- غير منصرف فقط
        ORDER BY f.operation_date DESC, f.created_at DESC
    ''').fetchall()

    # تحويل كل الصفوف إلى قواميس
    pending_operations = [dict(row) for row in pending_operations_rows]

    # العمليات المنصرفة اليوم
    today_dispensed_rows = conn.execute('''
        SELECT f.*, u.name as unit_name, r.name as status_name, d.name as dispense_name,
               us.name as user_name, us.role as user_role,
               (
                   SELECT a.created_at 
                   FROM activity_logs a 
                   WHERE a.table_name = 'fuel_operations' 
                   AND a.record_id = f.id 
                   AND a.action = 'تعديل حالة السند'
                   ORDER BY a.created_at DESC LIMIT 1
               ) as dispensed_at,
               (
                   SELECT us2.name 
                   FROM activity_logs a 
                   JOIN users us2 ON a.user_id = us2.id 
                   WHERE a.table_name = 'fuel_operations' 
                   AND a.record_id = f.id 
                   AND a.action = 'تعديل حالة السند'
                   ORDER BY a.created_at DESC LIMIT 1
               ) as dispensed_by
        FROM fuel_operations f
        LEFT JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        JOIN users us ON f.user_id = us.id
        WHERE f.receipt_status_id = 1  -- منصرف فقط
        AND DATE(f.operation_date) = DATE('now')
        ORDER BY f.operation_date DESC
    ''').fetchall()

    # تحويل إلى قواميس
    today_dispensed = [dict(row) for row in today_dispensed_rows]

    # جميع العمليات مع تفاصيل إضافية
    all_operations_rows = conn.execute('''
        SELECT 
            f.*,
            u.name as unit_name,
            r.name as status_name,
            d.name as dispense_name,
            us.name as user_name,
            us.role as user_role,
            (
                SELECT a.created_at 
                FROM activity_logs a 
                WHERE a.table_name = 'fuel_operations' 
                AND a.record_id = f.id 
                AND a.action = 'تعديل حالة السند'
                ORDER BY a.created_at DESC LIMIT 1
            ) as dispensed_at,
            (
                SELECT us2.name 
                FROM activity_logs a 
                JOIN users us2 ON a.user_id = us2.id 
                WHERE a.table_name = 'fuel_operations' 
                AND a.record_id = f.id 
                AND a.action = 'تعديل حالة السند'
                ORDER BY a.created_at DESC LIMIT 1
            ) as dispensed_by,
            (
                SELECT us3.name 
                FROM activity_logs a 
                JOIN users us3 ON a.user_id = us3.id 
                WHERE a.table_name = 'fuel_operations' 
                AND a.record_id = f.id 
                AND a.action LIKE '%تعديل%'
                AND a.action != 'تعديل حالة السند'
                ORDER BY a.created_at DESC LIMIT 1
            ) as last_updater
        FROM fuel_operations f
        LEFT JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        JOIN users us ON f.user_id = us.id
        ORDER BY f.operation_date DESC, f.created_at DESC
        LIMIT 500
    ''').fetchall()

    # تحويل إلى قواميس
    all_operations = [dict(row) for row in all_operations_rows]

    # الإحصائيات
    today_stats = conn.execute('''
        SELECT 
            COUNT(*) as total_operations,
            SUM(CASE WHEN receipt_status_id = 1 THEN 1 ELSE 0 END) as dispensed_operations,
            SUM(CASE WHEN receipt_status_id = 2 THEN 1 ELSE 0 END) as pending_operations,
            COALESCE(SUM(petrol_quantity), 0) as today_petrol,
            COALESCE(SUM(diesel_quantity), 0) as today_diesel
        FROM fuel_operations 
        WHERE operation_date = ?
    ''', (today,)).fetchone() or {'total_operations': 0, 'dispensed_operations': 0, 'pending_operations': 0,
                                  'today_petrol': 0, 'today_diesel': 0}

    # إحصائيات الشهر
    month_stats = conn.execute('''
        SELECT 
            COALESCE(SUM(petrol_quantity), 0) as month_petrol,
            COALESCE(SUM(diesel_quantity), 0) as month_diesel,
            COUNT(DISTINCT unit_id) as active_units
        FROM fuel_operations 
        WHERE month = ?
    ''', (current_month,)).fetchone() or {'month_petrol': 0, 'month_diesel': 0, 'active_units': 0}

    # البيانات للفلترة
    units_rows = conn.execute('SELECT * FROM units WHERE is_active = 1 ORDER BY name').fetchall()
    units = [dict(row) for row in units_rows]

    dispense_types_rows = conn.execute('SELECT * FROM dispense_types ORDER BY id').fetchall()
    dispense_types = [dict(row) for row in dispense_types_rows]

    conn.close()

    return render_template('fuel/dashboard.html',
                           current_unit=current_unit,
                           pending_operations=pending_operations,
                           today_dispensed=today_dispensed,
                           all_operations=all_operations,
                           stats={
                               'pending_operations': len(pending_operations),
                               'today_dispensed': len(today_dispensed),
                               'today_petrol': float(today_stats['today_petrol'] or 0),
                               'today_diesel': float(today_stats['today_diesel'] or 0),
                               'month_petrol': float(month_stats['month_petrol'] or 0),
                               'month_diesel': float(month_stats['month_diesel'] or 0),
                               'active_units': month_stats['active_units'] or 0
                           },
                           units=units,
                           dispense_types=dispense_types,
                           today=today,
                           today_petrol=float(today_stats['today_petrol'] or 0),
                           today_diesel=float(today_stats['today_diesel'] or 0))


# ============================================
# API لتعديل حالة السند
# ============================================

@app.route('/api/dispense-operation/<int:operation_id>', methods=['POST'])
@login_required
@role_required('المناوب بالمحروقات')
def dispense_operation(operation_id):
    """تعديل حالة السند إلى منصرف"""
    try:
        data = request.get_json()

        conn = get_db_connection()

        # التحقق من وجود العملية
        operation = conn.execute(
            'SELECT * FROM fuel_operations WHERE id = ?',
            (operation_id,)
        ).fetchone()

        if not operation:
            return jsonify({
                'success': False,
                'message': 'العملية غير موجودة'
            }), 404

        # التحقق من حالة السند (لا يمكن صرف المنصرف مسبقاً)
        if operation['receipt_status_id'] == 1:
            return jsonify({
                'success': False,
                'message': 'هذا السند تم صرفه مسبقاً'
            }), 400

        # تحديث حالة السند
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE fuel_operations 
            SET receipt_status_id = 1,  -- منصرف
                operation_officer = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data.get('operation_officer', ''), operation_id))

        # تسجيل النشاط
        log_activity(
            session['user_id'],
            'تعديل حالة السند',
            'fuel_operations',
            operation_id,
            f'تم صرف السند #{operation["receipt_number"]}. ملاحظات: {data.get("dispense_notes", "لا توجد")}'
        )

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'تم صرف السند بنجاح'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في صرف السند: {str(e)}'
        }), 500


@app.route('/api/operation/<int:operation_id>')
@login_required
def get_operation_details(operation_id):
    """الحصول على تفاصيل عملية معينة"""
    try:
        conn = get_db_connection()

        operation = conn.execute('''
            SELECT 
                f.*,
                u.name as unit_name,
                r.name as status_name,
                d.name as dispense_name,
                us.name as user_name,
                us.role as user_role,
                (
                    SELECT us2.name 
                    FROM activity_logs a 
                    JOIN users us2 ON a.user_id = us2.id 
                    WHERE a.table_name = 'fuel_operations' 
                    AND a.record_id = f.id 
                    AND a.action LIKE '%تعديل%'
                    ORDER BY a.created_at DESC LIMIT 1
                ) as last_updater
            FROM fuel_operations f
            LEFT JOIN units u ON f.unit_id = u.id
            JOIN receipt_statuses r ON f.receipt_status_id = r.id
            JOIN dispense_types d ON f.dispense_type_id = d.id
            JOIN users us ON f.user_id = us.id
            WHERE f.id = ?
        ''', (operation_id,)).fetchone()

        conn.close()

        if operation:
            return jsonify({
                'success': True,
                'operation': dict(operation)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'العملية غير موجودة'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في الحصول على التفاصيل: {str(e)}'
        }), 500


@app.route('/fuel/print-receipt/<int:operation_id>')
@login_required
@role_required('المناوب بالمحروقات')
def print_receipt(operation_id):
    """طباعة سند الصرف"""
    conn = get_db_connection()

    operation = conn.execute('''
        SELECT 
            f.*,
            u.name as unit_name,
            r.name as status_name,
            d.name as dispense_name,
            us.name as user_name,
            us.role as user_role
        FROM fuel_operations f
        LEFT JOIN units u ON f.unit_id = u.id
        JOIN receipt_statuses r ON f.receipt_status_id = r.id
        JOIN dispense_types d ON f.dispense_type_id = d.id
        JOIN users us ON f.user_id = us.id
        WHERE f.id = ?
    ''', (operation_id,)).fetchone()

    if not operation or operation['receipt_status_id'] != 1:
        flash('لا يمكن طباعة سند غير منصرف', 'warning')
        return redirect(url_for('fuel_dashboard'))

    conn.close()

    return render_template('fuel/print_receipt.html', operation=operation)


# ============================================
# API للإحصائيات
# ============================================

@app.route('/api/fuel/stats')
@login_required
@role_required('المناوب بالمحروقات')
def fuel_stats():
    """الحصول على إحصائيات المناوب بالمحروقات"""
    try:
        conn = get_db_connection()

        today = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%Y-%m')

        # إحصائيات اليوم
        today_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_operations,
                SUM(CASE WHEN receipt_status_id = 1 THEN 1 ELSE 0 END) as dispensed_today,
                SUM(CASE WHEN receipt_status_id = 2 THEN 1 ELSE 0 END) as pending_today,
                COALESCE(SUM(petrol_quantity), 0) as petrol_today,
                COALESCE(SUM(diesel_quantity), 0) as diesel_today
            FROM fuel_operations 
            WHERE operation_date = ?
        ''', (today,)).fetchone()

        # إحصائيات الأسبوع
        week_stats = conn.execute('''
            SELECT 
                operation_date,
                COUNT(*) as operations,
                COALESCE(SUM(petrol_quantity), 0) as petrol,
                COALESCE(SUM(diesel_quantity), 0) as diesel
            FROM fuel_operations 
            WHERE operation_date >= DATE('now', '-7 days')
            GROUP BY operation_date
            ORDER BY operation_date
        ''').fetchall()

        # إحصائيات الوحدات
        unit_stats = conn.execute('''
            SELECT 
                u.name as unit_name,
                COUNT(f.id) as operations,
                COALESCE(SUM(f.petrol_quantity), 0) as petrol,
                COALESCE(SUM(f.diesel_quantity), 0) as diesel
            FROM units u
            LEFT JOIN fuel_operations f ON u.id = f.unit_id
            WHERE u.is_active = 1
            AND f.operation_date >= DATE('now', '-30 days')
            GROUP BY u.id
            ORDER BY operations DESC
            LIMIT 10
        ''').fetchall()

        conn.close()

        return jsonify({
            'success': True,
            'stats': {
                'today': dict(today_stats) if today_stats else {},
                'week': [dict(row) for row in week_stats],
                'units': [dict(row) for row in unit_stats]
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في الحصول على الإحصائيات: {str(e)}'
        }), 500



# ============================================
# API Routes
# ============================================

@app.route('/api/add-operation', methods=['POST'])
@login_required
def add_operation():
    """إضافة عملية جديدة"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400

        conn = get_db_connection()

        # توليد رقم سند تلقائي
        last_receipt = conn.execute('SELECT COALESCE(MAX(receipt_number), 1000) FROM fuel_operations').fetchone()[0]
        receipt_number = last_receipt + 1

        # استخراج الشهر من التاريخ
        operation_date = data.get('operation_date', '')
        month = operation_date[:7] if operation_date else datetime.now().strftime('%Y-%m')[:7]

        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO fuel_operations 
            (operation_date, unit_id, driver_name, vehicle_type, petrol_quantity, 
             diesel_quantity, operation_officer, receipt_status_id, receipt_number,
             dispense_type_id, purpose, month, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            operation_date,
            data.get('unit_id'),
            data.get('driver_name', ''),
            data.get('vehicle_type', ''),
            float(data.get('petrol_quantity', 0)),
            float(data.get('diesel_quantity', 0)),
            data.get('operation_officer', ''),
            data.get('receipt_status_id', 1),
            receipt_number,
            data.get('dispense_type_id', 1),
            data.get('purpose', ''),
            month,
            data.get('notes', ''),
            session['user_id']
        ))

        operation_id = cursor.lastrowid

        # تسجيل النشاط
        log_activity(
            session['user_id'],
            'إضافة عملية',
            'fuel_operations',
            operation_id,
            f'إضافة عملية جديدة برقم السند {receipt_number}'
        )

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'تم إضافة العملية بنجاح',
            'receipt_number': receipt_number
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ: {str(e)}'
        }), 500

@app.route('/api/delete-operation/<int:operation_id>', methods=['DELETE'])
@login_required
def delete_operation(operation_id):
    """حذف عملية"""
    try:
        conn = get_db_connection()

        # الحصول على بيانات العملية قبل الحذف
        operation = conn.execute(
            'SELECT receipt_number FROM fuel_operations WHERE id = ?',
            (operation_id,)
        ).fetchone()

        if not operation:
            return jsonify({'success': False, 'message': 'العملية غير موجودة'}), 404

        # حذف العملية
        conn.execute('DELETE FROM fuel_operations WHERE id = ?', (operation_id,))

        # تسجيل النشاط
        log_activity(
            session['user_id'],
            'حذف عملية',
            'fuel_operations',
            operation_id,
            f'حذف العملية برقم السند {operation["receipt_number"]}'
        )

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'تم حذف العملية بنجاح'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ: {str(e)}'
        }), 500


# أضف هذه الدوال في ملف app.py في قسم API Routes

@app.route('/api/admin/users', methods=['GET', 'POST'])
@login_required
@role_required('مدير النظام')
def admin_users_api():
    """API لإدارة المستخدمين"""
    try:
        if request.method == 'POST':
            # إضافة مستخدم جديد
            data = request.get_json()

            # التحقق من البيانات
            required_fields = ['name', 'username', 'password', 'role']
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'message': f'الحقل {field} مطلوب'}), 400

            conn = get_db_connection()

            # التحقق من عدم تكرار اسم المستخدم
            existing_user = conn.execute(
                'SELECT id FROM users WHERE username = ?',
                (data['username'],)
            ).fetchone()

            if existing_user:
                conn.close()
                return jsonify({'success': False, 'message': 'اسم المستخدم موجود مسبقاً'}), 400

            # تشفير كلمة المرور
            hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')

            # إدخال المستخدم الجديد
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (name, username, password, role, unit_id, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (
                data['name'],
                data['username'],
                hashed_password,
                data['role'],
                data.get('unit_id') or None
            ))

            user_id = cursor.lastrowid

            # تسجيل النشاط
            log_activity(
                session['user_id'],
                'إضافة مستخدم',
                'users',
                user_id,
                f'إضافة مستخدم جديد: {data["name"]} ({data["role"]})'
            )

            conn.commit()
            conn.close()

            return jsonify({
                'success': True,
                'message': 'تم إضافة المستخدم بنجاح'
            })

        else:
            # الحصول على جميع المستخدمين
            conn = get_db_connection()
            users = conn.execute('''
                SELECT u.*, un.name as unit_name 
                FROM users u 
                LEFT JOIN units un ON u.unit_id = un.id 
                ORDER BY u.created_at DESC
            ''').fetchall()
            conn.close()

            return jsonify({
                'success': True,
                'users': [dict(user) for user in users]
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إدارة المستخدمين: {str(e)}'
        }), 500


@app.route('/api/admin/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required('مدير النظام')
def admin_user_api(user_id):
    """API لإدارة مستخدم محدد"""
    try:
        conn = get_db_connection()

        if request.method == 'GET':
            # الحصول على بيانات مستخدم
            user = conn.execute('''
                SELECT u.*, un.name as unit_name 
                FROM users u 
                LEFT JOIN units un ON u.unit_id = un.id 
                WHERE u.id = ?
            ''', (user_id,)).fetchone()

            conn.close()

            if user:
                return jsonify({
                    'success': True,
                    'user': dict(user)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'المستخدم غير موجود'
                }), 404

        elif request.method == 'PUT':
            # تحديث بيانات مستخدم
            data = request.get_json()

            # التحقق من البيانات
            required_fields = ['name', 'username', 'role']
            for field in required_fields:
                if field not in data:
                    conn.close()
                    return jsonify({'success': False, 'message': f'الحقل {field} مطلوب'}), 400

            # التحقق من عدم تكرار اسم المستخدم (باستثناء نفس المستخدم)
            existing_user = conn.execute(
                'SELECT id FROM users WHERE username = ? AND id != ?',
                (data['username'], user_id)
            ).fetchone()

            if existing_user:
                conn.close()
                return jsonify({'success': False, 'message': 'اسم المستخدم موجود مسبقاً'}), 400

            # تحديث البيانات
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET name = ?, username = ?, role = ?, unit_id = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data['name'],
                data['username'],
                data['role'],
                data.get('unit_id') or None,
                data.get('is_active', 1),
                user_id
            ))

            # تسجيل النشاط
            log_activity(
                session['user_id'],
                'تعديل مستخدم',
                'users',
                user_id,
                f'تعديل بيانات المستخدم ID: {user_id}'
            )

            conn.commit()
            conn.close()

            return jsonify({
                'success': True,
                'message': 'تم تحديث بيانات المستخدم بنجاح'
            })

        elif request.method == 'DELETE':
            # حذف مستخدم
            # لا يمكن حذف المستخدم الحالي
            if user_id == session['user_id']:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'لا يمكن حذف حسابك الخاص'
                }), 400

            # الحصول على بيانات المستخدم قبل الحذف
            user = conn.execute('SELECT name FROM users WHERE id = ?', (user_id,)).fetchone()

            if not user:
                conn.close()
                return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

            # حذف المستخدم
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))

            # تسجيل النشاط
            log_activity(
                session['user_id'],
                'حذف مستخدم',
                'users',
                user_id,
                f'حذف المستخدم: {user["name"]}'
            )

            conn.commit()
            conn.close()

            return jsonify({
                'success': True,
                'message': 'تم حذف المستخدم بنجاح'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إدارة المستخدم: {str(e)}'
        }), 500


@app.route('/api/admin/users/<int:user_id>/change-password', methods=['POST'])
@login_required
@role_required('مدير النظام')
def admin_change_password_api(user_id):
    """API لتغيير كلمة مرور مستخدم"""
    try:
        data = request.get_json()

        if 'new_password' not in data:
            return jsonify({'success': False, 'message': 'كلمة المرور الجديدة مطلوبة'}), 400

        if len(data['new_password']) < 6:
            return jsonify({'success': False, 'message': 'كلمة المرور يجب أن تكون 6 أحرف على الأقل'}), 400

        conn = get_db_connection()

        # تشفير كلمة المرور الجديدة
        hashed_password = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')

        # تحديث كلمة المرور
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET password = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (hashed_password, user_id))

        # تسجيل النشاط
        log_activity(
            session['user_id'],
            'تغيير كلمة المرور',
            'users',
            user_id,
            'تغيير كلمة مرور المستخدم'
        )

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'تم تغيير كلمة المرور بنجاح'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تغيير كلمة المرور: {str(e)}'
        }), 500


@app.route('/api/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('مدير النظام')
def admin_toggle_status_api(user_id):
    """API لتغيير حالة المستخدم"""
    try:
        data = request.get_json()

        if 'is_active' not in data:
            return jsonify({'success': False, 'message': 'حالة المستخدم مطلوبة'}), 400

        conn = get_db_connection()

        # لا يمكن تعطيل المستخدم الحالي
        if user_id == session['user_id'] and data['is_active'] == 0:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'لا يمكن تعطيل حسابك الخاص'
            }), 400

        # تحديث حالة المستخدم
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data['is_active'], user_id))

        # تسجيل النشاط
        action = 'تفعيل مستخدم' if data['is_active'] else 'تعطيل مستخدم'
        log_activity(
            session['user_id'],
            action,
            'users',
            user_id,
            f'{action} ID: {user_id}'
        )

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'تم {"تفعيل" if data["is_active"] else "تعطيل"} المستخدم بنجاح'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تغيير حالة المستخدم: {str(e)}'
        }), 500




# ============================================
# تشغيل التطبيق
# ============================================

if __name__ == '__main__':
    # التحقق من وجود قاعدة البيانات
    if not os.path.exists('database.db'):
        print("⚠️ قاعدة البيانات غير موجودة، يرجى تشغيل database.py أولاً")
        print("🔧 قم بتشغيل: python database.py")
    else:
        print("✅ قاعدة البيانات موجودة وجاهزة")

    # تشغيل التطبيق
    app.run(debug=True, host='0.0.0.0', port=5000)
