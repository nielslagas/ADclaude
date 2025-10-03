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

// Helper function to convert relative API URLs to full URLs
export const getFullApiUrl = (path: string): string => {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    // Already a full URL
    return path;
  }
  
  const baseUrl = getApiBaseUrl();
  
  if (path.startsWith('/api/v1/')) {
    // Convert /api/v1/... to http://hostname:8000/api/v1/...
    return `${baseUrl.replace('/api/v1', '')}${path}`;
  }
  
  if (path.startsWith('/')) {
    // Convert /... to http://hostname:8000/api/v1/...
    return `${baseUrl}${path}`;
  }
  
  // No leading slash, add it
  return `${baseUrl}/${path}`;
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
    // Don't log FormData as it can consume the file stream
    if (!(config.data instanceof FormData)) {
      console.log("Request data:", config.data)
    } else {
      console.log("Request data: FormData (file upload)")
    }
    
    const { data } = await supabase.auth.getSession()
    console.log("Session data:", data)
    const token = data?.session?.access_token
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      console.log("Auth token added to request")
    } else {
      console.warn("No auth token available")
      // For development only - use token with real user ID (Niels Lagas)
      config.headers.Authorization = 'Bearer eyJhbGciOiAibm9uZSIsICJ0eXAiOiAiSldUIn0.eyJzdWIiOiAiOTI3MzQyYWQtZDVhMC00Zjg4LTliYzMtODBmNzcwMjA3M2UwIiwgIm5hbWUiOiAiTmllbHMgTGFnYXMiLCAiaWF0IjogMTUxNjIzOTAyMn0.'
      console.log("Mock token added to request")
    }
  } catch (err) {
    console.error("Error getting auth session:", err)
    // For development only - use token with real user ID (Niels Lagas) after error
    config.headers.Authorization = 'Bearer eyJhbGciOiAibm9uZSIsICJ0eXAiOiAiSldUIn0.eyJzdWIiOiAiOTI3MzQyYWQtZDVhMC00Zjg4LTliYzMtODBmNzcwMjA3M2UwIiwgIm5hbWUiOiAiTmllbHMgTGFnYXMiLCAiaWF0IjogMTUxNjIzOTAyMn0.'
    console.log("Mock token added to request after error")
  }
  
  return config
})

// Enhanced error logging
apiClient.interceptors.response.use(
  response => {
    console.log(`Response from ${response.config.url}:`, response.status, response.data);
    return response;
  },
  error => {
    console.error('API Error:', error);
    const status = error.response?.status;

    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
      console.error('Response headers:', error.response.headers);
      console.error('Request URL:', error.config?.url);
      console.error('Request method:', error.config?.method);
      console.error('Request data:', error.config?.data);

      if (status === 401) {
        console.error('Unauthorized request - Authentication failed');
      } else if (status === 403) {
        console.error('Forbidden request - Permission denied');
      } else if (status === 404) {
        console.error('Resource not found - Check URL and parameters');
      } else if (status === 500) {
        console.error('Server error - Check backend logs');
      } else {
        console.error(`Unexpected status code: ${status}`);
      }
    } else if (error.request) {
      console.error('No response received - Network or CORS issue');
      console.error('Request details:', error.request);
    } else {
      console.error('Error setting up request:', error.message);
    }

    return Promise.reject(error);
  }
)

export { apiClient }
export default apiClient
