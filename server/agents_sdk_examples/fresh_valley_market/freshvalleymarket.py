#!/usr/bin/env python3
"""
Fresh Valley Market Customer Service AI Agent

A comprehensive customer service agent for Fresh Valley Market grocery store
that can handle inquiries about store hours, location, services, and transfer
calls to human operators when needed.
"""

import os
from datetime import datetime
from signalwire_agents import AgentBase, SwaigFunctionResult

class FreshValleyMarketAgent(AgentBase):
    def __init__(self):
        super().__init__(
            name="Fresh Valley Market Customer Service",
            auto_answer=True,
            record_call=True,  # Enable if you want to record calls
            port=int(os.environ.get('PORT', 5000))
        )
        
        # Store information
        self.store_info = {
            "name": "Fresh Valley Market",
            "address": "1234 Maple Street, Springfield, IL 62701",
            "phone": "(555) 555-FRESH",
            "email": "info@freshvalleymarket.com",
            "website": "www.freshvalleymarket.com",
            "established": "1994",
            "years_in_business": "over 30 years",
            "hours": {
                "monday": "6:00 AM - 10:00 PM",
                "tuesday": "6:00 AM - 10:00 PM", 
                "wednesday": "6:00 AM - 10:00 PM",
                "thursday": "6:00 AM - 10:00 PM",
                "friday": "6:00 AM - 11:00 PM",
                "saturday": "6:00 AM - 11:00 PM",
                "sunday": "7:00 AM - 9:00 PM"
            },
            "holiday_hours": {
                "new_years_day": "8:00 AM - 8:00 PM",
                "memorial_day": "7:00 AM - 9:00 PM",
                "independence_day": "7:00 AM - 9:00 PM",
                "labor_day": "7:00 AM - 9:00 PM",
                "thanksgiving": "CLOSED",
                "christmas_eve": "6:00 AM - 6:00 PM",
                "christmas": "CLOSED",
                "new_years_eve": "6:00 AM - 8:00 PM"
            },
            "departments": {
                "produce": "Fresh, locally sourced fruits and vegetables, organic options, pre-cut items",
                "meat_seafood": "Premium cuts, fresh seafood daily, custom cuts, marinated options",
                "deli": "Freshly sliced meats and cheeses, prepared foods, rotisserie chicken, catering",
                "bakery": "Fresh bread daily, pastries, custom cakes, gluten-free options",
                "dairy": "Farm-fresh milk and eggs, artisan cheeses, local partnerships",
                "frozen": "Quality frozen meals, ice cream, vegetables, specialty items",
                "pharmacy": "Full-service pharmacy, prescriptions, consultations, immunizations",
                "floral": "Fresh flowers, custom arrangements, wedding flowers, plants"
            },
            "services": {
                "shopping": ["Grocery pickup", "Home delivery", "Personal shopping", "Senior discounts"],
                "financial": ["Western Union", "Check cashing", "Money orders", "Coinstar"],
                "convenience": ["Propane exchange", "Key cutting", "Dry cleaning drop-off", "Lottery tickets"],
                "special": ["Catering", "Custom cakes", "Gift cards", "Seasonal items"]
            },
            "special_programs": {
                "rewards": "Fresh Valley Rewards - earn points, exclusive discounts, birthday specials",
                "senior_benefits": "10% discount Tuesdays, priority pharmacy, free pickup",
                "student_discounts": "College student discounts with ID, healthy snack promotions"
            },
            "community_involvement": [
                "Local school fundraising support",
                "Community event sponsorship", 
                "Food drive partnerships",
                "Senior citizen programs",
                "Environmental sustainability initiatives"
            ]
        }
        
        self._setup_agent()
    
    def _setup_agent(self):
        """Configure the agent with personality, voice, and capabilities"""
        
        # Configure voice and language
        self.add_language(
            "English", 
            "en-US", 
            "rime.spore",
            function_fillers=[
                "Looking up that information...",
                "Checking our system...",
                "Processing your request..."
            ]
        )
        
        # Add speech recognition hints for grocery store terms
        self.add_hints([
            "Fresh Valley Market", "grocery store", "produce", "deli", 
            "bakery", "pharmacy", "hours", "location", "delivery",
            "pickup", "transfer", "operator", "manager", "complaint",
            "meat", "seafood", "dairy", "frozen", "floral", "rewards",
            "senior discount", "student discount", "Western Union",
            "Coinstar", "propane", "check cashing", "money orders",
            "catering", "custom cakes", "gift cards", "organic",
            "gluten-free", "rotisserie", "immunizations", "prescriptions"
        ])
        
        # Configure AI parameters for friendly, helpful responses
        self.set_params({
            "ai_model": "gpt-4.1-nano",
            "end_of_speech_timeout": 800,
            "temperature": 0.7,
            "max_tokens": 200
        })
        
        # Set up the agent's personality and knowledge
        self._setup_personality()
        
        # Add skills
        self.add_skill("datetime")
        
        # Set global data with store information
        self.set_global_data(self.store_info)
        
        # Register custom tools
        self._register_tools()
    
    def _setup_personality(self):
        """Set up the agent's personality and knowledge base"""
        
        # Use POM sections instead of set_prompt_text to avoid conflicts
        self.prompt_add_section(
            "Role and Personality",
            f"You are a friendly and helpful customer service representative for {self.store_info['name']}, "
            f"a family-owned grocery store established in {self.store_info['established']} that has been serving the Springfield community for {self.store_info['years_in_business']}. "
            f"You are knowledgeable, patient, and always willing to help customers with their questions. "
            f"You take pride in providing excellent customer service and making every customer feel valued. "
            f"You represent a store that values quality, community, service, and convenience."
        )
        
        # Add structured sections using POM
        self.prompt_add_section(
            "Store Information",
            f"You work for {self.store_info['name']}, located at {self.store_info['address']}. "
            f"Our phone number is {self.store_info['phone']}. "
            f"Our email is {self.store_info['email']} and website is {self.store_info['website']}."
        )
        
        self.prompt_add_section(
            "Store Hours",
            "Our store hours are:",
            bullets=[
                f"Monday-Thursday: {self.store_info['hours']['monday']}",
                f"Friday-Saturday: {self.store_info['hours']['friday']}",
                f"Sunday: {self.store_info['hours']['sunday']}"
            ]
        )
        
        self.prompt_add_section(
            "Departments and Specialties",
            "We have eight departments, each with unique offerings:",
            bullets=[
                f"Fresh Produce: {self.store_info['departments']['produce']}",
                f"Meat & Seafood: {self.store_info['departments']['meat_seafood']}",
                f"Deli: {self.store_info['departments']['deli']}",
                f"Bakery: {self.store_info['departments']['bakery']}",
                f"Dairy: {self.store_info['departments']['dairy']}",
                f"Frozen Foods: {self.store_info['departments']['frozen']}",
                f"Pharmacy: {self.store_info['departments']['pharmacy']}",
                f"Floral: {self.store_info['departments']['floral']}"
            ]
        )
        
        self.prompt_add_section(
            "Services We Offer",
            "We provide comprehensive services organized by category:",
            bullets=[
                f"Shopping Services: {', '.join(self.store_info['services']['shopping'])}",
                f"Financial Services: {', '.join(self.store_info['services']['financial'])}",
                f"Convenience Services: {', '.join(self.store_info['services']['convenience'])}",
                f"Special Services: {', '.join(self.store_info['services']['special'])}"
            ]
        )
        
        self.prompt_add_section(
            "Special Programs",
            "We offer special programs for our valued customers:",
            bullets=[
                f"Rewards Program: {self.store_info['special_programs']['rewards']}",
                f"Senior Benefits: {self.store_info['special_programs']['senior_benefits']}",
                f"Student Discounts: {self.store_info['special_programs']['student_discounts']}"
            ]
        )
        
        self.prompt_add_section(
            "Community Involvement",
            "Fresh Valley Market is actively involved in our community through:",
            bullets=self.store_info['community_involvement']
        )
        
        self.prompt_add_section(
            "Customer Service Guidelines",
            "Always follow these principles:",
            bullets=[
                "Provide accurate information about store hours, location, and services",
                "If you cannot help with a specific request, offer to transfer to a human operator",
                "Thank customers for choosing Fresh Valley Market",
                "Keep responses concise but helpful"
            ]
        )
        
        self.prompt_add_section(
            "Transfer Guidelines",
            "Transfer customers to a human operator when:",
            bullets=[
                "They request to speak with a manager",
                "They have a complaint that needs human attention",
                "They need help with specific product availability or pricing",
                "They need assistance with online orders or technical issues",
                "They request services you cannot provide information about",
                "They seem frustrated or unsatisfied with your responses"
            ]
        )
        
        # Post-prompt for additional guidance
        self.set_post_prompt(
            "Always end your responses by asking if there's anything else you can help with. "
            "If a customer seems to need human assistance, proactively offer to transfer them to an operator."
        )
    
    def _register_tools(self):
        """Register custom SWAIG functions"""
        
        # Transfer to operator function
        self.define_tool(
            name="transfer_to_operator",
            description="Transfer the customer to a human operator or manager",
            parameters={
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for the transfer"
                    },
                    "department": {
                        "type": "string",
                        "description": "Specific department if needed (optional)",
                        "enum": ["general", "manager", "pharmacy", "deli", "bakery"]
                    }
                },
                "required": ["reason"]
            },
            handler=self.handle_transfer_to_operator,
            fillers={
                "en-US": [
                    "Let me connect you with someone who can help...",
                    "I'll transfer you to one of our team members...",
                    "Connecting you with a human operator...",
                    "Please hold while I transfer your call..."
                ]
            }
        )
        
        # Store status function
        self.define_tool(
            name="check_store_status",
            description="Check if the store is currently open based on current time and day",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self.handle_store_status,
            fillers={
                "en-US": [
                    "Let me check our current hours...",
                    "Checking if we're open right now...",
                    "Looking up our store status..."
                ]
            }
        )
        
        # Holiday hours function
        self.define_tool(
            name="get_holiday_hours",
            description="Get information about holiday hours and special store closures",
            parameters={
                "type": "object",
                "properties": {
                    "holiday": {
                        "type": "string",
                        "description": "Name of the holiday to check"
                    }
                }
            },
            handler=self.handle_holiday_hours,
            fillers={
                "en-US": [
                    "Let me check our holiday schedule...",
                    "Looking up our holiday hours...",
                    "Checking our special hours for that day..."
                ]
            }
        )
    
    def handle_transfer_to_operator(self, args, raw_data):
        """Handle transfer to human operator"""
        reason = args.get("reason", "Customer requested human assistance")
        department = args.get("department", "general")
        
        # Log the transfer reason
        call_id = raw_data.get("call_id", "unknown")
        print(f"Transfer requested - Call ID: {call_id}, Reason: {reason}, Department: {department}")
        
        # Update global data with transfer info
        transfer_info = {
            "transfer_reason": reason,
            "transfer_department": department,
            "transfer_time": datetime.now().isoformat()
        }
        
        # Create appropriate response based on department
        if department == "manager":
            response = "I'll connect you with one of our managers right away. Please hold on."
        elif department == "pharmacy":
            response = "I'll transfer you to our pharmacy department. They'll be able to help you with your medication needs."
        elif department in ["deli", "bakery"]:
            response = f"I'll connect you with our {department} department. They'll have the specific information you need."
        else:
            response = "I'll connect you with one of our customer service representatives who can provide more detailed assistance."
        
        return (SwaigFunctionResult(response)
                .update_global_data(transfer_info)
                .connect("+16503820000", final=True))  # Replace with actual operator number
    
    def handle_store_status(self, args, raw_data):
        """Check if store is currently open"""
        now = datetime.now()
        current_day = now.strftime("%A").lower()
        current_time = now.strftime("%I:%M %p")
        
        # Get today's hours
        today_hours = self.store_info['hours'].get(current_day, "Closed")
        
        if today_hours == "Closed":
            return SwaigFunctionResult(
                f"We're currently closed today. Our regular hours for {current_day.title()} are {today_hours}. "
                f"Is there anything else I can help you with?"
            )
        
        # For simplicity, assume store is open during business hours
        # In a real implementation, you'd parse the hours and check current time
        return SwaigFunctionResult(
            f"We're currently open! Today's hours are {today_hours}. "
            f"It's currently {current_time}. How can I help you today?"
        )
    
    def handle_holiday_hours(self, args, raw_data):
        """Handle holiday hours requests"""
        holiday = args.get("holiday", "").lower()
        
        # Normalize holiday names to match our data structure
        holiday_mapping = {
            "new year's day": "new_years_day",
            "new years day": "new_years_day",
            "memorial day": "memorial_day",
            "independence day": "independence_day",
            "july 4th": "independence_day",
            "july 4": "independence_day",
            "fourth of july": "independence_day",
            "labor day": "labor_day",
            "thanksgiving": "thanksgiving",
            "christmas eve": "christmas_eve",
            "christmas": "christmas",
            "new year's eve": "new_years_eve",
            "new years eve": "new_years_eve"
        }
        
        # Get normalized holiday key
        holiday_key = holiday_mapping.get(holiday, holiday.replace(" ", "_").replace("'", ""))
        
        # Check our holiday hours data
        if holiday_key in self.store_info['holiday_hours']:
            hours = self.store_info['holiday_hours'][holiday_key]
            if hours == "CLOSED":
                return SwaigFunctionResult(
                    f"We're closed on {holiday.title()}. We'll resume normal hours the next day. "
                    f"Is there anything else I can help you with?"
                )
            else:
                return SwaigFunctionResult(
                    f"Our hours on {holiday.title()} are {hours}. "
                    f"These are different from our regular hours. Is there anything else you need to know?"
                )
        else:
            return SwaigFunctionResult(
                f"I don't have specific information about our hours for {holiday}. "
                f"Let me transfer you to someone who can provide that information."
            ).add_action("transfer_to_operator", {"reason": f"Holiday hours inquiry for {holiday}"})
    
    def on_summary(self, summary, raw_data):
        """Handle conversation summaries for logging/analytics"""
        call_id = raw_data.get("call_id", "unknown")
        print(f"Call Summary - ID: {call_id}")
        print(f"Summary: {summary}")
        

# Create agent instance at module level for service detection
agent = FreshValleyMarketAgent()

def main():
    """Main function to run the agent"""
    print("🛒 Starting Fresh Valley Market Customer Service Agent...")
    print("📍 Store: 1234 Maple Street, Springfield, IL 62701")
    print("📞 Phone: (555) 555-FRESH")
    print("🕐 Hours: Mon-Thu 6AM-10PM, Fri-Sat 6AM-11PM, Sun 7AM-9PM")
    print("🤖 Agent ready to help customers!")
    print("-" * 60)
    
    # Run the agent (auto-detects environment)
    agent.run()
    return agent

if __name__ == "__main__":
    main() 