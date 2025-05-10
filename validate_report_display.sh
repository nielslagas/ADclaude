#!/bin/bash

REPORT_ID="efc57479-c765-458c-bc8e-98e43a969469"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"

echo "Validation script for report display"
echo "=================================="
echo

echo "1. Checking API availability..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/reports/templates" -H "Authorization: Bearer $TOKEN")
if [ $API_STATUS -eq 200 ]; then
    echo "✅ API is available (HTTP $API_STATUS)"
else
    echo "❌ API is not available (HTTP $API_STATUS)"
    exit 1
fi

echo "2. Checking report content..."
REPORT_CONTENT=$(curl -s "http://localhost:8000/api/v1/reports/$REPORT_ID" -H "Authorization: Bearer $TOKEN")
HAS_CONTENT=$(echo $REPORT_CONTENT | grep -c "\"content\":")
if [ $HAS_CONTENT -gt 0 ]; then
    echo "✅ Report has content field"
    
    # Check if content is an object with keys
    CONTENT_KEYS=$(echo $REPORT_CONTENT | python3 -c "import sys, json; data = json.load(sys.stdin); print(','.join(data['content'].keys()) if isinstance(data.get('content', {}), dict) else 'not_a_dict')")
    if [ "$CONTENT_KEYS" = "not_a_dict" ]; then
        echo "❌ Report content is not a dictionary"
    else
        echo "✅ Report content contains sections: $CONTENT_KEYS"
    fi
else
    echo "❌ Report is missing content field"
fi

echo "3. Checking frontend server..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5174/")
if [ $FRONTEND_STATUS -eq 200 ]; then
    echo "✅ Frontend server is running (HTTP $FRONTEND_STATUS)"
else
    echo "❌ Frontend server might not be running (HTTP $FRONTEND_STATUS)"
fi

echo
echo "Validation complete. Please visit:"
echo "http://localhost:5174/reports/$REPORT_ID"
echo "to check if the report is displayed correctly in the browser."