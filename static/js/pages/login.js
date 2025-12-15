// Login Form Functionality

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Get form values
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const role = document.getElementById('role').value;

            // Clear previous errors & messages
            clearAllErrors();
            hideMessages();

            // Validate inputs (côté front)
            const isValid = validateLoginForm(email, password, role);

            if (!isValid) {
                showErrorMessage('Please correct the errors in the form.');
                return;
            }

            // Facultatif : état de chargement visuel
            showLoadingState(true);

            // Si tout est OK → on laisse partir le formulaire vers Flask (/login)
            e.target.submit();
        });
    }
});

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
        // Tu peux passer à 8 si tu veux homogénéiser avec register
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

// Helper: Hide global messages
function hideMessages() {
    const errorDiv = document.getElementById('errorMessage');
    const successDiv = document.getElementById('successMessage');

    if (errorDiv) {
        errorDiv.classList.add('hidden');
        errorDiv.textContent = '';
    }
    if (successDiv) {
        successDiv.classList.add('hidden');
        successDiv.textContent = '';
    }
}

// Helper: Show error message
function showErrorMessage(message) {
    const errorDiv = document.getElementById('errorMessage');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }
}

// Helper: Show success message (optionnel)
function showSuccessMessage(message) {
    const successDiv = document.getElementById('successMessage');
    if (successDiv) {
        successDiv.textContent = message;
        successDiv.classList.remove('hidden');
    }
}

// Helper: Show/hide loading state
function showLoadingState(isLoading) {
    const btnText = document.getElementById('btnText');
    const btnLoading = document.getElementById('btnLoading');

    if (btnText && btnLoading) {
        btnText.classList.toggle('hidden', isLoading);
        btnLoading.classList.toggle('hidden', !isLoading);
    }
}
