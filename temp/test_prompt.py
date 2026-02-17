from libs.prompt import Prompt
import sys

if __name__ == "__main__":   
    # Read argv[1] as user input
    user_input = sys.argv[1] if len(sys.argv) > 1 else ""

    prompt = Prompt()
    content = prompt.create_prompt(user_input)
    if content:
        print(content)
    else:
        print("Skipping as no content")