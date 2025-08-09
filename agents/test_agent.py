from agents.job_agent import create_job_agent

if __name__ == '__main__':
    agent_executor = create_job_agent()

    # Loop to allow for multiple queries
    while True:
        # Prompt the user for their goal dynamically
        user_goal = input("What is your career goal today? (or type 'exit' to quit): ")

        # Check if the user wants to quit
        if user_goal.lower() == 'exit':
            print("Goodbye!")
            break

        # Make sure the user entered something
        if user_goal.strip():
            print(f"\n--- AGENT GOAL: {user_goal}  ---")

            # Run the agent with the user's dynamic goal
            result = agent_executor.invoke({"input": user_goal})

            print("\n---AGENT'S FINAL ANSWER---")
            print(result['output'])
            print("\n" + "=" * 50 + "\n")
        else:
            print("Please enter a valid goal.")