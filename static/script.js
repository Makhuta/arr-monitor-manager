// JavaScript for Sonarr/Radarr Monitor

/**
 * Copy text to clipboard
 * @param {string} elementId - ID of the input element containing text to copy
 */
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.error('Element not found:', elementId);
        return;
    }
    
    // Select and copy the text
    element.select();
    element.setSelectionRange(0, 99999); // For mobile devices
    
    try {
        document.execCommand('copy');
        showToast('Token copied to clipboard!', 'success');
    } catch (err) {
        console.error('Failed to copy text:', err);
        showToast('Failed to copy token', 'error');
    }
    
    // Clear selection
    window.getSelection().removeAllRanges();
}

/**
 * Regenerate webhook token for a configuration
 * @param {string} configId - ID of the configuration
 */
function regenerateToken(configId) {
    if (!confirm('Are you sure you want to regenerate the webhook token? You will need to update it in your Sonarr/Radarr settings.')) {
        return;
    }
    
    // Show loading state
    const button = event.target.closest('.dropdown-item');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Regenerating...';
    button.disabled = true;
    
    fetch(`/regenerate_token/${encodeURIComponent(configId)}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the token input field
            const tokenInput = document.getElementById(`token-${configId}`);
            if (tokenInput) {
                tokenInput.value = data.token;
            }
            showToast('Webhook token regenerated successfully!', 'success');
        } else {
            showToast('Failed to regenerate token: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error regenerating token:', error);
        showToast('Failed to regenerate token', 'error');
    })
    .finally(() => {
        // Restore button state
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, info)
 */
function showToast(message, type = 'info') {
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} border-0" 
             id="${toastId}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Create or get toast container
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1050';
        document.body.appendChild(toastContainer);
    }
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 3000
    });
    
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

/**
 * Validate form before submission
 */
function validateForm() {
    const form = document.querySelector('form');
    if (!form) return;
    
    form.addEventListener('submit', function(event) {
        const name = form.querySelector('#name').value.trim();
        const serviceType = form.querySelector('#service_type').value;
        const ipAddress = form.querySelector('#ip_address').value.trim();
        const apiToken = form.querySelector('#api_token').value.trim();
        const qualityScore = form.querySelector('#quality_score').value;
        const formatName = form.querySelector('#format_name').value.trim();
        
        // Basic validation
        if (!name || !serviceType || !ipAddress || !apiToken) {
            event.preventDefault();
            showToast('Please fill in all required fields', 'error');
            return;
        }
        
        // Check if at least one quality criteria is specified
        if (!qualityScore && !formatName) {
            if (!confirm('No quality criteria specified. The system will not automatically unmonitor content. Continue anyway?')) {
                event.preventDefault();
                return;
            }
        }
        
        // Show loading state on submit button
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Adding Configuration...';
            submitBtn.disabled = true;
            
            // Restore button after a delay (in case of validation errors)
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 5000);
        }
    });
}

/**
 * Initialize clipboard API if available
 */
function initializeClipboard() {
    // Check if clipboard API is available
    if (!navigator.clipboard) {
        console.warn('Clipboard API not available, falling back to document.execCommand');
        return;
    }
    
    // Update copyToClipboard function to use modern API
    window.copyToClipboardModern = function(elementId) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error('Element not found:', elementId);
            return;
        }
        
        navigator.clipboard.writeText(element.value)
            .then(() => {
                showToast('Token copied to clipboard!', 'success');
            })
            .catch(err => {
                console.error('Failed to copy text:', err);
                // Fallback to old method
                copyToClipboard(elementId);
            });
    };
}

/**
 * Auto-refresh configurations periodically
 */
function setupAutoRefresh() {
    // Auto-refresh every 5 minutes to show any manual YAML file changes
    setInterval(() => {
        // Only refresh if user is not actively editing the form
        const activeElement = document.activeElement;
        if (!activeElement || !activeElement.closest('form')) {
            window.location.reload();
        }
    }, 5 * 60 * 1000); // 5 minutes
}

/**
 * Initialize all features when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validation
    validateForm();
    
    // Initialize clipboard functionality
    initializeClipboard();
    
    // Setup auto-refresh (disabled by default, uncomment to enable)
    // setupAutoRefresh();
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    console.log('Sonarr/Radarr Monitor initialized');
});

/**
 * Handle form field interactions
 */
document.addEventListener('DOMContentLoaded', function() {
    // Auto-format IP address field
    const ipField = document.getElementById('ip_address');
    if (ipField) {
        ipField.addEventListener('blur', function() {
            let value = this.value.trim();
            // Remove protocol if present
            value = value.replace(/^https?:\/\//, '');
            // Remove trailing slash
            value = value.replace(/\/$/, '');
            this.value = value;
        });
    }
    
    // Show/hide quality criteria helper text
    const qualityScore = document.getElementById('quality_score');
    const formatName = document.getElementById('format_name');
    
    function updateQualityCriteriaHint() {
        const hasScore = qualityScore && qualityScore.value.trim();
        const hasFormat = formatName && formatName.value.trim();
        
        // You can add visual hints here if needed
        // For now, the validation happens on form submit
    }
    
    if (qualityScore) qualityScore.addEventListener('input', updateQualityCriteriaHint);
    if (formatName) formatName.addEventListener('input', updateQualityCriteriaHint);
});
