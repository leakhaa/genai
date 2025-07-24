#!/usr/bin/env python3
"""Command-line interface for the Warehouse AI Agent."""

import asyncio
import click
import json
from datetime import datetime
from typing import Optional

from app.models import UserIssueRequest
from app.services.warehouse_agent import warehouse_agent
from app.services.ai_classifier import ai_classifier
from app.services.database_service import database_service
from app.services.email_service import email_service


@click.group()
def cli():
    """Warehouse AI Agent CLI - Intelligent warehouse issue resolution."""
    pass


@cli.command()
@click.option('--message', '-m', required=True, help='Issue description')
@click.option('--email', '-e', required=True, help='User email address')
@click.option('--wait', '-w', is_flag=True, help='Wait for resolution completion')
def submit(message: str, email: str, wait: bool):
    """Submit a new warehouse issue for processing."""
    async def _submit():
        try:
            click.echo(f"🚀 Submitting issue: {message}")
            
            user_request = UserIssueRequest(
                message=message,
                user_email=email
            )
            
            resolution = await warehouse_agent.process_user_issue(user_request)
            
            click.echo(f"✅ Issue submitted successfully!")
            click.echo(f"Issue ID: {resolution.issue_id}")
            click.echo(f"Status: {resolution.status.value}")
            click.echo(f"Classification: {resolution.classified_issue.issue_type.value}")
            click.echo(f"Action: {resolution.classified_issue.action.value}")
            
            if wait:
                click.echo("⏳ Waiting for resolution...")
                while resolution.status.value not in ['RESOLVED', 'FAILED']:
                    await asyncio.sleep(5)
                    resolution = await warehouse_agent.get_resolution_status(resolution.issue_id)
                    if not resolution:
                        click.echo("❌ Issue not found")
                        return
                
                click.echo(f"🏁 Final Status: {resolution.status.value}")
                if resolution.resolution_summary:
                    click.echo(f"Summary: {resolution.resolution_summary}")
                    
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_submit())


@cli.command()
@click.argument('issue_id')
def status(issue_id: str):
    """Check the status of an issue."""
    async def _status():
        try:
            resolution = await warehouse_agent.get_resolution_status(issue_id)
            
            if not resolution:
                click.echo(f"❌ Issue {issue_id} not found")
                return
            
            click.echo(f"📊 Issue Status: {issue_id}")
            click.echo(f"Status: {resolution.status.value}")
            click.echo(f"Type: {resolution.classified_issue.issue_type.value}")
            click.echo(f"Created: {resolution.created_at}")
            click.echo(f"Updated: {resolution.updated_at}")
            
            if resolution.resolution_summary:
                click.echo(f"Summary: {resolution.resolution_summary}")
            
            if resolution.actions_taken:
                click.echo("\nActions Taken:")
                for action in resolution.actions_taken:
                    click.echo(f"  • {action}")
                    
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_status())


@cli.command()
@click.option('--status-filter', '-s', help='Filter by status')
@click.option('--limit', '-l', default=10, help='Number of issues to show')
def list(status_filter: Optional[str], limit: int):
    """List active issues."""
    async def _list():
        try:
            resolutions = await warehouse_agent.list_active_resolutions()
            
            if status_filter:
                resolutions = {
                    k: v for k, v in resolutions.items()
                    if v.status.value.lower() == status_filter.lower()
                }
            
            if not resolutions:
                click.echo("📭 No active issues found")
                return
            
            click.echo(f"📋 Active Issues ({len(resolutions)} total):")
            click.echo("-" * 80)
            
            for i, (issue_id, resolution) in enumerate(list(resolutions.items())[:limit]):
                click.echo(f"{i+1}. {issue_id}")
                click.echo(f"   Status: {resolution.status.value}")
                click.echo(f"   Type: {resolution.classified_issue.issue_type.value}")
                click.echo(f"   User: {resolution.original_request.user_email}")
                click.echo(f"   Created: {resolution.created_at}")
                click.echo()
                
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_list())


@cli.command()
@click.argument('message')
def classify(message: str):
    """Classify an issue without processing it."""
    async def _classify():
        try:
            click.echo(f"🧠 Classifying: {message}")
            
            classified_issue = await ai_classifier.classify_issue(message)
            
            click.echo("\n🎯 Classification Results:")
            click.echo(f"Issue Type: {classified_issue.issue_type.value}")
            click.echo(f"Action: {classified_issue.action.value}")
            click.echo(f"Confidence: {classified_issue.confidence_score:.2%}")
            click.echo(f"PO ID: {classified_issue.po_id or 'Not detected'}")
            click.echo(f"ASN ID: {classified_issue.asn_id or 'Not detected'}")
            click.echo(f"Pallet ID: {classified_issue.pallet_id or 'Not detected'}")
            click.echo(f"Requires Excel: {classified_issue.requires_excel}")
            
            if classified_issue.extracted_entities:
                click.echo("\nExtracted Entities:")
                for key, value in classified_issue.extracted_entities.items():
                    click.echo(f"  {key}: {value}")
                    
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_classify())


@cli.command()
@click.argument('po_id')
def po_info(po_id: str):
    """Get information about a specific PO."""
    async def _po_info():
        try:
            click.echo(f"📦 Getting info for PO: {po_id}")
            
            po_summary = await database_service.get_po_summary(po_id)
            pallets = await database_service.get_pallets_by_po(po_id)
            
            click.echo(f"\n📊 PO Summary:")
            click.echo(f"Total Pallets: {po_summary['pallet_count']}")
            click.echo(f"Total Quantity: {po_summary['total_quantity']}")
            click.echo(f"ASN Count: {po_summary['asn_count']}")
            
            if pallets:
                click.echo(f"\n📋 Pallets ({len(pallets)} total):")
                click.echo("-" * 60)
                for pallet in pallets[:10]:  # Show first 10
                    click.echo(f"• {pallet.pallet_id}: Qty={pallet.quantity}, Status={pallet.status}")
                    if pallet.location:
                        click.echo(f"  Location: {pallet.location}")
                
                if len(pallets) > 10:
                    click.echo(f"... and {len(pallets) - 10} more pallets")
            else:
                click.echo("\n📭 No pallets found for this PO")
                
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_po_info())


@cli.command()
def health():
    """Check system health."""
    async def _health():
        try:
            health_status = await warehouse_agent.health_check()
            
            click.echo("🏥 System Health Check:")
            click.echo(f"Warehouse Agent: {health_status.get('warehouse_agent', 'unknown')}")
            click.echo(f"Database: {'✅ Healthy' if health_status.get('database') else '❌ Unhealthy'}")
            click.echo(f"Active Resolutions: {health_status.get('active_resolutions', 0)}")
            click.echo(f"Timestamp: {health_status.get('timestamp', 'unknown')}")
            
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_health())


@cli.command()
@click.option('--max-age', '-a', default=24, help='Maximum age in hours')
def cleanup(max_age: int):
    """Clean up old resources."""
    async def _cleanup():
        try:
            click.echo(f"🧹 Cleaning up resources older than {max_age} hours...")
            
            # Clean up completed resolutions
            await warehouse_agent.cleanup_completed_resolutions(max_age)
            
            # Clean up temp files
            from app.services.excel_validator import excel_validator
            from app.services.screenshot_service import screenshot_service
            
            excel_validator.cleanup_temp_files(max_age)
            screenshot_service.cleanup_old_screenshots(max_age * 2)
            
            click.echo("✅ Cleanup completed!")
            
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_cleanup())


@cli.command()
def stats():
    """Show system statistics."""
    async def _stats():
        try:
            resolutions = await warehouse_agent.list_active_resolutions()
            
            # Calculate statistics
            total_issues = len(resolutions)
            status_counts = {}
            type_counts = {}
            
            for resolution in resolutions.values():
                status = resolution.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
                issue_type = resolution.classified_issue.issue_type.value
                type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
            
            click.echo("📈 System Statistics:")
            click.echo(f"Total Active Issues: {total_issues}")
            
            if status_counts:
                click.echo("\nStatus Breakdown:")
                for status, count in status_counts.items():
                    click.echo(f"  {status}: {count}")
            
            if type_counts:
                click.echo("\nIssue Type Breakdown:")
                for issue_type, count in type_counts.items():
                    click.echo(f"  {issue_type}: {count}")
                    
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_stats())


@cli.command()
@click.option('--host', '-h', default='0.0.0.0', help='Host to bind to')
@click.option('--port', '-p', default=8000, help='Port to bind to')
@click.option('--reload', '-r', is_flag=True, help='Enable auto-reload')
def serve(host: str, port: int, reload: bool):
    """Start the web server."""
    import uvicorn
    from app.config import settings
    
    click.echo(f"🚀 Starting Warehouse AI Agent server on {host}:{port}")
    click.echo(f"Debug mode: {settings.debug}")
    click.echo(f"Using Ollama: {settings.use_ollama}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload or settings.debug,
        log_level=settings.log_level.lower()
    )


@cli.command()
@click.option('--issue-type', '-t', required=True, 
              type=click.Choice(['ASN_MISSING', 'PO_MISSING', 'PALLET_MISSING', 'QUANTITY_MISMATCH']),
              help='Type of issue to test')
@click.option('--po-id', help='PO ID for testing')
@click.option('--asn-id', help='ASN ID for testing')
def test_email(issue_type: str, po_id: Optional[str], asn_id: Optional[str]):
    """Test SAP email functionality."""
    async def _test_email():
        try:
            from app.models import IssueType
            
            click.echo(f"📧 Testing SAP email for {issue_type}")
            
            issue_type_enum = IssueType(issue_type)
            success = await email_service.send_sap_request(
                issue_type=issue_type_enum,
                po_id=po_id,
                asn_id=asn_id
            )
            
            if success:
                click.echo("✅ SAP email sent successfully!")
            else:
                click.echo("❌ Failed to send SAP email")
                
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
    
    asyncio.run(_test_email())


if __name__ == '__main__':
    cli()