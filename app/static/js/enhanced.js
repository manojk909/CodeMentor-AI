// Enhanced JavaScript functionality for CodeLearn Pro
// Theme functionality
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
    updateNavbarTheme(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
    updateNavbarTheme(newTheme);
    
    // Add smooth transition
    document.body.style.transition = 'all 0.3s ease';
    setTimeout(() => {
        document.body.style.transition = '';
    }, 300);
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

function updateNavbarTheme(theme) {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        if (theme === 'light') {
            navbar.classList.remove('navbar-dark', 'bg-dark');
            navbar.classList.add('navbar-light');
        } else {
            navbar.classList.remove('navbar-light');
            navbar.classList.add('navbar-dark');
        }
        
        // Force update navbar link colors by re-applying styles
        const navLinks = navbar.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            // Remove and re-add classes to force style recalculation
            link.style.color = '';
            setTimeout(() => {
                if (theme === 'light') {
                    link.style.color = 'var(--text-secondary)';
                } else {
                    link.style.color = 'var(--text-secondary)';
                }
            }, 10);
        });
    }
}

// Notifications functionality
let notifications = [];

// Load notifications from server
function loadNotifications() {
    fetch('/api/notifications')
        .then(response => {
            if (response.status === 401) {
                // User not authenticated, stop trying to load notifications
                console.log('User not authenticated, skipping notification loading');
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                notifications = data.notifications;
                updateNotificationBadge();
                updateNotificationsList();
            } else if (data && !data.success) {
                console.log('Failed to load notifications:', data.error);
            }
        })
        .catch(error => {
            // Only log error if it's not a network/authentication issue
            if (error.name !== 'TypeError') {
                console.error('Error loading notifications:', error);
            }
        });
}

function markNotificationAsRead(id) {
    fetch(`/api/notifications/${id}/read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (response.status === 401) {
            console.log('User not authenticated');
            return;
        }
        return response.json();
    })
    .then(data => {
        if (data && data.success) {
            // Update local notifications array
            const notification = notifications.find(n => n.id === id);
            if (notification) {
                notification.is_read = true;
                updateNotificationBadge();
                updateNotificationsList();
            }
        }
    })
    .catch(error => {
        if (error.name !== 'TypeError') {
            console.error('Error marking notification as read:', error);
        }
    });
}

function clearNotifications() {
    fetch('/api/notifications/mark-all-read', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (response.status === 401) {
            console.log('User not authenticated');
            return;
        }
        return response.json();
    })
    .then(data => {
        if (data && data.success) {
            // Mark all notifications as read locally
            notifications.forEach(n => n.is_read = true);
            updateNotificationBadge();
            updateNotificationsList();
        }
    })
    .catch(error => {
        if (error.name !== 'TypeError') {
            console.error('Error clearing notifications:', error);
        }
    });
}

function updateNotificationBadge() {
    const badge = document.getElementById('notificationBadge');
    const unreadCount = notifications.filter(n => !n.is_read).length;
    
    if (badge) {
        if (unreadCount > 0) {
            badge.textContent = unreadCount;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }
    }
}

function updateNotificationsList() {
    const container = document.getElementById('notificationsList');
    const noNotifications = document.getElementById('noNotifications');
    
    if (!container) return;
    
    container.innerHTML = '';
    
    if (notifications.length === 0) {
        if (noNotifications) noNotifications.style.display = 'block';
        return;
    }
    
    if (noNotifications) noNotifications.style.display = 'none';
    
    notifications.slice(0, 5).forEach(notification => {
        const item = document.createElement('li');
        item.className = `dropdown-item${notification.is_read ? '' : ' bg-light'}`;
        item.style.cursor = 'pointer';
        item.style.borderLeft = notification.is_read ? 'none' : '3px solid #0d6efd';
        item.style.padding = '8px 16px';
        item.style.margin = '2px 0';
        item.style.borderRadius = '4px';
        item.onclick = () => markNotificationAsRead(notification.id);
        
        const typeIcon = {
            'info': 'fa-info-circle text-info',
            'success': 'fa-check-circle text-success',
            'warning': 'fa-exclamation-triangle text-warning',
            'error': 'fa-times-circle text-danger'
        }[notification.type] || 'fa-info-circle text-info';
        
        // Format the message with proper line breaks
        const formattedMessage = notification.message.replace(/\n/g, '<br>');
        
        item.innerHTML = `
            <div class="d-flex align-items-start p-2" style="max-width: 100%;">
                <i class="fas ${typeIcon} me-2 mt-1 flex-shrink-0"></i>
                <div class="flex-grow-1" style="min-width: 0;">
                    <div class="fw-bold mb-1" style="font-size: 0.9rem; color: ${notification.is_read ? '#6c757d' : '#212529'};">${notification.title}</div>
                    <div class="text-muted mb-2" style="font-size: 0.85rem; line-height: 1.4; white-space: pre-wrap; word-wrap: break-word;">${formattedMessage}</div>
                    <small class="text-muted" style="font-size: 0.75rem;">${new Date(notification.created_at).toLocaleString()}</small>
                </div>
            </div>
        `;
        
        container.appendChild(item);
    });
}

// Initialize notifications when page loads
function initNotifications() {
    // Only initialize notifications if notification dropdown exists (user is authenticated)
    const notificationDropdown = document.getElementById('notificationsDropdown');
    if (notificationDropdown) {
        loadNotifications();
        // Refresh notifications every 30 seconds
        setInterval(loadNotifications, 30000);
    }
}

// Daily coding hours functionality
function submitDailyCodingHours() {
    const hoursInput = document.getElementById('dailyCodingHours');
    const hours = parseFloat(hoursInput.value);
    
    if (isNaN(hours) || hours < 0 || hours > 24) {
        // Use browser notification instead of the removed addNotification
        alert('Please enter valid hours (0-24)');
        return;
    }
    
    fetch('/submit_daily_hours', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ hours: hours })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Daily coding hours recorded!');
            hoursInput.value = '';
            // Reload notifications to show the new one from server
            loadNotifications();
        } else {
            alert(data.error || 'Failed to record hours');
        }
    })
    .catch(error => {
        alert('Network error occurred');
    });
}

// Chart resizing functionality
function createCompactChart(canvasId, data, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    
    const ctx = canvas.getContext('2d');
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'bottom',
                labels: {
                    boxWidth: 12,
                    fontSize: 10
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: {
                    display: false
                },
                ticks: {
                    font: {
                        size: 10
                    }
                }
            },
            x: {
                grid: {
                    display: false
                },
                ticks: {
                    font: {
                        size: 10
                    }
                }
            }
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    return new Chart(ctx, {
        type: data.type || 'bar',
        data: data,
        options: mergedOptions
    });
}

// Initialize everything on page load
document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    initNotifications();
    
    // Set up daily hours input if present
    const dailyHoursBtn = document.getElementById('submitDailyHours');
    if (dailyHoursBtn) {
        dailyHoursBtn.addEventListener('click', submitDailyCodingHours);
    }
    
    // Enhanced mobile responsiveness
    handleMobileView();
    window.addEventListener('resize', handleMobileView);
});

function handleMobileView() {
    const isMobile = window.innerWidth < 768;
    const charts = document.querySelectorAll('canvas');
    
    charts.forEach(chart => {
        const container = chart.closest('.chart-container');
        if (container) {
            if (isMobile) {
                container.style.height = '200px';
            } else {
                container.style.height = '300px';
            }
        }
    });
}

// Add notification function for compatibility
function addNotification(title, message, type = 'info') {
    console.log(`Notification: ${title} - ${message}`);
    // In a real app, this would display a toast notification
    // For now, we'll just log it as the notifications system handles it via API
}

// Clear notifications function (alternative implementation)
function clearAllNotifications() {
    // Mark all notifications as read locally
    notifications.forEach(notification => {
        if (!notification.is_read) {
            markNotificationAsRead(notification.id);
        }
    });
}

// Export functions for global use
window.toggleTheme = toggleTheme;
window.addNotification = addNotification;
window.clearNotifications = clearNotifications;
window.markNotificationAsRead = markNotificationAsRead;
window.submitDailyCodingHours = submitDailyCodingHours;
window.createCompactChart = createCompactChart;