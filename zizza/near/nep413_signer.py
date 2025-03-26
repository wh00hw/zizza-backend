import base64
import hashlib
from borsh_construct import CStruct, String, Option, U8

standard_number = {
    "nep413": 413,
}

Nep413PayloadSchema = CStruct(
    "message" / String,
    "nonce" / U8[32],
    "recipient" / String,
    "callback_url" / Option(String),
)

def base64_to_uint8_array(b64_str):
    return list(base64.b64decode(b64_str))

def serialize_intent(intent_message, recipient, nonce, standard="nep413"):
    payload = {
        "message": intent_message,
        "nonce": base64_to_uint8_array(nonce),
        "recipient": recipient,
        "callback_url": None,
    }
    
    payload_serialized = Nep413PayloadSchema.build(payload)
    
    base_int = (2 ** 31) + standard_number[standard]
    base_int_serialized = base_int.to_bytes(4, byteorder='little', signed=False)
    combined_data = base_int_serialized + payload_serialized
    return hashlib.sha256(combined_data).digest()
