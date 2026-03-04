# ============================================================
# reader.py
# ============================================================
# This is the first and most important file in our project.
# Its only job is to look at a screenshot (like a photo of
# your class schedule) and pull out all the text from it.
#
# Normally reading text from images is really hard to code.
# But we're using OpenAI's AI to do the heavy lifting for us.
# We just send it the image and it sends back all the text.
# ============================================================


# --- IMPORTS ---
# "Imports" are how Python loads tools that other people built.
# Instead of writing everything from scratch, we borrow tools.

import os
# "os" lets Python talk to your operating system (Windows).
# We use it to read secret keys from your .env file safely.

from dotenv import load_dotenv
# "dotenv" is the tool that opens your .env file and loads
# whatever is inside it so Python can use it.
# Remember .env is where we store secret keys like passwords.

from openai import OpenAI
# This is the official OpenAI tool for Python.
# It lets us send images and messages to ChatGPT's AI
# and get responses back, all from inside our code.

import base64
# Images are files made of 1s and 0s (binary data).
# You can't just send a raw image file over the internet easily.
# "base64" converts the image into a long string of text,
# which is much easier to send to OpenAI's servers.
# Think of it like converting a photo into a very long text message.


# --- SETUP ---

load_dotenv()
# This line opens your .env file and loads everything in it.
# After this line runs, Python can access your secret keys.
# It must run BEFORE we try to use any of those keys below.

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# This creates our connection to OpenAI.
# os.getenv("OPENAI_API_KEY") goes into your .env file and
# finds the line that says OPENAI_API_KEY=your-key-here
# and grabs the key. We never type the key directly in code.
# "client" is now our OpenAI connection we can use anywhere.


# --- FUNCTIONS --- 

def encode_image(image_path):
    # --------------------------------------------------------
    # This function takes an image file and converts it to
    # base64 text so we can send it to OpenAI.
    #
    # "image_path" is the location of the image on your computer
    # for example: "samples/schedule.png"
    # --------------------------------------------------------

    with open(image_path, "rb") as image_file:
        # "open()" opens the file at the path we gave it.
        # "rb" means "read binary" — we're reading raw image data
        # not normal text. Images are binary files, not text files.
        # "as image_file" just gives it a nickname we can use below.

        return base64.b64encode(image_file.read()).decode("utf-8")
        # image_file.read() reads all the raw binary data of the image
        # base64.b64encode() converts that binary data into base64 text
        # .decode("utf-8") turns those bytes into a normal Python string
        # "return" sends the result back to whoever called this function


def extract_text_from_screenshot(image_path):
    # --------------------------------------------------------
    # This is the MAIN function of this file.
    # It takes a screenshot, sends it to OpenAI, and returns
    # all the text that OpenAI finds in the image.
    #
    # This is the function we'll call from other files when
    # we want to read a schedule screenshot.
    # -------------------------------------
    print(f"Reading screenshot: {image_path}")
    # This just prints a message to the terminal so you know
    # the program is working. "f" before the string lets us
    # put variables inside curly braces {} in the text.

    base64_image = encode_image(image_path)
    # Here we call the function we wrote above.
    # We give it the image path and it gives us back
    # the base64 version of the image, stored in base64_image.

    response = client.chat.completions.create(
        # This is where we actually talk to OpenAI.
        # "client.chat.completions.create" means:
        # "hey OpenAI, I want to send a message and get a reply"
        # Everything inside the parentheses is what we're sending.

    model="gpt-4o",
        # This tells OpenAI WHICH AI model to use.
        # "gpt-4o" is the one that can see and understand images.
        # If we used a text-only model it wouldn't be able to see screenshots.
    messages=[
            # "messages" is a list of what we're saying to the AI.
            # It's a list (using []) because you can have a conversation
            # with multiple back and forth messages. We just have one here.
            {
                "role": "user",
                # "role" tells OpenAI who is speaking.
                # "user" means this is coming from us (the human).
                # The other option is "assistant" which is the AI's replies.

                "content": [
                    # "content" is what we're actually sending.
                    # We're sending TWO things: a text instruction + the image.
                    # That's why content is a list [] with two items.

                    {
                        "type": "text",
                        "text": "This is a college schedule or syllabus screenshot. Please extract ALL text you can see exactly as it appears. Do not summarize, just extract everything."
                        # This is our instruction to the AI.
                        # We're telling it exactly what we want it to do.
                        # The clearer the instruction, the better the result.
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                            # This is how we send the image to OpenAI.
                            # We can't attach a file directly so instead
                            # we send it as a base64 string embedded in a URL.
                            # {base64_image} is the long string from encode_image().
                        }
                    }
                ]
            }
        ],

        max_tokens=2000
        # "tokens" are roughly like words — OpenAI charges per token.
        # This limits the response to 2000 tokens (about 1500 words).
        # For a schedule screenshot that's more than enough.
    )

    return response.choices[0].message.content
    # "response" is everything OpenAI sent back to us.
    # .choices[0] gets the first (and only) response option.
    # .message.content gets the actual text of the response.
    # "return" sends that text back to whoever called this function.