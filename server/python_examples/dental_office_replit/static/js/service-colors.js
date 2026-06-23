/**
 * Service Color Coordination Utility
 * Automatically applies color-coordinated classes to service elements
 */

// Service type mapping for JavaScript
const SERVICE_TYPE_MAPPING = {
    // Direct type mappings
    'cleaning': 'cleaning',
    'filling': 'filling',
    'whitening': 'whitening',
    'root_canal': 'root_canal',
    'extraction': 'extraction',
    'orthodontics': 'orthodontics',
    'checkup': 'checkup',
    'other': 'other',
    
    // Name-based mappings
    'regular cleaning': 'cleaning',
    'deep cleaning': 'cleaning',
    'dental cleaning': 'cleaning',
    'cavity filling': 'filling',
    'composite filling': 'filling',
    'teeth whitening': 'whitening',
    'professional whitening': 'whitening',
    'tooth whitening': 'whitening',
    'root canal': 'root_canal',
    'root canal treatment': 'root_canal',
    'tooth extraction': 'extraction',
    'dental extraction': 'extraction',
    'braces': 'orthodontics',
    'orthodontic': 'orthodontics',
    'dental checkup': 'checkup',
    'regular checkup': 'checkup',
    'examination': 'checkup'
};

/**
 * Get service type class from service name or type
 * @param {string} serviceInput - Service name or type
 * @returns {string} CSS class name
 */
function getServiceClass(serviceInput) {
    if (!serviceInput) return 'other';
    
    const input = serviceInput.toLowerCase();
    
    // Check direct match first
    if (SERVICE_TYPE_MAPPING[input]) {
        return SERVICE_TYPE_MAPPING[input];
    }
    
    // Check if any pattern matches
    for (const [pattern, type] of Object.entries(SERVICE_TYPE_MAPPING)) {
        if (input.includes(pattern)) {
            return type;
        }
    }
    
    return 'other';
}

/**
 * Apply service colors to elements automatically
 * Looks for elements with data-service-type, data-service-name, or specific selectors
 */
function applyServiceColors() {
    // Apply to elements with data-service-type attribute
    document.querySelectorAll('[data-service-type]').forEach(element => {
        const serviceType = element.getAttribute('data-service-type');
        const serviceClass = getServiceClass(serviceType);
        element.classList.add('service-label', serviceClass);
    });
    
    // Apply to elements with data-service-name attribute
    document.querySelectorAll('[data-service-name]').forEach(element => {
        const serviceName = element.getAttribute('data-service-name');
        const serviceClass = getServiceClass(serviceName);
        element.classList.add('service-label', serviceClass);
    });
    
    // Apply to service buttons in modals
    document.querySelectorAll('.service-btn').forEach(element => {
        const serviceType = element.getAttribute('data-type') || 
                           element.getAttribute('data-service-type') ||
                           element.textContent;
        const serviceClass = getServiceClass(serviceType);
        element.classList.add(serviceClass);
    });
    
    // Apply to appointment form service options
    document.querySelectorAll('#serviceTypeSelect option, #service option').forEach(option => {
        if (option.value && option.textContent) {
            const serviceClass = getServiceClass(option.textContent);
            option.setAttribute('data-service-class', serviceClass);
        }
    });
}

/**
 * Create colored service button
 * @param {string} serviceName - Name of the service
 * @param {string} serviceType - Type of the service (optional)
 * @param {Object} options - Additional options (onclick, classes, etc.)
 * @returns {HTMLElement} Colored service button element
 */
function createServiceButton(serviceName, serviceType = null, options = {}) {
    const button = document.createElement('button');
    const serviceClass = getServiceClass(serviceType || serviceName);
    
    button.className = `service-btn ${serviceClass} ${options.classes || ''}`;
    button.textContent = serviceName;
    
    if (options.onclick) {
        button.addEventListener('click', options.onclick);
    }
    
    if (options.attributes) {
        Object.entries(options.attributes).forEach(([key, value]) => {
            button.setAttribute(key, value);
        });
    }
    
    return button;
}

/**
 * Create colored service label/badge
 * @param {string} serviceName - Name of the service
 * @param {string} serviceType - Type of the service (optional)
 * @param {Object} options - Additional options (classes, etc.)
 * @returns {HTMLElement} Colored service label element
 */
function createServiceLabel(serviceName, serviceType = null, options = {}) {
    const label = document.createElement('span');
    const serviceClass = getServiceClass(serviceType || serviceName);
    
    label.className = `service-label ${serviceClass} ${options.classes || ''}`;
    label.textContent = serviceName;
    
    if (options.attributes) {
        Object.entries(options.attributes).forEach(([key, value]) => {
            label.setAttribute(key, value);
        });
    }
    
    return label;
}

/**
 * Update service dropdown styling
 * Colors the dropdown options based on service types
 */
function updateServiceDropdownStyling() {
    const serviceSelects = document.querySelectorAll('#serviceTypeSelect, #service, [name="service_id"]');
    
    serviceSelects.forEach(select => {
        select.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.textContent) {
                const serviceClass = getServiceClass(selectedOption.textContent);
                
                // Remove existing service classes
                this.classList.remove('cleaning', 'filling', 'whitening', 'root_canal', 
                                   'extraction', 'orthodontics', 'checkup', 'other');
                
                // Add new service class
                this.classList.add(serviceClass);
            }
        });
    });
}

/**
 * Initialize service colors when page loads
 */
function initServiceColors() {
    // Apply colors immediately
    applyServiceColors();
    
    // Update dropdown styling
    updateServiceDropdownStyling();
    
    // Re-apply when new content is added (for dynamic content)
    const observer = new MutationObserver(function(mutations) {
        let shouldReapply = false;
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                shouldReapply = true;
            }
        });
        if (shouldReapply) {
            setTimeout(applyServiceColors, 100); // Slight delay to ensure content is rendered
        }
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
}

// Auto-initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initServiceColors);
} else {
    initServiceColors();
}

// Export functions for manual use
window.ServiceColors = {
    getServiceClass,
    applyServiceColors,
    createServiceButton,
    createServiceLabel,
    updateServiceDropdownStyling,
    initServiceColors
}; 