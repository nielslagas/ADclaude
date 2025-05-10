#!/bin/bash
# Export document text using MS Word if available (on Windows)
DOCFILE="/mnt/d/Projects/ai-arbeidsdeskundige_claude/Arbeidsdeskundige data/AD rapportage format Staatvandienst.docx"
TXTFILE="/mnt/d/Projects/ai-arbeidsdeskundige_claude/ad_format.txt"

echo "Attempting to extract text from: $DOCFILE"

# First try with catdoc if available
if command -v catdoc &> /dev/null; then
    echo "Using catdoc to extract text..."
    catdoc "$DOCFILE" > "$TXTFILE"
    exit 0
fi

# Try with PowerShell if available (for Windows)
if command -v powershell.exe &> /dev/null; then
    echo "Using PowerShell to extract text..."
    powershell.exe -Command "
        \$word = New-Object -ComObject Word.Application
        \$word.Visible = \$false
        \$doc = \$word.Documents.Open('$DOCFILE')
        \$text = \$doc.Content.Text
        [System.IO.File]::WriteAllText('$TXTFILE', \$text)
        \$doc.Close()
        \$word.Quit()
    "
    exit 0
fi

echo "No available method to extract text from Word document."
echo "Please manually convert the document to text and save as $TXTFILE"
exit 1