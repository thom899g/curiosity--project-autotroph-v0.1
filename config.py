"""
Configuration module for Project Autotroph v0.1
Centralized configuration with environment variable validation
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class FirebaseConfig:
    """Firebase configuration with validation"""
    credentials_path: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
    project_id: str = os.getenv("FIREBASE_PROJECT_ID", "project-autotroph")
    collections: dict = None
    
    def __post_init__(self):
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Firebase credentials not found at {self.credentials_path}")
        self.collections = {
            "agent_state": "agent_state",
            "cycle_logs": "cycle_logs",
            "transaction_queue": "transaction_queue",
            "hardware_fund_ledger": "hardware_fund_ledger"
        }

@dataclass
class BlockchainConfig:
    """Blockchain network and wallet configuration"""
    rpc_url: str = os.getenv("WEB3_RPC_URL", "https://mainnet.base.org")
    chain_id: int = int(os.getenv("CHAIN_ID", "8453"))  # Base mainnet
    operational_wallet_pk: Optional[str] = os.getenv("OPERATIONAL_WALLET_PK")
    hardware_fund_address: str = os.getenv("HARDWARE_FUND_ADDRESS", "0x0000000000000000000000000000000000000000")
    
    # Gas parameters
    max_gas_price_gwei: float = float(os.getenv("MAX_GAS_PRICE_GWEI", "20"))
    min_profit_usd: float = float(os.getenv("MIN_PROFIT_USD", "0.01"))
    
    # Safety limits
    min_eth_balance: float = float(os.getenv("MIN_ETH_BALANCE", "0.001"))
    
    def __post_init__(self):
        if not self.operational_wallet_pk:
            raise ValueError("OPERATIONAL_WALLET_PK environment variable is required")

@dataclass
class TradingConfig:
    """Trading strategy and market configuration"""
    # Uniswap V3 Base pools
    usdc_dai_pool: str = "0x4C36388bE6F416A29C8d8Eee81C771cE6bE14B18"
    usdc_address: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    dai_address: str = "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
    
    # Subgraph endpoint
    uniswap_subgraph_url: str = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
    
    # Thresholds
    imbalance_threshold: float = 0.005  # 0.5%
    min_liquidity_usd: float = 10000.0
    slippage_tolerance: float = 0.005  # 0.5%
    deadline_seconds: int = 30
    
    # Cycle frequency (seconds)
    sense_interval: int = 300

@dataclass
class TelegramConfig:
    """Telegram alerting configuration"""
    bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
    enabled: bool = bool(os.getenv("TELEGRAM_ENABLED", "True"))

# Global configuration instances
firebase_config = FirebaseConfig()
blockchain_config = BlockchainConfig()
trading_config = TradingConfig()
telegram_config = TelegramConfig()

# Export configuration
__all__ = ['firebase_config', 'blockchain_config', 'trading_config', 'telegram_config']