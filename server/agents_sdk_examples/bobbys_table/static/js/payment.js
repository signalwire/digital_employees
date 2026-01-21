// Payment functionality for Bobby's Table
(function() {
    'use strict';
    
    // Prevent multiple initializations
    if (window.paymentSystemInitialized) {
        return;
    }
    window.paymentSystemInitialized = true;

    // Global payment system namespace
    if (typeof window.paymentSystem === 'undefined') {
        window.paymentSystem = {
            stripe: null,
            elements: null,
            cardElement: null,
            currentTotalAmount: null
        };
    }

    // Local references (no redeclaration issues in IIFE)
    let stripe = window.paymentSystem.stripe;
    let elements = window.paymentSystem.elements;
    let cardElement = window.paymentSystem.cardElement;
    let currentTotalAmount = window.paymentSystem.currentTotalAmount;

// Function to set current total amount from external context
window.setCurrentTotalAmount = function(amount) {
    currentTotalAmount = amount;
    window.paymentSystem.currentTotalAmount = amount;
};

// Initialize Stripe when the page loads (only once)
document.addEventListener('DOMContentLoaded', function() {
    if (!window.paymentSystem.stripe) {
        initializeStripe();
    }
});

async function initializeStripe() {
    try {
        // Get Stripe publishable key from the server
        const response = await fetch('/api/stripe/config');
        const config = await response.json();
        
        stripe = Stripe(config.publishable_key);
        window.paymentSystem.stripe = stripe;
        elements = stripe.elements({
            appearance: {
                theme: 'night',
                variables: {
                    colorPrimary: '#4d7eff',
                    colorBackground: '#212529',
                    colorText: '#ffffff',
                    colorDanger: '#dc3545',
                    fontFamily: 'system-ui, sans-serif',
                    spacingUnit: '4px',
                    borderRadius: '8px'
                }
            }
        });

        window.paymentSystem.elements = elements;
        
        // Create card element
        cardElement = elements.create('card', {
            style: {
                base: {
                    fontSize: '16px',
                    color: '#ffffff',
                    '::placeholder': {
                        color: '#adb5bd',
                    },
                },
                invalid: {
                    color: '#dc3545',
                    iconColor: '#dc3545'
                }
            }
        });
        
        window.paymentSystem.cardElement = cardElement;

        // Wait for DOM to be ready before mounting
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', mountStripeElements);
        } else {
            mountStripeElements();
        }
        
    } catch (error) {
        console.error('Error initializing Stripe:', error);
        showPaymentError('Failed to initialize payment system. Please try again later.');
    }
}

function mountStripeElements() {
    try {
        // Check if card element container exists
        const cardContainer = document.getElementById('card-element');
        if (!cardContainer) {
            console.warn('Card element container not found, will retry when modal opens');
            return;
        }

        // Mount the card element
        cardElement.mount('#card-element');

        // Handle real-time validation errors from the card Element
        cardElement.on('change', function(event) {
            const displayError = document.getElementById('card-errors');
            if (displayError) {
                if (event.error) {
                    displayError.textContent = event.error.message;
                } else {
                    displayError.textContent = '';
                }
            }
        });

        // Handle form submission
        const submitButton = document.getElementById('submit-payment');
        if (submitButton) {
            submitButton.addEventListener('click', handlePayment);
        }
        
    } catch (error) {
        console.error('Error mounting Stripe elements:', error);
    }
}

function openPaymentModal() {
    // Get current reservation data
    const reservationData = getCurrentReservationData();
    if (!reservationData) {
        showPaymentError('Unable to load reservation data');
        return;
    }

    // Use the global currentReservationId from calendar.js
    currentTotalAmount = reservationData.totalBill;

    // Populate payment details
    populatePaymentDetails(reservationData);

    // Show payment modal first
    const paymentModal = new bootstrap.Modal(document.getElementById('paymentModal'));
    paymentModal.show();

    // Wait for modal to be shown, then mount Stripe elements and pre-fill data
    document.getElementById('paymentModal').addEventListener('shown.bs.modal', function() {
        // Ensure Stripe elements are mounted
        if (cardElement && !document.getElementById('card-element').hasChildNodes()) {
            mountStripeElements();
        }

        // Pre-fill billing information if available
        const nameField = document.getElementById('billing-name');
        const smsField = document.getElementById('billing-sms');
        
        if (nameField && reservationData.name) {
            nameField.value = reservationData.name;
        }
        if (smsField && reservationData.phone_number) {
            smsField.value = reservationData.phone_number;
        }
    }, { once: true }); // Use once: true to prevent multiple event listeners
}

function populatePaymentDetails(reservationData) {
    const paymentDetails = document.getElementById('paymentDetails');
    
    let html = `
        <div class="card bg-primary text-white mb-4">
            <div class="card-header">
                <h6 class="mb-0">
                    <i class="fas fa-receipt me-2"></i>Payment Summary
                </h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p class="mb-1"><strong>Reservation:</strong> ${reservationData.name}</p>
                        <p class="mb-1"><strong>Date:</strong> ${reservationData.date}</p>
                        <p class="mb-1"><strong>Time:</strong> ${reservationData.time}</p>
                        <p class="mb-0"><strong>Party Size:</strong> ${reservationData.party_size} ${reservationData.party_size === 1 ? 'person' : 'people'}</p>
                    </div>
                    <div class="col-md-6 text-end">
                        <h4 class="mb-0">Total: $${currentTotalAmount.toFixed(2)}</h4>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (reservationData.orders && reservationData.orders.length > 0) {
        html += `
            <div class="card bg-dark border-secondary mb-3">
                <div class="card-header bg-secondary">
                    <h6 class="mb-0">Order Breakdown</h6>
                </div>
                <div class="card-body">
        `;

        reservationData.orders.forEach((order, idx) => {
            html += `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span>${order.person_name || `Person ${idx + 1}`}</span>
                    <span class="badge bg-primary">$${order.total_amount.toFixed(2)}</span>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    }

    paymentDetails.innerHTML = html;
}

async function handlePayment(event) {
    event.preventDefault();

    if (!stripe || !cardElement) {
        showPaymentError('Payment system not initialized');
        return;
    }

    // Validate form
    if (!validatePaymentForm()) {
        return;
    }

    // Show processing state
    setPaymentProcessing(true);

    try {
        // Determine payment type and create appropriate payment intent
        const isOrderPayment = window.paymentType === 'order';
        const paymentData = {
            amount: Math.round(currentTotalAmount * 100), // Convert to cents
            currency: 'usd'
        };
        
        if (isOrderPayment) {
            paymentData.order_id = window.currentOrderId;
        } else {
            paymentData.reservation_id = window.currentReservationId;
        }

        // Create payment intent
        const response = await fetch('/api/stripe/create-payment-intent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(paymentData)
        });

        const { client_secret, error } = await response.json();

        if (error) {
            throw new Error(error);
        }

        // Confirm payment with Stripe
        const { error: stripeError, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
            payment_method: {
                card: cardElement,
                billing_details: {
                    name: document.getElementById('billing-name')?.value || '',
                    email: document.getElementById('billing-email')?.value || null,
                    phone: document.getElementById('billing-sms')?.value || ''
                }
            }
        });

        if (stripeError) {
            throw new Error(stripeError.message);
        }

        if (paymentIntent.status === 'succeeded') {
            // Payment successful, update the appropriate record
            let updateResult;
            if (isOrderPayment) {
                updateResult = await updateOrderPaymentStatus(window.currentOrderId, paymentIntent.id, currentTotalAmount);
            } else {
                updateResult = await updatePaymentStatus(window.currentReservationId, paymentIntent.id, currentTotalAmount);
            }
            
            // Close payment modal and clean up backdrops
            const paymentModal = bootstrap.Modal.getInstance(document.getElementById('paymentModal'));
            paymentModal.hide();
            
            // Clean up any lingering backdrops after modal closes
            setTimeout(() => {
                const backdrops = document.querySelectorAll('.modal-backdrop');
                backdrops.forEach(backdrop => backdrop.remove());
            }, 300);
            
            // Handle post-payment actions based on type
            if (isOrderPayment) {
                // For orders, clear cart and close cart modal
                if (typeof window.cart !== 'undefined' && window.cart && window.cart.clearCart) {
                    window.cart.clearCart();
                }
                const cartModal = bootstrap.Modal.getInstance(document.getElementById('cartModal'));
                if (cartModal) {
                    cartModal.hide();
                }
                
                // Show success message
                let successMessage = `Payment successful! Your order #${window.currentOrderId} has been paid.`;
                if (updateResult && updateResult.sms_result && updateResult.sms_result.sms_sent) {
                    successMessage += ' A receipt has been sent to your phone via SMS.';
                }
                showPaymentSuccess(successMessage);
            } else {
                // For reservations, update the reservation details modal if it exists
                if (typeof updatePaymentButtons === 'function') {
                    updatePaymentButtons('paid');
                }
                
                // Show success message with SMS info
                let successMessage = 'Payment successful! Your bill has been paid.';
                if (updateResult && updateResult.sms_result && updateResult.sms_result.sms_sent) {
                    successMessage += ' A receipt has been sent to your phone via SMS.';
                }
                showPaymentSuccess(successMessage);
                
                // Call global success handler if available (for index page)
                if (typeof window.handlePaymentSuccess === 'function') {
                    window.handlePaymentSuccess(paymentIntent.id, currentTotalAmount);
                }
                
                // Refresh the calendar to show updated status
                if (typeof calendar !== 'undefined') {
                    calendar.refetchEvents();
                }
            }
        }

    } catch (error) {
        console.error('Payment error:', error);
        showPaymentError(error.message || 'Payment failed. Please try again.');
    } finally {
        setPaymentProcessing(false);
    }
}

function validatePaymentForm() {
    const requiredFields = [
        'billing-name',
        'billing-sms'
    ];

    for (const fieldId of requiredFields) {
        const field = document.getElementById(fieldId);
        if (!field) {
            showPaymentError(`Required field ${fieldId} not found`);
            return false;
        }
        if (!field.value.trim()) {
            field.focus();
            const label = field.labels && field.labels[0] ? field.labels[0].textContent : fieldId;
            showPaymentError(`Please fill in the ${label}`);
            return false;
        }
    }

    // Validate SMS number format (basic validation)
    const smsField = document.getElementById('billing-sms');
    if (!smsField) {
        showPaymentError('SMS field not found');
        return false;
    }
    
    const sms = smsField.value;
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    if (!phoneRegex.test(sms.replace(/[\s\-\(\)]/g, ''))) {
        smsField.focus();
        showPaymentError('Please enter a valid phone number');
        return false;
    }

    // Validate email format only if provided
    const emailField = document.getElementById('billing-email');
    if (emailField) {
        const email = emailField.value;
        if (email.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                emailField.focus();
                showPaymentError('Please enter a valid email address');
                return false;
            }
        }
    }

    return true;
}

async function updatePaymentStatus(reservationId, paymentIntentId, amount) {
    try {
        const smsField = document.getElementById('billing-sms');
        const smsNumber = smsField ? smsField.value : '';
        const response = await fetch('/api/reservations/payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                reservation_id: reservationId,
                payment_intent_id: paymentIntentId,
                amount: amount,
                status: 'paid',
                sms_number: smsNumber
            })
        });
        return await response.json();
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function updateOrderPaymentStatus(orderId, paymentIntentId, amount) {
    try {
        const smsField = document.getElementById('billing-sms');
        const smsNumber = smsField ? smsField.value : '';
        const response = await fetch(`/api/orders/${orderId}/payment`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                payment_status: 'paid',
                payment_intent_id: paymentIntentId,
                payment_amount: amount,
                sms_number: smsNumber
            })
        });
        return await response.json();
    } catch (error) {
        return { success: false, error: error.message };
    }
}

function setPaymentProcessing(processing) {
    const submitButton = document.getElementById('submit-payment');
    const processingDiv = document.getElementById('payment-processing');
    const form = document.getElementById('payment-form');

    if (processing) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        processingDiv.style.display = 'block';
        form.style.opacity = '0.6';
    } else {
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="fas fa-lock me-2"></i>Pay Now';
        processingDiv.style.display = 'none';
        form.style.opacity = '1';
    }
}

function getCurrentReservationData() {
    // This function should return the current reservation data
    // It will be called from the reservation details modal context or index page
    if (window.currentReservationData) {
        return window.currentReservationData;
    }
    
    // For index page context, we need to fetch the data
    if (window.currentReservationId && !window.currentReservationData) {
        // Return a promise-like structure for async loading
        return {
            id: window.currentReservationId,
            name: 'Loading...',
            totalBill: currentTotalAmount || 0,
            date: 'Loading...',
            time: 'Loading...',
            party_size: 1,
            phone_number: '',
            orders: []
        };
    }
    
    return null;
}

function showPaymentError(message) {
    // Create or update error alert
    let alertDiv = document.getElementById('payment-error-alert');
    if (!alertDiv) {
        alertDiv = document.createElement('div');
        alertDiv.id = 'payment-error-alert';
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            <span id="payment-error-message"></span>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('#paymentModal .modal-body').prepend(alertDiv);
    }
    
    document.getElementById('payment-error-message').textContent = message;
    alertDiv.style.display = 'block';
}

function showPaymentSuccess(message) {
    // Create success alert in the main page
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Expose functions to global scope
window.initializeStripe = initializeStripe;
window.openPaymentModal = openPaymentModal;
window.handlePayment = handlePayment;
window.showPaymentSuccess = showPaymentSuccess;
window.showPaymentError = showPaymentError;

})(); // Close IIFE