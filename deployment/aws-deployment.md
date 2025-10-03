# AWS Deployment Guide for AI-Arbeidsdeskundige

## Why AWS?

### Voordelen:
- **EU datacenters** (Frankfurt, Ireland)
- **Most mature AI services** (Bedrock, SageMaker)
- **Extensive compliance** certifications
- **Best auto-scaling** capabilities
- **Global CDN** (CloudFront)

## AWS Architecture: ECS Fargate + RDS

### CloudFormation Template
```yaml
# infrastructure.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'AI-Arbeidsdeskundige Production Infrastructure'

Parameters:
  Environment:
    Type: String
    Default: production
  VpcCidr:
    Type: String
    Default: '10.0.0.0/16'

Resources:
  # VPC and Networking
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCidr
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-arbeidsdeskundige-vpc'

  # Public Subnets for ALB
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: '10.0.1.0/24'
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: '10.0.2.0/24'
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: true

  # Private Subnets for ECS
  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: '10.0.3.0/24'
      AvailabilityZone: !Select [0, !GetAZs '']

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: '10.0.4.0/24'
      AvailabilityZone: !Select [1, !GetAZs '']

  # Internet Gateway
  InternetGateway:
    Type: AWS::EC2::InternetGateway

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  # NAT Gateway for private subnets
  NATGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt EIPForNAT.AllocationId
      SubnetId: !Ref PublicSubnet1

  EIPForNAT:
    Type: AWS::EC2::EIP
    Properties:
      Domain: vpc

  # ECS Cluster
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Sub '${Environment}-arbeidsdeskundige'
      CapacityProviders:
        - FARGATE
        - FARGATE_SPOT
      DefaultCapacityProviderStrategy:
        - CapacityProvider: FARGATE
          Weight: 1
          Base: 2
        - CapacityProvider: FARGATE_SPOT
          Weight: 4

  # PostgreSQL RDS with pgvector
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Subnet group for RDS
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2

  PostgreSQLDB:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: !Sub '${Environment}-arbeidsdeskundige-db'
      DBInstanceClass: db.t3.medium
      Engine: postgres
      EngineVersion: '15.4'
      MasterUsername: pgadmin
      MasterUserPassword: !Ref DBPassword
      AllocatedStorage: 100
      StorageType: gp3
      StorageEncrypted: true
      VPCSecurityGroups:
        - !Ref DBSecurityGroup
      DBSubnetGroupName: !Ref DBSubnetGroup
      BackupRetentionPeriod: 30
      MultiAZ: true
      PubliclyAccessible: false

  # ElastiCache Redis
  RedisSubnetGroup:
    Type: AWS::ElastiCache::SubnetGroup
    Properties:
      Description: Subnet group for Redis
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2

  RedisCluster:
    Type: AWS::ElastiCache::CacheCluster
    Properties:
      CacheNodeType: cache.t3.micro
      Engine: redis
      NumCacheNodes: 1
      VpcSecurityGroupIds:
        - !Ref RedisSecurityGroup
      CacheSubnetGroupName: !Ref RedisSubnetGroup

  # Application Load Balancer
  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub '${Environment}-arbeidsdeskundige-alb'
      Scheme: internet-facing
      Type: application
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref ALBSecurityGroup

  # ECS Service for Backend API
  BackendTaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: !Sub '${Environment}-backend-api'
      NetworkMode: awsvpc
      RequiresCompatibilities:
        - FARGATE
      Cpu: 1024
      Memory: 2048
      ExecutionRoleArn: !Ref ECSExecutionRole
      TaskRoleArn: !Ref ECSTaskRole
      ContainerDefinitions:
        - Name: backend-api
          Image: !Sub '${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/arbeidsdeskundige/backend:latest'
          PortMappings:
            - ContainerPort: 8000
              Protocol: tcp
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref BackendLogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: ecs
          Environment:
            - Name: DATABASE_URL
              Value: !Sub 
                - 'postgresql://pgadmin:${DBPassword}@${DBEndpoint}:5432/arbeidsdeskundige'
                - DBPassword: !Ref DBPassword
                  DBEndpoint: !GetAtt PostgreSQLDB.Endpoint.Address
          Secrets:
            - Name: ANTHROPIC_API_KEY
              ValueFrom: !Ref AnthropicAPIKey
            - Name: OPENAI_API_KEY
              ValueFrom: !Ref OpenAIAPIKey

  BackendService:
    Type: AWS::ECS::Service
    Properties:
      ServiceName: !Sub '${Environment}-backend-api'
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref BackendTaskDefinition
      DesiredCount: 2
      LaunchType: FARGATE
      NetworkConfiguration:
        AwsvpcConfiguration:
          SecurityGroups:
            - !Ref ECSSecurityGroup
          Subnets:
            - !Ref PrivateSubnet1
            - !Ref PrivateSubnet2
      LoadBalancers:
        - ContainerName: backend-api
          ContainerPort: 8000
          TargetGroupArn: !Ref BackendTargetGroup

  # Auto Scaling
  BackendAutoScalingTarget:
    Type: AWS::ApplicationAutoScaling::ScalableTarget
    Properties:
      MaxCapacity: 20
      MinCapacity: 2
      ResourceId: !Sub 'service/${ECSCluster}/${BackendService.Name}'
      RoleARN: !Sub 'arn:aws:iam::${AWS::AccountId}:role/application-autoscaling-ecs-service'
      ScalableDimension: ecs:service:DesiredCount
      ServiceNamespace: ecs

  BackendScalingPolicy:
    Type: AWS::ApplicationAutoScaling::ScalingPolicy
    Properties:
      PolicyName: BackendCPUScalingPolicy
      PolicyType: TargetTrackingScaling
      ScalingTargetId: !Ref BackendAutoScalingTarget
      TargetTrackingScalingPolicyConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ECSServiceAverageCPUUtilization
        TargetValue: 70.0

  # Secrets Manager
  AnthropicAPIKey:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub '${Environment}/arbeidsdeskundige/anthropic-api-key'
      SecretString: !Ref AnthropicKey

  OpenAIAPIKey:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub '${Environment}/arbeidsdeskundige/openai-api-key'
      SecretString: !Ref OpenAIKey

Parameters:
  DBPassword:
    Type: String
    NoEcho: true
    MinLength: 8
    
  AnthropicKey:
    Type: String
    NoEcho: true
    
  OpenAIKey:
    Type: String
    NoEcho: true

Outputs:
  LoadBalancerDNS:
    Description: DNS name of the load balancer
    Value: !GetAtt ApplicationLoadBalancer.DNSName
    Export:
      Name: !Sub '${Environment}-arbeidsdeskundige-alb-dns'
```

## Deployment with AWS CDK (TypeScript)

```typescript
// lib/arbeidsdeskundige-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecs_patterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

export class ArbeidsdeskundigeStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC
    const vpc = new ec2.Vpc(this, 'ArbeidsdeskundigeVPC', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        {
          cidrMask: 28,
          name: 'Database',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
    });

    // ECS Cluster
    const cluster = new ecs.Cluster(this, 'ArbeidsdeskundigeCluster', {
      vpc,
      containerInsights: true,
    });

    // RDS PostgreSQL
    const dbInstance = new rds.DatabaseInstance(this, 'PostgreSQLDatabase', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15_4,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      },
      multiAz: true,
      storageEncrypted: true,
      backupRetention: cdk.Duration.days(30),
      deletionProtection: true,
    });

    // ElastiCache Redis
    const redisSubnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
      description: 'Subnet group for Redis cluster',
      subnetIds: vpc.isolatedSubnets.map(subnet => subnet.subnetId),
    });

    const redisCluster = new elasticache.CfnCacheCluster(this, 'RedisCluster', {
      cacheNodeType: 'cache.t3.micro',
      engine: 'redis',
      numCacheNodes: 1,
      cacheSubnetGroupName: redisSubnetGroup.ref,
    });

    // Secrets
    const anthropicSecret = new secretsmanager.Secret(this, 'AnthropicAPIKey', {
      description: 'Anthropic API Key for Claude',
    });

    // Backend service
    const backendService = new ecs_patterns.ApplicationLoadBalancedFargateService(
      this,
      'BackendService',
      {
        cluster,
        taskImageOptions: {
          image: ecs.ContainerImage.fromRegistry('arbeidsdeskundige/backend:latest'),
          containerPort: 8000,
          environment: {
            NODE_ENV: 'production',
            DATABASE_URL: `postgresql://postgres:${dbInstance.secret!.secretValueFromJson('password')}@${dbInstance.instanceEndpoint.hostname}:5432/arbeidsdeskundige`,
          },
          secrets: {
            ANTHROPIC_API_KEY: ecs.Secret.fromSecretsManager(anthropicSecret),
          },
        },
        memoryLimitMiB: 2048,
        cpu: 1024,
        desiredCount: 2,
        publicLoadBalancer: true,
      }
    );

    // Auto Scaling
    const scalableTarget = backendService.service.autoScaleTaskCount({
      minCapacity: 2,
      maxCapacity: 20,
    });

    scalableTarget.scaleOnCpuUtilization('CpuScaling', {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.minutes(5),
      scaleOutCooldown: cdk.Duration.minutes(5),
    });

    scalableTarget.scaleOnMemoryUtilization('MemoryScaling', {
      targetUtilizationPercent: 80,
    });

    // CloudWatch Dashboard
    new cdk.aws_cloudwatch.Dashboard(this, 'ArbeidsdeskundigeDashboard', {
      dashboardName: 'Arbeidsdeskundige-Production',
      widgets: [
        [
          new cdk.aws_cloudwatch.GraphWidget({
            title: 'ECS Service CPU & Memory',
            left: [backendService.service.metricCpuUtilization()],
            right: [backendService.service.metricMemoryUtilization()],
          }),
        ],
        [
          new cdk.aws_cloudwatch.GraphWidget({
            title: 'Database Connections',
            left: [dbInstance.metricDatabaseConnections()],
          }),
        ],
      ],
    });

    // Outputs
    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: backendService.loadBalancer.loadBalancerDnsName,
      description: 'DNS name of the load balancer',
    });
  }
}
```

## Deployment Steps

### 1. Setup AWS CLI & CDK
```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Configure credentials
aws configure

# Install CDK
npm install -g aws-cdk
cdk bootstrap
```

### 2. Deploy Infrastructure
```bash
# Deploy with CloudFormation
aws cloudformation create-stack \
  --stack-name arbeidsdeskundige-production \
  --template-body file://infrastructure.yaml \
  --parameters ParameterKey=Environment,ParameterValue=production \
  --capabilities CAPABILITY_IAM

# Or deploy with CDK
cdk deploy ArbeidsdeskundigeStack
```

### 3. Setup ECR and Push Images
```bash
# Create ECR repositories
aws ecr create-repository --repository-name arbeidsdeskundige/backend
aws ecr create-repository --repository-name arbeidsdeskundige/frontend

# Login to ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.eu-west-1.amazonaws.com

# Build and push
docker build -t 123456789012.dkr.ecr.eu-west-1.amazonaws.com/arbeidsdeskundige/backend:latest ./app/backend
docker push 123456789012.dkr.ecr.eu-west-1.amazonaws.com/arbeidsdeskundige/backend:latest
```

### 4. Configure Database
```bash
# Connect to RDS and setup pgvector
psql -h your-rds-endpoint.rds.amazonaws.com -U postgres -d arbeidsdeskundige
CREATE EXTENSION IF NOT EXISTS vector;
```

## CI/CD with GitHub Actions

```yaml
# .github/workflows/aws-deploy.yml
name: Deploy to AWS ECS

on:
  push:
    branches: [main]

env:
  AWS_REGION: eu-west-1
  ECR_REPOSITORY: arbeidsdeskundige/backend
  ECS_SERVICE: production-backend-api
  ECS_CLUSTER: production-arbeidsdeskundige

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout
      uses: actions/checkout@v2

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1

    - name: Build, tag, and push image to Amazon ECR
      id: build-image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG ./app/backend
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        echo "::set-output name=image::$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"

    - name: Deploy to Amazon ECS
      uses: aws-actions/amazon-ecs-deploy-task-definition@v1
      with:
        task-definition: task-definition.json
        service: ${{ env.ECS_SERVICE }}
        cluster: ${{ env.ECS_CLUSTER }}
        wait-for-service-stability: true
```

## Cost Optimization

### Estimated Monthly Costs:
- **ECS Fargate**: €120-200 (2-10 tasks)
- **RDS PostgreSQL**: €80-150 (t3.medium Multi-AZ)
- **ElastiCache Redis**: €25-40
- **Application Load Balancer**: €20
- **NAT Gateway**: €40
- **Data Transfer**: €20-50
- **Total**: €305-500/month

### Savings Strategies:
- Use Savings Plans (up to 50% off)
- Reserved Instances for RDS
- Spot instances for workers
- CloudFront CDN for static content
- S3 Intelligent Tiering

## Monitoring & Alerts

```bash
# Create CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "High-CPU-Utilization" \
  --alarm-description "Alarm when CPU exceeds 70%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Setup SNS for notifications
aws sns create-topic --name arbeidsdeskundige-alerts
```

## Disaster Recovery

- **RTO**: 15 minutes (automated failover)
- **RPO**: 5 minutes (continuous replication)
- **Multi-AZ**: Automatic failover
- **Cross-region backups**: Daily to secondary region
- **Automated restoration**: CloudFormation templates