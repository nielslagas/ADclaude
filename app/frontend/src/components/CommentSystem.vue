<template>
  <div class="comment-system">
    <div class="comment-header">
      <h3>Opmerkingen</h3>
      <button @click="showCommentForm = !showCommentForm" class="btn-toggle">
        {{ showCommentForm ? 'Annuleren' : 'Opmerking toevoegen' }}
      </button>
    </div>

    <!-- Comment Form -->
    <div v-if="showCommentForm" class="comment-form">
      <div class="form-group">
        <label>Type opmerking:</label>
        <select v-model="newComment.comment_type">
          <option value="feedback">Feedback</option>
          <option value="suggestion">Suggestie</option>
          <option value="approval">Goedkeuring</option>
          <option value="rejection">Afwijzing</option>
        </select>
      </div>
      
      <div class="form-group">
        <label>Sectie (optioneel):</label>
        <select v-model="newComment.section_id">
          <option value="">Algemeen</option>
          <option v-for="section in availableSections" :key="section.id" :value="section.id">
            {{ section.title }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label>
          <input type="checkbox" v-model="newComment.is_internal">
          Interne opmerking (alleen zichtbaar voor arbeidsdeskundigen)
        </label>
      </div>

      <div class="form-group">
        <label>Opmerking:</label>
        <textarea 
          v-model="newComment.content" 
          placeholder="Typ hier uw opmerking..."
          rows="4"
          required
        ></textarea>
      </div>

      <div class="form-actions">
        <button @click="submitComment" :disabled="!newComment.content.trim() || isSubmitting" class="btn-primary">
          {{ isSubmitting ? 'Bezig...' : 'Opmerking plaatsen' }}
        </button>
        <button @click="cancelComment" class="btn-secondary">Annuleren</button>
      </div>
    </div>

    <!-- Comments List -->
    <div class="comments-list">
      <div v-if="loading" class="loading">Opmerkingen laden...</div>
      
      <div v-else-if="comments.length === 0" class="no-comments">
        Geen opmerkingen gevonden.
      </div>

      <div v-else>
        <CommentItem 
          v-for="comment in comments" 
          :key="comment.id"
          :comment="comment"
          :current-user="currentUser"
          @reply="handleReply"
          @resolve="handleResolve"
          @update="handleUpdate"
          @delete="handleDelete"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import CommentItem from './CommentItem.vue'
import type { Comment, CommentCreate } from '../types'

interface Props {
  reportId: string
  sectionId?: string | null
  includeInternal?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  sectionId: null,
  includeInternal: false
})

const emit = defineEmits<{
  commentsUpdated: [count: number]
}>()

const authStore = useAuthStore()
const currentUser = authStore.user

const comments = ref<Comment[]>([])
const loading = ref(false)
const showCommentForm = ref(false)
const isSubmitting = ref(false)

const newComment = ref<CommentCreate>({
  report_id: props.reportId,
  section_id: props.sectionId || null,
  content: '',
  comment_type: 'feedback',
  is_internal: false,
  parent_id: null
})

// Available sections for dropdown (these would come from the report template)
const availableSections = ref([
  { id: 'persoonsgegevens', title: 'Persoonsgegevens' },
  { id: 'klacht_en_hulpvraag', title: 'Klacht en hulpvraag' },
  { id: 'anamnese', title: 'Anamnese' },
  { id: 'onderzoek', title: 'Onderzoek' },
  { id: 'bevindingen', title: 'Bevindingen' },
  { id: 'conclusie', title: 'Conclusie' },
  { id: 'advies', title: 'Advies' }
])

const loadComments = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (props.sectionId) {
      params.append('section_id', props.sectionId)
    }
    if (props.includeInternal) {
      params.append('include_internal', 'true')
    }

    const response = await api.get(`/comments/report/${props.reportId}?${params}`)
    comments.value = response.data
    emit('commentsUpdated', comments.value.length)
  } catch (error) {
    console.error('Error loading comments:', error)
  } finally {
    loading.value = false
  }
}

const submitComment = async () => {
  if (!newComment.value.content.trim()) return

  isSubmitting.value = true
  try {
    const response = await api.post('/comments', newComment.value)
    
    // Add new comment to the list
    comments.value.unshift(response.data)
    emit('commentsUpdated', comments.value.length)
    
    // Reset form
    cancelComment()
  } catch (error) {
    console.error('Error submitting comment:', error)
    alert('Er is een fout opgetreden bij het plaatsen van de opmerking.')
  } finally {
    isSubmitting.value = false
  }
}

const cancelComment = () => {
  showCommentForm.value = false
  newComment.value = {
    report_id: props.reportId,
    section_id: props.sectionId || null,
    content: '',
    comment_type: 'feedback',
    is_internal: false,
    parent_id: null
  }
}

const handleReply = (parentComment: Comment) => {
  newComment.value.parent_id = parentComment.id
  newComment.value.section_id = parentComment.section_id
  showCommentForm.value = true
}

const handleResolve = async (commentId: string) => {
  try {
    await api.post(`/comments/${commentId}/resolve`)
    await loadComments() // Reload to get updated status
  } catch (error) {
    console.error('Error resolving comment:', error)
    alert('Er is een fout opgetreden bij het markeren van de opmerking als opgelost.')
  }
}

const handleUpdate = async (commentId: string, updateData: any) => {
  try {
    await api.put(`/comments/${commentId}`, updateData)
    await loadComments() // Reload to get updated comment
  } catch (error) {
    console.error('Error updating comment:', error)
    alert('Er is een fout opgetreden bij het bijwerken van de opmerking.')
  }
}

const handleDelete = async (commentId: string) => {
  if (!confirm('Weet u zeker dat u deze opmerking wilt verwijderen?')) {
    return
  }

  try {
    await api.delete(`/comments/${commentId}`)
    await loadComments() // Reload to reflect deletion
  } catch (error) {
    console.error('Error deleting comment:', error)
    alert('Er is een fout opgetreden bij het verwijderen van de opmerking.')
  }
}

// Watch for changes in reportId or sectionId
watch([() => props.reportId, () => props.sectionId], () => {
  loadComments()
}, { immediate: true })

onMounted(() => {
  loadComments()
})
</script>

<style scoped>
.comment-system {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.comment-header h3 {
  margin: 0;
  color: #2c3e50;
}

.btn-toggle {
  background: #3498db;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-toggle:hover {
  background: #2980b9;
}

.comment-form {
  background: white;
  border-radius: 6px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #34495e;
}

.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.form-group input[type="checkbox"] {
  margin-right: 8px;
}

.form-actions {
  display: flex;
  gap: 10px;
}

.btn-primary {
  background: #27ae60;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
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
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

.loading {
  text-align: center;
  padding: 20px;
  color: #7f8c8d;
}

.no-comments {
  text-align: center;
  padding: 20px;
  color: #7f8c8d;
  font-style: italic;
}

.comments-list {
  max-height: 600px;
  overflow-y: auto;
}
</style>