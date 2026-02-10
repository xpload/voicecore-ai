"""
Interactive Call Demo
Simulates real call scenarios with AI interaction
"""

import asyncio
import uuid
from datetime import datetime
from colorama import init, Fore, Back, Style
import sys

# Initialize colorama for colored output
init(autoreset=True)

class CallSimulator:
    """Simulates realistic call scenarios"""
    
    def __init__(self):
        self.call_id = None
        self.tenant_id = uuid.uuid4()
        self.conversation_history = []
    
    def print_header(self, text):
        """Print formatted header"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{text.center(80)}")
        print(f"{Fore.CYAN}{'='*80}\n")
    
    def print_customer(self, text):
        """Print customer message"""
        print(f"{Fore.GREEN}👤 Customer: {Style.RESET_ALL}{text}")
    
    def print_ai(self, text):
        """Print AI response"""
        print(f"{Fore.BLUE}🤖 AI: {Style.RESET_ALL}{text}")
    
    def print_agent(self, name, text):
        """Print agent message"""
        print(f"{Fore.YELLOW}👨‍💼 {name}: {Style.RESET_ALL}{text}")
    
    def print_system(self, text):
        """Print system message"""
        print(f"{Fore.MAGENTA}⚙️  System: {Style.RESET_ALL}{text}")
    
    def print_event(self, text):
        """Print event"""
        print(f"{Fore.WHITE}📋 Event: {Style.RESET_ALL}{text}")
    
    async def simulate_typing(self, duration=1.0):
        """Simulate typing delay"""
        await asyncio.sleep(duration)
    
    async def scenario_1_simple_inquiry(self):
        """Scenario 1: Simple business hours inquiry"""
        self.print_header("SCENARIO 1: Simple Business Hours Inquiry")
        
        self.call_id = uuid.uuid4()
        caller = "+1-555-0123"
        business = "+1-800-COMPANY"
        
        # Call initiated
        self.print_system(f"Incoming call from {caller} to {business}")
        self.print_event("CallInitiated")
        await self.simulate_typing(0.5)
        
        # AI answers
        self.print_system("Routing to AI Assistant")
        self.print_event("CallConnected")
        await self.simulate_typing(1.0)
        
        self.print_ai("Hello! Thank you for calling TechCorp. My name is Alex, your AI assistant. How can I help you today?")
        await self.simulate_typing(2.0)
        
        # Customer asks question
        self.print_customer("Hi, what are your business hours?")
        await self.simulate_typing(1.5)
        
        # AI responds
        self.print_ai("We're open Monday through Friday, 9 AM to 6 PM Eastern Time. We're closed on weekends and major holidays. Is there anything else I can help you with?")
        await self.simulate_typing(2.0)
        
        # Customer satisfied
        self.print_customer("That's all I needed, thank you!")
        await self.simulate_typing(1.0)
        
        self.print_ai("You're welcome! Have a great day!")
        await self.simulate_typing(0.5)
        
        # Call ends
        self.print_system("Call ending")
        self.print_event("CallEnded")
        
        # Summary
        print(f"\n{Fore.CYAN}📊 Call Summary:")
        print(f"   Duration: 45 seconds")
        print(f"   Handled by: AI")
        print(f"   Resolution: Successful")
        print(f"   Customer Satisfaction: ⭐⭐⭐⭐⭐")
    
    async def scenario_2_escalation(self):
        """Scenario 2: Complex issue requiring escalation"""
        self.print_header("SCENARIO 2: Complex Issue - Escalation to Human")
        
        self.call_id = uuid.uuid4()
        caller = "+1-555-0456"
        
        # Call initiated
        self.print_system(f"Incoming call from {caller}")
        self.print_event("CallInitiated")
        await self.simulate_typing(0.5)
        
        # AI answers
        self.print_system("Routing to AI Assistant")
        self.print_event("CallConnected")
        await self.simulate_typing(1.0)
        
        self.print_ai("Hello! Thank you for calling TechCorp. How may I assist you today?")
        await self.simulate_typing(2.0)
        
        # Customer has complex issue
        self.print_customer("I need to modify my enterprise contract. We want to add custom SLA terms and integrate with our existing infrastructure.")
        await self.simulate_typing(2.0)
        
        # AI recognizes complexity
        self.print_system("AI analyzing request...")
        self.print_system("Complexity detected: HIGH")
        self.print_system("Confidence: 0.65 (below threshold)")
        await self.simulate_typing(1.0)
        
        self.print_ai("I understand you need to modify your enterprise contract with custom SLA terms. This is an important request that requires specialized attention. Let me connect you with one of our enterprise specialists who can help you with this right away.")
        await self.simulate_typing(2.0)
        
        # Transfer initiated
        self.print_system("Initiating transfer to Enterprise Team")
        self.print_event("AIEscalationTriggered - Reason: complex_contract_inquiry")
        await self.simulate_typing(1.0)
        
        # Finding agent
        self.print_system("Finding available enterprise specialist...")
        await self.simulate_typing(1.5)
        
        self.print_system("Agent found: Sarah Johnson (Enterprise Specialist)")
        self.print_event("AgentAssignedToCall")
        await self.simulate_typing(0.5)
        
        # Transfer complete
        self.print_system("Transferring call...")
        self.print_event("CallTransferred")
        await self.simulate_typing(1.0)
        
        # Agent takes over
        self.print_agent("Sarah Johnson", "Hi! This is Sarah from our Enterprise team. I understand you need to modify your contract with custom SLA terms. I'd be happy to help you with that.")
        await self.simulate_typing(2.0)
        
        self.print_customer("Yes, exactly. We need 99.99% uptime guarantee and custom support response times.")
        await self.simulate_typing(2.0)
        
        self.print_agent("Sarah Johnson", "Absolutely, we can definitely accommodate that. Let me pull up your account and we'll go through the options together...")
        await self.simulate_typing(2.0)
        
        # Conversation continues
        self.print_system("Call in progress...")
        await self.simulate_typing(1.0)
        
        # Call ends
        self.print_system("Call ending")
        self.print_event("CallEnded")
        
        # Summary
        print(f"\n{Fore.CYAN}📊 Call Summary:")
        print(f"   Duration: 8 minutes 32 seconds")
        print(f"   Started with: AI")
        print(f"   Escalated to: Sarah Johnson (Enterprise Specialist)")
        print(f"   Escalation reason: Complex contract inquiry")
        print(f"   Resolution: In progress - Follow-up scheduled")
        print(f"   Customer Satisfaction: ⭐⭐⭐⭐⭐")
    
    async def scenario_3_frustrated_customer(self):
        """Scenario 3: Frustrated customer - sentiment detection"""
        self.print_header("SCENARIO 3: Frustrated Customer - Sentiment Detection")
        
        self.call_id = uuid.uuid4()
        caller = "+1-555-0789"
        
        # Call initiated
        self.print_system(f"Incoming call from {caller}")
        self.print_event("CallInitiated")
        await self.simulate_typing(0.5)
        
        # AI answers
        self.print_system("Routing to AI Assistant")
        self.print_event("CallConnected")
        await self.simulate_typing(1.0)
        
        self.print_ai("Hello! Thank you for calling TechCorp. How can I help you today?")
        await self.simulate_typing(2.0)
        
        # Frustrated customer
        self.print_customer("I've been trying to reach someone for THREE DAYS! Nobody has called me back and my service is still not working!")
        await self.simulate_typing(2.0)
        
        # AI detects negative sentiment
        self.print_system("AI analyzing sentiment...")
        self.print_system(f"{Fore.RED}⚠️  ALERT: Negative sentiment detected")
        self.print_system("Sentiment score: -0.85 (Very Negative)")
        self.print_system("Emotion: Frustration, Anger")
        await self.simulate_typing(1.0)
        
        self.print_ai("I sincerely apologize for the delay and the frustration this has caused you. This is absolutely not the level of service we strive for. Let me connect you with a supervisor right away who can help resolve this immediately.")
        await self.simulate_typing(2.0)
        
        # Immediate escalation
        self.print_system("PRIORITY ESCALATION INITIATED")
        self.print_event("AIEscalationTriggered - Reason: negative_sentiment")
        self.print_system("Urgency: HIGH")
        await self.simulate_typing(1.0)
        
        # Finding supervisor
        self.print_system("Finding available supervisor...")
        await self.simulate_typing(1.0)
        
        self.print_system("Supervisor found: Michael Chen (Customer Success Manager)")
        self.print_event("AgentAssignedToCall")
        await self.simulate_typing(0.5)
        
        # Transfer
        self.print_system("Transferring to supervisor...")
        self.print_event("CallTransferred")
        await self.simulate_typing(1.0)
        
        # Supervisor takes over
        self.print_agent("Michael Chen", "Hello, this is Michael Chen, Customer Success Manager. I'm very sorry for the issues you've experienced. I'm looking at your account right now and I'm going to personally make sure we get this resolved for you today.")
        await self.simulate_typing(2.5)
        
        self.print_customer("Thank you, I really appreciate that.")
        await self.simulate_typing(1.5)
        
        self.print_agent("Michael Chen", "I can see the issue here. Let me fix this right now...")
        await self.simulate_typing(2.0)
        
        # Issue resolved
        self.print_system("Issue resolved")
        await self.simulate_typing(1.0)
        
        self.print_agent("Michael Chen", "All set! Your service is now fully operational. I've also added a credit to your account for the inconvenience. Is there anything else I can help you with?")
        await self.simulate_typing(2.0)
        
        self.print_customer("No, that's perfect. Thank you so much for your help!")
        await self.simulate_typing(1.0)
        
        # Call ends
        self.print_system("Call ending")
        self.print_event("CallEnded")
        
        # Summary
        print(f"\n{Fore.CYAN}📊 Call Summary:")
        print(f"   Duration: 6 minutes 15 seconds")
        print(f"   Initial sentiment: Very Negative (-0.85)")
        print(f"   Final sentiment: Positive (+0.75)")
        print(f"   Handled by: AI → Michael Chen (Supervisor)")
        print(f"   Escalation: Immediate (negative sentiment)")
        print(f"   Resolution: Successful + Account credit")
        print(f"   Customer Satisfaction: ⭐⭐⭐⭐ (recovered)")
    
    async def scenario_4_multilingual(self):
        """Scenario 4: Multilingual support"""
        self.print_header("SCENARIO 4: Multilingual Support")
        
        self.call_id = uuid.uuid4()
        caller = "+52-555-1234"
        
        # Call initiated
        self.print_system(f"Incoming call from {caller} (Mexico)")
        self.print_event("CallInitiated")
        await self.simulate_typing(0.5)
        
        # AI answers in English
        self.print_system("Routing to AI Assistant")
        self.print_event("CallConnected")
        await self.simulate_typing(1.0)
        
        self.print_ai("Hello! Thank you for calling TechCorp. How can I help you today?")
        await self.simulate_typing(2.0)
        
        # Customer responds in Spanish
        self.print_customer("Hola, ¿habla español?")
        await self.simulate_typing(1.5)
        
        # AI detects language and switches
        self.print_system("Language detected: Spanish")
        self.print_system("Switching to Spanish mode")
        await self.simulate_typing(1.0)
        
        self.print_ai("¡Por supuesto! ¿En qué puedo ayudarle hoy?")
        self.print_system("(Translation: Of course! How can I help you today?)")
        await self.simulate_typing(2.0)
        
        self.print_customer("Necesito información sobre sus planes empresariales.")
        self.print_system("(Translation: I need information about your business plans.)")
        await self.simulate_typing(2.0)
        
        self.print_ai("Con gusto. Tenemos varios planes empresariales. ¿Cuántos empleados tiene su empresa?")
        self.print_system("(Translation: Gladly. We have several business plans. How many employees does your company have?)")
        await self.simulate_typing(2.0)
        
        self.print_customer("Somos aproximadamente 50 personas.")
        self.print_system("(Translation: We are approximately 50 people.)")
        await self.simulate_typing(1.5)
        
        self.print_ai("Perfecto. Para una empresa de 50 empleados, recomiendo nuestro plan Professional. Incluye...")
        self.print_system("(Translation: Perfect. For a company of 50 employees, I recommend our Professional plan. It includes...)")
        await self.simulate_typing(2.0)
        
        # Conversation continues
        self.print_system("Conversation continues in Spanish...")
        await self.simulate_typing(1.0)
        
        # Call ends
        self.print_system("Call ending")
        self.print_event("CallEnded")
        
        # Summary
        print(f"\n{Fore.CYAN}📊 Call Summary:")
        print(f"   Duration: 4 minutes 20 seconds")
        print(f"   Language: Spanish")
        print(f"   Handled by: AI (Multilingual)")
        print(f"   Resolution: Information provided")
        print(f"   Customer Satisfaction: ⭐⭐⭐⭐⭐")
    
    async def scenario_5_vip_customer(self):
        """Scenario 5: VIP customer priority routing"""
        self.print_header("SCENARIO 5: VIP Customer - Priority Routing")
        
        self.call_id = uuid.uuid4()
        caller = "+1-555-VIP1"
        
        # Call initiated
        self.print_system(f"Incoming call from {caller}")
        await self.simulate_typing(0.5)
        
        # VIP detected
        self.print_system(f"{Fore.YELLOW}⭐ VIP CUSTOMER DETECTED")
        self.print_system("Customer: John Smith - Enterprise Account")
        self.print_system("VIP Level: Platinum")
        self.print_system("Account Value: $50,000/month")
        self.print_event("CallInitiated")
        self.print_event("VIPCallPrioritized")
        await self.simulate_typing(1.0)
        
        # Priority routing
        self.print_system("Activating VIP routing protocol...")
        self.print_system("Bypassing queue")
        self.print_system("Finding dedicated VIP agent...")
        await self.simulate_typing(1.5)
        
        self.print_system("VIP Agent found: Jennifer Martinez (Senior Account Manager)")
        self.print_event("VIPAgentAssigned")
        await self.simulate_typing(0.5)
        
        # Direct to agent (no AI)
        self.print_system("Connecting directly to agent...")
        self.print_event("CallConnected")
        await self.simulate_typing(1.0)
        
        # Agent answers
        self.print_agent("Jennifer Martinez", "Good afternoon, Mr. Smith! This is Jennifer, your dedicated account manager. How can I help you today?")
        await self.simulate_typing(2.0)
        
        self.print_customer("Hi Jennifer! I wanted to discuss expanding our service to our new office in Chicago.")
        await self.simulate_typing(2.0)
        
        self.print_agent("Jennifer Martinez", "Excellent! Congratulations on the expansion. I actually have your account details right here. Let's talk about what you'll need for the Chicago office...")
        await self.simulate_typing(2.0)
        
        # Conversation continues
        self.print_system("Detailed consultation in progress...")
        await self.simulate_typing(1.0)
        
        # Call ends
        self.print_system("Call ending")
        self.print_event("CallEnded")
        
        # Summary
        print(f"\n{Fore.CYAN}📊 Call Summary:")
        print(f"   Duration: 12 minutes 45 seconds")
        print(f"   Customer Type: VIP Platinum")
        print(f"   Queue time: 0 seconds (bypassed)")
        print(f"   Handled by: Jennifer Martinez (Dedicated Account Manager)")
        print(f"   Resolution: Expansion plan created")
        print(f"   Customer Satisfaction: ⭐⭐⭐⭐⭐")
    
    async def run_all_scenarios(self):
        """Run all scenarios"""
        scenarios = [
            ("Simple Inquiry", self.scenario_1_simple_inquiry),
            ("Complex Escalation", self.scenario_2_escalation),
            ("Frustrated Customer", self.scenario_3_frustrated_customer),
            ("Multilingual Support", self.scenario_4_multilingual),
            ("VIP Customer", self.scenario_5_vip_customer)
        ]
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}╔{'═'*78}╗")
        print(f"{Fore.CYAN}{Style.BRIGHT}║{'VoiceCore AI - Interactive Call Demonstration'.center(78)}║")
        print(f"{Fore.CYAN}{Style.BRIGHT}╚{'═'*78}╝")
        
        print(f"\n{Fore.WHITE}Available Scenarios:")
        for i, (name, _) in enumerate(scenarios, 1):
            print(f"  {i}. {name}")
        print(f"  {len(scenarios) + 1}. Run All Scenarios")
        print(f"  0. Exit")
        
        choice = input(f"\n{Fore.YELLOW}Select scenario (0-{len(scenarios) + 1}): {Style.RESET_ALL}")
        
        try:
            choice = int(choice)
            if choice == 0:
                print(f"\n{Fore.CYAN}Goodbye!")
                return
            elif choice == len(scenarios) + 1:
                for name, scenario in scenarios:
                    await scenario()
                    await asyncio.sleep(2)
            elif 1 <= choice <= len(scenarios):
                await scenarios[choice - 1][1]()
            else:
                print(f"{Fore.RED}Invalid choice!")
        except ValueError:
            print(f"{Fore.RED}Invalid input!")
        except KeyboardInterrupt:
            print(f"\n\n{Fore.CYAN}Demo interrupted. Goodbye!")


async def main():
    """Main entry point"""
    simulator = CallSimulator()
    await simulator.run_all_scenarios()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Fore.CYAN}Demo terminated. Goodbye!")
        sys.exit(0)
