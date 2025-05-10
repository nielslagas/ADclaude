<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useReportStore } from '@/stores/report';
import { apiClient } from '@/services/api';
import { supabase } from '@/services/supabase';

const router = useRouter();
const reportStore = useReportStore();
const templates = ref<Record<string, any>>({});
const loading = ref(false);
const error = ref<string | null>(null);
const responseData = ref<any>(null);
const requestLogs = ref<string[]>([]);
const bearerToken = ref('');

// Add interceptor to log all requests and responses
apiClient.interceptors.request.use((config) => {
  requestLogs.value.push(`REQUEST: ${config.method?.toUpperCase()} ${config.url}`);
  if (config.headers?.Authorization) {
    requestLogs.value.push(`Token: ${config.headers.Authorization}`);
    bearerToken.value = config.headers.Authorization.toString().replace('Bearer ', '');
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    requestLogs.value.push(`RESPONSE: ${response.status} ${response.statusText}`);
    requestLogs.value.push(`Data: ${JSON.stringify(response.data, null, 2)}`);
    return response;
  },
  (error) => {
    requestLogs.value.push(`ERROR: ${error.message}`);
    if (error.response) {
      requestLogs.value.push(`Status: ${error.response.status}`);
      requestLogs.value.push(`Data: ${JSON.stringify(error.response.data, null, 2)}`);
    }
    return Promise.reject(error);
  }
);

const fetchTemplates = async () => {
  loading.value = true;
  error.value = null;
  
  try {
    const response = await apiClient.get('/reports/templates');
    templates.value = response.data;
    responseData.value = response.data;
  } catch (err: any) {
    console.error('Error fetching templates:', err);
    error.value = err.message || 'Failed to fetch templates';
    if (err.response) {
      error.value += ` - Status: ${err.response.status}, Data: ${JSON.stringify(err.response.data)}`;
    }
  } finally {
    loading.value = false;
  }
};

const fetchSession = async () => {
  const { data } = await supabase.auth.getSession();
  requestLogs.value.push(`SUPABASE SESSION: ${JSON.stringify(data, null, 2)}`);
};

const goToLogin = () => {
  router.push('/login');
};

const clearLogs = () => {
  requestLogs.value = [];
};

const getTokenInfo = () => {
  if (!bearerToken.value) return "No token available";
  
  try {
    // Split the token to get the payload part (second part)
    const parts = bearerToken.value.split('.');
    if (parts.length !== 3) return "Invalid token format";
    
    // Decode the base64-encoded payload
    const decodedPayload = atob(parts[1]);
    
    // Parse and return the JSON
    return JSON.parse(decodedPayload);
  } catch (e) {
    return `Error decoding token: ${e}`;
  }
};

onMounted(() => {
  // Do not auto fetch on mount
  fetchSession();
});
</script>

<template>
  <div class="test-container">
    <h1>API Debug View</h1>
    
    <div class="action-buttons">
      <button @click="fetchTemplates" :disabled="loading" class="btn btn-primary">
        Fetch Templates
      </button>
      <button @click="fetchSession" class="btn btn-primary">
        Check Session
      </button>
      <button @click="goToLogin" class="btn btn-secondary">
        Go to Login
      </button>
      <button @click="clearLogs" class="btn btn-secondary">
        Clear Logs
      </button>
    </div>
    
    <div v-if="loading" class="loading">
      Loading...
    </div>
    
    <div v-if="error" class="error-message">
      <h3>Error:</h3>
      <pre>{{ error }}</pre>
    </div>
    
    <div class="results-section">
      <h2>Token Information</h2>
      <pre class="token-info">{{ getTokenInfo() }}</pre>
      
      <h2>API Response</h2>
      <pre v-if="responseData" class="response-data">{{ JSON.stringify(responseData, null, 2) }}</pre>
      <p v-else>No response data available</p>
      
      <h2>Request & Response Logs</h2>
      <div class="request-logs">
        <div v-for="(log, index) in requestLogs" :key="index" class="log-entry">
          <pre>{{ log }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.test-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background-color 0.2s;
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-primary:disabled {
  background-color: #93c5fd;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #e5e7eb;
  color: #4b5563;
}

.btn-secondary:hover {
  background-color: #d1d5db;
}

.loading {
  margin: 1rem 0;
  font-style: italic;
}

.error-message {
  margin: 1rem 0;
  padding: 1rem;
  background-color: #fee2e2;
  border: 1px solid #ef4444;
  border-radius: 4px;
}

.error-message h3 {
  margin-top: 0;
  color: #b91c1c;
}

.results-section {
  margin-top: 2rem;
}

.token-info, .response-data {
  background-color: #f3f4f6;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.request-logs {
  background-color: #f8fafc;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  max-height: 400px;
  overflow-y: auto;
}

.log-entry {
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.log-entry:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.log-entry pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>