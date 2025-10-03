# Azure Deployment Guide for AI-Arbeidsdeskundige

## Why Azure for Government/Enterprise?

### Voordelen:
- **Nederlandse datacenters** (Amsterdam, Arnhem)
- **Overheid certificeringen** (ISO 27001, BIO)
- **Azure AD integratie** voor SSO
- **Compliance tools** voor AVG/GDPR
- **24/7 Nederlandse support**

## Azure Architecture

### Recommended Setup: Azure Container Apps
**Kosten: €200-400/maand**

```bicep
// main.bicep - Infrastructure as Code
param location string = 'westeurope'
param environmentName string = 'production'

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2021-09-01' = {
  name: 'arbeidsdeskundigeacr'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: true
  }
}

// PostgreSQL Flexible Server with pgvector
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2021-06-01' = {
  name: 'arbeidsdeskundige-db'
  location: location
  sku: {
    name: 'Standard_D2ds_v4'
    tier: 'GeneralPurpose'
  }
  properties: {
    version: '15'
    administratorLogin: 'pgadmin'
    administratorLoginPassword: '@secure()'
    storage: {
      storageSizeGB: 128
    }
    backup: {
      backupRetentionDays: 30
      geoRedundantBackup: 'Enabled'
    }
  }
}

// Redis Cache
resource redisCache 'Microsoft.Cache/redis@2021-06-01' = {
  name: 'arbeidsdeskundige-redis'
  location: location
  properties: {
    sku: {
      name: 'Standard'
      family: 'C'
      capacity: 1
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

// Container Apps Environment
resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2022-03-01' = {
  name: 'arbeidsdeskundige-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Backend API Container App
resource backendApi 'Microsoft.App/containerApps@2022-03-01' = {
  name: 'arbeidsdeskundige-api'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['https://arbeidsdeskundige.nl']
        }
      }
      secrets: [
        {
          name: 'db-connection'
          value: postgresServer.properties.fullyQualifiedDomainName
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.properties.adminUserEnabled
        }
      ]
    }
    template: {
      containers: [
        {
          image: 'arbeidsdeskundigeacr.azurecr.io/backend:latest'
          name: 'backend-api'
          resources: {
            cpu: 2
            memory: '4Gi'
          }
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'db-connection'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 2
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2021-06-01' = {
  name: 'arbeidsdeskundige-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'arbeidsdeskundige-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}
```

## Deployment Steps

### 1. Azure CLI Setup
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Create resource group
az group create \
  --name rg-arbeidsdeskundige \
  --location westeurope
```

### 2. Deploy Infrastructure
```bash
# Deploy using Bicep
az deployment group create \
  --resource-group rg-arbeidsdeskundige \
  --template-file main.bicep \
  --parameters environmentName=production

# Or using Azure Portal ARM template
```

### 3. Setup Container Registry
```bash
# Login to ACR
az acr login --name arbeidsdeskundigeacr

# Build and push images
docker build -t arbeidsdeskundigeacr.azurecr.io/backend:latest ./app/backend
docker push arbeidsdeskundigeacr.azurecr.io/backend:latest

docker build -t arbeidsdeskundigeacr.azurecr.io/frontend:latest ./app/frontend
docker push arbeidsdeskundigeacr.azurecr.io/frontend:latest
```

### 4. Configure Database
```bash
# Enable pgvector extension
az postgres flexible-server connect \
  --name arbeidsdeskundige-db \
  --database-name arbeidsdeskundige \
  --query-text "CREATE EXTENSION IF NOT EXISTS vector;"

# Configure firewall
az postgres flexible-server firewall-rule create \
  --resource-group rg-arbeidsdeskundige \
  --name arbeidsdeskundige-db \
  --rule-name AllowContainerApps \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255
```

### 5. Setup Key Vault for Secrets
```bash
# Create Key Vault
az keyvault create \
  --name kv-arbeidsdeskundige \
  --resource-group rg-arbeidsdeskundige \
  --location westeurope

# Add secrets
az keyvault secret set \
  --vault-name kv-arbeidsdeskundige \
  --name "AnthropicApiKey" \
  --value "your-key"

az keyvault secret set \
  --vault-name kv-arbeidsdeskundige \
  --name "OpenAIApiKey" \
  --value "your-key"
```

## Security & Compliance

### 1. Azure AD Integration
```yaml
# app-auth.yaml
authentication:
  enabled: true
  provider: AzureAD
  tenantId: your-tenant-id
  clientId: your-client-id
  clientSecret: '@Microsoft.KeyVault(SecretUri=https://kv-arbeidsdeskundige.vault.azure.net/secrets/ClientSecret/)'
```

### 2. Network Security
```bash
# Create NSG
az network nsg create \
  --resource-group rg-arbeidsdeskundige \
  --name nsg-arbeidsdeskundige

# Add rules
az network nsg rule create \
  --resource-group rg-arbeidsdeskundige \
  --nsg-name nsg-arbeidsdeskundige \
  --name AllowHTTPS \
  --priority 100 \
  --destination-port-ranges 443 \
  --access Allow \
  --protocol Tcp
```

### 3. Backup & DR
```bash
# Enable automated backups
az postgres flexible-server update \
  --resource-group rg-arbeidsdeskundige \
  --name arbeidsdeskundige-db \
  --backup-retention 30 \
  --geo-redundant-backup Enabled

# Create backup vault
az backup vault create \
  --resource-group rg-arbeidsdeskundige \
  --name vault-arbeidsdeskundige \
  --location westeurope
```

## Monitoring & Logging

### 1. Application Insights
```javascript
// Add to frontend
import { ApplicationInsights } from '@microsoft/applicationinsights-web';

const appInsights = new ApplicationInsights({
  config: {
    instrumentationKey: 'your-key',
    enableAutoRouteTracking: true
  }
});
appInsights.loadAppInsights();
```

### 2. Alerts
```bash
# CPU alert
az monitor metrics alert create \
  --name high-cpu-alert \
  --resource-group rg-arbeidsdeskundige \
  --scopes /subscriptions/xxx/resourceGroups/rg-arbeidsdeskundige \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --action-group email-alerts
```

## Cost Optimization

### Estimated Monthly Costs:
- **Container Apps**: €100-150
- **PostgreSQL Flexible**: €80-120
- **Redis Cache**: €40
- **Storage**: €20
- **Application Insights**: €30
- **Total**: €270-360/month

### Cost Saving Tips:
- Use Azure Reservations (up to 72% savings)
- Auto-shutdown dev/test environments
- Use Spot instances for workers
- Enable auto-scaling

## CI/CD with Azure DevOps

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

stages:
- stage: Build
  jobs:
  - job: BuildAndPush
    steps:
    - task: Docker@2
      inputs:
        containerRegistry: 'arbeidsdeskundigeacr'
        repository: 'backend'
        command: 'buildAndPush'
        Dockerfile: 'app/backend/Dockerfile.prod'

- stage: Deploy
  jobs:
  - deployment: DeployToProduction
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: AzureContainerApps@1
            inputs:
              azureSubscription: 'Azure-Connection'
              resourceGroup: 'rg-arbeidsdeskundige'
              containerAppName: 'arbeidsdeskundige-api'
              imageToDeploy: 'arbeidsdeskundigeacr.azurecr.io/backend:$(Build.BuildId)'
```

## Compliance Checklist

- ✅ Data residency in Netherlands
- ✅ GDPR/AVG compliant storage
- ✅ Encryption at rest and in transit
- ✅ Audit logging enabled
- ✅ Regular security assessments
- ✅ ISO 27001 certification
- ✅ BIO compliance for government