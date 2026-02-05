"""
database.py - ملف إنشاء وتهيئة قاعدة البيانات
"""
import sqlite3
import bcrypt
from datetime import datetime


def init_database():
    """إنشاء وتهيئة قاعدة البيانات"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    print("🚀 بدء إنشاء قاعدة البيانات...")

    # ============================================
    # إنشاء الجداول
    # ============================================

    print("📊 إنشاء الجداول...")

    # جدول الوحدات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        code TEXT UNIQUE,
        is_active BOOLEAN DEFAULT 1
    )
    ''')

    # جدول المستخدمين
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        unit_id INTEGER,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (unit_id) REFERENCES units(id)
    )
    ''')

    # جدول أنواع الصرف
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dispense_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    )
    ''')

    # جدول حالة السند
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS receipt_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        color_code TEXT
    )
    ''')

    # جدول العمليات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fuel_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_date TEXT NOT NULL,
        unit_id INTEGER NOT NULL,
        driver_name TEXT NOT NULL,
        vehicle_type TEXT NOT NULL,
        petrol_quantity REAL DEFAULT 0,
        diesel_quantity REAL DEFAULT 0,
        operation_officer TEXT,
        receipt_status_id INTEGER,
        receipt_number INTEGER UNIQUE,
        dispense_type_id INTEGER,
        purpose TEXT,
        month TEXT,
        notes TEXT,
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (unit_id) REFERENCES units(id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (dispense_type_id) REFERENCES dispense_types(id),
        FOREIGN KEY (receipt_status_id) REFERENCES receipt_statuses(id)
    )
    ''')

    # جدول سجل الأنشطة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        table_name TEXT,
        record_id INTEGER,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    # ============================================
    # إنشاء الفهارس
    # ============================================

    print("🔍 إنشاء الفهارس...")

    # فهارس جدول fuel_operations
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_ops_date ON fuel_operations(operation_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_ops_unit ON fuel_operations(unit_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_ops_month ON fuel_operations(month)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_ops_status ON fuel_operations(receipt_status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_ops_driver ON fuel_operations(driver_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_ops_officer ON fuel_operations(operation_officer)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_ops_user ON fuel_operations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_ops_receipt ON fuel_operations(receipt_number)")

    # فهارس جدول users
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_unit ON users(unit_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")

    # فهارس جدول units
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_units_name ON units(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_units_active ON units(is_active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_units_code ON units(code)")

    # فهارس جدول activity_logs
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON activity_logs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_action ON activity_logs(action)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_table ON activity_logs(table_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_created ON activity_logs(created_at)")

    # فهارس جداول التصنيف
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispense_types_name ON dispense_types(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipt_statuses_name ON receipt_statuses(name)")

    # ============================================
    # إدخال البيانات الأساسية
    # ============================================

    print("📝 إدخال البيانات الأساسية...")

    # إدخال أنواع الصرف
    dispense_types = [
        ('مخصص', 'صرف مخصص'),
        ('أوامر', 'صرف بناء على أوامر'),
        ('مهام', 'صرف لمهام محددة'),
        ('طارئ', 'صرف طارئ'),
        ('تدريب', 'صرف للتدريب')
    ]

    for name, desc in dispense_types:
        cursor.execute(
            "INSERT OR IGNORE INTO dispense_types (name, description) VALUES (?, ?)",
            (name, desc)
        )

    print(f"  ✅ تم إضافة {len(dispense_types)} نوع صرف")

    # إدخال حالات السند
    receipt_statuses = [
        ('منصرف', '#4CAF50'),  # أخضر
        ('غير منصرف', '#F44336'),  # أحمر
        ('معلق', '#FF9800'),  # برتقالي
        ('مسترد', '#2196F3')  # أزرق
    ]

    for name, color in receipt_statuses:
        cursor.execute(
            "INSERT OR IGNORE INTO receipt_statuses (name, color_code) VALUES (?, ?)",
            (name, color)
        )

    print(f"  ✅ تم إضافة {len(receipt_statuses)} حالة سند")

    # إدخال الوحدات
    units = [
        ('ق/اللواء', 'CMD'),
        ('ك1 س/ق', 'K1-CMD'),
        ('ك1 س1', 'K1-S1'),
        ('ك1 س2', 'K1-S2'),
        ('ك1 س3', 'K1-S3'),
        ('ك2 س/ق', 'K2-CMD'),
        ('ك2 س1', 'K2-S1'),
        ('ك2 س2', 'K2-S2'),
        ('ك2 س3', 'K2-S3'),
        ('ك3 س/ق', 'K3-CMD'),
        ('ك3 س1', 'K3-S1'),
        ('ك3 س2', 'K3-S2'),
        ('ك3 س3', 'K3-S3'),
        ('ك4 س/ق', 'K4-CMD'),
        ('ك4 س1', 'K4-S1'),
        ('ك4 س2', 'K4-S2'),
        ('ك4 س3', 'K4-S3'),
        ('الاستخبارات', 'INT'),
        ('التدريب', 'TRN'),
        ('البشرية', 'HR'),
        ('الامداد', 'LOG'),
        ('الاستطلاع', 'REC'),
        ('الطيران', 'AVN'),
        ('الاشارة', 'SIG'),
        ('الطبية', 'MED')
    ]

    for name, code in units:
        cursor.execute(
            "INSERT OR IGNORE INTO units (name, code) VALUES (?, ?)",
            (name, code)
        )

    print(f"  ✅ تم إضافة {len(units)} وحدة")

    # إدخال المستخدمين (4 مستخدمين فقط كما طلبت)
    users_data = [
        # مدير النظام
        ('admin', 'admin123', 'مدير النظام', 'مدير النظام', None),
        # مسؤول النظام
        ('sysadmin', 'sysadmin123', 'مسؤول النظام', 'مسؤول النظام', None),
        # المناوب بالعمليات
        ('ops1', 'ops123', 'المناوب بالعمليات - العمليات', 'المناوب بالعمليات', 2),
        # المناوب بالمحروقات
        ('fuel1', 'fuel123', 'المناوب بالمحروقات - المحروقات', 'المناوب بالمحروقات', 2),
    ]

    for username, password, name, role, unit_id in users_data:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute(
            "INSERT OR IGNORE INTO users (username, password, name, role, unit_id) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_password, name, role, unit_id)
        )

    print(f"  ✅ تم إضافة {len(users_data)} مستخدم")

    # ============================================
    # تأكيد والحفظ
    # ============================================

    conn.commit()
    conn.close()

    print("✅ تم إنشاء قاعدة البيانات بنجاح!")
    print("\n📋 بيانات الدخول الافتراضية:")
    print("===============================")
    for username, password, name, role, _ in users_data:
        print(f"👤 {name} ({role})")
        print(f"   المستخدم: {username}")
        print(f"   كلمة المرور: {password}")
        print("   ---")

    return True


def test_database():
    """اختبار اتصال قاعدة البيانات"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # اختبار العدادات
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM units")
        units_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM fuel_operations")
        operations_count = cursor.fetchone()[0]

        conn.close()

        print(f"\n📊 إحصائيات قاعدة البيانات:")
        print(f"   👥 المستخدمون: {users_count}")
        print(f"   🏢 الوحدات: {units_count}")
        print(f"   ⛽ العمليات: {operations_count}")

        return True

    except Exception as e:
        print(f"❌ خطأ في اختبار قاعدة البيانات: {e}")
        return False


if __name__ == '__main__':
    print("=" * 50)
    print("نظام إدارة قاعدة بيانات المحروقات")
    print("=" * 50)

    init_database()
    test_database()