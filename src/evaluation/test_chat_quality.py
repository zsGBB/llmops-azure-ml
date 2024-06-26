
from promptflow.azure import PFClient
from promptflow.entities import Run
from azure.identity import DefaultAzureCredential
import os


def quality_test(): 
  
  pf = PFClient(credential=DefaultAzureCredential(),
                subscription_id=os.environ.get('SUBSCRIPTION_ID'),
                resource_group_name=os.environ.get('RESOURCE_GROUP_NAME'),
                workspace_name=os.environ.get('WORKSPACE_NAME')
                )
  
  # Define Flows and Data
  chat_flow = "./src/chat/chat_rag_wiki" # set the flow directory
  eval_flow = "./src/evaluation/eval_flow" # set flow directory
  data = "./src/evaluation/input_test_data.csv" # set the data file

  # Define remote compute instance (serverless)
  resources = {"instance_type": "Standard_D2"}

 ##### Run chat flow #########
  chat_run = Run(
    display_name="Chat Run - Python",
    flow=chat_flow,
    data=data,
    resources=resources,
    column_mapping={  # map the url field from the data to the url input of the flow
    "input": "${data.input}",
    },
    environment_variables={
    "CONTENT_SAFE_BASE": os.environ.get('CONTENT_SAFE_BASE'),
    "CONTENT_SAFE_KEY": os.environ.get('CONTENT_SAFE_KEY'),
    "AZURE_OPENAI_API_KEY": os.environ.get('AZURE_OPENAI_API_KEY'),
    "AZURE_OPENAI_ENDPOINT": os.environ.get('AZURE_OPENAI_ENDPOINT'),
    "AZURE_OPENAI_DEPLOYMENT_NAME": os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME')
    }
  )

  chat_run_job = pf.runs.create_or_update(
    run=chat_run,
  )
  
  pf.runs.stream(chat_run_job) # This is important - essentially a wait function

 ###############################

 ##### Run eval flow  #########
  eval_run = Run(
      display_name="Eval Run - Python",
      flow=eval_flow,
      data=data,
      run=chat_run,
      resources=resources,
      column_mapping={  # map the url field from the data to the url input of the flow
        "question": "${data.input}",
        "answer": "${run.outputs.answer}",
        "context": "${run.outputs.context}"
      }
  )

  eval_run_job = pf.runs.create_or_update(
    run=eval_run,
  )
  
  pf.runs.stream(eval_run_job)

 ###############################

 # Run Tests with Assertions

  metric_dict = dict(pf.get_metrics(eval_run_job))

  print(f"RESULTS: {metric_dict}")

  assert(metric_dict['fluency'] >= 4)
  assert(metric_dict['answer_context_sim'] >= 0.85)
  assert(metric_dict['groundedness'] >= 4)

  return

if __name__ == "__main__":
  quality_test()  
