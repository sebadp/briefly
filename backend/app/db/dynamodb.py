"""DynamoDB connection and table management for articles."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import aioboto3
from botocore.config import Config

from app.config import get_settings


class DynamoDBClient:
    """Async DynamoDB client for article storage."""

    TABLE_NAME = "briefly-articles"

    def __init__(self):
        self.settings = get_settings()
        self.session = aioboto3.Session(
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.aws_region,
        )
        self.config = Config(retries={"max_attempts": 3, "mode": "adaptive"})

    async def get_client(self):
        """Get DynamoDB client context manager."""
        kwargs = {"config": self.config}
        if self.settings.dynamodb_endpoint_url:
            kwargs["endpoint_url"] = self.settings.dynamodb_endpoint_url
        return self.session.client("dynamodb", **kwargs)

    async def create_table_if_not_exists(self) -> None:
        """Create the articles table if it doesn't exist."""
        async with await self.get_client() as client:
            try:
                await client.describe_table(TableName=self.TABLE_NAME)
            except client.exceptions.ResourceNotFoundException:
                await client.create_table(
                    TableName=self.TABLE_NAME,
                    KeySchema=[
                        {"AttributeName": "pk", "KeyType": "HASH"},  # Partition key
                        {"AttributeName": "sk", "KeyType": "RANGE"},  # Sort key
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "pk", "AttributeType": "S"},
                        {"AttributeName": "sk", "AttributeType": "S"},
                    ],
                    BillingMode="PAY_PER_REQUEST",
                )
                # Wait for table to be active
                waiter = client.get_waiter("table_exists")
                await waiter.wait(TableName=self.TABLE_NAME)

    async def put_article(
        self,
        feed_id: UUID,
        article_id: str,
        title: str,
        summary: str,
        url: str,
        source_url: str,
        source_name: str,
        published_at: datetime | None = None,
        thumbnail_url: str | None = None,
    ) -> dict[str, Any]:
        """Store an article in DynamoDB."""
        now = datetime.now(UTC)

        # DynamoDB item
        item = {
            "pk": {"S": f"FEED#{feed_id}"},
            "sk": {"S": f"ARTICLE#{now.isoformat()}#{article_id}"},
            "article_id": {"S": article_id},
            "title": {"S": title},
            "summary": {"S": summary},
            "url": {"S": url},
            "source_url": {"S": source_url},
            "source_name": {"S": source_name},
            "scraped_at": {"S": now.isoformat()},
            # TTL: 30 days from now
            "ttl": {"N": str(int(now.timestamp()) + 30 * 24 * 60 * 60)},
        }

        if published_at:
            item["published_at"] = {"S": published_at.isoformat()}
        if thumbnail_url:
            item["thumbnail_url"] = {"S": thumbnail_url}

        async with await self.get_client() as client:
            await client.put_item(TableName=self.TABLE_NAME, Item=item)

        return {"article_id": article_id, "status": "created"}

    async def get_articles_by_feed(
        self,
        feed_id: UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get articles for a feed, sorted by most recent."""
        async with await self.get_client() as client:
            response = await client.query(
                TableName=self.TABLE_NAME,
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": {"S": f"FEED#{feed_id}"}},
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit,
            )

        articles = []
        for item in response.get("Items", []):
            articles.append(
                {
                    "id": item.get("article_id", {}).get("S"),
                    "title": item.get("title", {}).get("S"),
                    "summary": item.get("summary", {}).get("S"),
                    "url": item.get("url", {}).get("S"),
                    "source_url": item.get("source_url", {}).get("S"),
                    "source_name": item.get("source_name", {}).get("S"),
                    "published_at": item.get("published_at", {}).get("S"),
                    "scraped_at": item.get("scraped_at", {}).get("S"),
                    "thumbnail_url": item.get("thumbnail_url", {}).get("S"),
                }
            )

        return articles


# Singleton instance
dynamodb = DynamoDBClient()
