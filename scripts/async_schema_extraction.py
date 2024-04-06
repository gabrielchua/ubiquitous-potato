# Standard library imports
import asyncio
import base64
import json
import os
import random
from datetime import datetime

# Third-party imports
import pandas as pd
from openai import AsyncOpenAI

SYSTEM_PROMPT = """
You are a world-class fashion stylist.
You will receive an image of a clothing.
Label the clothing by their category, gender and occasion.
Provide your output in JSON format with the 4 keys:
(1) category
(2) gender
(3) occasion
(4) color

Here are the possible values for each key.
(1) category: ['top', 'bottom', 'one-piece', 'outerwear', 'shoes', 'accessories', 'hats']
(2) gender: ['male', 'female', 'unisex']
(3) occasion: ['work', 'leisure', 'formal']
(4) color: ['red', 'green', 'blue', 'yellow', 'black', 'white', 'grey', 'brown', 'orange', 'purple', 'pink', 'multi-color']

Each key can ONLY contain one string value.

Always reply with JSON. No code block.
"""

client = AsyncOpenAI()

def encode_image(file_bytes):
    """ Encode an image file to base64 """
    return base64.b64encode(file_bytes).decode('utf-8')

async def analyse_image(file_path, semaphore, attempt=1):
    """ Analyse an image and return the tagged data asynchronously with error handling, retry mechanism, and a maximum of 4 attempts. """
    async with semaphore:  # This ensures that only a limited number of tasks run concurrently
        try:
            image_base64 = encode_image(open(file_path, "rb").read())
            input_prompt = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}", "detail": "low"}}]
            response = await client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": input_prompt}],
                max_tokens=500,
            )
            tagged_data = response.choices[0].message.content
            tagged_data = json.loads(tagged_data)
            return tagged_data
        except Exception as e:
            if attempt < 4:  # Retry up to 4 attempts
                print(f"Error processing {file_path}: {e}. Attempt {attempt}/4. Retrying in 60 seconds...")
                await asyncio.sleep(60)  # Wait for 60 seconds before retrying
                return await analyse_image(file_path, semaphore, attempt + 1)  # Increment attempt and retry
            else:
                # Log the final failure after exceeding the retry limit and return None or an appropriate value
                print(f"Failed to process {file_path} after 4 attempts.")
                return [file_path, None, None, None, None]

async def process_file(file_name, semaphore):
    """ Process a file asynchronously and return the tagged data """
    tagged_data = await analyse_image(f"../images/{file_name}", semaphore)
    print(f"Completed {file_name}.")  # Print statement to indicate completion
    return [file_name, tagged_data['category'], tagged_data['gender'], tagged_data['occasion'], tagged_data['color']]

async def main():
    """ Main function to process all files asynchronously and save the results to a CSV file"""
    print(f"starting at {datetime.now()}")
    semaphore = asyncio.Semaphore(7)  # Allows up to 7 concurrent tasks
    file_names_all = [f for f in os.listdir('/Users/dsaid/Downloads/images/') if f.endswith('.jpg') or f.endswith('.png')]
    random.shuffle(file_names_all)
    file_names_all = file_names_all[:500]

    tasks = [process_file(file_name, semaphore) for file_name in file_names_all]
    results = await asyncio.gather(*tasks)

    df = pd.DataFrame(results, columns=['file_name', 'category', 'gender', 'occasion', 'color'])
    df.to_csv("../data/meta_data_v3_async.csv", index=False)
    print(f"ended at {datetime.now()}")

asyncio.run(main())
