<template>
  <div class="comment-item" :class="{ 'is-internal': comment.is_internal, 'is-resolved': comment.status === 'resolved' }">
    <div class="comment-header">
      <div class="comment-meta">
        <span class="comment-type" :class="`type-${comment.comment_type}`">
          {{ getTypeLabel(comment.comment_type) }}
        </span>
        <span v-if="comment.section_id" class="comment-section">
          {{ getSectionTitle(comment.section_id) }}
        </span>
        <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
        <span v-if="comment.is_internal" class="internal-badge">Intern</span>
        <span v-if="comment.status === 'resolved'" class="resolved-badge">Opgelost</span>
      </div>
      <div class="comment-actions">
        <button v-if="canEdit" @click="toggleEdit" class="btn-action">
          {{ isEditing ? 'Annuleren' : 'Bewerken' }}
        </button>
        <button v-if="canResolve && comment.status !== 'resolved'" @click="$emit('resolve', comment.id)" class="btn-action">
          Markeren als opgelost
        </button>
        <button v-if="canReply" @click="$emit('reply', comment)" class="btn-action">
          Reageren
        </button>
        <button v-if="canDelete" @click="$emit('delete', comment.id)" class="btn-action btn-danger">
          Verwijderen
        </button>
      </div>
    </div>

    <div class="comment-content">
      <div v-if="!isEditing" class="comment-text">{{ comment.content }}</div>
      <div v-else class="edit-form">
        <textarea v-model="editContent" rows="3"></textarea>
        <div class="edit-actions">
          <button @click="saveEdit" :disabled="!editContent.trim()" class="btn-primary">
            Opslaan
          </button>
          <button @click="cancelEdit" class="btn-secondary">
            Annuleren
          </button>
        </div>
      </div>
    </div>

    <!-- Replies -->
    <div v-if="comment.replies && comment.replies.length > 0" class="comment-replies">
      <CommentItem 
        v-for="reply in comment.replies" 
        :key="reply.id"
        :comment="reply"
        :current-user="currentUser"
        @reply="$emit('reply', $event)"
        @resolve="$emit('resolve', $event)"
        @update="$emit('update', $event.id, $event.data)"
        @delete="$emit('delete', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Comment } from '../types'

interface Props {
  comment: Comment
  currentUser: any
}

const props = defineProps<Props>()

const emit = defineEmits<{
  reply: [comment: Comment]
  resolve: [commentId: string]
  update: [commentId: string, data: any]
  delete: [commentId: string]
}>()

const isEditing = ref(false)
const editContent = ref('')

const canEdit = computed(() => {
  return props.currentUser && props.comment.user_id === props.currentUser.sub
})

const canDelete = computed(() => {
  return props.currentUser && props.comment.user_id === props.currentUser.sub
})

const canResolve = computed(() => {
  return props.currentUser && props.comment.status !== 'resolved'
})

const canReply = computed(() => {
  return props.currentUser && props.comment.status !== 'resolved'
})

const toggleEdit = () => {
  if (isEditing.value) {
    cancelEdit()
  } else {
    editContent.value = props.comment.content
    isEditing.value = true
  }
}

const saveEdit = () => {
  if (!editContent.value.trim()) return
  
  emit('update', props.comment.id, { content: editContent.value.trim() })
  isEditing.value = false
}

const cancelEdit = () => {
  isEditing.value = false
  editContent.value = ''
}

const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    feedback: 'Feedback',
    suggestion: 'Suggestie',
    approval: 'Goedkeuring',
    rejection: 'Afwijzing'
  }
  return labels[type] || type
}

const getSectionTitle = (sectionId: string): string => {
  const sections: Record<string, string> = {
    persoonsgegevens: 'Persoonsgegevens',
    klacht_en_hulpvraag: 'Klacht en hulpvraag',
    anamnese: 'Anamnese',
    onderzoek: 'Onderzoek',
    bevindingen: 'Bevindingen',
    conclusie: 'Conclusie',
    advies: 'Advies'
  }
  return sections[sectionId] || sectionId
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('nl-NL', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.comment-item {
  background: white;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border-left: 4px solid #3498db;
}

.comment-item.is-internal {
  border-left-color: #f39c12;
  background: #fef9e7;
}

.comment-item.is-resolved {
  border-left-color: #27ae60;
  background: #f8fffe;
  opacity: 0.8;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.comment-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.comment-type {
  background: #ecf0f1;
  color: #2c3e50;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.type-feedback {
  background: #e3f2fd;
  color: #1976d2;
}

.type-suggestion {
  background: #f3e5f5;
  color: #7b1fa2;
}

.type-approval {
  background: #e8f5e8;
  color: #2e7d32;
}

.type-rejection {
  background: #ffebee;
  color: #c62828;
}

.comment-section {
  background: #f0f0f0;
  color: #555;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.comment-date {
  color: #7f8c8d;
  font-size: 12px;
}

.internal-badge {
  background: #f39c12;
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.resolved-badge {
  background: #27ae60;
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.comment-actions {
  display: flex;
  gap: 5px;
}

.btn-action {
  background: none;
  border: 1px solid #ddd;
  color: #555;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-action:hover {
  background: #f8f9fa;
}

.btn-danger {
  border-color: #e74c3c;
  color: #e74c3c;
}

.btn-danger:hover {
  background: #fdf2f2;
}

.comment-content {
  margin-bottom: 10px;
}

.comment-text {
  line-height: 1.5;
  white-space: pre-wrap;
  color: #2c3e50;
}

.edit-form textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
  margin-bottom: 10px;
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.btn-primary {
  background: #27ae60;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-primary:hover:not(:disabled) {
  background: #229954;
}

.btn-primary:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

.comment-replies {
  margin-left: 20px;
  padding-left: 15px;
  border-left: 2px solid #ecf0f1;
}

@media (max-width: 768px) {
  .comment-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .comment-replies {
    margin-left: 10px;
    padding-left: 10px;
  }
}
</style>