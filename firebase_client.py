"""
Firebase Firestore client with connection pooling and error handling
"""
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient
from typing import Optional
import logging
from config import firebase_config

logger = logging.getLogger(__name__)

class FirebaseClient:
    """Singleton Firebase Firestore client with automatic initialization"""
    _instance: Optional[FirestoreClient] = None
    
    @classmethod
    def get_client(cls) -> FirestoreClient:
        """Get or initialize Firestore client singleton"""
        if cls._instance is None:
            try:
                # Initialize Firebase app if not already initialized
                if not firebase_admin._apps:
                    cred = credentials.Certificate(firebase_config.credentials_path)
                    firebase_admin.initialize_app(cred, {
                        'projectId': firebase_config.project_id
                    })
                
                cls._instance = firestore.client()
                logger.info("Firebase Firestore client initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize Firebase client: {e}")
                raise ConnectionError(f"Firebase initialization failed: {e}")
        
        return cls._instance
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """Get reference to specific collection"""
        client = cls.get_client()
        return client.collection(firebase_config.collections[collection_name])
    
    @classmethod
    def health_check(cls) -> bool:
        """Verify Firebase connectivity"""
        try:
            client = cls.get_client()
            # Simple read operation to test connection
            doc_ref = client.collection('health_check').document('test')
            doc_ref.set({'timestamp': firestore.SERVER_TIMESTAMP}, merge=True)
            return True
        except Exception as e:
            logger.error(f"Firebase health check failed: {e}")
            return False

# Utility functions for common operations
def atomic_increment(collection: str, doc_id: str, field: str, amount: int = 1) -> int:
    """
    Atomically increment a field in Firestore
    
    Args:
        collection: Collection name
        doc_id: Document ID
        field: Field to increment
        amount: Increment amount
        
    Returns:
        New value after increment
    """
    @firestore.transactional
    def update_in_transaction(transaction, doc_ref):
        snapshot = doc_ref.get(transaction=transaction)
        if snapshot.exists:
            current_value = snapshot.get(field) or 0
            new_value = current_value + amount
            transaction.update(doc_ref, {field: new_value})
            return new_value
        else:
            # Initialize document if it doesn't exist
            transaction.set(doc_ref, {field: amount})
            return amount
    
    try:
        client = FirebaseClient.get_client()
        doc_ref = client.collection(firebase_config.collections[collection]).document(doc_id)
        transaction = client.transaction()
        return update_in_transaction(transaction, doc_ref)
    except Exception as e:
        logger.error(f"Atomic increment failed: {e}")
        raise

def get_document(collection: str, doc_id: str) -> Optional[dict]:
    """Safe document retrieval with error handling"""
    try:
        client = FirebaseClient.get_client()
        doc_ref = client.collection(firebase_config.collections[collection]).document(doc_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Failed to get document {doc_id} from {collection}: {e}")
        return None

def update_document(collection: str, doc_id: str, data: dict, merge: bool = True) -> bool:
    """Update document with error handling"""
    try:
        client = FirebaseClient.get_client()
        doc_ref = client.collection(firebase_config.collections[collection]).document(doc_id)
        doc_ref.set(data, merge=merge)
        return True
    except Exception as e:
        logger.error(f"Failed to update document {doc_id} in {collection}: {e}")
        return False

__all__ = ['FirebaseClient', 'atomic_increment', 'get_document', 'update_document']