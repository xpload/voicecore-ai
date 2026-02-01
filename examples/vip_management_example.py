"""
VIP Management System Example for VoiceCore AI.

This example demonstrates how to use the VIP caller management system
to identify VIP callers, apply special handling rules, and manage
priority routing for premium customer experience.
"""

import asyncio
import uuid
from datetime import datetime, timedelta

from voicecore.services.vip_service import VIPService
from voicecore.services.call_routing_service import CallRoutingService
from voicecore.models import VIPPriority, VIPStatus, VIPHandlingRule


async def main():
    """Demonstrate VIP management system functionality."""
    
    # Initialize services
    vip_service = VIPService()
    routing_service = CallRoutingService()
    
    # Sample tenant ID
    tenant_id = uuid.uuid4()
    
    print("=== VoiceCore AI VIP Management System Demo ===\n")
    
    # 1. Create VIP callers with different priority levels
    print("1. Creating VIP callers...")
    
    vip_callers = []
    
    # Diamond VIP - Highest priority
    diamond_vip_data = {
        "phone_number": "+1555000001",
        "caller_name": "Sarah Johnson",
        "company_name": "Global Enterprises Inc",
        "vip_level": VIPPriority.DIAMOND.value,
        "status": VIPStatus.ACTIVE.value,
        "handling_rules": [
            VIPHandlingRule.IMMEDIATE_TRANSFER.value,
            VIPHandlingRule.CUSTOM_GREETING.value
        ],
        "custom_greeting": "Good day Ms. Johnson, thank you for calling. I'll connect you immediately.",
        "max_wait_time": 15,  # 15 seconds max wait
        "callback_priority": 1,
        "email": "sarah.johnson@globalent.com",
        "account_number": "VIP001",
        "account_value": 500000.0,
        "notes": "CEO of major client, requires immediate attention",
        "tags": ["ceo", "enterprise", "critical"]
    }
    
    # Platinum VIP - High priority with preferred agent
    platinum_vip_data = {
        "phone_number": "+1555000002",
        "caller_name": "Michael Chen",
        "company_name": "Tech Solutions Ltd",
        "vip_level": VIPPriority.PLATINUM.value,
        "status": VIPStatus.ACTIVE.value,
        "handling_rules": [
            VIPHandlingRule.DEDICATED_AGENT.value,
            VIPHandlingRule.PRIORITY_QUEUE.value
        ],
        "custom_greeting": "Hello Mr. Chen, I'll connect you to your dedicated account manager.",
        "max_wait_time": 30,
        "callback_priority": 1,
        "email": "m.chen@techsolutions.com",
        "account_number": "VIP002",
        "account_value": 250000.0,
        "preferred_agent_id": uuid.uuid4(),  # Would be actual agent ID
        "notes": "Prefers to work with dedicated account manager",
        "tags": ["tech", "dedicated-agent"]
    }
    
    # Gold VIP - Standard VIP treatment
    gold_vip_data = {
        "phone_number": "+1555000003",
        "caller_name": "Emma Rodriguez",
        "company_name": "Marketing Pro Agency",
        "vip_level": VIPPriority.GOLD.value,
        "status": VIPStatus.ACTIVE.value,
        "handling_rules": [VIPHandlingRule.PRIORITY_QUEUE.value],
        "max_wait_time": 60,
        "callback_priority": 2,
        "email": "emma@marketingpro.com",
        "account_number": "VIP003",
        "account_value": 75000.0,
        "notes": "Long-term client, excellent satisfaction scores",
        "tags": ["marketing", "loyal-customer"]
    }
    
    try:
        # Create VIP callers
        diamond_vip = await vip_service.create_vip_caller(tenant_id, diamond_vip_data)
        platinum_vip = await vip_service.create_vip_caller(tenant_id, platinum_vip_data)
        gold_vip = await vip_service.create_vip_caller(tenant_id, gold_vip_data)
        
        vip_callers = [diamond_vip, platinum_vip, gold_vip]
        
        print(f"✓ Created {len(vip_callers)} VIP callers")
        for vip in vip_callers:
            print(f"  - {vip.caller_name} ({vip.vip_level.value} level)")
        
    except Exception as e:
        print(f"✗ Error creating VIP callers: {e}")
        return
    
    print()
    
    # 2. Demonstrate VIP identification
    print("2. Testing VIP caller identification...")
    
    test_numbers = [
        "+1555000001",  # Diamond VIP
        "+1555000002",  # Platinum VIP
        "+1555000999"   # Non-VIP
    ]
    
    for phone_number in test_numbers:
        vip_caller = await vip_service.identify_vip_caller(tenant_id, phone_number)
        if vip_caller:
            priority = await vip_service.get_vip_routing_priority(tenant_id, vip_caller)
            print(f"✓ {phone_number}: VIP {vip_caller.caller_name} ({vip_caller.vip_level.value}) - Priority: {priority}")
        else:
            print(f"○ {phone_number}: Not a VIP caller")
    
    print()
    
    # 3. Demonstrate call routing with VIP priority
    print("3. Simulating VIP call routing...")
    
    # Simulate incoming calls
    calls = [
        {
            "caller_number": "+1555000001",  # Diamond VIP
            "call_id": uuid.uuid4(),
            "description": "Diamond VIP call"
        },
        {
            "caller_number": "+1555000002",  # Platinum VIP
            "call_id": uuid.uuid4(),
            "description": "Platinum VIP call"
        },
        {
            "caller_number": "+1555000999",  # Regular caller
            "call_id": uuid.uuid4(),
            "description": "Regular call"
        }
    ]
    
    for call in calls:
        print(f"\nProcessing: {call['description']}")
        
        # Identify if caller is VIP
        vip_caller = await vip_service.identify_vip_caller(tenant_id, call["caller_number"])
        is_vip = vip_caller is not None
        
        # Route the call
        routing_result = await routing_service.route_call(
            tenant_id=tenant_id,
            call_id=call["call_id"],
            caller_number=call["caller_number"],
            is_vip=is_vip
        )
        
        if routing_result.success:
            print(f"✓ Call routed successfully to agent")
            print(f"  Routing reason: {routing_result.routing_reason}")
        elif routing_result.queue_position:
            print(f"○ Call added to queue (position: {routing_result.queue_position})")
            print(f"  Estimated wait time: {routing_result.estimated_wait_time} seconds")
            print(f"  Routing reason: {routing_result.routing_reason}")
        else:
            print(f"✗ Call routing failed: {routing_result.error_message}")
    
    print()
    
    # 4. Demonstrate escalation rule checking
    print("4. Testing VIP escalation rules...")
    
    # Check escalation for Diamond VIP with long wait time
    diamond_vip = vip_callers[0]  # Diamond VIP
    escalation_rules = await vip_service.check_escalation_rules(
        tenant_id=tenant_id,
        vip_caller=diamond_vip,
        wait_time=120,  # 2 minutes wait
        queue_position=1
    )
    
    if escalation_rules:
        print(f"⚠ Escalation triggered for {diamond_vip.caller_name}:")
        for rule in escalation_rules:
            print(f"  - Rule: {rule.name}")
            print(f"    Type: {rule.escalation_type}")
    else:
        print(f"○ No escalation needed for {diamond_vip.caller_name}")
    
    print()
    
    # 5. Record VIP call history
    print("5. Recording VIP call history...")
    
    call_details = {
        "vip_level": diamond_vip.vip_level,
        "handling_rules_applied": diamond_vip.handling_rules,
        "preferred_agent_available": True,
        "routed_to_preferred": True,
        "wait_time_seconds": 5,
        "escalation_triggered": False,
        "custom_greeting_used": True,
        "satisfaction_rating": 5,
        "service_quality_score": 9.8,
        "issue_resolved": True,
        "resolution_time": 180,
        "caller_feedback": "Excellent service as always!",
        "agent_notes": "Customer inquiry about new features, provided demo"
    }
    
    try:
        call_history = await vip_service.record_vip_call(
            tenant_id=tenant_id,
            vip_caller_id=diamond_vip.id,
            call_id=uuid.uuid4(),
            call_details=call_details
        )
        print(f"✓ Call history recorded for {diamond_vip.caller_name}")
        print(f"  Service quality score: {call_history.service_quality_score}")
        print(f"  Resolution time: {call_history.resolution_time} seconds")
    except Exception as e:
        print(f"✗ Error recording call history: {e}")
    
    print()
    
    # 6. Get VIP analytics
    print("6. Retrieving VIP analytics...")
    
    try:
        analytics = await vip_service.get_vip_analytics(
            tenant_id=tenant_id,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow()
        )
        
        print("✓ VIP Analytics Summary:")
        print(f"  Escalation rate: {analytics.get('escalation_rate', 0):.1f}%")
        print(f"  Average quality score: {analytics.get('avg_quality_score', 'N/A')}")
        
        if 'by_vip_level' in analytics:
            print("  Call volume by VIP level:")
            for level_data in analytics['by_vip_level']:
                print(f"    - {level_data['vip_level']}: {level_data['call_count']} calls")
        
    except Exception as e:
        print(f"✗ Error retrieving analytics: {e}")
    
    print()
    
    # 7. List and manage VIP callers
    print("7. Managing VIP callers...")
    
    # List all VIP callers
    vip_list = await vip_service.list_vip_callers(
        tenant_id=tenant_id,
        limit=10
    )
    
    print(f"✓ Found {len(vip_list)} VIP callers:")
    for vip in vip_list:
        print(f"  - {vip.caller_name} ({vip.vip_level.value}) - {vip.total_calls} calls")
    
    # Update a VIP caller
    update_data = {
        "notes": "Updated notes - customer requested priority support",
        "tags": ["priority", "enterprise", "updated"]
    }
    
    try:
        updated_vip = await vip_service.update_vip_caller(
            tenant_id=tenant_id,
            vip_id=gold_vip.id,
            update_data=update_data
        )
        print(f"✓ Updated VIP caller: {updated_vip.caller_name}")
    except Exception as e:
        print(f"✗ Error updating VIP caller: {e}")
    
    print()
    
    # 8. Demonstrate bulk import
    print("8. Testing bulk VIP import...")
    
    bulk_vip_data = [
        {
            "phone_number": f"+155500000{i}",
            "caller_name": f"Bulk VIP {i}",
            "company_name": f"Company {i}",
            "vip_level": VIPPriority.SILVER.value,
            "status": VIPStatus.ACTIVE.value,
            "handling_rules": [VIPHandlingRule.PRIORITY_QUEUE.value],
            "account_value": 25000.0 + (i * 5000),
            "tags": ["bulk-import", "silver"]
        }
        for i in range(4, 7)  # Create 3 more VIPs
    ]
    
    try:
        import_results = await vip_service.bulk_import_vips(tenant_id, bulk_vip_data)
        print(f"✓ Bulk import completed:")
        print(f"  Total: {import_results['total']}")
        print(f"  Successful: {import_results['successful']}")
        print(f"  Failed: {import_results['failed']}")
        
        if import_results['errors']:
            print("  Errors:")
            for error in import_results['errors']:
                print(f"    - Row {error['row']}: {error['error']}")
    
    except Exception as e:
        print(f"✗ Error in bulk import: {e}")
    
    print("\n=== VIP Management System Demo Complete ===")
    print("\nKey Features Demonstrated:")
    print("• VIP caller identification and priority calculation")
    print("• Special handling rules (immediate transfer, dedicated agent, priority queue)")
    print("• Custom greetings and personalized service")
    print("• Escalation rule checking and management")
    print("• Call history recording and analytics")
    print("• Bulk import and management operations")
    print("• Integration with call routing system")


if __name__ == "__main__":
    # Note: This example requires a running database and proper configuration
    # In a real environment, you would have proper database setup and configuration
    print("VIP Management System Example")
    print("Note: This example requires proper database setup and configuration")
    print("Run with: python examples/vip_management_example.py")
    
    # Uncomment the following line to run the demo (requires database setup)
    # asyncio.run(main())