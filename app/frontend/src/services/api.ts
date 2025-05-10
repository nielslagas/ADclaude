import axios from 'axios'
import { supabase } from './supabase'

// Use window.location.hostname to determine the API URL
const getApiBaseUrl = () => {
  // In browser environment
  if (typeof window !== 'undefined') {
    // Get the hostname from the current browser window
    const hostname = window.location.hostname;
    // Use the same hostname but with the backend port
    return `http://${hostname}:8000/api/v1`;
  }
  // Fallback for non-browser environments
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
};

const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to each request
apiClient.interceptors.request.use(async (config) => {
  try {
    console.log(`Request to ${config.method?.toUpperCase()} ${config.url}`)
    console.log("Request data:", config.data)
    
    const { data } = await supabase.auth.getSession()
    console.log("Session data:", data)
    const token = data?.session?.access_token
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      console.log("Auth token added to request")
    } else {
      console.warn("No auth token available")
      // For development only - always add a mock token if none exists
      config.headers.Authorization = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlX3VzZXJfaWQiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
      console.log("Mock token added to request")
    }
  } catch (err) {
    console.error("Error getting auth session:", err)
    // For development only - always add a mock token if error occurs
    config.headers.Authorization = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlX3VzZXJfaWQiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
    console.log("Mock token added to request after error")
  }
  
  return config
})

// Handle common errors
apiClient.interceptors.response.use(
  response => response,
  error => {
    const status = error.response?.status

    if (status === 401) {
      // Handle unauthorized - redirect to login or refresh token
      console.error('Unauthorized request')
    } else if (status === 403) {
      console.error('Forbidden request')
    } else if (status === 404) {
      console.error('Resource not found')
    } else if (status === 500) {
      console.error('Server error')
    }

    return Promise.reject(error)
  }
)

export { apiClient }
