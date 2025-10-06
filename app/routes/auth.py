from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.services.proficiency_assessment import assess_english_proficiency
from app.supabase_client import supabase, progress_tracker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class SignUpRequest(BaseModel):
    email: str
    password: str
    firstName: str
    lastName: str
    grade: str
    english_proficiency_text: str

@router.post("/signup", summary="User Sign-Up with Proficiency Assessment")
async def signup(request: SignUpRequest):
    """
    Handles the user sign-up process.
    1. Checks if user already exists or is soft-deleted.
    2. Assesses English proficiency to assign a starting stage.
    3. Creates the user in Supabase Auth.
    4. Initializes user progress at the assigned stage.
    """
    logger.info(f"Received sign-up request for email: {request.email}")

    try:
        # Step 1: Check if user already exists in our profiles table
        existing_profile_response = supabase.table('profiles').select('id, is_deleted').eq('email', request.email).execute()
        
        if existing_profile_response.data:
            existing_profile = existing_profile_response.data[0]
            if existing_profile.get('is_deleted'):
                logger.warning(f"Signup attempt for a deleted account: {request.email}")
                raise HTTPException(
                    status_code=400,
                    detail="This account has been deleted. Please restore your account or wait 30 days for it to be permanently removed."
                )
            else:
                logger.warning(f"Signup attempt for an existing email: {request.email}")
                raise HTTPException(status_code=400, detail="A user with this email address is already registered.")

        # Step 2: Assess English proficiency
        assigned_stage = await assess_english_proficiency(request.english_proficiency_text)
        logger.info(f"Assigned stage {assigned_stage} for user {request.email}")

        # Step 3: Create user in Supabase Auth
        logger.info(f"Creating user in Supabase Auth for {request.email}")
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "role": 'student',
                    "first_name": request.firstName,
                    "last_name": request.lastName,
                    "grade": request.grade,
                    "assigned_start_stage": assigned_stage,  # Store assigned stage in user metadata
                    "english_proficiency_text": request.english_proficiency_text  # Store proficiency text too
                }
            }
        })

        if auth_response.user:
            user = auth_response.user
            logger.info(f"User created successfully in Supabase Auth with ID: {user.id}")

            # Step 4: Initialize user progress with the assigned stage
            logger.info(f"Initializing progress for user {user.id} at stage {assigned_stage}")
            
            init_result = await progress_tracker.initialize_user_progress(
                user_id=user.id,
                assigned_start_stage=assigned_stage,
                english_proficiency_text=request.english_proficiency_text
            )

            if not init_result["success"]:
                # This is a critical failure. The user exists in auth but not in our system.
                # A more robust solution might involve a cleanup or retry mechanism.
                logger.error(f"Failed to initialize progress for user {user.id}: {init_result.get('error')}")
                # We still return a success to the user, as their account is created.
                # They will be prompted to re-initialize on their first app open.
                return {"success": True, "message": "Account created, but progress initialization failed. Please log in."}
            
            logger.info(f"Successfully signed up and initialized progress for user {user.id}")
            return {"success": True, "message": "Sign-up successful! Please check your email to verify your account."}
        
        elif auth_response.error:
            logger.error(f"Error creating user in Supabase Auth: {auth_response.error.message}")
            raise HTTPException(status_code=400, detail=auth_response.error.message)
        
        else:
            logger.error("An unknown error occurred during Supabase user creation.")
            raise HTTPException(status_code=500, detail="An unexpected error occurred during sign-up.")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"An unexpected error occurred in the signup endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")