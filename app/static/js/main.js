// Main JavaScript functionality for CodeLearn Pro
class CodeLearnPro {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeAnimations();
        this.setupTheme();
        this.setupTooltips();
        this.setupProgressBars();
        this.setupCounters();
        this.setupNotifications();
    }

    setupEventListeners() {
        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const href = anchor.getAttribute('href');
                if (href && href !== '#') {
                    const target = document.querySelector(href);
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                }
            });
        });

        // Form validation
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', this.validateForm.bind(this));
        });

        // Auto-resize textareas
        document.querySelectorAll('textarea').forEach(textarea => {
            textarea.addEventListener('input', this.autoResizeTextarea.bind(this));
        });

        // Search functionality
        const searchInputs = document.querySelectorAll('input[type="search"], input[placeholder*="search"]');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
        });

        // Modal enhancements
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('shown.bs.modal', this.focusFirstInput);
        });

        // Click outside to close dropdowns
        document.addEventListener('click', this.closeDropdowns);

        // Keyboard navigation
        document.addEventListener('keydown', this.handleKeyboardNavigation);
    }

    initializeAnimations() {
        // Intersection Observer for scroll animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-slide-up');
                    // Start counters when they come into view
                    if (entry.target.classList.contains('counter')) {
                        this.animateCounter(entry.target);
                    }
                }
            });
        }, observerOptions);

        // Observe all cards and counter elements
        document.querySelectorAll('.glass-card, .counter').forEach(card => {
            observer.observe(card);
        });

        // Parallax effect for hero section
        this.setupParallax();
    }

    setupTheme() {
        // Theme is handled by enhanced.js, no need for duplicate setup
        // Just load saved theme if enhanced.js hasn't loaded yet
        if (!window.toggleTheme) {
            const savedTheme = localStorage.getItem('theme') || 'dark';
            document.documentElement.setAttribute('data-theme', savedTheme);
        }
    }

    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Custom tooltips for platform icons
        document.querySelectorAll('.platform-icon').forEach(icon => {
            icon.addEventListener('mouseenter', this.showCustomTooltip);
            icon.addEventListener('mouseleave', this.hideCustomTooltip);
        });
    }

    setupProgressBars() {
        // Animate progress bars when they come into view
        const progressBars = document.querySelectorAll('.progress-bar');
        const progressObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const progressBar = entry.target;
                    const width = progressBar.style.width;
                    progressBar.style.width = '0%';
                    setTimeout(() => {
                        progressBar.style.width = width;
                    }, 100);
                }
            });
        });

        progressBars.forEach(bar => {
            progressObserver.observe(bar);
        });
    }

    setupCounters() {
        // Counter animation setup
        this.counters = document.querySelectorAll('.counter');
        this.counterAnimated = new Set();
    }

    setupNotifications() {
        // Setup notification system
        this.notificationContainer = this.createNotificationContainer();
        
        // Auto-hide flash messages
        document.querySelectorAll('.alert').forEach(alert => {
            setTimeout(() => {
                this.fadeOut(alert);
            }, 5000);
        });
    }

    // Animation Methods
    animateCounter(element) {
        if (this.counterAnimated.has(element)) return;
        
        const target = parseInt(element.getAttribute('data-target') || element.textContent);
        const duration = 2000;
        const start = performance.now();
        const startValue = 0;

        const animate = (currentTime) => {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = Math.floor(startValue + (target - startValue) * easeOutQuart);
            
            element.textContent = current;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.textContent = target;
                this.counterAnimated.add(element);
            }
        };

        requestAnimationFrame(animate);
    }

    setupParallax() {
        const heroSection = document.querySelector('.hero-section');
        if (!heroSection) return;

        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const parallaxElements = document.querySelectorAll('.floating-card');
            
            parallaxElements.forEach((element, index) => {
                const speed = 0.5 + (index * 0.1);
                const yPos = -(scrolled * speed);
                element.style.transform = `translateY(${yPos}px)`;
            });
        });
    }

    // Form Validation
    validateForm(e) {
        const form = e.target;
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('is-invalid');
                this.showFieldError(field, 'This field is required');
            } else {
                field.classList.remove('is-invalid');
                this.hideFieldError(field);
            }
        });

        // Email validation
        const emailFields = form.querySelectorAll('input[type="email"]');
        emailFields.forEach(field => {
            if (field.value && !this.isValidEmail(field.value)) {
                isValid = false;
                field.classList.add('is-invalid');
                this.showFieldError(field, 'Please enter a valid email address');
            }
        });

        // Password confirmation
        const passwordField = form.querySelector('input[name="password"]');
        const confirmField = form.querySelector('input[name="confirm_password"]');
        if (passwordField && confirmField && passwordField.value !== confirmField.value) {
            isValid = false;
            confirmField.classList.add('is-invalid');
            this.showFieldError(confirmField, 'Passwords do not match');
        }

        if (!isValid) {
            e.preventDefault();
        }
    }

    showFieldError(field, message) {
        let errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            field.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    }

    hideFieldError(field) {
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Utility Methods
    autoResizeTextarea(e) {
        const textarea = e.target;
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    handleSearch(e) {
        const query = e.target.value.toLowerCase();
        const searchableElements = document.querySelectorAll('[data-searchable]');
        
        searchableElements.forEach(element => {
            const text = element.textContent.toLowerCase();
            const parent = element.closest('.card, .list-group-item, tr');
            
            if (text.includes(query) || query === '') {
                parent.style.display = '';
            } else {
                parent.style.display = 'none';
            }
        });
    }

    focusFirstInput(e) {
        const modal = e.target;
        const firstInput = modal.querySelector('input, textarea, select');
        if (firstInput) {
            firstInput.focus();
        }
    }

    closeDropdowns(e) {
        if (!e.target.matches('.dropdown-toggle')) {
            document.querySelectorAll('.dropdown-menu.show').forEach(dropdown => {
                dropdown.classList.remove('show');
            });
        }
    }

    handleKeyboardNavigation(e) {
        // ESC key to close modals
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                modal.hide();
            }
        }

        // Arrow key navigation for cards
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            const focusedElement = document.activeElement;
            if (focusedElement.classList.contains('card') || focusedElement.classList.contains('btn')) {
                e.preventDefault();
                this.navigateCards(e.key === 'ArrowRight');
            }
        }
    }

    navigateCards(forward) {
        const cards = Array.from(document.querySelectorAll('.card, .btn'));
        const currentIndex = cards.indexOf(document.activeElement);
        
        if (currentIndex !== -1) {
            const nextIndex = forward 
                ? (currentIndex + 1) % cards.length 
                : (currentIndex - 1 + cards.length) % cards.length;
            cards[nextIndex].focus();
        }
    }

    // Theme Methods - Removed duplicate, using enhanced.js implementation

    // Notification Methods
    createNotificationContainer() {
        let container = document.querySelector('.notification-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notification-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    }

    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show notification-item`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        this.notificationContainer.appendChild(notification);

        // Auto-hide
        setTimeout(() => {
            this.fadeOut(notification);
        }, duration);

        return notification;
    }

    fadeOut(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }, 300);
    }

    // Custom Tooltip Methods
    showCustomTooltip(e) {
        const element = e.target;
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = element.getAttribute('data-tooltip') || element.title;
        
        document.body.appendChild(tooltip);
        
        // Position tooltip
        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
        
        // Store reference for cleanup
        element._tooltip = tooltip;
        
        // Animate in
        setTimeout(() => {
            tooltip.classList.add('show');
        }, 10);
    }

    hideCustomTooltip(e) {
        const element = e.target;
        if (element._tooltip) {
            element._tooltip.remove();
            delete element._tooltip;
        }
    }

    // API Helper Methods
    async makeRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        const mergedOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, mergedOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Request failed:', error);
            this.showNotification('An error occurred. Please try again.', 'danger');
            throw error;
        }
    }

    // Local Storage Helpers
    saveToStorage(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
        } catch (error) {
            console.error('Failed to save to storage:', error);
        }
    }

    loadFromStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to load from storage:', error);
            return defaultValue;
        }
    }

    // Progress Tracking
    trackProgress(action, data = {}) {
        const progressData = this.loadFromStorage('progress', {});
        const timestamp = new Date().toISOString();
        
        if (!progressData[action]) {
            progressData[action] = [];
        }
        
        progressData[action].push({
            timestamp,
            ...data
        });
        
        this.saveToStorage('progress', progressData);
    }

    // Study Session Helpers
    startStudySession(type, topics = '') {
        const sessionData = {
            type,
            topics,
            startTime: Date.now(),
            problems: 0,
            notes: ''
        };
        
        this.saveToStorage('activeSession', sessionData);
        this.showNotification(`Started ${type} session`, 'success');
        
        // Update UI
        this.updateSessionUI(true, sessionData);
    }

    endStudySession(duration, problems, notes) {
        const sessionData = this.loadFromStorage('activeSession');
        if (!sessionData) return;
        
        const completedSession = {
            ...sessionData,
            endTime: Date.now(),
            duration,
            problems,
            notes
        };
        
        // Save to history
        const sessions = this.loadFromStorage('studySessions', []);
        sessions.push(completedSession);
        this.saveToStorage('studySessions', sessions);
        
        // Clear active session
        localStorage.removeItem('activeSession');
        
        this.showNotification('Study session completed!', 'success');
        this.trackProgress('study_session', completedSession);
        
        // Update UI
        this.updateSessionUI(false);
    }

    updateSessionUI(active, sessionData = null) {
        const sessionButton = document.querySelector('[data-session-toggle]');
        if (!sessionButton) return;
        
        if (active) {
            sessionButton.textContent = 'End Session';
            sessionButton.className = 'btn btn-danger';
            sessionButton.setAttribute('data-bs-target', '#endSessionModal');
        } else {
            sessionButton.textContent = 'Start Session';
            sessionButton.className = 'btn btn-primary';
            sessionButton.setAttribute('data-bs-target', '#startSessionModal');
        }
    }

    // Platform Integration Helpers
    syncPlatformData(platform, username) {
        this.showNotification(`Syncing ${platform} data...`, 'info');
        
        // Show loading state
        const syncButton = document.querySelector(`[data-platform="${platform}"] button`);
        if (syncButton) {
            syncButton.disabled = true;
            syncButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Syncing...';
        }
        
        // This would typically make an API call
        setTimeout(() => {
            if (syncButton) {
                syncButton.disabled = false;
                syncButton.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Sync';
            }
            this.showNotification(`${platform} data synced successfully!`, 'success');
        }, 2000);
    }

    // Flashcard Helpers
    reviewFlashcard(cardId, quality) {
        this.trackProgress('flashcard_review', { cardId, quality });
        
        // Calculate next review date based on spaced repetition algorithm
        const nextReview = this.calculateNextReview(quality);
        
        this.showNotification(
            quality >= 4 ? 'Great job! 🎉' : 'Keep practicing! 💪', 
            quality >= 4 ? 'success' : 'warning'
        );
        
        return nextReview;
    }

    calculateNextReview(quality) {
        // Simple spaced repetition algorithm
        const intervals = {
            1: 1,      // 1 day
            2: 1,      // 1 day
            3: 6,      // 6 days
            4: 14,     // 2 weeks
            5: 30      // 1 month
        };
        
        const days = intervals[quality] || 1;
        const nextReview = new Date();
        nextReview.setDate(nextReview.getDate() + days);
        
        return nextReview;
    }

    // Initialization method to be called when DOM is ready
    static init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                new CodeLearnPro();
            });
        } else {
            new CodeLearnPro();
        }
    }
}

// Global utility functions
window.codeLearnPro = {
    showNotification: (message, type, duration) => {
        const app = window.app || new CodeLearnPro();
        return app.showNotification(message, type, duration);
    },
    
    trackProgress: (action, data) => {
        const app = window.app || new CodeLearnPro();
        return app.trackProgress(action, data);
    },
    
    syncPlatform: (platform, username) => {
        const app = window.app || new CodeLearnPro();
        return app.syncPlatformData(platform, username);
    }
};

// Global functions for form validation (accessible from templates)
window.showFieldError = function(field, message) {
    let errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        field.parentNode.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
    field.classList.add('is-invalid');
};

window.hideFieldError = function(field) {
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
    field.classList.remove('is-invalid');
};

// CSS for custom tooltips and notifications
const styles = `
    .custom-tooltip {
        position: absolute;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        pointer-events: none;
        opacity: 0;
        transform: translateY(5px);
        transition: all 0.2s ease;
        z-index: 10000;
    }
    
    .custom-tooltip.show {
        opacity: 1;
        transform: translateY(0);
    }
    
    .notification-item {
        transform: translateX(100%);
        transition: all 0.3s ease;
        margin-bottom: 10px;
        max-width: 350px;
    }
    
    .notification-item.show {
        transform: translateX(0);
    }
    
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(15, 15, 35, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }
    
    .pulse-animation {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: .5;
        }
    }
`;

// Inject styles
const styleSheet = document.createElement('style');
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);

// Initialize the application
CodeLearnPro.init();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CodeLearnPro;
}
