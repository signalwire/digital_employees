document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling for menu navigation if needed
    const menuCards = document.querySelectorAll('.menu-item-card');
    
    // Add hover effects and interactions for menu items
    menuCards.forEach(card => {
        const addButton = card.querySelector('.btn-accent');
        
        if (addButton && !addButton.hasAttribute('data-listener-added')) {
            addButton.setAttribute('data-listener-added', 'true');
            addButton.addEventListener('click', function() {
                // Get item details from the card
                const itemCard = this.closest('.menu-item-card');
                const itemName = itemCard.querySelector('.card-title').textContent;
                const itemDescription = itemCard.querySelector('.card-text').textContent;
                const itemPriceText = itemCard.querySelector('.menu-item-price').textContent;
                const itemPrice = parseFloat(itemPriceText.replace('$', ''));
                
                // Generate a unique ID based on the item name
                const itemId = itemName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                
                // Add to cart
                if (typeof cart !== 'undefined') {
                    cart.addItem(itemId, itemName, itemPrice, itemDescription);
                }
                
                // Visual feedback
                this.innerHTML = '<i class="fas fa-check me-1"></i>Added!';
                this.classList.add('btn-success');
                this.classList.remove('btn-accent');
                
                // Reset after 2 seconds
                setTimeout(() => {
                    this.innerHTML = 'Add to Order';
                    this.classList.remove('btn-success');
                    this.classList.add('btn-accent');
                }, 2000);
            });
        }
    });
    
    // Add scroll-to-section functionality if needed
    const sectionHeaders = document.querySelectorAll('.card-header h3');
    sectionHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            this.closest('.card').scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
            });
        });
    });
}); 