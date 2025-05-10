import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiClient } from '@/services/api'
import type { Document, DocumentUpload } from '@/types'

export const useDocumentStore = defineStore('document', () => {
  // State
  const documents = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const uploadProgress = ref(0)

  // Actions
  const uploadDocument = async (documentData: DocumentUpload) => {
    loading.value = true
    error.value = null
    uploadProgress.value = 0
    
    try {
      const formData = new FormData()
      formData.append('case_id', documentData.case_id)
      formData.append('file', documentData.file)
      
      const response = await apiClient.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))
          uploadProgress.value = percentCompleted
        }
      })
      
      const newDocument = response.data
      documents.value.unshift(newDocument)
      return newDocument
    } catch (err) {
      console.error('Error uploading document:', err)
      error.value = err.message || 'Failed to upload document'
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchDocument = async (id: string) => {
    loading.value = true
    error.value = null
    
    try {
      // Add a timestamp to prevent browser caching
      const response = await apiClient.get(`/documents/${id}?_t=${Date.now()}`)
      
      // Log document content for debugging
      console.log('Document fetched successfully:', { 
        id: response.data.id, 
        filename: response.data.filename, 
        status: response.data.status
      })
      
      // Set the current document value
      currentDocument.value = response.data
      return response.data
    } catch (err) {
      console.error(`Error fetching document ${id}:`, err)
      error.value = err.message || 'Failed to fetch document details'
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteDocument = async (id: string) => {
    loading.value = true
    error.value = null
    
    try {
      await apiClient.delete(`/documents/${id}`)
      documents.value = documents.value.filter(d => d.id !== id)
      
      if (currentDocument.value && currentDocument.value.id === id) {
        currentDocument.value = null
      }
    } catch (err) {
      console.error(`Error deleting document ${id}:`, err)
      error.value = err.message || 'Failed to delete document'
      throw err
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    documents.value = []
    currentDocument.value = null
    error.value = null
    uploadProgress.value = 0
  }

  return {
    documents,
    currentDocument,
    loading,
    error,
    uploadProgress,
    uploadDocument,
    fetchDocument,
    deleteDocument,
    reset
  }
})
