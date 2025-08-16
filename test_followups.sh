#!/bin/bash

# Test script for follow-up questions functionality

echo "Testing Follow-up Questions Quality"
echo "==================================="

BASE_URL="http://localhost:8000"

# Function to test a question and extract follow-ups
test_question() {
    local test_name="$1"
    local question="$2"
    
    echo ""
    echo "--- Test: $test_name ---"
    echo "Question: '$question'"
    
    # Make the request and parse response
    response=$(curl -s -X POST "$BASE_URL/query" \
        -H "Content-Type: application/json" \
        -d "{\"question\": \"$question\", \"chat_history\": []}")
    
    if [ $? -eq 0 ]; then
        # Extract follow-up questions using python
        followups=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    followups = data.get('followup_questions', [])
    print(f'Count: {len(followups)}')
    for i, q in enumerate(followups, 1):
        print(f'  {i}. {q}')
    
    # Basic quality analysis
    issues = []
    if len(followups) == 0:
        issues.append('No follow-ups generated')
    elif len(followups) < 2:
        issues.append('Too few follow-ups')
    elif len(followups) > 4:
        issues.append('Too many follow-ups')
    
    if len(followups) != len(set(followups)):
        issues.append('Duplicate questions')
    
    if issues:
        print(f'Issues: {\"#\".join(issues)}')
    else:
        print('Quality: GOOD')
        
except Exception as e:
    print(f'ERROR: {e}')
    print('Raw response:', file=sys.stderr)
    print(sys.stdin.read(), file=sys.stderr)
")
        echo "$followups"
    else
        echo "ERROR: Request failed"
    fi
    
    # Wait between requests to avoid rate limiting
    sleep 12
}

# Test cases
test_question "Wisnet Experience" "Tell me about your experience at Wisnet"
test_question "Vue.js Projects" "Show me your Vue.js projects"  
test_question "Illustrations" "What illustrations do you have?"
test_question "Development Philosophy" "What is your development philosophy?"
test_question "Random/Nonsense" "Random nonsense question xyz"
test_question "Backend Technologies" "Do you work with backend technologies?"
test_question "Creative Process" "Tell me about your creative process"
test_question "JavaScript Skills" "What JavaScript frameworks do you use?"
test_question "Portfolio Question" "Show me your best work"
test_question "Empty Question" ""

echo ""
echo "==================================="
echo "Test Complete"