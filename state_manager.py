"""
State management for Project Autotroph with transaction safety and atomic operations
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from firebase_client import (
    FirebaseClient, 
    atomic_increment, 
    get_document, 
    update_document
)
from config import firebase_config

logger = logging.getLogger(__name__)

class StateManager:
    """Manages agent state with atomic operations and consistency guarantees"""
    
    def __init__(self):
        self.client = FirebaseClient.get_client()
        self.collections = firebase_config.collections
    
    # ============ AGENT STATE OPERATIONS ============
    
    def get_agent_state(self) -> Dict[str, Any]:
        """Get current agent state with defaults for missing values"""
        state = get_document("agent_state", "current") or {}
        
        # Set defaults for required fields
        defaults = {
            "last_nonce": 0,
            "gas_price_ceiling_gwei": 20.0,
            "min_profit_usd": 0.01,
            "operational_wallet_balance": "0.0",
            "hardware_fund_address": "",
            "last_cycle_time": datetime.utcnow().isoformat() + "Z",
            "circuit_breaker_active": False,
            "total_profit_usd": 0.0,
            "cycles_executed": 0
        }
        
        # Merge with defaults
        return {**defaults, **state}
    
    def update_agent_state(self, updates: Dict[str, Any]) -> bool:
        """Update agent state atomically"""
        return update_document("agent_state", "current", updates)
    
    def increment_nonce(self) -> int:
        """Atomically increment and return new nonce"""
        return atomic_increment("agent_state", "current", "last_nonce")
    
    def get_current_nonce(self) -> int:
        """Get current nonce without incrementing"""
        state = self.get_agent_state()
        return state.get("last_nonce", 0)
    
    # ============ CYCLE LOGGING ============
    
    def log_cycle(self, cycle_data: Dict[str, Any]) -> str:
        """
        Log a complete cycle with timestamp
        
        Args:
            cycle_data: Dictionary containing cycle information
            
        Returns:
            Generated cycle ID
        """
        cycle_id = f"cycle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Add metadata
        cycle_data.update({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cycle_id": cycle_id
        })
        
        try:
            collection = FirebaseClient.get_collection("cycle_logs")
            collection.document(cycle_id).set(cycle_data)
            logger.info(f"Logged cycle {cycle_id}")
            return cycle_id
        except Exception as e:
            logger.error(f"Failed to log cycle: {e}")
            raise
    
    # ============ TRANSACTION QUEUE MANAGEMENT ============
    
    def add_to_transaction_queue(self, tx_hash: str, nonce: int) -> bool:
        """Add transaction to queue with timeout"""
        try:
            queue_data = {
                "status": "pending",
                "tx_hash": tx_hash,
                "nonce": nonce,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "timeout_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z",
                "retry_count": 0,
                "confirmed": False
            }
            
            collection = FirebaseClient.get_collection("transaction_queue")
            collection.document(f"tx_{nonce}").set(queue_data)
            return True
        except Exception as e:
            logger.error(f"Failed to add transaction to queue: {e}")
            return False
    
    def update_transaction_status(self, nonce: int, status: str, **kwargs) -> bool:
        """Update transaction status and additional data"""
        try:
            doc_ref = FirebaseClient.get_collection("transaction_queue").document(f"tx_{nonce}")
            update_data = {"status": status, **kwargs}
            
            # If transaction is confirmed or failed, mark it as processed
            if status in ["confirmed", "failed"]:
                update_data["processed_at"] = datetime.utcnow().isoformat() + "Z"
            
            doc_ref.update(update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update transaction status: {e}")
            return False
    
    def get_pending_transactions(self) -> list:
        """Get all pending transactions"""
        try:
            collection = FirebaseClient.get_collection("transaction_queue")
            query = collection.where("status", "==", "pending")
            docs = query.stream()
            
            pending = []
            for doc in docs:
                data = doc.to_dict()
                data["doc_id"] = doc.id
                pending.append(data)
            
            return pending
        except Exception as e:
            logger.error(f"Failed to get pending transactions: {e}")
            return []
    
    def cleanup_old_transactions(self, hours_old: int = 24):
        """Clean up old processed transactions"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)
            collection = FirebaseClient.get_collection("transaction_queue")
            
            # Get old processed transactions
            query = collection.where("processed_at", "<", cutoff_time.isoformat() + "Z")
            
            batch = self.client.batch()
            count = 0
            
            for doc in query.stream():
                batch.delete(doc.reference)
                count += 1
                
                # Firestore batch limit is 500 operations
                if count % 500 == 0:
                    batch.commit()
                    batch = self.client.batch()
            
            if count % 500 != 0:
                batch.commit()
            
            logger.info(f"Cleaned up {count} old transactions")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old transactions: {e}")
    
    # ============ HARDWARE FUND LEDGER ============
    
    def log_hardware_fund_transfer(self, amount_usd: float, tx_hash: str) -> bool:
        """Log verified hardware fund transfer"""
        try:
            transfer_id = f"transfer_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            transfer_data = {
                "transfer_id": transfer_id,
                "amount_usd": amount_usd,
                "tx_hash": tx_hash,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "verified": True,  # Only logged after manual verification in v0.1
                "verified_by": "manual_v0.1",
                "verified_at": datetime.utcnow().isoformat() + "Z"
            }
            
            collection = FirebaseClient.get_collection("hardware_fund_ledger")
            collection.document(transfer_id).set(transfer_data)
            
            # Update total hardware fund contributions
            current_state = self.get_agent_state()
            new_total