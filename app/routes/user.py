# app/routes/user.py
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from datetime import datetime

from app.schemas.user_input import UserRegisterInput, StageResult, WordPressUserRegistration, UserLogin
from app.services.cefr_evaluator import evaluate_cefr_level
from app.database import get_db

router = APIRouter()

WP_TABLE_PREFIX = os.getenv("WP_TABLE_PREFIX", "wp_")

WP_SITE_URL = os.getenv("WP_SITE_URL")
WP_API_USERNAME = os.getenv("WP_API_USERNAME")
WP_API_APPLICATION_PASSWORD = os.getenv("WP_API_APPLICATION_PASSWORD")

DEFAULT_WP_TOKEN_ENDPOINT_PATH = "/wp-json/jwt-auth/v1/token"

@router.post(
    "/register",
    response_model=StageResult,
    summary="User Registration with CEFR Stage Assignment",
    description=(
        "Assigns a CEFR English proficiency stage (A0 to C2) to a new user during app registration.\n\n"
        "The user submits a short English writing sample (2–3 sentences). This sample is evaluated using GPT-4 "
        "to determine the most appropriate CEFR level:\n\n"
        "- **A0**: No understanding or broken grammar (nonsensical text).\n"
        "- **A1 to C2**: Increasing levels of proficiency based on clarity, vocabulary, and grammar.\n\n"
        "Returns the assigned CEFR stage and user name."
    )
)


@router.post("/register", response_model=StageResult)
async def register_user(user_input: UserRegisterInput):
    stage = evaluate_cefr_level(user_input.writing_sample)
    return StageResult(name=user_input.name, assigned_stage=stage)


@router.post("/register-wordpress", status_code=status.HTTP_201_CREATED)
async def register_wordpress_user_api(user_data: WordPressUserRegistration, db: Session = Depends(get_db)):
    if not all([WP_SITE_URL, WP_API_USERNAME, WP_API_APPLICATION_PASSWORD]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WordPress API credentials or site URL for user creation are not configured."
        )

    wp_api_users_url = f"{WP_SITE_URL.rstrip('/')}/wp-json/wp/v2/users"
    wp_token_url = f"{WP_SITE_URL.rstrip('/')}{DEFAULT_WP_TOKEN_ENDPOINT_PATH}"

    api_payload = {
        "username": user_data.username,
        "email": user_data.email,
        "password": user_data.password,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "roles": ["subscriber"]
    }

    new_user_id = None
    access_token = None
    user_creation_successful = False
    metadata_update_successful = False
    token_retrieval_successful = False
    
    final_response_message = ""
    metadata_error_detail_message = None
    token_error_detail_message = None

    # 1. Create User via WordPress API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                wp_api_users_url,
                json=api_payload,
                auth=(WP_API_USERNAME, WP_API_APPLICATION_PASSWORD)
            )
        
        if response.status_code == 201:
            response_data = response.json()
            new_user_id = response_data.get("id")
            if not new_user_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User created via API, but no ID returned."
                )
            user_creation_successful = True
        else:
            try:
                error_details = response.json()
                detail_message = error_details.get("message", response.text)
            except Exception:
                detail_message = response.text
           
            raise HTTPException(
                status_code=response.status_code,
                detail=f"WordPress API User Creation Error: {detail_message}"
            )
    except httpx.RequestError as e:
        print(f"HTTPX RequestError during WP user creation: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error connecting to WordPress API for user creation: {str(e)}")
    except Exception as e:
        print(f"Unexpected error during WP API user creation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error during user creation API call: {str(e)}")

    # 2. Add/Update Custom Usermeta (only if user creation was successful)
    try:
        meta_to_add_or_update = [
            {"meta_key": "date_of_birth", "meta_value": user_data.date_of_birth.isoformat() if user_data.date_of_birth else None},
            {"meta_key": "english_assessment_text", "meta_value": user_data.english_assessment_text},
        ]
        insert_usermeta_query = text(f"""
            INSERT INTO {WP_TABLE_PREFIX}usermeta (user_id, meta_key, meta_value)
            VALUES (:user_id, :meta_key, :meta_value)
            ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value)
        """)

        for item in meta_to_add_or_update:
            if item["meta_value"] is not None:
                db.execute(insert_usermeta_query, {
                    "user_id": new_user_id,
                    "meta_key": item["meta_key"],
                    "meta_value": str(item["meta_value"])
                })
        
        db.execute(insert_usermeta_query, {"user_id": new_user_id, "meta_key": "nickname", "meta_value": user_data.username})
        if user_data.first_name:
            db.execute(insert_usermeta_query, {"user_id": new_user_id, "meta_key": "first_name", "meta_value": user_data.first_name})
        if user_data.last_name:
            db.execute(insert_usermeta_query, {"user_id": new_user_id, "meta_key": "last_name", "meta_value": user_data.last_name})

        db.commit()
        metadata_update_successful = True
    except Exception as e:
        db.rollback()
        print(f"User {new_user_id} created via WP API, but failed to save custom usermeta: {e}")
        metadata_error_detail_message = str(e)

    # 3. Get Access Token for the new user (user_creation_successful must be true)
    try:
        async with httpx.AsyncClient() as client:
            token_payload = {
                "username": user_data.username,
                "password": user_data.password
            }
            token_response = await client.post(wp_token_url, data=token_payload)

        if token_response.status_code == 200:
            token_data = token_response.json()
            access_token = token_data.get("token") or \
                           token_data.get("data", {}).get("token") or \
                           token_data.get("jwt_token")
            if access_token:
                token_retrieval_successful = True
            else:
                token_error_detail_message = "Token endpoint success (200), but token field was missing/empty in response."
                print(f"Token endpoint success, but no token found in response: {token_data}")
        else:
            try:
                error_details = token_response.json()
                token_error_detail_message = error_details.get("message", token_response.text)
            except Exception:
                token_error_detail_message = token_response.text
            print(f"Failed to retrieve token. Status: {token_response.status_code}, Detail: {token_error_detail_message}")

    except httpx.RequestError as e:
        print(f"HTTPX RequestError during WP token retrieval: {e}")
        token_error_detail_message = f"Error connecting to WordPress token API: {str(e)}"
    except Exception as e:
        print(f"Unexpected error during WP token retrieval: {e}")
        token_error_detail_message = f"Unexpected error during token retrieval: {str(e)}"

    if user_creation_successful and metadata_update_successful and token_retrieval_successful:
        final_response_message = "User registered, metadata updated, and token retrieved successfully."
    elif user_creation_successful and metadata_update_successful:
        final_response_message = "User registered and metadata updated. Token retrieval failed."
    elif user_creation_successful and token_retrieval_successful:
        final_response_message = "User registered and token retrieved. Metadata update failed."
    elif user_creation_successful:
        final_response_message = "User registered. Metadata update and token retrieval failed."

    response_payload = {
        "message": final_response_message,
        "user_id": new_user_id,
        "access_token": access_token if access_token else None
    }
    if metadata_error_detail_message:
        response_payload["metadata_error_detail"] = metadata_error_detail_message
    if token_error_detail_message and not token_retrieval_successful:
        response_payload["token_error_detail"] = token_error_detail_message
    
    
    return response_payload


@router.post("/login-wordpress")
async def login_wordpress_user(login_data: UserLogin, db: Session = Depends(get_db)):
    if not WP_SITE_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WordPress site URL is not configured."
        )

    # 1. Check if user exists in the database and get their username and ID
    get_user_query = text(f"SELECT ID, user_login FROM {WP_TABLE_PREFIX}users WHERE user_email = :email")
    user_record = db.execute(get_user_query, {"email": login_data.email}).fetchone()

    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials."
        )
    
    user_id = user_record[0]
    username = user_record[1]

    # 2. Make API request to get the access token
    wp_token_url = f"{WP_SITE_URL.rstrip('/')}{DEFAULT_WP_TOKEN_ENDPOINT_PATH}"
    token_payload = {
        "username": username,
        "password": login_data.password
    }

    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(wp_token_url, json=token_payload)

        # This will now be handled inside the try block
        token_response.raise_for_status() # Raise an exception for 4xx/5xx responses

        token_data = token_response.json()
        access_token = token_data.get("token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login successful, but token was not found in the response from WordPress."
            )
        
        return {
            "message": "Login successful.",
            "user_id": user_id,
            "access_token": access_token
        }
    except httpx.HTTPStatusError:
        # This catches 4xx/5xx errors from raise_for_status()
        # It's the most common case for a wrong password.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials."
        )
    except httpx.RequestError as e:
        # This catches network errors
        print(f"HTTPX RequestError during WP token retrieval for login: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error connecting to authentication service."
        )
    except Exception as e:
        # A catch-all for other unexpected errors, like JSON decoding failure
        print(f"Unexpected error during login process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login."
        )

