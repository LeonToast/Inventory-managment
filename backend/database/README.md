# Database design

This folder contains the MongoDB schema and index setup for the inventory management project.

## Collections

- `Medlem` - members/admin accounts
- `register-validering` - pending account applications
- `warehouse` - warehouse locations
- `material` - inventory items
- `deliveries` - inbound deliveries
- `reports` - announcements and reports
- `audit_logs` - system activity log
- `settings` - configuration values

## Initialize the database

```python
from pymongo import MongoClient
from backend.database import initialize_database

client = MongoClient("mongodb+srv://...")
db = client["inventory-manager"]
initialize_database(db)
```
