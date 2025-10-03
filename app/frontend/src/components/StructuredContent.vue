<template>
  <div class="structured-content">
    <!-- Structured Content Display -->
    <div v-if="structuredData" class="structured-section">
      <!-- Section Header -->
      <div class="section-header">
        <h2 class="section-title">{{ structuredData.title }}</h2>
        <span class="section-format-badge">Gestructureerde Content</span>
      </div>

      <!-- Summary -->
      <div v-if="structuredData.summary" class="section-summary">
        <p class="summary-text">{{ structuredData.summary }}</p>
      </div>

      <!-- Main Content -->
      <div class="main-content">
        <div 
          v-for="(element, index) in structuredData.main_content" 
          :key="index"
          class="content-element"
          :class="element.type"
        >
          <!-- Paragraph Element -->
          <div v-if="element.type === 'paragraph'" class="paragraph-element">
            <p v-html="formatText(element.content)"></p>
          </div>

          <!-- List Element -->
          <div v-else-if="element.type === 'list'" class="list-element">
            <h4 v-if="element.metadata?.title" class="list-title">
              {{ element.metadata.title }}
            </h4>
            <ul v-if="element.metadata?.style === 'bullet'" class="bullet-list">
              <li v-for="(item, idx) in element.content" :key="idx" class="list-item">
                <span v-if="item.label" class="item-label">{{ item.label }}</span>
                <span class="item-value">{{ item.value }}</span>
                <span v-if="item.detail" class="item-detail">({{ item.detail }})</span>
              </li>
            </ul>
            <ol v-else-if="element.metadata?.style === 'numbered'" class="numbered-list">
              <li v-for="(item, idx) in element.content" :key="idx" class="list-item">
                <span v-if="item.label" class="item-label">{{ item.label }}</span>
                <span class="item-value">{{ item.value }}</span>
                <span v-if="item.detail" class="item-detail">({{ item.detail }})</span>
              </li>
            </ol>
          </div>

          <!-- Assessment Matrix Element -->
          <div v-else-if="element.type === 'assessment'" class="assessment-element">
            <div class="assessment-matrix">
              <!-- Group by category -->
              <div 
                v-for="category in getAssessmentCategories(element.content)" 
                :key="category"
                class="assessment-category"
              >
                <h4 class="category-title">{{ getCategoryLabel(category) }}</h4>
                <div class="assessment-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Aspect</th>
                        <th>Capaciteit</th>
                        <th>Frequentie</th>
                        <th>Beperking</th>
                        <th>Notities</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr 
                        v-for="(item, idx) in getAssessmentsByCategory(element.content, category)" 
                        :key="idx"
                      >
                        <td class="aspect-cell">{{ item.aspect }}</td>
                        <td class="capacity-cell">{{ item.capacity }}</td>
                        <td class="frequency-cell">{{ item.frequency || '-' }}</td>
                        <td class="limitation-cell" :class="{ 'has-limitation': item.limitation && item.limitation !== 'geen' }">
                          {{ item.limitation || '-' }}
                        </td>
                        <td class="notes-cell">{{ item.notes || '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Conclusions -->
      <div v-if="structuredData.conclusions && structuredData.conclusions.length > 0" class="conclusions-section">
        <h3 class="conclusions-title">Conclusies</h3>
        <ul class="conclusions-list">
          <li v-for="(conclusion, index) in structuredData.conclusions" :key="index" class="conclusion-item">
            {{ conclusion }}
          </li>
        </ul>
      </div>

      <!-- Recommendations -->
      <div v-if="structuredData.recommendations && structuredData.recommendations.length > 0" class="recommendations-section">
        <h3 class="recommendations-title">Aanbevelingen</h3>
        <div class="recommendations-list">
          <div 
            v-for="(rec, index) in structuredData.recommendations" 
            :key="index" 
            class="recommendation-item"
            :class="`priority-${rec.priority}`"
          >
            <div class="recommendation-header">
              <span class="priority-badge" :class="`priority-${rec.priority}`">
                {{ getPriorityLabel(rec.priority) }}
              </span>
              <span v-if="rec.timeline" class="timeline-badge">{{ rec.timeline }}</span>
            </div>
            <div class="recommendation-content">
              <p class="action">{{ rec.action }}</p>
              <p v-if="rec.rationale" class="rationale">
                <strong>Rationale:</strong> {{ rec.rationale }}
              </p>
              <p v-if="rec.responsible_party" class="responsible">
                <strong>Verantwoordelijke:</strong> {{ rec.responsible_party }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Fallback to Plain Text -->
    <div v-else class="plain-content">
      <div v-html="formatPlainText(plainContent)"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  structuredData?: any
  plainContent?: string
}

const props = defineProps<Props>()

// Helper functions
function formatText(text: string): string {
  if (!text) return ''
  // Simple formatting: **bold** -> <strong>bold</strong>
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
}

function formatPlainText(text: string): string {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

function getAssessmentCategories(assessments: any[]): string[] {
  if (!assessments) return []
  const categories = [...new Set(assessments.map(item => item.category))]
  // Sort: fysiek, mentaal, sociaal
  const order = ['fysiek', 'mentaal', 'sociaal']
  return categories.sort((a, b) => {
    const indexA = order.indexOf(a)
    const indexB = order.indexOf(b)
    if (indexA === -1) return 1
    if (indexB === -1) return -1
    return indexA - indexB
  })
}

function getAssessmentsByCategory(assessments: any[], category: string): any[] {
  if (!assessments) return []
  return assessments.filter(item => item.category === category)
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    'fysiek': 'Fysieke Belastbaarheid',
    'mentaal': 'Mentale Belastbaarheid',
    'sociaal': 'Sociale Belastbaarheid'
  }
  return labels[category] || category.charAt(0).toUpperCase() + category.slice(1)
}

function getPriorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    'critical': 'KRITIEK',
    'high': 'HOOG',
    'medium': 'GEMIDDELD',
    'low': 'LAAG'
  }
  return labels[priority] || priority.toUpperCase()
}
</script>

<style scoped>
.structured-content {
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
}

.section-title {
  color: #1e40af;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.section-format-badge {
  background: #3b82f6;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.section-summary {
  background: #f8fafc;
  padding: 1rem;
  border-radius: 6px;
  border-left: 4px solid #3b82f6;
  margin-bottom: 1.5rem;
}

.summary-text {
  font-size: 1.1rem;
  line-height: 1.6;
  margin: 0;
  color: #334155;
  font-weight: 500;
}

.main-content {
  margin-bottom: 2rem;
}

.content-element {
  margin-bottom: 1.5rem;
}

.paragraph-element p {
  line-height: 1.6;
  color: #374151;
  margin-bottom: 1rem;
}

.list-element {
  margin-bottom: 1.5rem;
}

.list-title {
  color: #1e40af;
  margin-bottom: 0.75rem;
  font-size: 1.1rem;
}

.bullet-list, .numbered-list {
  margin-left: 1rem;
}

.list-item {
  margin-bottom: 0.5rem;
  line-height: 1.5;
}

.item-label {
  font-weight: 600;
  color: #1e40af;
  margin-right: 0.5rem;
}

.item-value {
  color: #374151;
}

.item-detail {
  color: #6b7280;
  font-style: italic;
  margin-left: 0.5rem;
}

/* Assessment Matrix Styles */
.assessment-element {
  background: #f9fafb;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.assessment-category {
  margin-bottom: 2rem;
}

.category-title {
  color: #1e40af;
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #d1d5db;
}

.assessment-table table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.assessment-table th {
  background: #1e40af;
  color: white;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  font-size: 0.9rem;
}

.assessment-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: top;
}

.aspect-cell {
  font-weight: 600;
  color: #374151;
  background: #f8fafc;
}

.capacity-cell {
  color: #059669;
  font-weight: 500;
}

.frequency-cell {
  color: #7c3aed;
}

.limitation-cell {
  color: #6b7280;
}

.limitation-cell.has-limitation {
  color: #dc2626;
  font-weight: 500;
}

.notes-cell {
  color: #6b7280;
  font-size: 0.9rem;
}

/* Conclusions Styles */
.conclusions-section {
  background: #ecfdf5;
  padding: 1.5rem;
  border-radius: 8px;
  border-left: 4px solid #10b981;
  margin-bottom: 1.5rem;
}

.conclusions-title {
  color: #065f46;
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.conclusions-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.conclusion-item {
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
  line-height: 1.6;
  color: #064e3b;
}

.conclusion-item::before {
  content: "✓";
  position: absolute;
  left: 0;
  color: #10b981;
  font-weight: bold;
}

/* Recommendations Styles */
.recommendations-section {
  background: #fef3c7;
  padding: 1.5rem;
  border-radius: 8px;
  border-left: 4px solid #f59e0b;
}

.recommendations-title {
  color: #92400e;
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.recommendation-item {
  background: white;
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 6px;
  border-left: 4px solid #d1d5db;
}

.recommendation-item.priority-critical {
  border-left-color: #dc2626;
}

.recommendation-item.priority-high {
  border-left-color: #f59e0b;
}

.recommendation-item.priority-medium {
  border-left-color: #3b82f6;
}

.recommendation-item.priority-low {
  border-left-color: #10b981;
}

.recommendation-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.priority-badge {
  padding: 0.25rem 0.6rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.priority-badge.priority-critical {
  background: #fecaca;
  color: #dc2626;
}

.priority-badge.priority-high {
  background: #fed7aa;
  color: #ea580c;
}

.priority-badge.priority-medium {
  background: #bfdbfe;
  color: #2563eb;
}

.priority-badge.priority-low {
  background: #bbf7d0;
  color: #059669;
}

.timeline-badge {
  background: #f3f4f6;
  color: #6b7280;
  padding: 0.25rem 0.6rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.recommendation-content .action {
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
}

.recommendation-content .rationale,
.recommendation-content .responsible {
  font-size: 0.9rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.plain-content {
  line-height: 1.6;
  color: #374151;
}
</style>