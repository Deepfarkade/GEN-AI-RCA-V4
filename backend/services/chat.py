from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException, status
from backend.models.chat import ChatMessage, ChatResponse, ChatSession
from backend.database.mongodb import MongoDB
from datetime import datetime
from bson import ObjectId
import logging
import json
from .ai_service import AIService
import pandas as pd
from backend.services.ask_df import AskDF
import os



class ChatService:
    def __init__(self):
        self.sessions_collection = "chat_sessions"
        self.messages_collection = "chat_messages"
        self.ai_service = AIService.get_instance()

    def _serialize_datetime(self, obj: Any) -> Any:
        """Recursively convert datetime objects to ISO format strings"""
        if isinstance(obj, dict):
            return {key: self._serialize_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def _deserialize_datetime(self, obj: Any) -> Any:
        """Recursively convert ISO format strings back to datetime objects"""
        if isinstance(obj, dict):
            return {key: self._deserialize_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._deserialize_datetime(item) for item in obj]
        elif isinstance(obj, str) and 'T' in obj:
            try:
                return datetime.fromisoformat(obj)
            except ValueError:
                return obj
        return obj

    async def create_session(self, user_id: str) -> ChatSession:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            
            session = ChatSession(
                id=str(ObjectId()),
                title="New Analysis",
                user_id=str(user_id),
                timestamp=datetime.utcnow(),
                messages=[
                    ChatMessage(
                        id=str(ObjectId()),
                        text="Hello! How can I help you with supply chain analysis today?",
                        sender="bot",
                        timestamp=datetime.utcnow(),
                        session_id=str(ObjectId()),
                        next_question="What is my finalized unconstrained forecast for all months to be fed into the Master Planning process?"
                    )
                ]
            )
            
            session_dict = self._serialize_datetime(session.model_dump())
            await sessions.insert_one(session_dict)
            return session

        except Exception as e:
            logging.error(f"Failed to create chat session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat session"
            )

    async def process_message(self, text: str, session_id: str, user: dict) -> ChatResponse:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            
            # Verify session exists and belongs to user
            session = await sessions.find_one({
                "id": session_id,
                "user_id": str(user["_id"])
            })
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
            
            # Save user message
            user_message = ChatMessage(
                id=str(ObjectId()),
                text=text,
                sender="user",
                session_id=session_id,
                timestamp=datetime.utcnow()
            )
            
            # Get AI response
            # ai_response = await self.ai_service.get_ai_response(text, str(user["_id"]))
            ai_response = await self.ai_service.get_ai_response(text, str(user["_id"]),session_id)
            
            # Create response object with potential table data
            response = ChatResponse(
                id=str(ObjectId()),
                text=ai_response['content'],
                sender="bot",
                session_id=session_id,
                timestamp=datetime.utcnow(),
                response_type=ai_response['type'],
                table_data=ai_response.get('data') if ai_response['type'] == 'sql_response' else None,
                summary=ai_response.get('summary') if ai_response['type'] == 'sql_response' else None,
                next_question=ai_response.get('next_question')
            )
            
            # Serialize messages for MongoDB storage
            user_message_dict = self._serialize_datetime(user_message.model_dump())
            response_dict = self._serialize_datetime(response.model_dump())
            
            # Update session with messages
            await sessions.update_one(
                {"id": session_id},
                {
                    "$push": {"messages": {
                        "$each": [user_message_dict, response_dict]
                    }},
                    "$set": {
                        "last_message": response.text,
                        "timestamp": datetime.utcnow()
                    }
                }
            )
            
            return response

        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Failed to process message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process message"
            )
        



    async def get_message_by_id(self, message_id: str, session_id: str) -> Optional[ChatMessage]:
        """
        Fetch a specific message by its ID from a session.
        """
        sessions = await MongoDB.get_collection(self.sessions_collection)
        session = await sessions.find_one({"id": session_id})

        if not session:
            logging.error(f"Session with ID {session_id} not found.")
            return None

        for message in session.get("messages", []):
            if message.get("id") == message_id:
                logging.debug(f"Message found: {message}")
                return ChatMessage(**message)

        logging.error(f"Message with ID {message_id} not found in session {session_id}.")
        return None




    async def get_session_by_id(self, session_id: str, user_id: str) -> ChatSession:
        """
        Fetches a specific chat session by its ID and validates that it belongs to the given user_id.
        """
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            session = await sessions.find_one({"id": session_id, "user_id": user_id})
            if not session:
                return None  # Return None if the session does not exist or does not belong to the user
            
            # Deserialize datetime objects
            deserialized_session = self._deserialize_datetime(session)
            return ChatSession(**deserialized_session)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch session by ID: {str(e)}"
            )

    



    async def ask_on_df(
    self,
    df_question: str,
    session_id: str,
    user_id: str,
    parent_message_id: str
    
    ) -> ChatResponse:
        """
        Handles a user's question about a specific DataFrame (DF).
        """

        # Step 1: Fetch the session and validate ownership
        sessions = await MongoDB.get_collection(self.sessions_collection)
        session = await sessions.find_one({"id": session_id, "user_id": user_id})

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found or unauthorized."
            )

        # Step 2: Fetch the specific message containing table_data
        df_message = await self.get_message_by_id(parent_message_id, session_id)
        if not df_message or not df_message.table_data:
            logging.error(f"Message with ID {parent_message_id} does not contain table_data.")
            raise HTTPException(
                status_code=404,
                detail="Message with table_data not found or doesn't exist in this session."
            )

        # Step 3: Convert `table_data` to a Pandas DataFrame
        table_data = df_message.table_data
        if not table_data.get("records") or not table_data.get("columns"):
            logging.error(f"Invalid table_data structure: {table_data}")
            raise HTTPException(
                status_code=400,
                detail="Invalid or missing table_data."
            )

        try:
            # Convert table_data to Pandas DataFrame
            df = pd.DataFrame.from_records(table_data["records"], columns=table_data["columns"])
            logging.debug(f"DataFrame created successfully with shape: {df.shape}")
        except Exception as e:
            logging.error(f"Error while converting table_data to DataFrame: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process table_data into a DataFrame."
            )

        # Step 4: Save the DataFrame to a temporary CSV file
        temp_csv_path = "temp2.csv"
        try:
            df.to_csv(temp_csv_path, index=False)
            logging.info(f"DataFrame saved to {temp_csv_path}")
        except Exception as e:
            logging.error(f"Error saving DataFrame to CSV: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save DataFrame to temporary CSV."
            )

        # Step 5: Use AskDF for analysis (Code Interpreter)
        askdf_instance = AskDF(df)
        try:
            # Pass the temporary CSV path or DataFrame to AskDF
            answer_text = askdf_instance.ask_df(df_question)
        except Exception as e:
            logging.error(f"AskDF processing error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process the DataFrame query."
            )

        # Step 6: Remove the temporary CSV after use
        try:
            os.remove(temp_csv_path)
            logging.info(f"Temporary CSV file {temp_csv_path} removed successfully.")
        except Exception as e:
            logging.warning(f"Failed to remove temporary CSV file: {e}")

        assistant_msg = ChatResponse(
                            id=str(ObjectId()),
                            text=answer_text,
                            sender="bot",
                            session_id=session_id,
                            timestamp=datetime.utcnow(),
                            response_type="text",
                            df_parent=parent_message_id  # Links to the parent DF message
                        )



        # Step 8: Save the assistant response to the session
        assistant_msg_dict = self._serialize_datetime(assistant_msg.model_dump())
        await sessions.update_one(
            {"id": session_id},
            {
                "$push": {"messages": assistant_msg_dict},
                "$set": {
                    "last_message": assistant_msg.text,
                    "timestamp": datetime.utcnow()
                }
            }
        )

        return assistant_msg


    



    async def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            cursor = sessions.find({"user_id": user_id}).sort("timestamp", -1)

            user_sessions = []
            async for session in cursor:
                # Filter messages with df_parent in the backend
                session["messages"] = [
                    message for message in session.get("messages", [])
                    if not message.get("df_parent")
                ]
                deserialized_session = self._deserialize_datetime(session)
                user_sessions.append(ChatSession(**deserialized_session))

            return user_sessions

        except Exception as e:
            logging.error(f"Failed to get user sessions: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch chat sessions"
            )


    







    # async def get_user_sessions(self, user_id: str) -> List[ChatSession]:
    #     try:
    #         sessions = await MongoDB.get_collection(self.sessions_collection)
    #         cursor = sessions.find({"user_id": user_id}).sort("timestamp", -1)
            
    #         user_sessions = []
    #         async for session in cursor:
    #             # Deserialize datetime objects from the stored session
    #             deserialized_session = self._deserialize_datetime(session)
    #             user_sessions.append(ChatSession(**deserialized_session))
            
    #         return user_sessions

    #     except Exception as e:
    #         logging.error(f"Failed to get user sessions: {str(e)}")
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail="Failed to fetch chat sessions"
    #         )

    # async def get_session_messages(self, session_id: str, user_id: str) -> List[ChatMessage]:
    #     try:
    #         sessions = await MongoDB.get_collection(self.sessions_collection)
    #         session = await sessions.find_one({"id": session_id, "user_id": user_id})

    #         if not session:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="Chat session not found"
    #             )

    #         messages = [
    #             message for message in session.get("messages", [])
    #             if not message.get("df_parent")  # Exclude DF messages
    #         ]

    #         logging.debug(f"Filtered messages for session {session_id}: {messages}")
    #         return [ChatMessage(**message) for message in messages]
    #     except Exception as e:
    #         logging.error(f"Failed to get session messages: {str(e)}")
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail="Failed to fetch session messages"
    #         )


    # backend/services/chat.py

    async def get_session_messages(self, session_id: str, user_id: str) -> List[ChatMessage]:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            session = await sessions.find_one({"id": session_id, "user_id": user_id})

            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )

            # Filter out DF-related messages
            messages = [
                message for message in session.get("messages", [])
                if not message.get("df_parent")  # Exclude DF messages
            ]

            logging.debug(f"Filtered messages for session {session_id}: {messages}")
            return [ChatMessage(**message) for message in messages]
        except Exception as e:
            logging.error(f"Failed to get session messages: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch session messages"
            )






    async def delete_session(self, session_id: str, user_id: str) -> None:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            result = await sessions.delete_one({
                "id": session_id,
                "user_id": user_id
            })
            
            if result.deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )

        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Failed to delete session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete chat session"
            )

