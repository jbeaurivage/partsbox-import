import os
from dotenv import load_dotenv
from anthropic import Anthropic
import re
import json

# Load all parts from JSON file
def load_parts(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f).get("data")

load_dotenv()
json_path = "all_parts.json"

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

parts = load_parts(json_path)
output = []

# Process only the first 50 parts
for idx, part in enumerate(parts):
    description = part.get("part/description", "")
    footprint = part.get("part/footprint", "")
    try:
        message = client.messages.create(
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    Extract electronic component data for this part. 
                    Only output structured JSON with the specified fields. Don't parse fields other than the ones in the provided examples. Respect the provided string format for all fields in the examples.

                    example output format for resistors:
                    {{ "type": "resistor", "resistance": "10k", "footprint": "0402", "tolerance": "1%", "power_rating": "0.1W" }}

                    example output format for capacitors:
                    {{ "type": "capacitor", "capacitance": "10uF", "footprint": "0402", "tolerance": "1%", "voltage_rating": "10V", "dielectric": "X7R" }}

                    example output format for other types:
                    {{
                        null
                    }}

                    The provided footprint field may be empty, try to extract the footprint from the description if necessary.

                    <data>
                    description: {description}
                    footprint: {footprint}
                    </data>

                    Only output raw json without any additional formatting. No code blocks.
                    """,
                }
            ],
            model="claude-opus-4-6",
        )
        # Extract text from the first TextBlock in message.content
        content_text = ""
        if isinstance(message.content, list) and len(message.content) > 0:
            content_text = message.content[0].text
        else:
            content_text = str(message.content)

        print(content_text)
        # Remove markdown code block markers if present
        content_text = re.sub(r"^```json|^```|```$", "", content_text, flags=re.MULTILINE).strip()

        extracted_data = None
        try:
            extracted_data = json.loads(content_text)
        except Exception:
            match = re.search(r'\{.*\}', content_text, re.DOTALL)
            if match:
                extracted_data = json.loads(match.group(0))
            else:
                extracted_data = {}

        result = {
            "part_id": part.get("part/id"),
            "specs": extracted_data
        }
        output.append(result)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Error processing part {part.get('part/id')}: {e}")

# Write output to a JSON file
with open("extracted_parts2.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)