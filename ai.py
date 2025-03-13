import json
import database
import datetime
import time
import requests
import os
from dotenv import load_dotenv
import traceback

import functions
load_dotenv(override=True)

gemini_api_key = os.environ.get('GeminiProKey')
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-pro-exp-02-05:generateContent?key={}".format(gemini_api_key)
headers = {"Content-Type": "application/json",}


today = datetime.date.today()
year = today.year
month = today.month
day = today.day


function_descriptions = [
        {
            "name": "get_information",
            "description": "this function gives any information you need to answer users questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "info": {
                        "type": "string",
                        "enum": ["businessDescription", "booking","services","training","policy","payment_plans","contact"],
                        "description": 'you specify what information you want to get. you must choose one of this ["businessDescription", "booking","services","training","policy","payment_plans","contact"] use businessDescription for general info.'
                    },
                },
                "required": ["info"],
            }
        },
        {
            "name": "check_availablity",
            "description": "This function lets you check availability within a specified date. The date can be provided as a specific date (YYYY-MM-DD) or as a weekday name (e.g., 'Monday', 'next Tuesday'). If a weekday name is provided, it will be interpreted as the next occurrence of that weekday.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for checking availability. Can be a specific date in YYYY-MM-DD format or a weekday name (e.g., 'Monday', 'next Friday', 'Tue','today'.'tomorrow').'examples': ['2025-03-10', ;Monday;, 'next wednesday','today','tomorrow'] you can also use the 'general' this will return available dates with in current month",
                    },
                
                },
                "required": ["date"],
            }
        },
]

class llm:

    def __init__(self):
        self.responseType = "text"
        self.function_descriptions = function_descriptions
        self.instruction = """

You are Dee, a casual and friendly receptionist at a lash salon booking appointments from online ads. We offer eyelash extensions (Classic - $130, Hybrid - $140, 2-3D - $150, 4-6D - $170, Mega Volume - $190), eyebrow PMU (see below), and EMSculpt (non-invasive body fat treatment - single session $95, 3-session package $270).  Eyebrow PMU services are $550 each, except Nano Brows which are $650.

**Personality:**

*   **"dear" - First Contact:** Use "dear" in your *very first* response to a new customer.  Don't use it again unless there's a long pause in the conversation.
*   **Casual Tone:** Lowercase (unless a proper name or new message start), relaxed grammar ("u" for "you", "ima" for "I'm going to").
*   **Emojis - Sparingly!:** Use emojis (❤️, 🥰, ✨, 😊), but *only* in about *one out of every three* messages.  Don't put an emoji in every response.
*   **Short & Direct:** Be concise. Answer questions directly. Don't volunteer extra info.
*   **Be Dee:** *You are Dee.* Don't state your role.
*   **Deposit Focused:** Get that $20 deposit for lash extensions (Zelle: +12019278282, or payment link). Get a screenshot for Zelle.  Deposits vary for other services.
*   **Get the Name:** Ask for the customer's name before confirming the appointment.
*  If a customer asks for a specific time, and you don't answer, and then aske for another, you should answere that it is available.
*   **NO Markdown:** Plain text only.
* **Pricing:** Don't list prices unless asked. Use the `get_information` function with the `services` parameter *first*, then state the price.

**Function Calls - ALWAYS Use These:**

*   **`check_availability`:**  *Before* providing *any* availability information (days, times), *always* call this function. The function description tells you how to use the `date` parameter.  Don't guess availability!
*   **`get_information`:** Use this to get any info you need (services, booking details, prices, etc.). The function description explains the options.  Use this to retrieve specific pricing if asked.

**Examples (Illustrative - Don't Repeat These Exactly, Adapt to the Situation):**

**Scenario 1 (General Inquiry):**

*   Customer: hi
*   You: hey dear ❤️ what can i help u with?

**Scenario 2 (Direct Availability Question):**

*   Customer: do u have any openings next week?
*   You: hey dear ❤️ let me check!
    *   *(Internally, call `check_availability` with `date: "next week"`)*
*   You:  *(After function call)*  yep, we got openings on tuesday and thursday.

**Scenario 3 (Service Inquiry):**

*  Customer: hi! i saw ur ad. what services do u offer?
*   You: hey dear ❤️ we do lash extensions, eyebrow pmu, and emsculpt.  anything specific u were interested in?

**Scenario 4 (Pricing Inquiry):**

*   Customer:  how much for classic lashes?
*   You: *(Internally, call `get_information` with `info: "services"`)*
*   You: hey! the classic set is on special right now for $90 (usually $130).

**Scenario 5 (Follow-up after long pause):**

* Customer: ok i'll zelle you (sends money 3 hours later).
* You: hey dear, got the payment! what's ur name?

"""

    def function_call(self,response,_id):
        
        function_call = response["candidates"][0]["content"]["parts"][0]["functionCall"]
        function_name = function_call["name"]
        function_args = function_call["args"]
        print(function_name)
        print(function_args)
    
        if function_name == "get_information": 
            info = function_args.get("info")
            
            if info:
                returned_info = functions.get_information(info)
                print(returned_info)
                return {"function_response":str(returned_info),"image":None}
                
            else:
                return {"function_response":"information type is required","image":None}

        if function_name == "check_availablity":
            date = function_args.get("date")
            if date:
                available_on = functions.availablity(date)
                return {"function_response":f"this are the times we are available tell the user well:\n{available_on}","image":None}

        if function_name == "off_topic":
            return {"function_response":'you should only assist the user with only our property and business realted question.so dont assist! tell them to google it or somthing.',"image":None}
        else:
            return {"function_response":'function not found!'}


    def generate_response(self,_id,messages):
        data = {
                "contents": messages,
                "system_instruction": {
                      "parts": [
                        {
                          "text": self.instruction
                        }, 
                      ],
                      "role": "system" 
                    },
                "tools": [{
                    "functionDeclarations": function_descriptions
                    }],
                "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
        ],
                "generationConfig": {
                "temperature": 0.1,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048,
                "stopSequences": [],
                #'safety_settings': [{"category":"HARM_CATEGORY_DEROGATORY","threshold":4},{"category":"HARM_CATEGORY_TOXICITY","threshold":4},{"category":"HARM_CATEGORY_VIOLENCE","threshold":4},{"category":"HARM_CATEGORY_SEXUAL","threshold":4},{"category":"HARM_CATEGORY_MEDICAL","threshold":4},{"category":"HARM_CATEGORY_DANGEROUS","threshold":4}]
              },}


    
        retries = 0
        max_retries = 3
        while retries < max_retries:
            try:
                print("Executing request...")
                response = requests.post(url, headers=headers, json=data)
                print(f"Status Code: {response.status_code}, Response Body: {response.text}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data:
                        print("Valid response received:")
                        break
                    else:
                        print("Empty JSON response received, retrying...")
                else:
                    print(f"Received non-200 status code: {response.status_code}")
                
                time.sleep(5)
            except requests.exceptions.RequestException as e:
                print(f'Request failed: {e}, retrying...')
                time.sleep(5)
            retries += 1
        
        if retries >= max_retries:
            raise Exception("Failed to get response from the model")

        # Process all parts of the response to handle parallel function calls and text
        has_function_calls = False
        text_content = ""
        
        # Check if we have a valid response
        if not response_data or "candidates" not in response_data:
            return "Sorry, I couldn't generate a response at this time."
            
        parts = response_data["candidates"][0]["content"]["parts"]
        
        # First, collect any text content
        for part in parts:
            if "text" in part and part["text"]:
                text_content += part["text"] + "\n"
            
            # Track if we have function calls to process
            if "functionCall" in part:
                has_function_calls = True
        
        # If no function calls, return the text directly
        if not has_function_calls:
            # Structure the response properly before returning and saving
            response_message = {
                "role": "model",
                "parts": [{"text": text_content.strip()}]
            }
            database.add_message(_id, [response_message], "model")
            return text_content.strip()
            
        # Process parallel function calls
        for part in parts:
            if "functionCall" in part:
                # Process this function call
                function_name = part["functionCall"]["name"]
                function_args = part["functionCall"]["args"]
                print(f"Parallel function call detected: {function_name}")
                
                # Execute the function
                function_response = self.function_call({"candidates": [{"content": {"parts": [part]}}]}, _id)
                function_response_message = function_response["function_response"]
                
                # Add the function call and response to the conversation history
                function = [{
                    "functionCall": {
                        "name": function_name,
                        "args": function_args
                    }
                }]
                functionResponse = [{
                    "functionResponse": {
                        "name": function_name,
                        "response": {
                            "name": function_name,
                            "content": function_response_message
                        }
                    }
                }]
                
                # Update messages for next API call (but don't save to database yet)
                messages.append({
                    "role": "model",
                    "parts": function
                })
                messages.append({
                    "role": "function",
                    "parts": functionResponse
                })
        
        # After processing all function calls, make a final API call to get the AI's processed response
        retries = 0
        max_retries = 3
        while retries < max_retries:
            try:
                print("Making final request with function responses...")
                final_response = requests.post(url, headers=headers, json=data)
                
                if final_response.status_code == 200:
                    final_data = final_response.json()
                    if final_data and "candidates" in final_data:
                        # Get the final text response after AI has processed function results
                        final_text = final_data["candidates"][0]["content"]["parts"][0]["text"]
                        # Structure the final response properly and save ONLY THIS to database
                        response_message = {
                            "role": "model",
                            "parts": [{"text": final_text}]
                        }
                        database.add_message(_id, [response_message], "model")
                        return final_text
                    else:
                        print("Empty final response, retrying...")
                else:
                    print(f"Received non-200 status code: {final_response.status_code}")
                
                retries += 1
                time.sleep(5)
            except requests.exceptions.RequestException as e:
                print(f'Final request failed: {e}, retrying...')
                retries += 1
                time.sleep(5)
        
        # If final request fails, return the original text response as a fallback
        final_response = text_content.strip() if text_content else "Sorry, I couldn't process the response at this time."
        # Structure the final response properly
        response_message = {
            "role": "model",
            "parts": [{"text": final_response}]
        }
        database.add_message(_id, [response_message], "model")
        return final_response

# messages = [] 
# while True:
#     user_msg = input("User: ")
#     message = {"role":"user","parts":[{"text":user_msg}]}
#     messages.append(message)
#     print(messages)
#     ai = llm()
#     response = ai.generate_response(123,messages)
#     print(ai)
