#!/usr/bin/env python3
"""CDK App entry point for Briefly infrastructure."""

import os
import aws_cdk as cdk

from stacks.database_stack import DatabaseStack
from stacks.backend_stack import BackendStack


app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

# Database stack (RDS + DynamoDB)
db_stack = DatabaseStack(app, "BrieflyDatabaseStack", env=env)

# Backend stack (ECS Fargate)
backend_stack = BackendStack(
    app,
    "BrieflyBackendStack",
    vpc=db_stack.vpc,
    database=db_stack.database,
    dynamodb_table=db_stack.dynamodb_table,
    env=env,
)
backend_stack.add_dependency(db_stack)

app.synth()
