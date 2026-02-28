from agents.job_agent import create_job_agent
from langchain_core.messages import HumanMessage

if __name__ == '__main__':
    agent = create_job_agent()

    # Loop to allow for multiple queries
    while True:
        try:
            # Prompt the user for their goal dynamically
            user_goal = input("What is your career goal today? (or type 'exit' to quit): ")

            # Check if the user wants to quit
            if user_goal.lower() == 'exit':
                print("Goodbye!")
                break

            # Make sure the user entered something
            if user_goal.strip():
                print(f"\n--- AGENT GOAL: {user_goal}  ---")

                # Run the agent with the user's input
                # The new create_agent returns a compiled state graph that accepts messages
                result = agent.invoke({
                    "messages": [HumanMessage(content=user_goal)]
                })

                print("\n---AGENT'S FINAL ANSWER---")
                # Extract the last message from the result
                if "messages" in result and result["messages"]:
                    last_message = result["messages"][-1]
                    if hasattr(last_message, 'content'):
                        print(last_message.content)
                    else:
                        print(result)
                else:
                    print(result)
                print("\n" + "=" * 50 + "\n")
            else:
                print("Please enter a valid goal.")

        except Exception as e:
            print(f"\nAn error occurred: {e}")
            print("Restarting the conversation loop.")
            continue