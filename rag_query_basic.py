
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
agent_id = "FYNTRHVA3D"
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
# NOW load the ACTUAL inspection data
# ============================================================
print("\nLoading tower inspection data...")
inspection_file = 'CTI_10105_BostonTurnpikeBolton_CompoundPayload.json'

try:
    with open(inspection_file, 'r') as f:
        inspection_data = json.load(f)
    
    # Convert to string for the prompt
    json_string = json.dumps(inspection_data, indent=2)
    
    print(f"Loaded inspection data:")
    print(f"   File: {inspection_file}")
    print(f"   Size: {len(json_string):,} characters")
    
    # Show a preview
    if 'site_name' in inspection_data:
        print(f"   Site: {inspection_data.get('site_name', 'Unknown')}")
    if 'sections' in inspection_data:
        print(f"   Sections: {len(inspection_data.get('sections', []))}")
    
except FileNotFoundError:
    print(f"Error: File '{inspection_file}' not found!")
    print(f"   Current directory files:")
    import os
    for file in os.listdir('.'):
        if file.endswith('.json'):
            print(f"     - {file}")
    exit(1)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON in file: {e}")
    exit(1)

# ============================================================
# Check if payload is too large
# ============================================================
MAX_CHARS = 200000  # Bedrock has limits around 200K chars

if len(json_string) > MAX_CHARS:
    print(f"\nWARNING: JSON is very large ({len(json_string):,} chars)")
    print(f"   This may exceed Bedrock limits. Consider analyzing sections separately.")
    
    # Option: Analyze just the structure first
    structure_summary = {
        'total_size': len(json_string),
        'top_level_keys': list(inspection_data.keys()),
        'sections_count': len(inspection_data.get('sections', [])) if 'sections' in inspection_data else 'N/A'
    }
    
    print(f"\nData Structure:")
    print(json.dumps(structure_summary, indent=2))
    
    use_full = input("\nProceed with full JSON anyway? (yes/no): ").strip().lower()
    if use_full != 'yes':
        print("Exiting...")
        exit(0)

print("\n" + "="*70)
print("ANALYZING INSPECTION DATA")
print("="*70)

# ============================================================
# Test prompts with the ACTUAL inspection data
# ============================================================

test_prompts = [
    f"""Analyze this tower inspection JSON payload for data integrity issues:
```json
{json_string}
```

Please identify:
1. Missing or null values in critical fields
2. Data type inconsistencies (strings where numbers expected, etc.)
3. Height discrepancies or unrealistic measurements
4. Incomplete sections
5. Any other data quality issues

For each issue found, specify:
- The exact location (section, field path)
- What the issue is
- Why it's a problem
- Suggested fix""",
]

# Run the analysis
for i, prompt in enumerate(test_prompts, 1):
    print(f"\n{'='*70}")
    print(f"TEST {i}: {'Data Integrity Analysis' if i == 1 else 'Data Summary'}")
    print(f"{'='*70}")
    
    try:
        print(f"Sending request to agent...")
        result = agent.invoke_agent(
            agent_id=agent['agent_id'],
            alias_id=agent['alias_id'],
            prompt=prompt
        )
        
        print(f"\nAgent Response:\n")
        print(result['response'])
        
        # Save response to file
        output_file = f"analysis_result_{i}.txt"
        with open(output_file, 'w') as f:
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
print(f"  - analysis_result_2.txt (Data Summary)")