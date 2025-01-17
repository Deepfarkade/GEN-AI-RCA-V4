# Now implemeneting the logic of displaying the dataframe on the frontend,
#challenge is : message is first stored in mongoDB then it is being displayed on frontend
#but we don't want to store the entire DF on mongoDB


from interpreter import interpreter
from typing import Optional,List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from fastapi import HTTPException, status

import os

import json
from backend.services.sahdevvv import sd
from datetime import datetime
from backend.services.custom_json import TableDataSerializer
from backend.services.summary_generator import DataframeSummary
from backend.services.prompt_next_question import PromptQuestion
from backend.services.get_history import GetContext  # Import the GetContext class


from diskcache import Cache
 
cache_dir = os.path.join(os.path.dirname(__file__), "../cache_directory")
#cache_dir = "./backend/cache_directory"
cache = Cache(cache_dir,size_limit=int(1e12),eviction_policy="none")


class AIService:
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=10)
    _active_sessions = {} 

    def __init__(self):
        # Configure environment first
        self._configure_environment()
     
        # Single interpreter configuration for Azure
        interpreter.reset()
        interpreter.llm.model = "azure/gpt-4"
        interpreter.llm.temperature=0.2
        interpreter.system_message += """
        Run shell commands with -y so the user doesn't have to confirm them.
        """

    def _configure_environment(self):
        """Configure environment settings for OpenAI and SSL"""
        try:
       
            
            logging.info("Configuration completed successfully")
            
        except Exception as e:
            logging.error(f"Failed to configure environment: {str(e)}")
            raise

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AIService()
        return cls._instance
    

    

    async def get_ai_response(self, message: str, user_id: str,session_id:str) -> str:
        """Get AI response asynchronously with user-isolated context"""
        try:
            get_context = GetContext()
            
            context_str = await get_context.get_session_context(session_id, user_id)


            response = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._process_user_message,
                message,
                user_id,
                context_str
            )
            return response
        except Exception as e:
            logging.error(f"AI Service error for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI response"
            )

    def _process_user_message(self, message: str, user_id: str,context_str:str) -> dict:
        """Process message with user-specific interpreter context"""


        #### Cache #########

        cache_key = message
    
        # Check cache
        cached_response = cache.get(cache_key)
        if cached_response:
            print("Cache hit!")
            return cached_response
    
        print("Cache miss! Processing...")
        prompt_question_object=PromptQuestion
        print("*"*80)
        print(context_str)
        print("*"*80)

        print("Suggested next question : ",prompt_question_object.get_similar_question(message,"ESP"))
        next_question=prompt_question_object.get_similar_question(message,"ESP")

        # interpreter.custom_instructions = f"""
    
        # This conversation is specific to user {user_id}.
        
        # Recent Conversation Context:
        # {context_str}
        # Refer the above provided user questions and SQL statements to deduce the meaning of the question asked by the user if needed.
        
        # Always maintain context and be helpful.

        #  You are 'Maddy', an AI assistant created by EY India GEN AI Engineers. Your primary focus is on:
        # 1. Supply chain analysis and optimization
        # 2. Root cause analysis (RCA)
        # 3. Predictive quality analysis (PQA)
        # 4. Data summarization and forecasting
        # 5. Machine learning insights

        # Always maintain a professional tone while being helpful and precise in your responses.
        # Focus on providing actionable insights and clear explanations.
        # """
        print("Got history")

        try:
            #final_prompt=context_str+message
            #print(final_prompt)
            # print("*"*80)
            # print(final_prompt)
            # print("*"*80)
            extracted_sql,df,msg = sd.execute_query_with_retries(message,context_str)

            print(df.head())
            #sql,df,response=sd.execute_query_with_retries(question=message, max_retries=2)
            
            if not df.empty:
                # Convert DataFrame to dict for JSON serialization
                df.to_csv("temp.csv")
                tds=TableDataSerializer
                df_dict = df.to_dict('records')
                df_dict_serialized = tds.serialize_records(df_dict)
                df_columns = df.columns.tolist()
                summary_object=DataframeSummary(df)
                summary=summary_object.generate_summary(question=message)
                ai_response = {
                    'type': 'sql_response',
                    'content': extracted_sql,
                    'data': {
                        'records': df_dict_serialized,
                        'columns': df_columns
                    },
                    'summary':summary,
                    'next_question':next_question
                }
                

            else:
                ai_response = {
                    'type': 'text',
                    'content': msg,
                    'next_question': next_question
                }

            #self._save_chat_interaction(user_id, message, ai_response['content'])
            cache.set(cache_key, ai_response, expire=None)
            return ai_response

        except Exception as e:
            logging.error(f"Chat processing error: {e}")
            stringgg=sd.generate_fallback_response(message,"",context_str)
            return {
                'type': 'text',
               'content':stringgg,
               'next_question':next_question
            }