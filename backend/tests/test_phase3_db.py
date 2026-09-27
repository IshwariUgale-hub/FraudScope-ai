"""Phase 3 Test Suite: Database persistence, behavioral context calculation, and API endpoints.

Tests all required Phase 3 functionalities:
1. Database connectivity
2. Direct transaction model persistence
3. Transaction scoring with PostgreSQL/SQLAlchemy persistence
4. Retrieval of transaction by transaction_id
5. Retrieval of user transaction history with pagination
6. Backend behavioral context calculation from DB history (velocity & seconds_since_prev)
7. Cold-start user handling (no prior history)
8. Input validation error handling (422)
9. Non-existent transaction retrieval (404)
"""

import sys
import unittest
from pathlib import Path

# Ensure paths are configured
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_project_root = _backend_dir.parent
for _p in (str(_backend_dir), str(_project_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.transaction import Transaction
from app.services.fraud_service import fraud_service

# Create isolated in-memory test database with StaticPool so all connections share the DB
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply dependency override
app.dependency_overrides[get_db] = override_get_db


class Phase3DatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)
        # Initialize the ML model once for testing
        fraud_service.initialize()
        cls._client_context = TestClient(app)
        cls.client = cls._client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._client_context.__exit__(None, None, None)
        Base.metadata.drop_all(bind=test_engine)
        app.dependency_overrides.clear()

    def setUp(self):
        # Clean up tables between test runs
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)

    def test_01_database_health(self):
        """Verifies health check endpoint and database connectivity."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("database", data)

    def test_02_direct_model_persistence(self):
        """Verifies direct SQLAlchemy Transaction model creation and querying."""
        db = TestingSessionLocal()
        txn = Transaction(
            transaction_id="TXN-UNITTEST-001",
            user_id="U_TEST_001",
            amount=5000.0,
            timestamp=1727448000,
            device_id="test_device_1",
            location="Mumbai",
            currency="Rs",
            txn_count_10min=1,
            seconds_since_prev=86400.0,
            risk_score=25,
            risk_level="LOW",
            ml_probability=0.15,
            ml_points=9.0,
            rule_points=16.0,
            recommended_action="Allow",
            summary="Low risk transaction.",
            reasons=[{"signal": "Normal", "detail": "All ok", "points": 0.0}],
            features={"log_amount": 8.5},
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        self.assertIsNotNone(txn.id)
        queried = db.query(Transaction).filter_by(transaction_id="TXN-UNITTEST-001").first()
        self.assertIsNotNone(queried)
        self.assertEqual(queried.user_id, "U_TEST_001")
        self.assertEqual(queried.amount, 5000.0)
        db.close()

    def test_03_score_and_persist_transaction(self):
        """Tests POST /api/v1/transactions/score and verifies record was saved in DB."""
        payload = {
            "user_id": "C_DEMO_01",
            "amount": 85000.0,
            "hour": 2,
            "device_id": "device_new_x",
            "location": "Delhi",
            "txn_count_10min": 7,
            "seconds_since_prev": 120.0,
        }
        resp = self.client.post("/api/v1/transactions/score", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("transaction_id", data)
        self.assertIn("risk_score", data)
        self.assertIn("risk_level", data)
        self.assertIn("reasons", data)
        self.assertIn("summary", data)

        txn_id = data["transaction_id"]

        # Verify presence in database
        db = TestingSessionLocal()
        stored = db.query(Transaction).filter_by(transaction_id=txn_id).first()
        self.assertIsNotNone(stored)
        self.assertEqual(stored.amount, 85000.0)
        self.assertEqual(stored.risk_score, data["risk_score"])
        self.assertEqual(stored.risk_level, data["risk_level"])
        db.close()

    def test_04_get_transaction_by_id(self):
        """Tests GET /api/v1/transactions/{transaction_id}."""
        # Score a transaction first
        payload = {
            "user_id": "U_FETCH_01",
            "amount": 1200.0,
            "hour": 14,
            "device_id": "device_android",
            "location": "Pune",
        }
        score_resp = self.client.post("/api/v1/transactions/score", json=payload)
        self.assertEqual(score_resp.status_code, 200)
        txn_id = score_resp.json()["transaction_id"]

        # Retrieve by ID
        fetch_resp = self.client.get(f"/api/v1/transactions/{txn_id}")
        self.assertEqual(fetch_resp.status_code, 200)
        detail = fetch_resp.json()
        self.assertEqual(detail["transaction_id"], txn_id)
        self.assertEqual(detail["user_id"], "U_FETCH_01")
        self.assertEqual(detail["amount"], 1200.0)
        self.assertEqual(detail["location"], "Pune")

    def test_05_get_transaction_not_found(self):
        """Tests GET /api/v1/transactions/nonexistent returns 404."""
        resp = self.client.get("/api/v1/transactions/TXN-NONEXISTENT")
        self.assertEqual(resp.status_code, 404)

    def test_06_get_user_transactions(self):
        """Tests GET /api/v1/users/{user_id}/transactions pagination."""
        user_id = "U_HISTORY_USER"
        # Create 3 transactions for this user
        for i in range(3):
            payload = {
                "user_id": user_id,
                "amount": 1000.0 * (i + 1),
                "hour": 10 + i,
                "device_id": "dev_1",
                "location": "Bengaluru",
            }
            res = self.client.post("/api/v1/transactions/score", json=payload)
            self.assertEqual(res.status_code, 200)

        # Retrieve user transactions
        resp = self.client.get(f"/api/v1/users/{user_id}/transactions?limit=10&skip=0")
        self.assertEqual(resp.status_code, 200)
        hist = resp.json()
        self.assertEqual(hist["user_id"], user_id)
        self.assertEqual(hist["total_transactions"], 3)
        self.assertEqual(len(hist["transactions"]), 3)

    def test_07_backend_derived_behavioral_context(self):
        """Verifies that consecutive transactions derive velocity and time delta from DB."""
        user_id = "U_VELOCITY_TEST"
        t0 = 1727448000

        # Txn 1: Base transaction
        res1 = self.client.post("/api/v1/transactions/score", json={
            "user_id": user_id,
            "amount": 2000.0,
            "hour": 10,
            "device_id": "device_known",
            "location": "Mumbai",
            "timestamp": t0,
        })
        self.assertEqual(res1.status_code, 200)
        txn1_id = res1.json()["transaction_id"]

        # Txn 2: 120 seconds later
        # Even if client passes bogus txn_count_10min=99, DB derived context must prevail!
        res2 = self.client.post("/api/v1/transactions/score", json={
            "user_id": user_id,
            "amount": 2500.0,
            "hour": 10,
            "device_id": "device_known",
            "location": "Mumbai",
            "timestamp": t0 + 120,
            "txn_count_10min": 99,  # Bogus client input
        })
        self.assertEqual(res2.status_code, 200)
        txn2_id = res2.json()["transaction_id"]

        # Verify stored context in DB
        db = TestingSessionLocal()
        stored2 = db.query(Transaction).filter_by(transaction_id=txn2_id).first()
        self.assertEqual(stored2.seconds_since_prev, 120.0)
        # Should be 2 transactions in last 10 minutes (Txn 1 + Txn 2), NOT 99!
        self.assertEqual(stored2.txn_count_10min, 2)
        # Device was seen in Txn 1, so is_new_device must be 0
        self.assertEqual(stored2.is_new_device, 0)
        db.close()

    def test_08_cold_start_user(self):
        """Verifies safe cold-start handling for brand new user with no DB or profile history."""
        new_user = "U_COLD_START_999"
        res = self.client.post("/api/v1/transactions/score", json={
            "user_id": new_user,
            "amount": 3000.0,
            "hour": 12,
            "device_id": "new_phone",
            "location": "Jaipur",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("risk_score", data)
        self.assertIn("risk_level", data)

        # Check stored default context
        db = TestingSessionLocal()
        stored = db.query(Transaction).filter_by(transaction_id=data["transaction_id"]).first()
        self.assertEqual(stored.txn_count_10min, 1)
        self.assertEqual(stored.seconds_since_prev, 86400.0)
        db.close()

    def test_09_invalid_input_validation(self):
        """Verifies that invalid amounts or hours return clean 422 errors."""
        # Negative amount
        res_amt = self.client.post("/api/v1/transactions/score", json={
            "user_id": "U_ERR",
            "amount": -50.0,
            "hour": 12,
            "device_id": "dev",
            "location": "Pune",
        })
        self.assertEqual(res_amt.status_code, 422)

        # Invalid hour
        res_hr = self.client.post("/api/v1/transactions/score", json={
            "user_id": "U_ERR",
            "amount": 500.0,
            "hour": 28,
            "device_id": "dev",
            "location": "Pune",
        })
        self.assertEqual(res_hr.status_code, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
