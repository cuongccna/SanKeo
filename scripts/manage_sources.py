import asyncio
import sys
import os
import argparse
from sqlalchemy import select, delete
from tabulate import tabulate

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import AsyncSessionLocal
from src.database.models import SourceConfig, SourceTag

async def list_sources():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SourceConfig))
        sources = result.scalars().all()
        
        data = []
        for s in sources:
            data.append([s.chat_id, s.name, s.tag, s.priority])
            
        print(tabulate(data, headers=["Chat ID", "Name", "Tag", "Priority"], tablefmt="grid"))

async def add_source(chat_id, name, tag, priority):
    async with AsyncSessionLocal() as session:
        # Check if exists
        result = await session.execute(select(SourceConfig).where(SourceConfig.chat_id == chat_id))
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"⚠️ Source {chat_id} already exists. Updating...")
            existing.name = name
            existing.tag = tag
            existing.priority = priority
        else:
            new_source = SourceConfig(chat_id=chat_id, name=name, tag=tag, priority=priority)
            session.add(new_source)
            
        await session.commit()
        print(f"✅ Source {name} ({chat_id}) saved with tag {tag}.")

async def remove_source(chat_id):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(SourceConfig).where(SourceConfig.chat_id == chat_id))
        await session.commit()
        print(f"🗑️ Source {chat_id} removed.")

def main():
    parser = argparse.ArgumentParser(description="Manage Source Configs for SanKeo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    subparsers.add_parser("list", help="List all configured sources")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add or update a source")
    add_parser.add_argument("chat_id", type=int, help="Telegram Chat ID (e.g., -100123456)")
    add_parser.add_argument("name", type=str, help="Name of the source")
    add_parser.add_argument("tag", type=str, choices=[t.value for t in SourceTag], help="Tag type")
    add_parser.add_argument("--priority", type=int, default=1, help="Priority (1-10)")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a source")
    remove_parser.add_argument("chat_id", type=int, help="Telegram Chat ID to remove")

    args = parser.parse_args()

    if args.command == "list":
        asyncio.run(list_sources())
    elif args.command == "add":
        asyncio.run(add_source(args.chat_id, args.name, args.tag, args.priority))
    elif args.command == "remove":
        asyncio.run(remove_source(args.chat_id))

if __name__ == "__main__":
    main()
