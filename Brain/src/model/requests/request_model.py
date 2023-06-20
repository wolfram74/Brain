from typing import Optional

from pydantic import BaseModel
from fastapi import Depends, Request, HTTPException
from user_agents import parse

from Brain.src.common.utils import (
    DEFAULT_HOST_NAME,
    OPENAI_API_KEY,
    PINECONE_KEY,
    FIREBASE_ENV,
    PINECONE_ENV,
)

"""user-agent management"""


class ClientInfo:
    def __init__(self, browser, os, device_type):
        self.browser = browser
        self.os = os
        self.device_type = device_type

    def is_browser(self) -> bool:
        if (
            self.browser == "Chrome"
            or self.browser == "Firefox"
            or self.browser == "Safari"
            or self.browser == "Edge"
        ):
            return True
        return False


def parse_user_agent(user_agent: str) -> Optional[ClientInfo]:
    if not user_agent:
        return None

    ua = parse(user_agent)

    device_type = "desktop" if ua.is_pc else "mobile" if ua.is_mobile else "tablet"
    client_info = ClientInfo(
        browser=ua.browser.family, os=ua.os.family, device_type=device_type
    )

    return client_info


def get_client_info(request: Request):
    user_agent = request.headers.get("user-agent", "")

    if not user_agent:
        raise HTTPException(
            status_code=400,
            detail="User-Agent header is required",
        )

    return parse_user_agent(user_agent)


"""
{
    "host_name": string,
    "openai_key": string, 
    "pinecone_key": string, 
    "pinecone_env": string,
    "firebase_key": string,
    "settings": {
            "temperature": float
        }, 
    "token": string, 
    "uuid": string, 
}
"""


class BasicReq(BaseModel):
    class Settings(BaseModel):
        temperature: float = 0.6

    host_name: str
    openai_key: str
    pinecone_key: str
    pinecone_env: str
    firebase_key: str
    token: str = ""
    uuid: str = ""
    settings: Settings

    def to_json(self):
        return {
            "host_name": self.host_name,
            "openai_key": self.openai_key,
            "pinecone_key": self.pinecone_key,
            "pinecone_env": self.pinecone_env,
            "firebase_key": self.firebase_key,
            "settings": {"temperature": self.settings.temperature},
            "token": self.token,
            "uuid": self.uuid,
        }


"""endpoint: /sendNotification"""


class Notification(BasicReq):
    message: str


"""endpoint: /uploadImage"""


class UploadImage(BasicReq):
    image_name: str
    status: str


"""endpoint: /image_relatedness"""


class ImageRelatedness(BasicReq):
    image_name: str
    message: str


"""endpoint: /feedback"""


class Feedback(BasicReq):
    class Prompt(BaseModel):
        image_name: str
        message: str

    prompt: Prompt
    completion: Prompt
    rating: int


"""endpoint: /chat_rising"""


class ChatRising(BasicReq):
    class Format(BaseModel):
        role: str
        content: str

    history: list[Format]
    user_input: str
    model: str


"""endpoint: /send_sms"""


class SendSMS(BasicReq):
    class Body(BaseModel):
        _from: str
        to: str
        body: str

    data: Body


"""endpoint : /train/contacts"""


class TrainContacts(BasicReq):
    class ContactReq(BaseModel):
        contactId: str
        displayName: str
        phoneNumbers: list[str]
        status: str

    contacts: list[ContactReq]


"""endpoint /browser/item"""


class BrowserItem(BasicReq):
    class ItemReq(BaseModel):
        title: str
        link: str

    items: list[ItemReq]
    prompt: str
