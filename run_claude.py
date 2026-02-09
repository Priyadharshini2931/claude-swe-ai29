import os
from dotenv import load_dotenv
from anthropic import Anthropic

def main():
    # Load environment variables
    load_dotenv()

    # Read API key
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("CRITICAL ERROR: ANTHROPIC_API_KEY is not set.")
        return

    # Initialize Claude client
    client = Anthropic(api_key=api_key)

    # Create message
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": "Explain Artificial Intelligence in very simple words"
            }
        ]
    )

    # Print Claude reply
    print("\n--- Claude Response ---\n")
    print(response.content[0].text)

if __name__ == "__main__":
    main()
