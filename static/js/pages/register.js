// Registration Form Functionality

document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            // On bloque d'abord la soumission
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
            hideMessages();

            // Validate inputs côté front
            const isValid = validateRegisterForm(
                fullName,
                email,
                password,
                confirmPassword,
                userRole,
                termsAccepted
            );

            // Si invalide → on affiche les erreurs et on s'arrête là
            if (!isValid) {
                showErrorMessage('Please correct the errors in the form.');
                return;
            }

            // Si tout est OK côté front → on laisse partir le formulaire vers Flask
            e.target.submit();
        });
    }
});

// Validation function (inchangée)
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

// Helper: Hide both global messages
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

// Helper: Show success message (tu peux le garder si tu veux)
function showSuccessMessage(message) {
    const successDiv = document.getElementById('successMessage');
    if (successDiv) {
        successDiv.textContent = message;
        successDiv.classList.remove('hidden');
    }
}
