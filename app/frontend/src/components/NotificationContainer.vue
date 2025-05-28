<template>
  <Teleport to="body">
    <div 
      v-if="notificationStore.hasNotifications"
      class="notification-container"
      role="region"
      aria-label="Meldingen"
    >
      <TransitionGroup 
        name="notification" 
        tag="div" 
        class="notification-list"
      >
        <div
          v-for="notification in notificationStore.notifications"
          :key="notification.id"
          class="notification-wrapper"
        >
          <div
            :class="[
              'notification',
              `notification-${notification.type}`,
              { 'notification-persistent': notification.persistent }
            ]"
            role="alert"
            :aria-live="notification.type === 'error' ? 'assertive' : 'polite'"
          >
            <!-- Icon -->
            <div class="notification-icon">
              <svg 
                v-if="notification.type === 'success'" 
                width="20" 
                height="20" 
                viewBox="0 0 20 20" 
                fill="currentColor"
              >
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              
              <svg 
                v-else-if="notification.type === 'error'" 
                width="20" 
                height="20" 
                viewBox="0 0 20 20" 
                fill="currentColor"
              >
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
              
              <svg 
                v-else-if="notification.type === 'warning'" 
                width="20" 
                height="20" 
                viewBox="0 0 20 20" 
                fill="currentColor"
              >
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
              
              <svg 
                v-else
                width="20" 
                height="20" 
                viewBox="0 0 20 20" 
                fill="currentColor"
              >
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
              </svg>
            </div>

            <!-- Content -->
            <div class="notification-content">
              <div class="notification-title">{{ notification.title }}</div>
              <div class="notification-message">{{ notification.message }}</div>
              
              <!-- Actions -->
              <div 
                v-if="notification.actions && notification.actions.length > 0"
                class="notification-actions"
              >
                <button
                  v-for="action in notification.actions"
                  :key="action.label"
                  :class="[
                    'notification-action',
                    `notification-action-${action.style || 'secondary'}`
                  ]"
                  @click="action.action"
                >
                  {{ action.label }}
                </button>
              </div>
            </div>

            <!-- Close button -->
            <button
              class="notification-close"
              @click="notificationStore.removeNotification(notification.id)"
              aria-label="Melding sluiten"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z"/>
              </svg>
            </button>

            <!-- Progress bar for auto-dismiss -->
            <div
              v-if="notification.duration && notification.duration > 0"
              class="notification-progress"
              :style="{ '--duration': `${notification.duration}ms` }"
            ></div>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useNotificationStore } from '@/stores/notification'

const notificationStore = useNotificationStore()
</script>

<style scoped>
.notification-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 1000;
  pointer-events: none;
  max-width: 420px;
  width: 100%;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.notification-wrapper {
  pointer-events: auto;
}

.notification {
  background: white;
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--gray-200);
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  position: relative;
  overflow: hidden;
  transition: all var(--transition-duration);
}

.notification:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

/* Type-specific styling */
.notification-success {
  border-left: 4px solid var(--success-color);
}

.notification-success .notification-icon {
  color: var(--success-color);
  background: var(--success-light);
}

.notification-error {
  border-left: 4px solid var(--error-color);
}

.notification-error .notification-icon {
  color: var(--error-color);
  background: var(--error-light);
}

.notification-warning {
  border-left: 4px solid var(--warning-color);
}

.notification-warning .notification-icon {
  color: var(--warning-color);
  background: var(--warning-light);
}

.notification-info {
  border-left: 4px solid var(--info-color);
}

.notification-info .notification-icon {
  color: var(--info-color);
  background: var(--info-light);
}

/* Icon */
.notification-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Content */
.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  line-height: 1.25;
}

.notification-message {
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: 1.4;
  word-wrap: break-word;
}

/* Actions */
.notification-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  flex-wrap: wrap;
}

.notification-action {
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all var(--transition-duration);
}

.notification-action-primary {
  background: var(--primary-color);
  color: white;
}

.notification-action-primary:hover {
  background: var(--primary-dark);
}

.notification-action-secondary {
  background: var(--gray-100);
  color: var(--text-primary);
  border: 1px solid var(--gray-200);
}

.notification-action-secondary:hover {
  background: var(--gray-200);
}

.notification-action-danger {
  background: var(--error-color);
  color: white;
}

.notification-action-danger:hover {
  background: var(--error-dark);
}

/* Close button */
.notification-close {
  width: 1.5rem;
  height: 1.5rem;
  border: none;
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-duration);
  flex-shrink: 0;
}

.notification-close:hover {
  background: var(--gray-100);
  color: var(--text-primary);
}

/* Progress bar for auto-dismiss */
.notification-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gray-200);
}

.notification-progress::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: currentColor;
  opacity: 0.5;
  width: 100%;
  animation: notification-progress var(--duration) linear;
  transform-origin: left;
}

.notification-success .notification-progress::after {
  background: var(--success-color);
}

.notification-error .notification-progress::after {
  background: var(--error-color);
}

.notification-warning .notification-progress::after {
  background: var(--warning-color);
}

.notification-info .notification-progress::after {
  background: var(--info-color);
}

@keyframes notification-progress {
  from {
    transform: scaleX(1);
  }
  to {
    transform: scaleX(0);
  }
}

/* Transitions */
.notification-enter-active {
  transition: all 0.3s ease-out;
}

.notification-leave-active {
  transition: all 0.3s ease-in;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%) scale(0.9);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%) scale(0.9);
}

.notification-move {
  transition: transform 0.3s ease;
}

/* Responsive */
@media (max-width: 640px) {
  .notification-container {
    left: 1rem;
    right: 1rem;
    max-width: none;
  }
  
  .notification {
    padding: 0.875rem;
  }
  
  .notification-actions {
    flex-direction: column;
  }
  
  .notification-action {
    justify-content: center;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .notification {
    background: var(--gray-800);
    border-color: var(--gray-700);
    color: var(--gray-100);
  }
  
  .notification-title {
    color: var(--gray-100);
  }
  
  .notification-message {
    color: var(--gray-300);
  }
  
  .notification-close:hover {
    background: var(--gray-700);
    color: var(--gray-100);
  }
}
</style>