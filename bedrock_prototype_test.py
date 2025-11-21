import logging
import boto3
from botocore.exceptions import ClientError
import time
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BedrockAgentTester:
    """Low-level testing class for Bedrock agents"""
    
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.agent_client = boto3.client('bedrock-agent')
        self.runtime_client = boto3.client('bedrock-agent-runtime')
        self.alias_id = None
        

    def get_agent(self, agent_id, log_error=True):
        """
        Gets information about an agent.

        :param agent_id: The unique identifier of the agent.
        :param log_error: Whether to log any errors that occur when getting the agent.
                          If True, errors will be logged to the logger. If False, errors
                          will still be raised, but not logged.
        :return: The information about the requested agent.
        """

        try:
            response = self.agent_client.get_agent(agentId=agent_id)
            agent = response["agent"]
        except ClientError as e:
            if log_error:
                logger.error(f"Couldn't get agent {agent_id}. {e}")
            raise
        else:
            return agent
        
    def create_agent_alias(self, name, agent_id):
        """
        Creates an alias of an agent that can be used to deploy the agent.

        :param name: The name of the alias.
        :param agent_id: The unique identifier of the agent.
        :return: Details about the alias that was created.
        """
        try:
            response = self.agent_client.create_agent_alias(
                agentAliasName=name, agentId=agent_id
            )
            agent_alias = response["agentAlias"]
        except ClientError as e:
            logger.error(f"Couldn't create agent alias. {e}")
            raise
        else:
            return agent_alias

    def get_agent_details(self):
        """Get current agent status and details"""
        try:
            response = self.agent_client.get_agent(agentId=self.agent_id)
            agent = response['agent']
            
            logger.info(f"Agent Details:")
            logger.info(f"  Name: {agent['agentName']}")
            logger.info(f"  Status: {agent['agentStatus']}")
            logger.info(f"  Model: {agent['foundationModel']}")
            logger.info(f"  Created: {agent.get('createdAt', 'N/A')}")
            
            return agent
        except ClientError as e:
            logger.error(f"Failed to get agent details: {e}")
            raise
    
    def prepare_agent(self):
        """Prepare agent for use (compile the agent)"""
        try:
            logger.info(f"Preparing agent {self.agent_id}...")
            response = self.agent_client.prepare_agent(agentId=self.agent_id)
            
            # Wait for preparation to complete
            max_attempts = 30
            attempt = 0
            
            while attempt < max_attempts:
                agent = self.get_agent_details()
                status = agent['agentStatus']
                
                if status == 'PREPARED':
                    logger.info("Agent prepared successfully")
                    return True
                elif status == 'FAILED':
                    logger.error("Agent preparation failed")
                    return False
                elif status == 'PREPARING':
                    logger.info(f"Still preparing... (attempt {attempt+1}/{max_attempts})")
                    time.sleep(5)
                    attempt += 1
                else:
                    logger.warning(f"Unexpected status: {status}")
                    time.sleep(5)
                    attempt += 1
            
            logger.error("Preparation timed out")
            return False
            
        except ClientError as e:
            logger.error(f"Failed to prepare agent: {e}")
            raise
    
    def create_or_get_alias(self, alias_name="test-alias"):
        """Create an alias for the agent or get existing one"""
        try:
            # First, try to list existing aliases
            response = self.agent_client.list_agent_aliases(agentId=self.agent_id)
            
            if response['agentAliasSummaries']:
                # Use first existing alias
                self.alias_id = response['agentAliasSummaries'][0]['agentAliasId']
                logger.info(f"Using existing alias: {self.alias_id}")
                return self.alias_id
            
            # Create new alias if none exist
            logger.info(f"Creating new alias: {alias_name}")
            response = self.agent_client.create_agent_alias(
                agentId=self.agent_id,
                agentAliasName=alias_name
            )
            
            self.alias_id = response['agentAlias']['agentAliasId']
            logger.info(f"Created alias: {self.alias_id}")
            
            # Wait for alias to be ready
            time.sleep(5)
            
            return self.alias_id
            
        except ClientError as e:
            logger.error(f"Failed to create/get alias: {e}")
            raise
    
    def invoke_agent_simple(self, prompt, session_id=None):
        """
        Simple agent invocation - single turn
        This is the basic building block for agent interaction
        """
        if not self.alias_id:
            raise ValueError("No alias ID set. Call create_or_get_alias() first")
        
        if not session_id:
            session_id = f"session-{int(time.time())}"
        
        try:
            logger.info(f"Invoking agent with prompt: {prompt}")
            
            response = self.runtime_client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.alias_id,
                sessionId=session_id,
                inputText=prompt
            )
            
            # Parse streaming response
            completion = ""
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        completion += chunk['bytes'].decode('utf-8')
            
            logger.info(f"Agent response received ({len(completion)} chars)")
            return {
                'session_id': session_id,
                'response': completion,
                'prompt': prompt
            }
            
        except ClientError as e:
            logger.error(f"Failed to invoke agent: {e}")
            raise
    
    def invoke_agent_detailed(self, prompt, session_id=None):
        """
        Detailed agent invocation - captures all event types
        Useful for understanding agent reasoning and tool use
        """
        if not self.alias_id:
            raise ValueError("No alias ID set. Call create_or_get_alias() first")
        
        if not session_id:
            session_id = f"session-{int(time.time())}"
        
        try:
            response = self.runtime_client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.alias_id,
                sessionId=session_id,
                inputText=prompt
            )
            
            events = []
            completion = ""
            
            for event in response.get('completion', []):
                event_type = list(event.keys())[0]
                events.append({
                    'type': event_type,
                    'data': event[event_type]
                })
                
                if event_type == 'chunk':
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        text = chunk['bytes'].decode('utf-8')
                        completion += text
                        logger.info(f"  [CHUNK] {text[:100]}...")
                elif event_type == 'trace':
                    logger.info(f"  [TRACE] {event['trace']}")
            
            return {
                'session_id': session_id,
                'response': completion,
                'events': events,
                'event_count': len(events)
            }
            
        except ClientError as e:
            logger.error(f"Failed to invoke agent: {e}")
            raise
    
    def test_multi_turn_conversation(self):
        """Test multi-turn conversation capability"""
        session_id = f"multi-turn-{int(time.time())}"
        
        logger.info("\n" + "="*60)
        logger.info("TESTING MULTI-TURN CONVERSATION")
        logger.info("="*60)
        
        conversation = [
            "Hello, what's your name?",
            "What can you help me with?",
            "Can you remember what I asked you first?"
        ]
        
        for i, prompt in enumerate(conversation, 1):
            logger.info(f"\n--- Turn {i} ---")
            result = self.invoke_agent_simple(prompt, session_id)
            print(f"\n👤 User: {prompt}")
            print(f"🤖 Agent: {result['response']}\n")
            time.sleep(1)
    
    def test_basic_capabilities(self):
        """Test basic agent capabilities"""
        logger.info("\n" + "="*60)
        logger.info("TESTING BASIC CAPABILITIES")
        logger.info("="*60)
        
        test_cases = [
            {
                'name': 'Simple Question',
                'prompt': 'What is 2+2?'
            },
            {
                'name': 'Information Retrieval',
                'prompt': 'What is the capital of France?'
            },
            {
                'name': 'Reasoning',
                'prompt': 'If I have 5 apples and give away 2, how many do I have left?'
            },
            {
                'name': 'Instruction Following',
                'prompt': 'List three colors, one per line, in alphabetical order.'
            }
        ]
        
        results = []
        for test in test_cases:
            logger.info(f"\n--- Testing: {test['name']} ---")
            result = self.invoke_agent_simple(test['prompt'])
            results.append(result)
            
            print(f"\n📝 Test: {test['name']}")
            print(f"👤 Prompt: {test['prompt']}")
            print(f"🤖 Response: {result['response']}\n")
            time.sleep(2)
        
        return results
    
    def cleanup_agent(self):
        """Delete the agent (for cleanup)"""
        try:
            logger.info(f"Deleting agent {self.agent_id}...")
            
            # First delete all aliases
            response = self.agent_client.list_agent_aliases(agentId=self.agent_id)
            for alias in response.get('agentAliasSummaries', []):
                alias_id = alias['agentAliasId']
                logger.info(f"Deleting alias {alias_id}...")
                self.agent_client.delete_agent_alias(
                    agentId=self.agent_id,
                    agentAliasId=alias_id
                )
            
            # Then delete the agent
            self.agent_client.delete_agent(agentId=self.agent_id)
            logger.info("✅ Agent deleted successfully")
            
        except ClientError as e:
            logger.error(f"Failed to delete agent: {e}")
            raise


def run_low_level_tests(agent_id):
    """Run all low-level tests"""
    print("\n" + "="*60)
    print("BEDROCK AGENT LOW-LEVEL TESTING SUITE")
    print("="*60)
    
    tester = BedrockAgentTester(agent_id)
    
    # Test 1: Get agent details
    print("\nTest 1: Get Agent Details")
    tester.get_agent_details()
    
    # Test 2: Prepare agent
    print("\nTest 2: Prepare Agent")
    if not tester.prepare_agent():
        print("Agent preparation failed. Cannot continue.")
        return
    
    # Test 3: Create/get alias
    print("\nTest 3: Create/Get Alias")
    tester.create_or_get_alias()
    
    # Test 4: Simple invocation
    print("\nTest 4: Simple Invocation")
    result = tester.invoke_agent_simple("Hello! Introduce yourself briefly.")
    print(f"\n👤 User: Hello! Introduce yourself briefly.")
    print(f"🤖 Agent: {result['response']}\n")
    
    # Test 5: Detailed invocation (see all events)
    print("\nTest 5: Detailed Invocation (with events)")
    result = tester.invoke_agent_detailed("What is AI?")
    print(f"\n👤 User: What is AI?")
    print(f"🤖 Agent: {result['response']}")
    print(f"📊 Total events captured: {result['event_count']}\n")
    
    # Test 6: Multi-turn conversation
    print("\nTest 6: Multi-turn Conversation")
    tester.test_multi_turn_conversation()
    
    # Test 7: Basic capabilities
    print("\nTest 7: Basic Capabilities")
    tester.test_basic_capabilities()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    
    # Optional: Cleanup
    # Uncomment if you want to delete the agent after testing
    # cleanup = input("\nDelete agent? (yes/no): ")
    # if cleanup.lower() == 'yes':
    #     tester.cleanup_agent()


def main():
    """Main entry point"""
    
    # Your existing agent ID
    agent_id = "P9PEJY138X"
    
    # Run all low-level tests
    run_low_level_tests(agent_id)


if __name__ == "__main__":
    main()