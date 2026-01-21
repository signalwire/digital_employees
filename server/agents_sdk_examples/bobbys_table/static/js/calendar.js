let selectedDate = null;
let menuData = [];
let calendar; // Make calendar globally accessible
let currentReservationId; // Global reservation ID for payment processing

// Make currentReservationId globally accessible
window.currentReservationId = null;

// Test function to check if modal works
function testModal() {
    console.log('Testing modal...');
    try {
        const modalElement = document.getElementById('newReservationModal');
        console.log('Modal element:', modalElement);
        
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
            console.log('Modal should be showing now');
        } else {
            console.error('Modal element not found!');
        }
    } catch (error) {
        console.error('Error testing modal:', error);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing calendar...');
    
    var calendarEl = document.getElementById('calendar');
    console.log('Calendar element:', calendarEl);
    
    // Only initialize calendar if the calendar element exists and FullCalendar is available
    if (calendarEl && typeof FullCalendar !== 'undefined') {
        // Initialize calendar
        calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',  // Set month view as default
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'  // Month first in the view options
        },
        height: 'auto',
        contentHeight: 'auto',
        expandRows: true,
        aspectRatio: 1.35,
        handleWindowResize: true,
        slotMinTime: '09:00:00',
        slotMaxTime: '21:00:00',
        allDaySlot: false,
        scrollTime: '12:00:00',  // Start scroll position at noon
        scrollTimeReset: false,  // Don't reset scroll position when changing dates
        selectable: true,
        selectMirror: true,
        nowIndicator: true,
        dayMaxEvents: 5,  // Show up to 5 events per day with increased cell height
        moreLinkClick: 'popover',  // Show popover for additional events
        weekNumbers: false,  // Remove week numbers (W22, etc.)
        editable: true,
        eventTimeFormat: { // 12-hour format for events
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        },
        slotLabelFormat: { // 12-hour format for time slots
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        },
        selectConstraint: {
            startTime: '09:00',
            endTime: '21:00',
            dows: [0, 1, 2, 3, 4, 5, 6]
        },
        businessHours: {
            daysOfWeek: [0, 1, 2, 3, 4, 5, 6],
            startTime: '09:00',
            endTime: '21:00',
        },
        select: function(info) {
            console.log('Calendar select triggered:', info);
            
            try {
                // Show the new reservation modal
                const modalElement = document.getElementById('newReservationModal');
                console.log('Modal element found:', modalElement);
                
                const reservationModal = new bootstrap.Modal(modalElement);
                
                // Set the selected date in the form
                const dateInput = document.getElementById('reservation_date');
                console.log('Date input found:', dateInput);
                dateInput.value = info.startStr.split('T')[0];
                
                // Handle time setting for select dropdown
                const timeStr = info.startStr.split('T')[1] ? info.startStr.split('T')[1].slice(0, 5) : '12:00';
                const timeSelect = document.getElementById('reservation_time');
                console.log('Time select found:', timeSelect);
                
                console.log('Setting time to:', timeStr);
                
                // Find the closest available time slot
                let closestTime = '12:00';
                const availableTimes = Array.from(timeSelect.options).map(option => option.value).filter(value => value);
                
                if (availableTimes.includes(timeStr)) {
                    closestTime = timeStr;
                } else {
                    // Find the closest time slot
                    const selectedMinutes = parseInt(timeStr.split(':')[0]) * 60 + parseInt(timeStr.split(':')[1]);
                    let minDiff = Infinity;
                    
                    availableTimes.forEach(time => {
                        const timeMinutes = parseInt(time.split(':')[0]) * 60 + parseInt(time.split(':')[1]);
                        const diff = Math.abs(timeMinutes - selectedMinutes);
                        if (diff < minDiff) {
                            minDiff = diff;
                            closestTime = time;
                        }
                    });
                }
                
                timeSelect.value = closestTime;
                console.log('Final time set to:', closestTime);
                
                console.log('Showing modal...');
                reservationModal.show();
                
                // Fetch menu items and render party order forms when modal opens
                fetchMenuItems();
                calendar.unselect();
                
            } catch (error) {
                console.error('Error in select handler:', error);
            }
        },
        dateClick: function(info) {
            console.log('Date click triggered:', info);
            
            try {
                // Fallback for when select doesn't work
                const modalElement = document.getElementById('newReservationModal');
                const reservationModal = new bootstrap.Modal(modalElement);
                
                // Set the clicked date
                document.getElementById('reservation_date').value = info.dateStr;
                
                // Set default time to 12:00 PM
                document.getElementById('reservation_time').value = '12:00';
                
                console.log('Showing modal via dateClick...');
                reservationModal.show();
                
                // Fetch menu items and render party order forms when modal opens
                fetchMenuItems();
                
            } catch (error) {
                console.error('Error in dateClick handler:', error);
            }
        },
        eventClick: function(info) {
            // Show event details in the modal
            showReservationDetails(info.event);
        },
        datesSet: function(info) {
            // Reset reservation count tracking when view changes (month/week/day or date navigation)
            console.log('📅 Calendar view/date changed, resetting reservation count tracking');
            lastReservationCount = 0;
            initialCountSet = false;
        },
        events: '/api/reservations/calendar'
    });

        console.log('Rendering calendar...');
        calendar.render();
        console.log('Calendar rendered');
    } else {
        console.log('Calendar element not found or FullCalendar not available, skipping calendar initialization');
    }

    // Make testModal available globally for debugging
    window.testModal = testModal;

    // Schedule button event listeners (only if elements exist)
    document.querySelectorAll('#scheduleBtn, #scheduleBtn2').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const reservationModal = new bootstrap.Modal(document.getElementById('newReservationModal'));
            
            // Set today's date as default
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('reservation_date').value = today;
            
            reservationModal.show();
            // Fetch menu items and render party order forms when modal opens
            fetchMenuItems();
        });
    });

    // Only add event listeners if elements exist
    const partySizeInput = document.getElementById('partySizeInput');
    if (partySizeInput) {
        partySizeInput.addEventListener('input', function() {
            renderPartyOrderForms();
        });
    }

    // Add event listener for when the new reservation modal is shown (only if modal exists)
    const newReservationModal = document.getElementById('newReservationModal');
    if (newReservationModal) {
        newReservationModal.addEventListener('shown.bs.modal', function() {
            fetchMenuItems();
        });
    }

    // Handle old school reservation checkbox (only if element exists)
    const oldSchoolReservation = document.getElementById('oldSchoolReservation');
    if (oldSchoolReservation) {
        oldSchoolReservation.addEventListener('change', function() {
            const orderSection = document.getElementById('orderSection');
            if (this.checked) {
                orderSection.style.display = 'none';
            } else {
                orderSection.style.display = 'block';
                // Re-render party order forms when showing the section
                renderPartyOrderForms();
            }
        });
    }

    // Handle old school reservation checkbox for edit modal (only if element exists)
    const editOldSchoolReservation = document.getElementById('editOldSchoolReservation');
    if (editOldSchoolReservation) {
        editOldSchoolReservation.addEventListener('change', function() {
            const editOrderSection = document.getElementById('editOrderSection');
            if (this.checked) {
                editOrderSection.style.display = 'none';
            } else {
                editOrderSection.style.display = 'block';
                // Re-render party order forms when showing the section
                renderEditPartyOrderForms();
            }
        });
    }

    const reservationForm = document.getElementById('reservationForm');
    if (reservationForm) {
        reservationForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        // Check if this is an old school reservation
        const isOldSchool = document.getElementById('oldSchoolReservation').checked;
        
        if (!isOldSchool) {
            // Collect party orders only if not old school
            const partyOrders = [];
            const partySize = parseInt(document.getElementById('partySizeInput').value) || 1;
            const nameInputs = document.querySelectorAll('.party-member-name');
            for (let i = 0; i < partySize; i++) {
                const name = nameInputs[i].value || '';
                const items = [];
                document.querySelectorAll(`input.menu-qty[data-person="${i}"]`).forEach(function(input) {
                    if (parseInt(input.value) > 0) {
                        items.push({
                            menu_item_id: input.dataset.id,
                            quantity: input.value
                        });
                    }
                });
                partyOrders.push({ name, items });
            }
            formData.append('party_orders', JSON.stringify(partyOrders));
        } else {
            // For old school reservations, send empty party orders
            formData.append('party_orders', JSON.stringify([]));
        }
        fetch('/api/reservations', {
            method: 'POST',
            body: formData
        }).then(resp => resp.json())
          .then(data => {
            if (data.success) {
                // Close the modal
                bootstrap.Modal.getInstance(document.getElementById('newReservationModal')).hide();
                // Refresh the calendar to show the new reservation
                calendar.refetchEvents();
                // Show success message
                alert('Reservation created successfully!');
            } else {
                alert('Error: ' + (data.error || 'Could not create reservation.'));
            }
          });
        });
    }
});

function showReservationDetails(event) {
    const details = document.getElementById('reservationDetails');
    
    // Handle different parameter structures
    let reservationId;
    if (event.id) {
        // Called from calendar event or table with {id: 'x', title: 'y'} format
        reservationId = event.id;
        currentReservationId = reservationId;
        window.currentReservationId = reservationId;
    } else if (typeof event === 'string' || typeof event === 'number') {
        // Called directly with reservation ID
        reservationId = event;
        currentReservationId = reservationId;
        window.currentReservationId = reservationId;
    } else {
        console.error('Invalid event parameter:', event);
        return;
    }
    
    // Fetch reservation and order details from backend
    fetch(`/api/reservations/${reservationId}`)
        .then(resp => {
            console.log('API Response status:', resp.status);
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
            }
            return resp.json();
        })
        .then(reservation => {
            console.log('Reservation data received:', reservation);
            // Format time in 12-hour format
            const time12hr = new Date(`1970-01-01T${reservation.time}`).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
            let html = `
                <div class="mb-3">
                    <h5 class="fw-bold mb-1" style="color: #00e6a7;">Reservation Details</h5>
                    <div><strong>Reservation Number:</strong> <span class="badge bg-primary">${reservation.reservation_number}</span></div>
                    <div><strong>Name:</strong> ${reservation.name}</div>
                    <div><strong>Party Size:</strong> ${reservation.party_size}</div>
                    <div><strong>Date:</strong> ${reservation.date}</div>
                    <div><strong>Time:</strong> ${time12hr}</div>
                    <div><strong>Phone:</strong> ${reservation.phone_number}</div>
                    <div><strong>Status:</strong> ${reservation.status}</div>
                    ${reservation.special_requests ? `<div><strong>Special Requests:</strong> ${reservation.special_requests}</div>` : ''}
                </div>
                <hr class="my-3">
                <h5 class="fw-bold mb-3" style="color: #00e6a7;">Party Orders</h5>
            `;
            let totalBill = 0;
            if (reservation.orders && reservation.orders.length > 0) {
                reservation.orders.forEach((order, idx) => {
                    html += `
                        <div class="card mb-3 bg-dark text-light border-0 shadow-sm">
                            <div class="card-header bg-secondary text-light d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>Person ${idx + 1} ${idx === 0 ? '(Reservation Holder)' : ''}</strong> - ${order.person_name || ''}
                                </div>
                                <div class="text-end">
                                    <span class="badge bg-primary">Order #${order.order_number}</span>
                                </div>
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                    `;
                    if (order.items && order.items.length > 0) {
                        order.items.forEach(item => {
                            const itemName = item.menu_item ? item.menu_item.name : `Item ID ${item.menu_item_id} (Not Found)`;
                            html += `
                                <li class="list-group-item bg-dark text-light d-flex justify-content-between align-items-center">
                                    <span><strong>${itemName}</strong> <small class="text-muted">x${item.quantity}</small></span>
                                    <span class="text-accent">$${(item.price_at_time * item.quantity).toFixed(2)}</span>
                                </li>
                            `;
                        });
                    } else {
                        html += `<li class="list-group-item bg-dark text-light">No items ordered.</li>`;
                    }
                    html += `
                                </ul>
                                <div class="mt-2 text-end"><strong>Total:</strong> <span class="text-accent">$${order.total_amount ? order.total_amount.toFixed(2) : '0.00'}</span></div>
                            </div>
                        </div>
                    `;
                    // Add to total bill
                    totalBill += order.total_amount || 0;
                });
                
                // Add Total Bill section
                html += `
                    <hr class="my-3">
                    <div class="card bg-primary text-light border-0 shadow-lg">
                        <div class="card-body text-center">
                            <h5 class="card-title mb-2"><i class="fas fa-receipt me-2"></i>Total Bill</h5>
                            <h3 class="text-white fw-bold">$${totalBill.toFixed(2)}</h3>
                `;
                
                // Add payment status and reference information if paid
                if (reservation.payment_status === 'paid') {
                    html += `
                        <div class="mt-3 pt-3 border-top border-light">
                            <div class="d-flex justify-content-center align-items-center mb-2">
                                <i class="fas fa-check-circle me-2 text-success"></i>
                                <span class="badge bg-success">PAID</span>
                            </div>
                    `;
                    
                    // Add payment date if available
                    if (reservation.payment_date) {
                        const paymentDate = new Date(reservation.payment_date).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        });
                        html += `<div class="small text-light mb-1">Paid on: ${paymentDate}</div>`;
                    }
                    
                    // Add confirmation number if available
                    if (reservation.confirmation_number) {
                        html += `
                            <div class="small text-light mb-1">
                                <strong>Confirmation #:</strong> ${reservation.confirmation_number}
                            </div>
                        `;
                    }
                    
                    // Add payment reference if available
                    if (reservation.payment_intent_id) {
                        const paymentId = reservation.payment_intent_id;
                        // Show only last 8 characters for security
                        const maskedPaymentId = paymentId.length > 8 ? '...' + paymentId.slice(-8) : paymentId;
                        html += `
                            <div class="small text-light">
                                <strong>Payment Ref:</strong> ${maskedPaymentId}
                            </div>
                        `;
                    }
                    
                    html += `</div>`;
                }
                
                html += `
                        </div>
                    </div>
                `;
            } else {
                html += `
                    <div class="text-center py-4">
                        <i class="fas fa-utensils fa-3x text-muted mb-3"></i>
                        <h6 class="text-muted">No party orders found</h6>
                        <p class="text-muted small">This reservation doesn't have any pre-orders yet.</p>
                        <p class="text-muted small">Click "Edit & Add Items" to add food and drinks to this reservation.</p>
                    </div>
                `;
            }
            details.innerHTML = html;
            
            // Store reservation data globally for payment processing
            window.currentReservationData = {
                ...reservation,
                totalBill: totalBill,
                time: time12hr
            };
            
            // Show appropriate payment button based on payment status
            updatePaymentButtons(reservation.payment_status || 'unpaid');
            
            // Update button states based on reservation status
            updateModalButtonStates(reservation.status || 'confirmed');
            
            // Start monitoring payment status for this reservation
            startPaymentStatusMonitoring(reservation.id, reservation.payment_status || 'unpaid');
            
            new bootstrap.Modal(document.getElementById('reservationModal')).show();
        })
        .catch(error => {
            console.error('Error fetching reservation details:', error);
            console.error('Error details:', error.message, error.stack);
            alert(`Error loading reservation details: ${error.message}. Please check the browser console for more details.`);
        });
}

function updatePaymentButtons(status) {
    const payBillBtn = document.getElementById('payBillBtn');
    const billPaidBtn = document.getElementById('billPaidBtn');

    if (status === 'paid') {
        payBillBtn.style.display = 'none';
        billPaidBtn.style.display = 'inline-block';
    } else {
        payBillBtn.style.display = 'inline-block';
        billPaidBtn.style.display = 'none';
    }
}

function updateReservationStatusInModal(newStatus) {
    // Find the status element in the reservation details and update it
    const detailsDiv = document.getElementById('reservationDetails');
    if (detailsDiv) {
        // Look for the status line and update it
        const statusRegex = /<div><strong>Status:<\/strong>\s*([^<]+)<\/div>/;
        const currentHTML = detailsDiv.innerHTML;
        
        let statusDisplay = newStatus;
        let statusClass = '';
        
        // Format status with appropriate styling
        switch(newStatus.toLowerCase()) {
            case 'cancelled':
                statusDisplay = '<span class="badge bg-danger">Cancelled</span>';
                break;
            case 'confirmed':
                statusDisplay = '<span class="badge bg-success">Confirmed</span>';
                break;
            case 'pending':
                statusDisplay = '<span class="badge bg-warning">Pending</span>';
                break;
            default:
                statusDisplay = `<span class="badge bg-secondary">${newStatus}</span>`;
        }
        
        if (statusRegex.test(currentHTML)) {
            // Update existing status
            const updatedHTML = currentHTML.replace(statusRegex, `<div><strong>Status:</strong> ${statusDisplay}</div>`);
            detailsDiv.innerHTML = updatedHTML;
        } else {
            // Status line might not exist, could add it if needed
            console.log('Status line not found in reservation details');
        }
    }
}

function updateModalButtonStates(reservationStatus) {
    // Get all the action buttons
    const cancelBtn = document.getElementById('cancelReservationBtn');
    const editBtn = document.getElementById('editReservationBtn');
    const rescheduleBtn = document.getElementById('rescheduleBtn');
    const payBillBtn = document.getElementById('payBillBtn');
    
    if (reservationStatus && reservationStatus.toLowerCase() === 'cancelled') {
        // Disable all action buttons for cancelled reservations
        if (cancelBtn) {
            cancelBtn.innerHTML = '<i class="fas fa-ban me-2"></i>Cancelled';
            cancelBtn.className = 'btn btn-secondary btn-lg';
            cancelBtn.disabled = true;
        }
        if (editBtn) {
            editBtn.disabled = true;
            editBtn.className = 'btn btn-secondary btn-lg';
            editBtn.innerHTML = '<i class="fas fa-ban me-2"></i>Cannot Edit (Cancelled)';
        }
        if (rescheduleBtn) {
            rescheduleBtn.disabled = true;
            rescheduleBtn.className = 'btn btn-secondary btn-lg';
            rescheduleBtn.innerHTML = '<i class="fas fa-ban me-2"></i>Cannot Reschedule (Cancelled)';
        }
        if (payBillBtn) {
            payBillBtn.style.display = 'none'; // Hide payment button for cancelled reservations
        }
    } else {
        // Reset buttons to normal state for active reservations
        if (cancelBtn) {
            cancelBtn.innerHTML = '<i class="fas fa-times me-2"></i>Cancel Reservation';
            cancelBtn.className = 'btn btn-outline-danger btn-lg';
            cancelBtn.disabled = false;
        }
        if (editBtn) {
            editBtn.disabled = false;
            editBtn.className = 'btn btn-info btn-lg';
            editBtn.innerHTML = '<i class="fas fa-edit me-2"></i>Edit & Add Items';
        }
        if (rescheduleBtn) {
            rescheduleBtn.disabled = false;
            rescheduleBtn.className = 'btn btn-accent btn-lg';
            rescheduleBtn.innerHTML = '<i class="fas fa-calendar-alt me-2"></i>Reschedule';
        }
        // Payment button visibility is handled by updatePaymentButtons()
    }
}

// Payment status monitoring variables
let paymentStatusInterval = null;
let currentMonitoringReservationId = null;

function startPaymentStatusMonitoring(reservationId, currentStatus) {
    // Clear any existing monitoring
    stopPaymentStatusMonitoring();
    
    // Only monitor if payment is not already paid
    if (currentStatus === 'paid') {
        return;
    }
    
    currentMonitoringReservationId = reservationId;
    console.log(`🔍 Starting payment status monitoring for reservation ${reservationId}`);
    
    // Check payment status every 5 seconds
    paymentStatusInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/reservations/${reservationId}`);
            if (response.ok) {
                const reservation = await response.json();
                const newStatus = reservation.payment_status || 'unpaid';
                
                // If status changed to paid, update the UI
                if (newStatus === 'paid' && currentStatus !== 'paid') {
                    console.log(`✅ Payment status changed to paid for reservation ${reservationId}`);
                    
                    // Update the payment buttons
                    updatePaymentButtons('paid');
                    
                    // Update the stored reservation data
                    if (window.currentReservationData) {
                        window.currentReservationData.payment_status = 'paid';
                        window.currentReservationData.payment_date = reservation.payment_date;
                        window.currentReservationData.confirmation_number = reservation.confirmation_number;
                        window.currentReservationData.payment_intent_id = reservation.payment_intent_id;
                    }
                    
                    // Refresh the reservation details to show payment information
                    showReservationDetails(reservationId);
                    
                    // Show a notification
                    showPaymentStatusNotification('Payment received! Your bill has been marked as paid.');
                    
                    // Refresh the calendar to show updated status
                    if (typeof calendar !== 'undefined') {
                        calendar.refetchEvents();
                    }
                    
                    // Stop monitoring since payment is complete
                    stopPaymentStatusMonitoring();
                }
                
                currentStatus = newStatus;
            }
        } catch (error) {
            console.error('Error checking payment status:', error);
        }
    }, 5000); // Check every 5 seconds
}

function stopPaymentStatusMonitoring() {
    if (paymentStatusInterval) {
        console.log(`🛑 Stopping payment status monitoring for reservation ${currentMonitoringReservationId}`);
        clearInterval(paymentStatusInterval);
        paymentStatusInterval = null;
        currentMonitoringReservationId = null;
    }
}

function showPaymentStatusNotification(message) {
    // Create a toast notification
    const toastHtml = `
        <div class="toast align-items-center text-white bg-success border-0" role="alert" aria-live="assertive" aria-atomic="true" style="position: fixed; top: 20px; right: 20px; z-index: 9999;">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-check-circle me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Add toast to body
    document.body.insertAdjacentHTML('beforeend', toastHtml);
    
    // Show the toast
    const toastElement = document.body.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function editCurrentReservation() {
    if (!currentReservationId) {
        alert('No reservation selected');
        return;
    }
    
    // Close the details modal first
    const detailsModal = bootstrap.Modal.getInstance(document.getElementById('reservationModal'));
    if (detailsModal) {
        detailsModal.hide();
    }
    
    // Open the edit reservation modal instead of redirecting
    editReservation(currentReservationId);
}

function renderPartyOrderForms() {
    const partySize = parseInt(document.getElementById('partySizeInput').value) || 1;
    const partyOrdersDiv = document.getElementById('partyOrders');
    partyOrdersDiv.innerHTML = '';
    for (let i = 0; i < partySize; i++) {
        partyOrdersDiv.innerHTML += `
            <div class="card mb-3 bg-dark text-light border-0 shadow-sm">
                <div class="card-header bg-secondary text-light">
                    <strong>Person ${i + 1} ${i === 0 ? '(Reservation Holder)' : ''}</strong>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">Name</label>
                        <input type="text" class="form-control party-member-name" placeholder="Optional">
                    </div>
                    <div class="menu-items">
                        ${renderMenuItems(i)}
                    </div>
                </div>
            </div>
        `;
    }
}

function renderMenuItems(personIndex) {
    let html = '';
    if (menuData.length > 0) {
        menuData.forEach(category => {
            html += `
                <div class="mb-3">
                    <h6 class="mb-2">${category.name}</h6>
                    <div class="list-group">
            `;
            category.items.forEach(item => {
                html += `
                    <div class="list-group-item bg-dark text-light d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${item.name}</strong>
                            <div class="text-muted small">${item.description}</div>
                            <div class="text-accent">$${item.price.toFixed(2)}</div>
                        </div>
                        <div style="width: 100px;">
                            <input type="number" class="form-control form-control-sm menu-qty" 
                                   value="0" min="0" data-id="${item.id}" data-person="${personIndex}">
                        </div>
                    </div>
                `;
            });
            html += `
                    </div>
                </div>
            `;
        });
    } else {
        html = '<div class="text-muted">Loading menu items...</div>';
    }
    return html;
}

function fetchMenuItems() {
    if (menuData.length === 0) {
        fetch('/api/menu_items')
            .then(resp => resp.json())
            .then(items => {
                // Group items by category
                const categories = {};
                items.forEach(item => {
                    if (!categories[item.category]) {
                        categories[item.category] = {
                            name: item.category,
                            items: []
                        };
                    }
                    categories[item.category].items.push(item);
                });
                menuData = Object.values(categories);
                renderPartyOrderForms();
            });
    }
}

function deleteReservation(reservationId) {
    if (confirm('Are you sure you want to delete this reservation?')) {
        fetch(`/api/reservations/${reservationId}`, {
            method: 'DELETE'
        }).then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Failed to delete reservation. Please try again.');
            }
        }).catch(error => {
            console.error('Error:', error);
            alert('An error occurred while deleting the reservation.');
        });
    }
}

function editReservation(reservationId) {
    currentReservationId = reservationId; // Set the global reservation ID
    window.currentReservationId = reservationId; // Also set on window object
    
    // Fetch reservation details
    fetch(`/api/reservations/${reservationId}`)
        .then(resp => resp.json())
        .then(reservation => {
            // Populate form fields
            document.getElementById('editName').value = reservation.name;
            document.getElementById('editPartySize').value = reservation.party_size;
            document.getElementById('editTime').value = reservation.time;
            document.getElementById('editPhone').value = reservation.phone_number;
            document.getElementById('editRequests').value = reservation.special_requests || '';
            document.getElementById('editDate').value = reservation.date;
            
            // Check if this is an old school reservation (no orders)
            const hasOrders = reservation.orders && reservation.orders.length > 0;
            const oldSchoolCheckbox = document.getElementById('editOldSchoolReservation');
            const editOrderSection = document.getElementById('editOrderSection');
            
            if (!hasOrders) {
                // This is an old school reservation
                oldSchoolCheckbox.checked = true;
                editOrderSection.style.display = 'none';
            } else {
                // This has orders, show the order section
                oldSchoolCheckbox.checked = false;
                editOrderSection.style.display = 'block';
            }

            // Ensure menu items are loaded, then render edit form
            if (menuData.length === 0) {
                fetch('/api/menu_items')
                    .then(resp => resp.json())
                    .then(items => {
                        // Group items by category
                        const categories = {};
                        items.forEach(item => {
                            if (!categories[item.category]) {
                                categories[item.category] = {
                                    name: item.category,
                                    items: []
                                };
                            }
                            categories[item.category].items.push(item);
                        });
                        menuData = Object.values(categories);
                        renderEditPartyOrderForms(reservation);
                    });
            } else {
                renderEditPartyOrderForms(reservation);
            }

            // Show modal
            new bootstrap.Modal(document.getElementById('editReservationModal')).show();
        });
}

// Handle form submission
document.getElementById('editReservationForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);

    // Check if this is an old school reservation
    const isOldSchool = document.getElementById('editOldSchoolReservation').checked;
    
    if (!isOldSchool) {
        // Collect party orders only if not old school
        const partyOrders = [];
        const partySize = parseInt(document.getElementById('editPartySize').value) || 1;
        const nameInputs = document.querySelectorAll('#editPartyOrders .party-member-name');

        for (let i = 0; i < partySize; i++) {
            const name = nameInputs[i].value || '';
            const items = [];
            document.querySelectorAll(`#editPartyOrders input.menu-qty[data-person="${i}"]`).forEach(function(input) {
                if (parseInt(input.value) > 0) {
                    items.push({
                        menu_item_id: input.dataset.id,
                        quantity: input.value
                    });
                }
            });
            partyOrders.push({ name, items });
        }
        formData.append('party_orders', JSON.stringify(partyOrders));
    } else {
        // For old school reservations, send empty party orders
        formData.append('party_orders', JSON.stringify([]));
    }

    // Convert FormData to JSON object
    const jsonData = {};
    for (let [key, value] of formData.entries()) {
        jsonData[key] = value;
    }
    
    // Submit the form
    fetch(`/api/reservations/${currentReservationId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(jsonData)
    }).then(resp => {
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
        }
        return resp.json();
    })
      .then(data => {
        if (data.success) {
            // Close modal and refresh calendar
            bootstrap.Modal.getInstance(document.getElementById('editReservationModal')).hide();
            calendar.refetchEvents();
            alert('Reservation updated successfully!');
        } else {
            alert('Error: ' + (data.error || 'Could not update reservation.'));
        }
    }).catch(error => {
        console.error('Error:', error);
        alert('An error occurred while updating the reservation.');
    });
});

// Reschedule reservation function
function rescheduleReservation() {
    if (!currentReservationId) {
        alert('No reservation selected');
        return;
    }
    
    // Close the details modal first
    const detailsModal = bootstrap.Modal.getInstance(document.getElementById('reservationModal'));
    if (detailsModal) {
        detailsModal.hide();
    }
    
    // Wait for the modal to close before opening the edit modal
    setTimeout(() => {
        editReservation(currentReservationId);
    }, 300); // Wait for modal close animation
}

// Cancel reservation function
function cancelReservation() {
    if (!currentReservationId) {
        alert('No reservation selected');
        return;
    }
    
    if (confirm('Are you sure you want to cancel this reservation? This action cannot be undone.')) {
        // Get the cancel button to update its state
        const cancelBtn = document.getElementById('cancelReservationBtn');
        const originalBtnContent = cancelBtn.innerHTML;
        
        // Show loading state
        cancelBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Cancelling...';
        cancelBtn.disabled = true;
        
        fetch(`/api/reservations/${currentReservationId}`, {
            method: 'DELETE'
        }).then(response => {
            if (response.ok) {
                // Update button to show cancelled state
                cancelBtn.innerHTML = '<i class="fas fa-ban me-2"></i>Cancelled';
                cancelBtn.className = 'btn btn-secondary btn-lg';
                cancelBtn.disabled = true;
                
                // Disable other action buttons since reservation is cancelled
                const editBtn = document.getElementById('editReservationBtn');
                const rescheduleBtn = document.getElementById('rescheduleBtn');
                const payBillBtn = document.getElementById('payBillBtn');
                
                if (editBtn) {
                    editBtn.disabled = true;
                    editBtn.className = 'btn btn-secondary btn-lg';
                    editBtn.innerHTML = '<i class="fas fa-ban me-2"></i>Cannot Edit (Cancelled)';
                }
                if (rescheduleBtn) {
                    rescheduleBtn.disabled = true;
                    rescheduleBtn.className = 'btn btn-secondary btn-lg';
                    rescheduleBtn.innerHTML = '<i class="fas fa-ban me-2"></i>Cannot Reschedule (Cancelled)';
                }
                if (payBillBtn) {
                    payBillBtn.style.display = 'none'; // Hide payment button for cancelled reservations
                }
                
                // Update the reservation status in the details
                updateReservationStatusInModal('cancelled');
                
                // Refresh the calendar
                calendar.refetchEvents();
                
                // Show success message
                showPaymentStatusNotification('Reservation cancelled successfully');
                
                // Close the modal after a brief delay to show the status change
                setTimeout(() => {
                    bootstrap.Modal.getInstance(document.getElementById('reservationModal')).hide();
                }, 2000); // 2 second delay
                
            } else {
                // Restore button on error
                cancelBtn.innerHTML = originalBtnContent;
                cancelBtn.disabled = false;
                alert('Failed to cancel reservation. Please try again.');
            }
        }).catch(error => {
            console.error('Error:', error);
            // Restore button on error
            cancelBtn.innerHTML = originalBtnContent;
            cancelBtn.disabled = false;
            alert('An error occurred while cancelling the reservation.');
        });
    }
}

// Render party order forms for edit modal
function renderEditPartyOrderForms(reservation) {
    const partySize = parseInt(reservation.party_size) || 1;
    const partyOrdersDiv = document.getElementById('editPartyOrders');
    partyOrdersDiv.innerHTML = '';
    
    for (let i = 0; i < partySize; i++) {
        const existingOrder = reservation.orders && reservation.orders[i] ? reservation.orders[i] : null;
        
        partyOrdersDiv.innerHTML += `
            <div class="card mb-3 bg-dark text-light border-0 shadow-sm">
                <div class="card-header bg-secondary text-light">
                    <strong>Person ${i + 1} ${i === 0 ? '(Reservation Holder)' : ''}</strong>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">Name</label>
                        <input type="text" class="form-control party-member-name" placeholder="Optional" value="${existingOrder ? existingOrder.person_name || '' : ''}">
                    </div>
                    <div class="menu-items">
                        ${renderEditMenuItems(i, existingOrder)}
                    </div>
                </div>
            </div>
        `;
    }
}

// Render menu items for edit modal with existing quantities
function renderEditMenuItems(personIndex, existingOrder) {
    let html = '';
    if (menuData.length > 0) {
        menuData.forEach(category => {
            html += `
                <div class="mb-3">
                    <h6 class="mb-2">${category.name}</h6>
                    <div class="list-group">
            `;
            category.items.forEach(item => {
                // Find existing quantity for this item
                let existingQuantity = 0;
                if (existingOrder && existingOrder.items) {
                    const existingItem = existingOrder.items.find(orderItem => {
                        return orderItem.menu_item && orderItem.menu_item.id === item.id;
                    });
                    if (existingItem) {
                        existingQuantity = existingItem.quantity;
                    }
                }
                
                html += `
                    <div class="list-group-item bg-dark text-light d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${item.name}</strong>
                            <div class="text-muted small">${item.description}</div>
                            <div class="text-accent">$${item.price.toFixed(2)}</div>
                        </div>
                        <div style="width: 100px;">
                            <input type="number" class="form-control form-control-sm menu-qty" 
                                   value="${existingQuantity}" min="0" data-id="${item.id}" data-person="${personIndex}">
                        </div>
                    </div>
                `;
            });
            html += `
                    </div>
                </div>
            `;
        });
    } else {
        html = '<div class="text-muted">Loading menu items...</div>';
    }
    return html;
}

// Add event listener to stop payment monitoring when reservation modal is closed
document.addEventListener('DOMContentLoaded', function() {
    const reservationModal = document.getElementById('reservationModal');
    if (reservationModal) {
        reservationModal.addEventListener('hidden.bs.modal', function() {
            stopPaymentStatusMonitoring();
        });
    }
}); 

// Auto-refresh calendar every 60 seconds to catch SWAIG reservations (reduced from 30s)
let autoRefreshInterval = null;
let lastReservationCount = 0;
let initialCountSet = false; // Track if we've set the initial count

function startAutoRefresh() {
    // Only start auto-refresh if calendar exists and we're on the calendar page
    if (typeof calendar !== 'undefined' && document.getElementById('calendar')) {
        console.log('📅 Starting auto-refresh for SWAIG reservations (60s interval)');
        
        autoRefreshInterval = setInterval(() => {
            console.log('🔄 Auto-refreshing calendar for new phone reservations...');
            calendar.refetchEvents();
            
            // Check for new reservations and show notification
            checkForNewReservations();
        }, 60000); // 60 seconds - more reasonable refresh rate
    }
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        console.log('⏹️ Stopping calendar auto-refresh');
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

async function checkForNewReservations() {
    try {
        // Get current date range from calendar
        const view = calendar.view;
        const start = view.activeStart.toISOString();
        const end = view.activeEnd.toISOString();
        
        // Fetch current reservations
        const response = await fetch(`/api/reservations/calendar?start=${start}&end=${end}`);
        if (response.ok) {
            const reservations = await response.json();
            
            // If this is the first time, just set the initial count without showing notifications
            if (!initialCountSet) {
                lastReservationCount = reservations.length;
                initialCountSet = true;
                console.log(`📊 Initial reservation count set: ${lastReservationCount}`);
                return;
            }
            
            // Check if we have new reservations (only after initial count is set)
            if (reservations.length > lastReservationCount) {
                const newCount = reservations.length - lastReservationCount;
                showNewReservationNotification(newCount);
                console.log(`📞 ${newCount} new reservations detected!`);
            }
            
            // Update the count
            lastReservationCount = reservations.length;
            console.log(`📊 Current reservation count: ${lastReservationCount}`);
        }
    } catch (error) {
        console.error('Error checking for new reservations:', error);
    }
}

function showNewReservationNotification(count) {
    const message = count === 1 
        ? '📞 New phone reservation received!' 
        : `📞 ${count} new phone reservations received!`;
    
    // Play a subtle notification sound (optional - browser dependent)
    try {
        // Create a subtle beep sound
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime); // 800 Hz tone
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime); // Low volume
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (e) {
        // Ignore audio errors - not critical
        console.log('Audio notification not available');
    }
    
    // Create toast notification
    const toastHtml = `
        <div class="toast align-items-center text-white bg-success border-0" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-phone me-2"></i><strong>${message}</strong>
                    <small class="d-block text-light opacity-75 mt-1">Calendar updated automatically</small>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.body.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, { delay: 8000 }); // Longer delay - 8 seconds
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Manual refresh function for immediate updates
function refreshCalendarNow() {
    if (typeof calendar !== 'undefined') {
        console.log('🔄 Manual calendar refresh triggered');
        calendar.refetchEvents();
        checkForNewReservations();
    }
}

// Make it available globally for debugging
window.refreshCalendarNow = refreshCalendarNow;

// Initialize auto-refresh when calendar is ready
document.addEventListener('DOMContentLoaded', function() {
    // Wait for calendar to initialize, then start auto-refresh
    setTimeout(() => {
        if (typeof calendar !== 'undefined') {
            // 🚀 PRIORITY: Start real-time updates first (instant)
            initializeRealTimeUpdates();
            
            // Keep auto-refresh as fallback (60-second polling)
            startAutoRefresh();
            
            // Initialize reservation count
            checkForNewReservations();
            
            // Do one initial refresh after 5 seconds (reduced from multiple refreshes)
            setTimeout(() => {
                console.log('🔄 Initial refresh for recent reservations');
                refreshCalendarNow();
            }, 5000);
        }
    }, 2000);
    
    // Stop auto-refresh and real-time updates when leaving the page
    window.addEventListener('beforeunload', function() {
        stopAutoRefresh();
        stopRealTimeUpdates();
    });
    
    // Pause auto-refresh when page is not visible (tab switching)
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            stopAutoRefresh();
            stopRealTimeUpdates();
        } else {
            // Restart when page becomes visible again
            setTimeout(() => {
                if (typeof calendar !== 'undefined') {
                    initializeRealTimeUpdates();
                    startAutoRefresh();
                }
            }, 1000);
        }
    });
});

// 🚀 REAL-TIME CALENDAR UPDATES via Server-Sent Events (SSE)
let calendarEventSource = null;

function initializeRealTimeUpdates() {
    // Only initialize if calendar exists and SSE is supported
    if (typeof calendar === 'undefined' || !window.EventSource) {
        console.log('⚠️ Calendar or SSE not available, skipping real-time updates');
        return;
    }
    
    console.log('🚀 Initializing real-time calendar updates via SSE');
    
    // Create SSE connection
    calendarEventSource = new EventSource('/api/calendar/events-stream');
    
    calendarEventSource.onopen = function(event) {
        console.log('✅ SSE connection established for calendar updates');
    };
    
    calendarEventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'ping') {
                // Keepalive ping - ignore
                return;
            }
            
            if (data.type === 'calendar_refresh') {
                console.log('📅 Real-time calendar update received:', data);
                
                // Trigger instant calendar refresh
                calendar.refetchEvents();
                
                // Show notification for phone reservations
                if (data.source === 'phone_swaig') {
                    showRealTimeReservationNotification(data);
                }
                
                // Update reservation count for auto-refresh system
                if (typeof checkForNewReservations === 'function') {
                    setTimeout(() => {
                        checkForNewReservations();
                    }, 1000); // Small delay to ensure data is available
                }
            }
            
        } catch (error) {
            console.error('❌ Error processing SSE calendar event:', error);
        }
    };
    
    calendarEventSource.onerror = function(event) {
        console.error('❌ SSE connection error:', event);
        
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
            if (calendarEventSource.readyState === EventSource.CLOSED) {
                console.log('🔄 Attempting to reconnect SSE...');
                initializeRealTimeUpdates();
            }
        }, 5000);
    };
}

function showRealTimeReservationNotification(data) {
    let message;
    switch (data.event_type) {
        case 'reservation_created':
            message = `📞 New phone reservation: ${data.customer_name}`;
            break;
        case 'reservation_updated':
            message = `📞 Reservation updated: ${data.customer_name}`;
            break;
        case 'reservation_cancelled':
            message = `📞 Reservation cancelled: ${data.customer_name}`;
            break;
        default:
            message = `📞 Reservation ${data.event_type}: ${data.customer_name}`;
    }
    
    // Create enhanced toast notification
    const toastHtml = `
        <div class="toast align-items-center text-white bg-success border-0" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-phone me-2"></i><strong>${message}</strong>
                    <small class="d-block text-light opacity-75 mt-1">
                        ${data.date} at ${data.time} • Party of ${data.party_size} • Calendar updated instantly
                    </small>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.body.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, { delay: 10000 }); // 10 second delay
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
    
    // Play notification sound
    playNotificationSound();
}

function playNotificationSound() {
    try {
        // Create a more pleasant notification sound
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator1 = audioContext.createOscillator();
        const oscillator2 = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator1.connect(gainNode);
        oscillator2.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        // Create a pleasant two-tone chime
        oscillator1.frequency.setValueAtTime(800, audioContext.currentTime); // High tone
        oscillator2.frequency.setValueAtTime(600, audioContext.currentTime); // Low tone
        
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime); // Low volume
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.8);
        
        oscillator1.start(audioContext.currentTime);
        oscillator1.stop(audioContext.currentTime + 0.3);
        
        oscillator2.start(audioContext.currentTime + 0.1);
        oscillator2.stop(audioContext.currentTime + 0.5);
    } catch (e) {
        // Ignore audio errors - not critical
        console.log('Audio notification not available');
    }
}

function stopRealTimeUpdates() {
    if (calendarEventSource) {
        console.log('⏹️ Stopping real-time calendar updates');
        calendarEventSource.close();
        calendarEventSource = null;
    }
}