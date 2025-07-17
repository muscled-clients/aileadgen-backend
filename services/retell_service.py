import os
import requests
from typing import Dict, Any, Optional
import json

class RetellService:
    def __init__(self):
        self.api_key = os.getenv("RETELL_API_KEY")
        self.base_url = "https://api.retellai.com"
        
        if not self.api_key:
            raise ValueError("Missing RETELL_API_KEY environment variable")
            
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def create_phone_call(self, to_number: str, agent_id: str) -> Dict[str, Any]:
        """Create a phone call with Retell.ai"""
        try:
            url = f"{self.base_url}/v2/create-phone-call"
            payload = {
                "from_number": os.getenv("RETELL_FROM_NUMBER", "+14014165676"),  # Using your Retell.ai number
                "to_number": to_number,
                "retell_llm_dynamic_variables": {
                    "name": "there",
                    "company_name": "AI Lead Gen"
                }
            }
            
            print(f"Creating Retell call to {to_number} with agent {agent_id}")
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 201:
                result = response.json()
                print(f"✅ Call created successfully: {result}")
                return result
            else:
                print(f"❌ Error creating call: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            print(f"❌ Exception in create_phone_call: {e}")
            return {"error": str(e)}
    
    async def create_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create an AI agent for conversations"""
        try:
            url = f"{self.base_url}/create-agent"
            
            response = requests.post(url, headers=self.headers, json=agent_config)
            
            if response.status_code == 201:
                result = response.json()
                print(f"✅ Agent created successfully: {result}")
                return result
            else:
                print(f"❌ Error creating agent: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            print(f"❌ Exception in create_agent: {e}")
            return {"error": str(e)}
    
    async def get_agents(self) -> Dict[str, Any]:
        """Get list of existing agents"""
        try:
            url = f"{self.base_url}/list-agents"
            
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Agents retrieved: {result}")
                return result
            else:
                print(f"❌ Error getting agents: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            print(f"❌ Exception in get_agents: {e}")
            return {"error": str(e)}
    
    def get_default_agent_config(self) -> Dict[str, Any]:
        """Get default agent configuration for lead generation"""
        return {
            "agent_name": "AI Lead Gen Agent",
            "voice_id": "11labs-adriana",
            "language": "en-US",
            "response_engine": {
                "type": "retell_llm",
                "llm_id": "gpt-4o-mini",
                "begin_message": "Hello! I'm calling from AI Lead Gen to discuss how we can help generate more leads for your business. How are you doing today?"
            },
            "general_prompt": """You are an AI sales representative for AI Lead Gen, a company that helps businesses generate more leads through AI-powered solutions.

Your goals:
1. Build rapport with the prospect
2. Understand their current lead generation challenges  
3. Explain how AI Lead Gen can help them
4. Book a 15-minute discovery call

Key points to cover:
- Ask about their current lead generation methods
- Understand their pain points (not enough leads, low quality leads, too time-consuming)
- Explain how AI can automate and improve their lead generation
- Offer to schedule a brief call to show them a demo

Keep the conversation natural, friendly, and focused on their needs. Ask open-ended questions and listen to their responses. If they're interested, try to book a call for later this week.

Be conversational and human-like. Don't sound robotic or scripted."""
        }