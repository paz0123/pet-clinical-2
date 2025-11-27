// Registration Form Functionality

document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
});

async function handleRegister(e) {
    e.preventDefault();

    // Get form values
    const fullName = document.getElementById('fullName').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const userRole = document.getElementById('userRole').value;
    const termsAccepted = document.getElementById('terms').checked;

    // Clear previous errors
    clearAllErrors();

    // Validate inputs
    if (!validateRegisterForm(fullName, email, password, confirmPassword, userRole, termsAccepted)) {
        return;
    }

    // Show loading state
    showLoadingState(true);

    try {
        // Call backend API
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fullName: fullName,
                email: email,
                password: password,
                userRole: userRole
            })
        });

        const data = await response.json();

        if (response.ok) {
            showSuccessMessage('Account created successfully! Redirecting to login...');

            // Redirect after 2 seconds
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 2000);

        } else {
            showErrorMessage(data.message || 'Registration failed. Please try again.');
        }

    } catch (error) {
        console.error('Registration error:', error);
        showErrorMessage('An error occurred. Please try again later.');
    } finally {
        showLoadingState(false);
    }
}

// Validation function
function validateRegisterForm(fullName, email, password, confirmPassword, userRole, termsAccepted) {
    let isValid = true;

    // Full Name validation
    if (!fullName) {
        showFieldError('fullName', 'Full name is required');
        isValid = false;
    } else if (fullName.length < 3) {
        showFieldError('fullName', 'Name must be at least 3 characters');
        isValid = false;
    }

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
    } else if (password.length < 8) {
        showFieldError('password', 'Password must be at least 8 characters');
        isValid = false;
    }

    // Confirm password validation
    if (!confirmPassword) {
        showFieldError('confirmPassword', 'Please confirm your password');
        isValid = false;
    } else if (password !== confirmPassword) {
        showFieldError('confirmPassword', 'Passwords do not match');
        isValid = false;
    }

    // Role validation
    if (!userRole) {
        showFieldError('userRole', 'Please select a role');
        isValid = false;
    }

    // Terms validation
    if (!termsAccepted) {
        showFieldError('terms', 'You must accept the terms and conditions');
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