# Briefly - AWS CDK Infrastructure

Infrastructure as Code using AWS CDK for deploying the Briefly application.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Amplify    │────▶│     ALB      │────▶│  ECS Fargate │
│  (Frontend)  │     │              │     │  (Backend)   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                     ┌──────────────────────────┼──────────────────────────┐
                     │                          │                          │
                     ▼                          ▼                          ▼
              ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
              │     RDS      │          │   DynamoDB   │          │   Secrets    │
              │  PostgreSQL  │          │   (Articles) │          │   Manager    │
              └──────────────┘          └──────────────┘          └──────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
cdk deploy --all

# Deploy specific stack
cdk deploy BrieflyBackendStack
```

## Stacks

| Stack | Description |
|-------|-------------|
| `BrieflyDatabaseStack` | RDS PostgreSQL + DynamoDB table |
| `BrieflyBackendStack` | ECS Fargate service for FastAPI |
| `BrieflyFrontendStack` | Amplify for Next.js |

## Environment Variables

Set these before deploying:

```bash
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1
export ANTHROPIC_API_KEY=sk-ant-...
```
