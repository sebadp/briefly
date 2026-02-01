# AWS CDK Learning Guide - Briefly Infrastructure

Guía para aprender AWS CDK (Python) usando la infraestructura de Briefly como ejemplo práctico.

---

## 🎯 ¿Qué es AWS CDK?

**Cloud Development Kit** - Infrastructure as Code usando lenguajes de programación reales en lugar de YAML/JSON.

```python
# Así se crea un bucket S3 con CDK
from aws_cdk import aws_s3 as s3

bucket = s3.Bucket(self, "MyBucket",
    versioned=True,
    encryption=s3.BucketEncryption.S3_MANAGED
)
```

### CDK vs Terraform vs CloudFormation

| Característica | CDK | Terraform | CloudFormation |
|---------------|-----|-----------|----------------|
| **Lenguaje** | Python, TS, Java | HCL (propio) | YAML/JSON |
| **Multi-cloud** | ❌ Solo AWS | ✅ Cualquiera | ❌ Solo AWS |
| **Loops/Condiciones** | ✅ Nativo | ⚠️ Limitado | ⚠️ Muy limitado |
| **Type Safety** | ✅ Full | ❌ Parcial | ❌ No |
| **Learning Curve** | Fácil si sabés Python | Nuevo lenguaje | Verbose |

---

## 📚 Conceptos Fundamentales

### App → Stack → Construct

```
┌─────────────────────────────────────────┐
│                  App                      │
│  ┌──────────────┐  ┌──────────────────┐  │
│  │ DatabaseStack │  │  BackendStack    │  │
│  │  ┌─────────┐ │  │  ┌────────────┐  │  │
│  │  │   VPC   │ │  │  │ ECS Cluster│  │  │
│  │  ├─────────┤ │  │  ├────────────┤  │  │
│  │  │   RDS   │ │──▶│  │  Fargate   │  │  │
│  │  ├─────────┤ │  │  ├────────────┤  │  │
│  │  │DynamoDB │ │  │  │    ALB     │  │  │
│  │  └─────────┘ │  │  └────────────┘  │  │
│  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────┘
```

| Concepto | Descripción | Ejemplo en Briefly |
|----------|-------------|-------------------|
| **App** | Entry point, contiene stacks | `app.py` |
| **Stack** | Unidad deployable (CloudFormation stack) | `DatabaseStack`, `BackendStack` |
| **Construct** | Componente reutilizable (L1, L2, L3) | `ec2.Vpc`, `rds.DatabaseInstance` |

### Niveles de Constructs

- **L1 (Cfn*)**: 1:1 con CloudFormation (bajo nivel)
- **L2**: Abstracciones con defaults sensatos ✅ *Usamos estos*
- **L3 (Patterns)**: Soluciones completas pre-armadas

```python
# L1 - Muy verbose, control total
cfn_bucket = s3.CfnBucket(self, "L1Bucket", bucket_name="my-bucket")

# L2 - Balance ideal ✅
bucket = s3.Bucket(self, "L2Bucket", versioned=True)

# L3 - Solución completa
ecs_patterns.ApplicationLoadBalancedFargateService(...)
```

---

## 🏗️ Estructura del Proyecto Briefly

```
infra/
├── app.py              # Entry point - define stacks
├── cdk.json            # Configuración CDK
├── requirements.txt    # Dependencias Python
└── stacks/
    ├── __init__.py
    ├── database_stack.py   # VPC + RDS + DynamoDB
    └── backend_stack.py    # ECS Fargate + ALB
```

---

## 🚀 Quick Start

### 1. Instalación

```bash
# Instalar CDK CLI
npm install -g aws-cdk

# Verificar
cdk --version
```

### 2. Setup del Proyecto

```bash
cd infra

# Crear virtualenv
python -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Comandos Esenciales

```bash
# Ver diferencias (como terraform plan)
cdk diff

# Deploy todos los stacks
cdk deploy --all

# Deploy stack específico
cdk deploy BrieflyDatabaseStack

# Destruir
cdk destroy --all

# Sintetizar CloudFormation (debug)
cdk synth
```

---

## 📖 Anatomía de un Stack

### DatabaseStack Explicado

```python
# stacks/database_stack.py

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Duration,
)
from constructs import Construct


class DatabaseStack(Stack):
    """Stack para bases de datos."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1️⃣ VPC - Networking
        self.vpc = ec2.Vpc(
            self,
            "BrieflyVpc",
            max_azs=2,                    # 2 availability zones
            nat_gateways=1,               # Para acceso a internet desde private
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",        # Sin internet - para RDS
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # 2️⃣ RDS PostgreSQL
        self.database = rds.DatabaseInstance(
            self,
            "BrieflyDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO,   # Free tier!
            ),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            database_name="briefly",
            # 🔐 Credenciales auto-generadas en Secrets Manager
            credentials=rds.Credentials.from_generated_secret("briefly_admin"),
            allocated_storage=20,
            deletion_protection=False,    # True en prod
            removal_policy=RemovalPolicy.DESTROY,
        )

        # 3️⃣ DynamoDB para artículos
        self.dynamodb_table = dynamodb.Table(
            self,
            "BrieflyArticles",
            table_name="briefly-articles",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="SK", 
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )
```

### BackendStack Explicado

```python
# stacks/backend_stack.py

class BackendStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,              # ⬅️ Recibe VPC del DatabaseStack
        database: rds.DatabaseInstance,
        dynamodb_table: dynamodb.Table,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1️⃣ ECS Cluster
        cluster = ecs.Cluster(self, "BrieflyCluster", vpc=vpc)

        # 2️⃣ Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "BrieflyBackendTask",
            memory_limit_mib=512,
            cpu=256,
        )

        # 3️⃣ Container con imagen desde ../backend
        container = task_definition.add_container(
            "BrieflyBackend",
            image=ecs.ContainerImage.from_asset("../backend"),
            environment={
                "ENVIRONMENT": "production",
            },
            secrets={
                # 🔐 Inyecta secrets automáticamente
                "DATABASE_URL": ecs.Secret.from_secrets_manager(
                    database.secret, "connectionString"
                ),
            },
        )
        container.add_port_mappings(ecs.PortMapping(container_port=8000))

        # 4️⃣ Fargate Service + ALB (L3 Pattern!)
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "BrieflyBackendService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            public_load_balancer=True,
        )

        # 5️⃣ Auto Scaling
        scaling = self.fargate_service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=4,
        )
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
        )
```

### Conectar Stacks en app.py

```python
# app.py
app = cdk.App()

# Stack 1: Databases
db_stack = DatabaseStack(app, "BrieflyDatabaseStack", env=env)

# Stack 2: Backend (depende de Stack 1)
backend_stack = BackendStack(
    app,
    "BrieflyBackendStack",
    vpc=db_stack.vpc,                    # ⬅️ Pasa recursos
    database=db_stack.database,
    dynamodb_table=db_stack.dynamodb_table,
    env=env,
)
backend_stack.add_dependency(db_stack)   # ⬅️ Ordena deploy

app.synth()
```

---

## 💡 Patterns Útiles

### 1. Outputs (para obtener valores post-deploy)

```python
cdk.CfnOutput(
    self,
    "BackendUrl",
    value=f"http://{self.fargate_service.load_balancer.load_balancer_dns_name}",
    description="URL del backend",
)
```

### 2. Environment Variables vs Secrets

```python
# Variables normales (visibles)
environment={
    "ENVIRONMENT": "production",
    "LOG_LEVEL": "INFO",
}

# Secrets (desde Secrets Manager)
secrets={
    "API_KEY": ecs.Secret.from_secrets_manager(my_secret),
}
```

### 3. Removal Policies

```python
# Dev - destruir todo al hacer cdk destroy
removal_policy=RemovalPolicy.DESTROY

# Prod - mantener datos
removal_policy=RemovalPolicy.RETAIN

# Prod - crear snapshot antes de destruir
removal_policy=RemovalPolicy.SNAPSHOT
```

### 4. Tags Globales

```python
# En app.py - aplica a todos los recursos
cdk.Tags.of(app).add("Project", "Briefly")
cdk.Tags.of(app).add("Environment", "dev")
```

---

## 🔧 Comandos de Referencia

```bash
# Bootstrap (primera vez por cuenta/región)
cdk bootstrap aws://ACCOUNT/REGION

# Ver CloudFormation generado
cdk synth > template.yaml

# Deploy sin confirmación (CI/CD)
cdk deploy --all --require-approval never

# Ver diferencias antes de deploy
cdk diff

# Listar stacks
cdk list

# Destruir específico
cdk destroy BrieflyBackendStack
```

---

## 📋 Deployment Checklist

```bash
# 1. Configurar AWS
aws configure

# 2. Bootstrap CDK (solo primera vez)
cdk bootstrap

# 3. Ver plan
cdk diff

# 4. Deploy databases primero
cdk deploy BrieflyDatabaseStack

# 5. Deploy backend
cdk deploy BrieflyBackendStack

# 6. Ver outputs
aws cloudformation describe-stacks \
  --stack-name BrieflyBackendStack \
  --query 'Stacks[0].Outputs'
```

---

## 🎓 Próximos Pasos

1. **Agregar FrontendStack**: Amplify para hosting Next.js
2. **Custom Domain**: Route53 + ACM para HTTPS
3. **CI/CD**: GitHub Actions con `cdk deploy`
4. **Monitoring**: CloudWatch dashboards y alertas
5. **Multi-environment**: Stacks separados para dev/staging/prod

---

## 🔗 Recursos

- [AWS CDK Docs](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [CDK API Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [CDK Patterns](https://cdkpatterns.com/)
- [CDK Workshop](https://cdkworkshop.com/)
