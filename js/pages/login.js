// Login Form Functionality

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});

async function handleLogin(e) {
    e.preventDefault();

    // Get form values
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const role = document.getElementById('role').value;

    // Clear previous errors
    clearAllErrors();

    // Validate inputs
    if (!validateLoginForm(email, password, role)) {
        return;
    }

    // Show loading state
    showLoadingState(true);

    try {
        // Call backend API
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                password: password,
                role: role
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Save token to localStorage
            localStorage.setItem('authToken', data.token);
            localStorage.setItem('userRole', role);
            localStorage.setItem('userName', data.name);

            // Show success message
            showSuccessMessage('Login successful! Redirecting...');

            // Redirect after 1 second
            setTimeout(() => {
                redirectToDashboard(role);
            }, 1000);

        } else {
            showErrorMessage(data.message || 'Login failed. Please check your credentials.');
        }

    } catch (error) {
        console.error('Login error:', error);
        showErrorMessage('An error occurred. Please try again later.');
    } finally {
        showLoadingState(false);
    }
}

// Validation function
function validateLoginForm(email, password, role) {
    let isValid = true;

    // Email validation
    if (!email) {
        showFieldError('email', 'Email is required');
        isValid = false;
    } else if (!isValidEmail(email)) {
        showFieldError('email', 'Please enter a valid email');
        isValid = false;
    }

    // Password validation
    if (!password) {
        showFieldError('password', 'Password is required');
        isValid = false;
    } else if (password.length < 6) {
        showFieldError('password', 'Password must be at least 6 characters');
        isValid = false;
    }

    // Role validation
    if (!role) {
        showFieldError('role', 'Please select a role');
        isValid = false;
    }

    return isValid;
}

// Helper: Check if email is valid
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Helper: Show field error
function showFieldError(fieldId, message) {
    const errorElement = document.getElementById(fieldId + 'Error');
    if (errorElement) {
        errorElement.textContent = message;
    }
}

// Helper: Clear all errors
function clearAllErrors() {
    document.querySelectorAll('.form-error').forEach(el => {
        el.textContent = '';
    });
}

// Helper: Show error message
function showErrorMessage(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Helper: Show success message
function showSuccessMessage(message) {
    const successDiv = document.getElementById('successMessage');
    successDiv.textContent = message;
    successDiv.classList.remove('hidden');
}

// Helper: Show/hide loading state
function showLoadingState(isLoading) {
    document.getElementById('btnText').classList.toggle('hidden', isLoading);
    document.getElementById('btnLoading').classList.toggle('hidden', !isLoading);
}

// Helper: Redirect based on role
function redirectToDashboard(role) {
    switch(role) {
        case 'pet_owner':
            window.location.href = '../pages/pet-owner-dashboard.html';
            break;
        case 'clinic_staff':
            window.location.href = '../pages/staff-dashboard.html';
            break;
        case 'admin':
            window.location.href = '../pages/admin-dashboard.html';
            break;
        default:
            window.location.href = '../index.html';
    }
}