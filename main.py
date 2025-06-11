import requests
import json
import time
from typing import List, Dict, Any, Union

from llm_client import LLMClient
from config import PAPER_SEARCH_SERVER_URL, PDF_SUMMARIZE_SERVER_URL
from utils.logger import log_tool_call, print_streaming_response

# Initialize LLM Client
llm = LLMClient()

# maintain conversation history
conversation_history: List[Dict[str, Any]] = []

# --- Tool Execution Functions ---
def execute_paper_search_tool(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Calls the paper_search MCP server."""
    payload = {"query": query, "max_results": max_results}
    start_time = time.time()
    outcome = "unknown"
    try:
        response = requests.post(
            f"{PAPER_SEARCH_SERVER_URL}/paper_search", json=payload, timeout=60
        )
        response.raise_for_status()
        result = response.json()
        outcome = "success"
        
        if result.get("status") == "success":
            papers = result.get("papers", [])
            if papers:
                formatted_papers = "\n\n".join([
                    f"Title: {p.get('title', 'N/A')}\nAuthors: {', '.join(p.get('authors', ['N/A']))}\nPublished: {p.get('published', 'N/A')}\nPDF URL: {p.get('pdf_url', 'N/A')}"
                    for p in papers
                ])
                return {"tool_output": f"Found {len(papers)} papers:\n{formatted_papers}"}
            else:
                return {"tool_output": "No papers found for your query."}
        else:
            outcome = "failure"
            return {"tool_output": f"Error from paper_search server: {result.get('detail', 'Unknown error')}"}
    except requests.exceptions.RequestException as e:
        outcome = "failure"
        return {"tool_output": f"Failed to call paper_search tool: {e}"}
    except json.JSONDecodeError as e:
        outcome = "failure"
        return {"tool_output": f"Failed to decode JSON from paper_search server: {e}. Response: {response.text}"}
    finally:
        latency = time.time() - start_time
        log_tool_call("paper_search", payload, latency, outcome)


def execute_pdf_summarize_tool(pdf_url: str) -> Dict[str, Any]:
    """Calls the pdf_summarize MCP server."""
    payload = {"pdf_url": pdf_url}
    start_time = time.time()
    outcome = "unknown" 
    try:
        response = requests.post(
            f"{PDF_SUMMARIZE_SERVER_URL}/pdf_summarize", json=payload, timeout=120
        ) # Increased timeout for PDF download/processing
        response.raise_for_status()
        result = response.json()
        outcome = "success"
        
        if result.get("status") == "success":
            return {"tool_output": f"Summary: {result.get('summary')}"}
        else:
            outcome = "failure"
            return {"tool_output": f"Error from pdf_summarize server: {result.get('detail', 'Unknown error')}"}
    except requests.exceptions.RequestException as e:
        outcome = "failure"
        return {"tool_output": f"Failed to call pdf_summarize tool: {e}"}
    except json.JSONDecodeError as e:
        outcome = "failure"
        return {"tool_output": f"Failed to decode JSON from pdf_summarize server: {e}. Response: {response.text}"}
    finally:
        latency = time.time() - start_time
        log_tool_call("pdf_summarize", payload, latency, outcome)



def run_chat_agent():
    print("Scientific Paper Scout - Command Line Chat")
    print("Type 'exit' to quit.")
    print("------------------------------------------")

    global conversation_history 


    conversation_history.append({"role": "system", "content": "You are a helpful AI assistant that helps users discover and summarize recent research papers using the available tools. When searching, try to be specific about the query and number of results. For summarization, request a PDF URL."})

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == 'exit':
            print("Exiting chat. Goodbye!")
            break

        conversation_history.append({"role": "user", "content": user_input})

   
        accumulated_assistant_content = ""
        accumulated_assistant_tool_calls_dict: Dict[str, Dict[str, Any]] = {} 
        tool_calls_to_execute_ordered: List[Dict[str, str]] = []

        try:
            stream = llm.generate_response(conversation_history)
            for chunk in stream:
                if llm.provider == "openai":
                    delta = chunk.choices[0].delta
                    
             
                    if delta.content:
                        print_streaming_response(delta.content)
                        accumulated_assistant_content += delta.content

                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            current_tool_call_id = tool_call_delta.id
                            current_function_name = tool_call_delta.function.name
                            arguments_chunk = tool_call_delta.function.arguments if tool_call_delta.function.arguments is not None else ""

                            if current_tool_call_id:
                                accumulated_assistant_tool_calls_dict[current_tool_call_id] = {
                                    "id": current_tool_call_id,
                                    "type": "function",
                                    "function": {
                                        "name": current_function_name,
                                        "arguments": "" 
                                    }
                                }
  
                                tool_calls_to_execute_ordered.append(accumulated_assistant_tool_calls_dict[current_tool_call_id])
                            

                            if current_tool_call_id:
                                target_tool_call_obj = accumulated_assistant_tool_calls_dict[current_tool_call_id]
                            elif len(tool_calls_to_execute_ordered) > 0:
                                target_tool_call_obj = tool_calls_to_execute_ordered[-1]
                            else:

                                print_streaming_response("\nWARNING: Received tool_call_delta with ID=None but no active tool call. Skipping chunk.")
                                continue # Skip this chunk if we can't associate it

                            target_tool_call_obj["function"]["arguments"] += arguments_chunk
                            
            assistant_message_for_history = {"role": "assistant"}
            if accumulated_assistant_content:
                assistant_message_for_history["content"] = accumulated_assistant_content.strip()
            valid_tool_calls_for_history = [
                tc for tc in tool_calls_to_execute_ordered if tc["function"]["arguments"].strip() or tc["function"]["name"]
            ]
            if valid_tool_calls_for_history:
                assistant_message_for_history["tool_calls"] = valid_tool_calls_for_history
            
            if "content" in assistant_message_for_history or "tool_calls" in assistant_message_for_history:
                conversation_history.append(assistant_message_for_history)


            for tool_call_obj in tool_calls_to_execute_ordered:
                function_name = tool_call_obj["function"]["name"]
                tool_call_id = tool_call_obj["id"]
                
         
                parsed_arguments = json.loads(tool_call_obj["function"]["arguments"] if tool_call_obj["function"]["arguments"] else "{}") 
                
                print_streaming_response(f"\n[AI requests tool call: {function_name} with args: {parsed_arguments}]")
                
                tool_output_dict = {}
                if function_name == "paper_search":
                    tool_output_dict = execute_paper_search_tool(**parsed_arguments)
                elif function_name == "pdf_summarize":
                    tool_output_dict = execute_pdf_summarize_tool(**parsed_arguments)
                else:
                    tool_output_dict = {"tool_output": f"Unknown tool: {function_name}"}

                conversation_history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": function_name, 
                        "content": tool_output_dict["tool_output"],
                    }
                )
    
                print_streaming_response("\n[AI processing tool output...]\n")
                follow_up_stream = llm.generate_response(conversation_history)
                temp_follow_up_content = ""
                follow_up_tool_calls_list = [] 

                follow_up_assistant_message = {"role": "assistant"}
                
                for follow_up_chunk in follow_up_stream:
                    if llm.provider == "openai":
                        delta = follow_up_chunk.choices[0].delta
                        if delta.content:
                            print_streaming_response(delta.content)
                            temp_follow_up_content += delta.content
                        
                        if delta.tool_calls:
                          
                            for tc_delta in delta.tool_calls:
                                if tc_delta.id: 
                                    follow_up_tool_calls_list.append({
                                        "id": tc_delta.id,
                                        "type": "function",
                                        "function": {
                                            "name": tc_delta.function.name,
                                            "arguments": tc_delta.function.arguments if tc_delta.function.arguments is not None else ""
                                        }
                                    })
                
                if temp_follow_up_content:
                    follow_up_assistant_message["content"] = temp_follow_up_content.strip()
                if follow_up_tool_calls_list:
                    follow_up_assistant_message["tool_calls"] = follow_up_tool_calls_list # Append if actual tool calls are found
                
                if "content" in follow_up_assistant_message or "tool_calls" in follow_up_assistant_message:
                    conversation_history.append(follow_up_assistant_message)


        except json.JSONDecodeError as e:
            print(f"\nAn error occurred while parsing JSON from LLM response (or tool arguments): {e}")
            if accumulated_assistant_tool_calls_dict: # Correct variable name used in condition
                print(f"Problematic accumulated_tool_calls: {json.dumps(accumulated_assistant_tool_calls_dict, indent=2)}")
            conversation_history.pop()
            print("Please try again.")
        except requests.exceptions.RequestException as e:
            print(f"\nAn error occurred during tool server communication: {e}")
            conversation_history.pop() 
            print("Please try again.")
        except Exception as e:
            print(f"\nAn unexpected error occurred during LLM interaction: {e}")
            print(f"Error details: {e}")
            conversation_history.pop() 
            print("Please try again.")

if __name__ == "__main__":
    run_chat_agent()