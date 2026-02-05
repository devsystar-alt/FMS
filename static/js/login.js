/**
 * login.js - دوال JavaScript لصفحة تسجيل الدخول
 */

// تهيئة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    initLoginPage();
});

function initLoginPage() {
    // إضافة تأثيرات للصفحة
    addPageAnimations();

    // إضافة مستمعين للأحداث
    setupEventListeners();

    // التحقق من التخزين المحلي لـ "تذكرني"
    checkRememberMe();
}

function addPageAnimations() {
    // إضافة تأثيرات للعناصر
    const elements = document.querySelectorAll('.form-group, .role-btn, .credential-card');

    elements.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';

        setTimeout(() => {
            element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

function setupEventListeners() {
    // التحقق من صحة البيانات أثناء الكتابة
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    if (usernameInput) {
        usernameInput.addEventListener('input', validateUsername);
    }

    if (passwordInput) {
        passwordInput.addEventListener('input', validatePassword);
    }

    // مستمع للضغط على Enter
    document.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const activeElement = document.activeElement;
            if (activeElement.tagName === 'INPUT') {
                e.preventDefault();
                document.getElementById('loginForm').dispatchEvent(new Event('submit'));
            }
        }
    });
}

function validateUsername() {
    const username = this.value.trim();
    const errorElement = document.getElementById('usernameError');

    if (username.length === 0) {
        errorElement.textContent = 'اسم المستخدم مطلوب';
        this.style.borderColor = '#e74c3c';
        return false;
    }

    if (username.length < 3) {
        errorElement.textContent = 'اسم المستخدم قصير جداً';
        this.style.borderColor = '#e74c3c';
        return false;
    }

    errorElement.textContent = '';
    this.style.borderColor = '#4CAF50';
    return true;
}

function validatePassword() {
    const password = this.value;
    const errorElement = document.getElementById('passwordError');

    if (password.length === 0) {
        errorElement.textContent = 'كلمة المرور مطلوبة';
        this.style.borderColor = '#e74c3c';
        return false;
    }

    if (password.length < 6) {
        errorElement.textContent = 'كلمة المرور يجب أن تكون 6 أحرف على الأقل';
        this.style.borderColor = '#e74c3c';
        return false;
    }

    errorElement.textContent = '';
    this.style.borderColor = '#4CAF50';
    return true;
}

function checkRememberMe() {
    const rememberMe = localStorage.getItem('rememberMe');
    const username = localStorage.getItem('rememberedUsername');

    if (rememberMe === 'true' && username) {
        document.getElementById('username').value = username;
        document.getElementById('remember').checked = true;
    }
}

function saveRememberMe() {
    const rememberMe = document.getElementById('remember').checked;
    const username = document.getElementById('username').value;

    if (rememberMe) {
        localStorage.setItem('rememberMe', 'true');
        localStorage.setItem('rememberedUsername', username);
    } else {
        localStorage.removeItem('rememberMe');
        localStorage.removeItem('rememberedUsername');
    }
}

// دالة لإظهار رسالة تحميل
function showLoading(message = 'جاري تسجيل الدخول...') {
    const loginBtn = document.getElementById('loginBtn');
    const loginText = document.getElementById('loginText');
    const loginSpinner = document.getElementById('loginSpinner');

    if (loginBtn && loginText && loginSpinner) {
        loginText.textContent = message;
        loginSpinner.classList.remove('hidden');
        loginBtn.disabled = true;
    }
}

// دالة لإخفاء رسالة التحمل
function hideLoading() {
    const loginBtn = document.getElementById('loginBtn');
    const loginText = document.getElementById('loginText');
    const loginSpinner = document.getElementById('loginSpinner');

    if (loginBtn && loginText && loginSpinner) {
        loginText.textContent = 'تسجيل الدخول';
        loginSpinner.classList.add('hidden');
        loginBtn.disabled = false;
    }
}

// دالة لعرض رسالة خطأ
function showError(field, message) {
    const errorElement = document.getElementById(`${field}Error`);
    const inputElement = document.getElementById(field);

    if (errorElement && inputElement) {
        errorElement.textContent = message;
        inputElement.style.borderColor = '#e74c3c';

        // اهتزاز الحقل
        inputElement.style.animation = 'shake 0.5s ease-in-out';
        setTimeout(() => {
            inputElement.style.animation = '';
        }, 500);
    }
}

// أنيميشن للاهتزاز
const shakeAnimation = `
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
    20%, 40%, 60%, 80% { transform: translateX(5px); }
}
`;

const styleSheet = document.createElement('style');
styleSheet.textContent = shakeAnimation;
document.head.appendChild(styleSheet);