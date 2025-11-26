import json
from botocore.exceptions import ClientError
import logging
from custom_agent_builder import create_data_analyst_agent, test_custom_agent
from custom_agent_builder import CustomAgentBuilder


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print("USING EXISTING AGENT")
print("="*70)

# Create an INSTANCE of CustomAgentBuilder
builder = CustomAgentBuilder()

# Get agent information
agent_id = "IO0QWGMS3A"
agent_info = builder.get_agent(agent_id)

print(f"\nAgent Found!")
print(f"   Agent Name: {agent_info['agentName']}")
print(f"   Agent ID: {agent_info['agentId']}")
print(f"   Status: {agent_info['agentStatus']}")

# Get or create alias
print("\nGetting alias...")
alias_response = builder.agent_client.list_agent_aliases(agentId=agent_id)
aliases = alias_response.get('agentAliasSummaries', [])

if not aliases:
    print("No alias found, creating one...")
    alias_response = builder.agent_client.create_agent_alias(
        agentId=agent_id,
        agentAliasName=f"{agent_info['agentName']}-alias"
    )
    alias_id = alias_response['agentAlias']['agentAliasId']
    print(f"Created alias: {alias_id}")
else:
    alias_id = aliases[0]['agentAliasId']
    print(f"Using existing alias: {alias_id}")

if agent_info['agentStatus'] != 'PREPARED':
    print(f"\nAgent status is '{agent_info['agentStatus']}', preparing...")
    builder._prepare_agent(agent_id)
else:
    print(f"Agent is already prepared")

agent = {
    'agent_id': agent_id,
    'alias_id': alias_id,
    'agent_arn': agent_info['agentArn']
}
print(f"RAG Agent Created!")
print(f"Agent ID: {agent['agent_id']}")
print(f"Alias ID: {agent['alias_id']}")

print("\nSaving agent info...")
with open('agent_config.json', 'w') as f:
    json.dump(agent, f, indent=2)
print("Agent info saved to: agent_config.json")

# ============================================================
# NOW load the parsed markdown data
# ============================================================
print("\nLoading parsed inspection data...")
markdown_file = 'my_custom_report.md'

try:
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    print(f"Loaded markdown data:")
    print(f"   File: {markdown_file}")
    print(f"   Size: {len(markdown_content):,} characters")
    
    # Show a preview of first few lines
    preview_lines = markdown_content.split('\n')[:10]
    print(f"   Preview:")
    for line in preview_lines:
        if line.strip():
            print(f"     {line[:80]}")
    
except FileNotFoundError:
    print(f"Error: File '{markdown_file}' not found!")
    print(f"   Current directory files:")
    import os
    for file in os.listdir('.'):
        if file.endswith('.md'):
            print(f"     - {file}")
    exit(1)
except Exception as e:
    print(f"Error reading markdown file: {e}")
    exit(1)

# ============================================================
# Check if payload is too large
# ============================================================
MAX_CHARS = 200000  # Bedrock has limits around 200K chars

if len(markdown_content) > MAX_CHARS:
    print(f"\nWARNING: Markdown is very large ({len(markdown_content):,} chars)")
    print(f"   This may exceed Bedrock limits.")
    
    use_full = input("\nProceed with full markdown anyway? (yes/no): ").strip().lower()
    if use_full != 'yes':
        print("Exiting...")
        exit(0)

print("\n" + "="*70)
print("ANALYZING INSPECTION DATA")
print("="*70)

# ============================================================
# Test prompts with the parsed markdown data
# ============================================================

test_prompts = [
    f"""Analyze this tower inspection data for data integrity issues:

{markdown_content}

Please identify:
1. Missing or null values in critical fields
2. Data type inconsistencies (strings where numbers expected, etc.)
3. Height discrepancies or unrealistic measurements
4. Incomplete sections or records
5. Any other data quality issues
6. General counts of records recorded in the survey and important observations

For each issue found, specify:
- The exact location (section, record number)
- What the issue is
- Why it's a problem
- Suggested fix""",
]

# Run the analysis
for i, prompt in enumerate(test_prompts, 1):
    print(f"\n{'='*70}")
    print(f"TEST {i}: Data Integrity Analysis")
    print(f"{'='*70}")
    
    try:
        print(f"Sending request to agent...")
        result = builder.invoke_agent(
            agent_id=agent['agent_id'],
            alias_id=agent['alias_id'],
            prompt=prompt
        )
        
        print(f"\nAgent Response:\n")
        print(result['response'])
        
        # Save response to file
        output_file = f"analysis_result_{i}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:  # Add encoding='utf-8'
            f.write(f"Prompt:\n{test_prompts[i-1][:200]}...\n\n")
            f.write(f"Response:\n{result['response']}")
        print(f"\nResponse saved to: {output_file}")
        
    except Exception as e:
        print(f"Error during test {i}: {e}")
        logger.exception("Full error:")
    
    if i < len(test_prompts):
        print("\nWaiting 3 seconds before next test...")
        import time
        time.sleep(3)

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print(f"\nAgent Details:")
print(f"  Agent ID: {agent['agent_id']}")
print(f"  Alias ID: {agent['alias_id']}")
print(f"\nResults saved to:")
print(f"  - analysis_result_1.txt (Data Integrity Issues)")