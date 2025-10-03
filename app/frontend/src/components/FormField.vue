<template>
  <div class="form-field" :class="{ 'form-field-error': hasError, 'form-field-success': isValid }">
    <label 
      v-if="label" 
      :for="fieldId" 
      class="form-label"
      :class="{ 'form-label-required': required }"
    >
      {{ label }}
      <span v-if="required" class="required-indicator" aria-label="verplicht veld">*</span>
    </label>
    
    <div class="form-input-container">
      <!-- Text Input -->
      <input
        v-if="type === 'text' || type === 'email' || type === 'password'"
        :id="fieldId"
        :type="type"
        :value="modelValue"
        @input="handleInput"
        @blur="handleBlur"
        @focus="handleFocus"
        :placeholder="placeholder"
        :disabled="disabled"
        :required="required"
        :maxlength="maxLength"
        :minlength="minLength"
        :aria-describedby="hasError ? `${fieldId}-error` : hasHelp ? `${fieldId}-help` : undefined"
        :aria-invalid="hasError"
        class="form-input"
        :class="{ 
          'form-input-error': hasError, 
          'form-input-success': isValid,
          'form-input-disabled': disabled 
        }"
      />
      
      <!-- Textarea -->
      <textarea
        v-else-if="type === 'textarea'"
        :id="fieldId"
        :value="modelValue"
        @input="handleInput"
        @blur="handleBlur"
        @focus="handleFocus"
        :placeholder="placeholder"
        :disabled="disabled"
        :required="required"
        :maxlength="maxLength"
        :minlength="minLength"
        :rows="rows"
        :aria-describedby="hasError ? `${fieldId}-error` : hasHelp ? `${fieldId}-help` : undefined"
        :aria-invalid="hasError"
        class="form-textarea"
        :class="{ 
          'form-input-error': hasError, 
          'form-input-success': isValid,
          'form-input-disabled': disabled 
        }"
      ></textarea>
      
      <!-- Select -->
      <select
        v-else-if="type === 'select'"
        :id="fieldId"
        :value="modelValue"
        @change="handleInput"
        @blur="handleBlur"
        @focus="handleFocus"
        :disabled="disabled"
        :required="required"
        :aria-describedby="hasError ? `${fieldId}-error` : hasHelp ? `${fieldId}-help` : undefined"
        :aria-invalid="hasError"
        class="form-select"
        :class="{ 
          'form-input-error': hasError, 
          'form-input-success': isValid,
          'form-input-disabled': disabled 
        }"
      >
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option 
          v-for="option in options" 
          :key="option.value" 
          :value="option.value"
        >
          {{ option.label }}
        </option>
      </select>
      
      <!-- Character Counter -->
      <div 
        v-if="maxLength && showCharCounter" 
        class="char-counter"
        :class="{ 'char-counter-warning': isNearLimit, 'char-counter-error': isOverLimit }"
        :aria-live="isNearLimit ? 'polite' : 'off'"
      >
        {{ currentLength }}/{{ maxLength }}
      </div>
      
      <!-- Validation Icons -->
      <div v-if="showValidationIcon" class="validation-icon" aria-hidden="true">
        <svg v-if="hasError" class="icon-error" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        <svg v-else-if="isValid" class="icon-success" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
        </svg>
      </div>
    </div>
    
    <!-- Error Message -->
    <Transition name="slide-down">
      <div 
        v-if="hasError" 
        :id="`${fieldId}-error`"
        class="form-error"
        role="alert"
        aria-live="polite"
      >
        <svg class="error-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M8 15A7 7 0 108 1a7 7 0 000 14zM8 4a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 018 4zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
        </svg>
        {{ currentError }}
      </div>
    </Transition>
    
    <!-- Help Text -->
    <div 
      v-if="helpText && !hasError" 
      :id="`${fieldId}-help`"
      class="form-help"
    >
      {{ helpText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { generateId } from '@/utils/helpers'

interface Option {
  value: string | number
  label: string
}

interface Props {
  modelValue: string | number
  type?: 'text' | 'email' | 'password' | 'textarea' | 'select'
  label?: string
  placeholder?: string
  helpText?: string
  required?: boolean
  disabled?: boolean
  maxLength?: number
  minLength?: number
  rows?: number
  showCharCounter?: boolean
  showValidationIcon?: boolean
  options?: Option[]
  validators?: Array<(value: string | number) => string | null>
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  required: false,
  disabled: false,
  rows: 3,
  showCharCounter: false,
  showValidationIcon: true,
  options: undefined,
  validators: () => []
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  'validation': [isValid: boolean, error?: string]
}>()

const fieldId = ref(generateId('field'))
const isTouched = ref(false)
const isFocused = ref(false)
const localError = ref<string | null>(null)

// Computed properties
const currentLength = computed(() => String(props.modelValue || '').length)
const isNearLimit = computed(() => 
  props.maxLength ? currentLength.value >= props.maxLength * 0.8 : false
)
const isOverLimit = computed(() => 
  props.maxLength ? currentLength.value > props.maxLength : false
)

const hasHelp = computed(() => Boolean(props.helpText))

const currentError = computed(() => {
  if (!isTouched.value && !localError.value) return null
  
  const value = String(props.modelValue || '')
  
  // Built-in validations
  if (props.required && !value.trim()) {
    return 'Dit veld is verplicht'
  }
  
  if (props.minLength && value.length > 0 && value.length < props.minLength) {
    return `Minimaal ${props.minLength} karakters vereist`
  }
  
  if (props.maxLength && value.length > props.maxLength) {
    return `Maximaal ${props.maxLength} karakters toegestaan`
  }
  
  if (props.type === 'email' && value && !isValidEmail(value)) {
    return 'Voer een geldig e-mailadres in'
  }
  
  // Custom validators
  for (const validator of props.validators) {
    const error = validator(props.modelValue)
    if (error) return error
  }
  
  return localError.value
})

const hasError = computed(() => Boolean(currentError.value))
const isValid = computed(() => 
  isTouched.value && 
  !hasError.value && 
  String(props.modelValue || '').length > 0
)

// Helper function
const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

// Event handlers
const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
  emit('update:modelValue', target.value)
}

const handleBlur = () => {
  isTouched.value = true
  isFocused.value = false
}

const handleFocus = () => {
  isFocused.value = true
}

// Watch for validation changes
watch([currentError, isValid], ([error, valid]) => {
  emit('validation', !error, error || undefined)
}, { immediate: true })

</script>

<style scoped>
.form-field {
  margin-bottom: var(--spacing-lg);
  position: relative;
}

.form-label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  line-height: var(--line-height-tight);
}

.form-label-required {
  position: relative;
}

.required-indicator {
  color: var(--error-color);
  margin-left: 2px;
  font-weight: var(--font-weight-semibold);
}

.form-input-container {
  position: relative;
  display: flex;
  align-items: center;
}

.form-input,
.form-textarea,
.form-select {
  display: block;
  width: 100%;
  padding: var(--spacing-md);
  font-size: var(--font-size-base);
  font-family: var(--font-family);
  color: var(--text-primary);
  background-color: var(--bg-primary);
  border: 2px solid var(--border-color);
  border-radius: var(--radius);
  transition: all var(--transition-fast);
  appearance: none;
  outline: none;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--text-muted);
}

/* Success state */
.form-input-success {
  border-color: var(--success-color);
  padding-right: 3rem;
}

.form-input-success:focus {
  border-color: var(--success-color);
  box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.1);
}

/* Error state */
.form-input-error {
  border-color: var(--error-color);
  padding-right: 3rem;
}

.form-input-error:focus {
  border-color: var(--error-color);
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

/* Disabled state */
.form-input-disabled {
  background-color: var(--bg-muted);
  color: var(--text-muted);
  cursor: not-allowed;
  opacity: 0.6;
}

/* Textarea specific */
.form-textarea {
  resize: vertical;
  min-height: 2.5rem;
}

/* Select specific */
.form-select {
  cursor: pointer;
}

.form-select:not(:disabled):not([readonly]) {
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.75rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}

/* Character counter */
.char-counter {
  position: absolute;
  right: var(--spacing-sm);
  bottom: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  pointer-events: none;
  z-index: 1;
}

.char-counter-warning {
  color: var(--warning-color);
}

.char-counter-error {
  color: var(--error-color);
  font-weight: var(--font-weight-medium);
}

/* Validation icons */
.validation-icon {
  position: absolute;
  right: var(--spacing-md);
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 2;
}

.icon-error {
  color: var(--error-color);
}

.icon-success {
  color: var(--success-color);
}

/* Error message */
.form-error {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--error-color);
  background-color: var(--error-light);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: var(--radius);
  line-height: var(--line-height-normal);
}

.error-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

/* Help text */
.form-help {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  line-height: var(--line-height-normal);
}

/* Transitions */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.2s ease-out;
}

.slide-down-enter-from {
  opacity: 0;
  transform: translateY(-0.5rem);
}

.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .form-input,
  .form-textarea,
  .form-select {
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: var(--font-size-base);
  }
  
  .char-counter {
    position: static;
    margin-top: var(--spacing-xs);
    text-align: right;
  }
  
  .validation-icon {
    right: var(--spacing-sm);
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .form-input,
  .form-textarea,
  .form-select {
    background-color: var(--gray-800);
    border-color: var(--gray-600);
    color: var(--gray-100);
  }
  
  .form-input:focus,
  .form-textarea:focus,
  .form-select:focus {
    border-color: var(--primary-color);
    background-color: var(--gray-750);
  }
  
  .form-input::placeholder,
  .form-textarea::placeholder {
    color: var(--gray-400);
  }
  
  .form-error {
    background-color: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.2);
  }
}

/* Focus visible for better accessibility */
.form-input:focus-visible,
.form-textarea:focus-visible,
.form-select:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .form-input,
  .form-textarea,
  .form-select {
    border-width: 2px;
  }
  
  .form-input-error,
  .form-input-success {
    border-width: 3px;
  }
}
</style>