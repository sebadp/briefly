"""Backend stack - ECS Fargate for FastAPI."""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_dynamodb as dynamodb,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    Duration,
)


class BackendStack(Stack):
    """Stack for backend ECS Fargate service."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        database: rds.DatabaseInstance,
        dynamodb_table: dynamodb.Table,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECS Cluster
        cluster = ecs.Cluster(
            self,
            "BrieflyCluster",
            vpc=vpc,
            container_insights=True,
        )

        # Anthropic API key secret (create manually or via CLI)
        anthropic_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "AnthropicApiKey",
            "briefly/anthropic-api-key",
        )

        # Task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "BrieflyBackendTask",
            memory_limit_mib=512,
            cpu=256,
        )

        # Grant permissions
        database.secret.grant_read(task_definition.task_role)
        dynamodb_table.grant_read_write_data(task_definition.task_role)
        anthropic_secret.grant_read(task_definition.task_role)

        # Container
        container = task_definition.add_container(
            "BrieflyBackend",
            image=ecs.ContainerImage.from_asset("../backend"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="briefly-backend"),
            environment={
                "ENVIRONMENT": "production",
                "DYNAMODB_TABLE_NAME": dynamodb_table.table_name,
                "AWS_REGION": self.region,
            },
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(
                    database.secret, "connectionString"
                ),
                "ANTHROPIC_API_KEY": ecs.Secret.from_secrets_manager(anthropic_secret),
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
            ),
        )

        container.add_port_mappings(
            ecs.PortMapping(container_port=8000)
        )

        # Fargate service with ALB
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "BrieflyBackendService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            public_load_balancer=True,
            listener_port=80,
            health_check_grace_period=Duration.seconds(60),
        )

        # Configure health check
        self.fargate_service.target_group.configure_health_check(
            path="/health",
            healthy_http_codes="200",
        )

        # Auto scaling
        scaling = self.fargate_service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=4,
        )

        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )

        # Outputs
        cdk.CfnOutput(
            self,
            "BackendUrl",
            value=f"http://{self.fargate_service.load_balancer.load_balancer_dns_name}",
            description="Backend API URL",
        )
