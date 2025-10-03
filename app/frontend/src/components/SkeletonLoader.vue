<template>
  <div class="skeleton-container" :aria-label="ariaLabel || 'Inhoud wordt geladen'">
    <!-- Card skeleton for case items -->
    <div v-if="type === 'card'" class="skeleton-card">
      <div class="skeleton-header">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-badge"></div>
      </div>
      <div class="skeleton-body">
        <div class="skeleton-line skeleton-text"></div>
        <div class="skeleton-line skeleton-text-short"></div>
        <div class="skeleton-meta">
          <div class="skeleton-line skeleton-date"></div>
          <div class="skeleton-line skeleton-status"></div>
        </div>
      </div>
    </div>

    <!-- List skeleton for documents -->
    <div v-else-if="type === 'list'" class="skeleton-list">
      <div class="skeleton-list-item" v-for="n in count" :key="n">
        <div class="skeleton-icon"></div>
        <div class="skeleton-content">
          <div class="skeleton-line skeleton-title"></div>
          <div class="skeleton-line skeleton-text-short"></div>
        </div>
        <div class="skeleton-actions">
          <div class="skeleton-button"></div>
          <div class="skeleton-button"></div>
        </div>
      </div>
    </div>

    <!-- Table skeleton -->
    <div v-else-if="type === 'table'" class="skeleton-table">
      <div class="skeleton-table-header">
        <div class="skeleton-line skeleton-table-cell" v-for="n in columns" :key="n"></div>
      </div>
      <div class="skeleton-table-row" v-for="n in count" :key="n">
        <div class="skeleton-line skeleton-table-cell" v-for="c in columns" :key="c"></div>
      </div>
    </div>

    <!-- Form skeleton -->
    <div v-else-if="type === 'form'" class="skeleton-form">
      <div class="skeleton-form-group" v-for="n in count" :key="n">
        <div class="skeleton-line skeleton-label"></div>
        <div class="skeleton-input"></div>
      </div>
    </div>

    <!-- Report skeleton -->
    <div v-else-if="type === 'report'" class="skeleton-report">
      <div class="skeleton-report-header">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line skeleton-subtitle"></div>
      </div>
      <div class="skeleton-report-content">
        <div class="skeleton-line skeleton-text" v-for="n in 5" :key="n"></div>
        <div class="skeleton-line skeleton-text-short"></div>
      </div>
    </div>

    <!-- Text skeleton (default) -->
    <div v-else class="skeleton-text-block">
      <div class="skeleton-line skeleton-text" v-for="n in count" :key="n"></div>
      <div class="skeleton-line skeleton-text-short"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  type?: 'card' | 'list' | 'table' | 'form' | 'report' | 'text'
  count?: number
  columns?: number
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  count: 3,
  columns: 4
})
</script>

<style scoped>
.skeleton-container {
  width: 100%;
}

/* Base skeleton animation */
@keyframes skeleton-pulse {
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
}

.skeleton-line,
.skeleton-icon,
.skeleton-badge,
.skeleton-button,
.skeleton-input {
  background: linear-gradient(
    90deg,
    var(--gray-200) 25%,
    var(--gray-100) 50%,
    var(--gray-200) 75%
  );
  background-size: 200px 100%;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  border-radius: var(--radius);
}

/* Card Skeleton */
.skeleton-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-sm);
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.skeleton-title {
  height: 20px;
  width: 60%;
}

.skeleton-badge {
  height: 24px;
  width: 80px;
  border-radius: var(--radius-full);
}

.skeleton-body {
  space-y: var(--spacing-sm);
}

.skeleton-text {
  height: 16px;
  width: 100%;
  margin-bottom: var(--spacing-sm);
}

.skeleton-text-short {
  height: 16px;
  width: 70%;
  margin-bottom: var(--spacing-sm);
}

.skeleton-meta {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-md);
}

.skeleton-date {
  height: 14px;
  width: 120px;
}

.skeleton-status {
  height: 14px;
  width: 80px;
}

/* List Skeleton */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
}

.skeleton-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius);
  flex-shrink: 0;
}

.skeleton-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.skeleton-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.skeleton-button {
  width: 80px;
  height: 36px;
  border-radius: var(--radius);
}

/* Table Skeleton */
.skeleton-table {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.skeleton-table-header,
.skeleton-table-row {
  display: grid;
  grid-template-columns: repeat(var(--columns, 4), 1fr);
  gap: var(--spacing-md);
  padding: var(--spacing-md);
}

.skeleton-table-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.skeleton-table-row {
  border-bottom: 1px solid var(--border-color);
}

.skeleton-table-row:last-child {
  border-bottom: none;
}

.skeleton-table-cell {
  height: 16px;
  width: 100%;
}

/* Form Skeleton */
.skeleton-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.skeleton-form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.skeleton-label {
  height: 16px;
  width: 25%;
}

.skeleton-input {
  height: 44px;
  width: 100%;
  border-radius: var(--radius);
}

/* Report Skeleton */
.skeleton-report {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
}

.skeleton-report-header {
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.skeleton-report-header .skeleton-title {
  height: 28px;
  width: 50%;
  margin-bottom: var(--spacing-md);
}

.skeleton-subtitle {
  height: 20px;
  width: 70%;
}

.skeleton-report-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* Text Block Skeleton */
.skeleton-text-block {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .skeleton-card {
    padding: var(--spacing-md);
  }
  
  .skeleton-list-item {
    padding: var(--spacing-sm);
  }
  
  .skeleton-table-header,
  .skeleton-table-row {
    grid-template-columns: repeat(2, 1fr);
    padding: var(--spacing-sm);
  }
  
  .skeleton-report {
    padding: var(--spacing-lg);
  }
  
  .skeleton-meta {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  .skeleton-actions {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  .skeleton-button {
    width: 100%;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .skeleton-line,
  .skeleton-icon,
  .skeleton-badge,
  .skeleton-button,
  .skeleton-input {
    background: linear-gradient(
      90deg,
      var(--gray-700) 25%,
      var(--gray-600) 50%,
      var(--gray-700) 75%
    );
  }
  
  .skeleton-card,
  .skeleton-list-item,
  .skeleton-table,
  .skeleton-report {
    background: var(--gray-800);
    border-color: var(--gray-700);
  }
  
  .skeleton-table-header {
    background: var(--gray-700);
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .skeleton-line,
  .skeleton-icon,
  .skeleton-badge,
  .skeleton-button,
  .skeleton-input {
    animation: none;
    background: var(--gray-200);
  }
  
  @media (prefers-color-scheme: dark) {
    .skeleton-line,
    .skeleton-icon,
    .skeleton-badge,
    .skeleton-button,
    .skeleton-input {
      background: var(--gray-700);
    }
  }
}
</style>