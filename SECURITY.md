# Security Guidelines

This document outlines security best practices for the AI-Arbeidsdeskundige Claude application.

## API Key Management

### Best Practices

1. **Never hardcode API keys in source code**
   - Always use environment variables or secure secret management
   - API keys should never be committed to the repository

2. **Use .env files for local development**
   - Store all API keys in a local `.env` file
   - Add `.env` to `.gitignore` to prevent accidental commits
   - Use the provided `.env.example` as a template (contains no real keys)

3. **API Key Usage in Docker**
   - Pass API keys to containers via environment variables
   - Use docker-compose environment variables or .env files
   - Example: `OPENAI_API_KEY=${OPENAI_API_KEY}` in docker-compose.yml

4. **Secure Logging**
   - Never log full API keys
   - When debugging, log only:
     - Whether a key is present (boolean)
     - The key's length
     - At most, a highly truncated version (e.g., first 2 chars + last 2 chars)

### Setting Up API Keys

To set up API keys for the application:

1. Copy the example environment file:
   ```bash
   cp docker-compose.example.env .env
   ```

2. Edit the `.env` file and add your API keys:
   ```
   # API Keys for different providers
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

3. Run the application using docker-compose:
   ```bash
   docker-compose up -d
   ```

## Sensitive Information Handling

1. **User Data**
   - Store all user data in the database, not in text files
   - Ensure proper access controls to user data
   - Do not log or expose personal information in application logs

2. **Audio Files**
   - Audio recordings should be stored securely
   - Implement proper access controls to audio files
   - Delete temporary audio files after processing

3. **Transcriptions**
   - Ensure transcription results are only visible to authorized users
   - Do not expose transcription results in logs
   - Store transcriptions securely in the database

## Testing With Sensitive Data

1. **Test Environment Setup**
   - Use separate API keys for testing/development
   - Never use production keys in testing environments
   - Use mock or sanitized data for tests

2. **Test Scripts**
   - Never hardcode API keys in test scripts
   - Use environment variables for sensitive data
   - Ensure test scripts clean up after themselves

## Security Review Checklist

Periodically perform a security review of the codebase:

- [ ] Check for hardcoded API keys or credentials
- [ ] Review logging to ensure no sensitive data is exposed
- [ ] Verify proper access controls for user data
- [ ] Check for any temporary files containing sensitive information
- [ ] Review Docker configuration for security best practices
- [ ] Verify that all environment variables are properly documented