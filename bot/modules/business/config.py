import os

class BusinessConfig:
    """Business module configuration"""
    
    # VPS Settings
    VPS_HOST = os.getenv("VPS_HOST")
    VPS_PORT = int(os.getenv("VPS_PORT", "22"))
    VPS_USERNAME = os.getenv("VPS_USERNAME")
    VPS_PRIVATE_KEY = os.getenv("VPS_PRIVATE_KEY")
    
    # Docker Settings
    DOCKER_NETWORK = "n8n_network"
    DOCKER_IMAGE = "n8nio/n8n:latest"
    
    # Client Settings
    BASE_PORT = 5678
    MAX_CLIENTS = 10
