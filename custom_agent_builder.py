import boto3
import time
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomAgentBuilder:
    """Build custom Bedrock agents with specific capabilities"""
    
    def __init__(self):
        self.agent_client = boto3.client('bedrock-agent')
        self.runtime_client = boto3.client('bedrock-agent-runtime')

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
        
    def create_custom_agent(self, agent_config):
        """
        Create an agent with custom configuration
        
        agent_config = {
            'name': 'MyAgent',
            'instructions': 'Your custom instructions...',
            'model': 'anthropic.claude-sonnet-4-5-20250929-v1:0',
            'role_arn': 'arn:aws:iam::615898656387:role/BedrockAgentRole',
            'description': 'What this agent does'
        }
        """
        try:
            logger.info(f"Creating agent: {agent_config['name']}")
            
            response = self.agent_client.create_agent(
                agentName=agent_config['name'],
                foundationModel=agent_config['model'],
                agentResourceRoleArn=agent_config['role_arn'],
                instruction=agent_config['instructions'],
                description=agent_config.get('description', ''),
                idleSessionTTLInSeconds=agent_config.get('session_timeout', 600)
            )
            
            agent = response['agent']
            agent_id = agent['agentId']
            
            logger.info(f"\nCreated agent: {agent_id}")
            
            # Prepare the agent
            logger.info("Preparing agent...")
            self._prepare_agent(agent_id)
            
            # Create alias
            logger.info("Creating alias...")
            alias_id = self._create_alias(agent_id, agent_config['name'])
            
            return {
                'agent_id': agent_id,
                'alias_id': alias_id,
                'agent_arn': agent['agentArn']
            }
            
        except ClientError as e:
            logger.error(f"Failed to create agent: {e}")
            raise
    
    def _prepare_agent(self, agent_id):
        """Prepare agent for use"""
        self.agent_client.prepare_agent(agentId=agent_id)
        
        # Wait for preparation
        max_attempts = 30
        for _ in range(max_attempts):
            response = self.agent_client.get_agent(agentId=agent_id)
            status = response['agent']['agentStatus']
            
            if status == 'PREPARED':
                logger.info("\nAgent prepared")
                return True
            elif status == 'FAILED':
                raise Exception("Agent preparation failed")
            
            time.sleep(5)
        
        raise Exception("Agent preparation timed out")
    
    def _create_alias(self, agent_id, agent_name):
        """Create alias for agent"""
        response = self.agent_client.create_agent_alias(
            agentId=agent_id,
            agentAliasName=f"{agent_name}-alias"
        )
        return response['agentAlias']['agentAliasId']
    
    def invoke_agent(self, agent_id, alias_id, prompt, session_id=None):
        """Invoke an agent with a prompt"""
        if not session_id:
            session_id = f"session-{int(time.time())}"
        
        response = self.runtime_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=prompt
        )
        
        # Parse response
        completion = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    completion += chunk['bytes'].decode('utf-8')
        
        return {
            'response': completion,
            'session_id': session_id
        }


# ============================================================
# Data Analysis Agent !!!!
# ============================================================

def create_data_analyst_agent():
    """
    Agent specialized in data analysis and SQL queries
    """
    builder = CustomAgentBuilder()
    
    instructions = """
You are a Data Analysis Agent specialized in analyzing data and pointing out integrity issues for tower inspection reports. You are an expert in tower inspections and 
know all the information required about tower parts and issues that arise on towers. Your job is to provide meaningful insight into the data integrity issue with the data.

Your capabilities:
1. Understand data analysis requirements
2. Explain data patterns and insights
3. Recommend data visualization approaches

When given a question to point out data flaws:
- Scan through the payload and look for values out of the ordinary
- I.e. height decrepencies, strings when there should be an int, null values
- Explain your reasoning
- Provide actionable insights

Be precise, analytical, and focus on data-driven answers.
"""
    
    config = {
        'name': 'DataAnalyst-Agent',
        'instructions': instructions,
        'model': 'anthropic.claude-sonnet-4-5-20250929-v1:0',
        'role_arn': 'arn:aws:iam::615898656387:role/BedrockAgentRole',
        'description': 'Specialized agent for data analysis on TIA inspections'
    }
    
    return builder.create_custom_agent(config)


# ============================================================
# EXAMPLE 4: Custom RAG Agent (Your Use Case)
# ============================================================

# def create_rag_query_agent():
#     """
#     Agent specialized in RAG queries combining vector and SQL data
#     """
#     builder = CustomAgentBuilder()
    
#     instructions = """
# You are a RAG Query Agent specialized in retrieving and analyzing information from both vectorized and structured data sources.

# Your capabilities:
# 1. Understand user queries and determine the best data source (vector DB vs SQL)
# 2. Formulate appropriate queries for each data source
# 3. Combine and synthesize information from multiple sources
# 4. Provide accurate, context-aware responses

# When handling a query:
# - Analyze if it requires semantic search (vector), structured data (SQL), or both
# - For vector searches: Identify key semantic concepts
# - For SQL queries: Generate precise, optimized queries
# - Combine results intelligently and provide coherent answers

# Decision framework:
# - Use VECTOR search for: conceptual questions, semantic similarity, document retrieval
# - Use SQL for: specific data lookups, aggregations, structured reports
# - Use BOTH for: complex questions requiring context + specific data

# Be intelligent about data source selection and provide comprehensive, accurate responses.
# """
    
#     config = {
#         'name': 'RAG-Query-Agent',
#         'instructions': instructions,
#         'model': 'anthropic.claude-sonnet-4-5-20250929-v1:0',
#         'role_arn': 'arn:aws:iam::615898656387:role/BedrockAgentRole',
#         'description': 'RAG agent for vector and SQL data queries',
#         'session_timeout': 1800  # 30 minutes for complex queries
#     }
    
#     return builder.create_custom_agent(config)


# ============================================================
# Multi-Agent Orchestrator
# ============================================================

class MultiAgentOrchestrator:
    """Orchestrate multiple specialized agents"""
    
    def __init__(self, agents):
        """
        agents = {
            'data_analyst': {'agent_id': '...', 'alias_id': '...'},
            'researcher': {'agent_id': '...', 'alias_id': '...'},
            ...
        }
        """
        self.agents = agents
        self.builder = CustomAgentBuilder()
        
    def route_query(self, query):
        """Route query to appropriate agent based on content"""
        query_lower = query.lower()
        
        # Simple keyword-based routing (can be made more sophisticated)
        if any(word in query_lower for word in ['sql', 'database', 'query', 'data']):
            return 'data_analyst'
        elif any(word in query_lower for word in ['research', 'find', 'information']):
            return 'researcher'
        elif any(word in query_lower for word in ['code', 'review', 'function', 'bug']):
            return 'code_review'
        else:
            return 'rag_query'
    
    def execute_query(self, query, specific_agent=None):
        """Execute query using appropriate agent"""
        
        # Route to specific agent or auto-route
        agent_key = specific_agent or self.route_query(query)
        
        if agent_key not in self.agents:
            raise ValueError(f"Unknown agent: {agent_key}")
        
        agent_info = self.agents[agent_key]
        
        logger.info(f"Routing to agent: {agent_key}")
        
        result = self.builder.invoke_agent(
            agent_id=agent_info['agent_id'],
            alias_id=agent_info['alias_id'],
            prompt=query
        )
        
        return {
            'agent_used': agent_key,
            'response': result['response'],
            'session_id': result['session_id']
        }


# ============================================================
# Testing Your Custom Agents
# ============================================================

def test_custom_agent(agent_info, test_prompts):
    """Test a custom agent with prompts"""
    builder = CustomAgentBuilder()
    
    print("\n" + "="*70)
    print(f"TESTING CUSTOM AGENT: {agent_info['agent_id']}")
    print("="*70)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nTest {i}:")
        print(f"Prompt: {prompt}")
        
        result = builder.invoke_agent(
            agent_id=agent_info['agent_id'],
            alias_id=agent_info['alias_id'],
            prompt=prompt
        )
        
        print(f"Response:\n{result['response']}\n")
        time.sleep(2)


def main():
    """Main demo"""
    
    print("\n" + "="*70)
    print("CUSTOM AGENTIC SYSTEM BUILDER")
    print("="*70)

    test = CustomAgentBuilder()

    test._prepare_agent("NWH21AVR2Q")
    time.sleep(2)
    
    # # Choose what to create
    # print("\nWhat would you like to create?")
    # print("1. Data Analyst Agent")
    
    # choice = input("\nEnter choice (1-5): ").strip()
    
    # if choice == "1":
    #     print("\nCreating Data Analyst Agent...")
    #     agent = create_data_analyst_agent()
    #     print(f"\nAgent created!")
    #     print(f"   Agent ID: {agent['agent_id']}")
    #     print(f"   Alias ID: {agent['alias_id']}")
        
    #     # Test it
    #     test_prompts = [
    #         "How would I query a database to find the top 10 customers by revenue?",
    #         "What's the best way to analyze sales trends over time?"
    #     ]
    #     test_custom_agent(agent, test_prompts)
    
    # elif choice == "4":
    #     print("\nCreating RAG Query Agent...")
    #     agent = create_rag_query_agent()
    #     print(f"\nAgent created!")
    #     print(f"   Agent ID: {agent['agent_id']}")
    #     print(f"   Alias ID: {agent['alias_id']}")
        
        # Test it
        # test_prompts = [
        #     "I need to find all data integrity issue within the payload provided"
        # ]
        # test_custom_agent(agent, test_prompts)
    
    print("\n" + "="*70)
    print("SETUP COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()