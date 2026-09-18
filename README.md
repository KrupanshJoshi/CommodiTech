# Commodity Compliance Scanner — Full Stack

Smart India Hackathon (SIH) 2026 Problem Statement.

An automated regulatory inspection and statutory assurance application connecting a modern **Google Stitch UI Frontend** (React + TypeScript + Tailwind CSS) with a robust **Flask REST API Backend**, SQLite database, OpenCV image preprocessing, real Tesseract OCR, deterministic 15-rule compliance engine, and ReportLab PDF assessment generator.

---

## Architecture Flow

```
Stitch Frontend (React + Vite + TS)
        ↓  (REST API with JWT Bearer Token)
Flask Backend (app.py / routes / models)
        ↓
Tesseract OCR + OpenCV Preprocessing (CLAHE, deskew, adaptive threshold)
        ↓
Field Extraction & Garbage Filter (12 mandatory parameters)
        ↓
Human Verification & Rectification (/scan/review/:id)
        ↓
Deterministic Compliance Engine (15 statutory rules R01–R15)
        ↓
Score & Categorized Findings (PASS / WARNING / FAIL + Recommendations)
        ↓
Official PDF Assessment Report (ReportLab) & SQLite Ledger
```

---

## Project Structure

```
commodity-compliance-scanner/
├── frontend/                     # React 19 + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── api/client.ts         # Centralized REST API service
│   │   ├── context/AuthContext.tsx # JWT auth & session persistence
│   │   ├── pages/                # 8 Integrated Stitch UI screens
│   │   │   ├── Login.tsx         # Terminal Authentication & Inspector Registration
│   │   │   ├── Dashboard.tsx     # Cockpit metrics & real-time distribution
│   │   │   ├── NewScan.tsx       # Ingestion & Tesseract OCR pipeline
│   │   │   ├── DataReview.tsx    # 12-Field human review & date pickers
│   │   │   ├── ComplianceResult.tsx # Deterministic rule findings & score gauge
│   │   │   ├── ReportView.tsx    # Official PDF preview & certificate download
│   │   │   ├── ScanHistory.tsx   # Consignment search, filter & ledger
│   │   │   ├── RulesRegistry.tsx # 15 Statutory rules reference & modal
│   │   │   └── Settings.tsx      # Profile update & terminal diagnostics
│   │   └── types/index.ts        # Full domain & API TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── backend/                      # Flask 3 REST API
│   ├── app.py                    # Flask application factory
│   ├── config.py                 # Configuration & environment loader
│   ├── extensions.py             # SQLAlchemy & CORS singletons
│   ├── models/                   # User, Scan, Report ORM entities
│   ├── routes/                   # Auth, Scans, OCR, Compliance, Reports, Dashboard, Rules, Settings
│   ├── services/                 # OCR, Field Extraction, Compliance Engine, PDF Generation
│   ├── utils/                    # JWT auth decorators, validators, SQLite shim
│   ├── database/                 # SQLite storage (compliance_scanner.db)
│   ├── uploads/                  # Ingested label images
│   └── reports/                  # Generated PDF compliance dossiers
├── tests/
│   └── test_api.py               # Complete pytest test suite
├── sample_images/                # Sample test labels (compliant, partial, missing)
├── requirements.txt              # Backend dependencies
├── run.py                        # Backend server entrypoint
└── README.md
```

---

## Quick Start & Running the Application

### 1. Start the Flask Backend API

```powershell
# In workspace root:
python run.py
```
- API will start at: `http://localhost:5000`
- Database initialized automatically at `backend/database/compliance_scanner.db`

### 2. Start the Stitch Frontend

```powershell
# In a new terminal window:
cd frontend
npm install
npm run dev
```
- Frontend will open at: `http://localhost:5173`

---

## Running Automated Tests & Builds

### Run Backend Pytest Suite
```powershell
python -m pytest tests/ -v
```

### Build Frontend Production Bundle
```powershell
cd frontend
npm run build
```

---

## Authentication & Demo Access

- **One-click demo credentials**: Click `⚡ Auto-fill Demo` on the login screen or register any inspector email.
- **Default inspector**: `inspector@fssai.gov.in` / `demo123456`
- **Security**: Stateless HMAC-SHA256 JWT Bearer tokens passed on all requests via `Authorization: Bearer <token>`.

---

## End-to-End Workflow Demonstration

1. **Terminal Authentication**: Register or login as an authorized inspector.
2. **Dashboard Overview**: Monitor total scanned consignments, pass rate, average compliance score, and recent audit logs.
3. **Launch New Inspection**: Select commodity category (e.g. *Turmeric Powder*), upload packaging image or choose sample preset.
4. **Automated Vision & OCR**: Image is preprocessed with OpenCV (CLAHE, deskew, noise filtering) and characters extracted via Tesseract.
5. **Human Review & Verification**: Review 12 mandatory statutory declarations with confidence indicators, rectify uncertain values using calendar date pickers, and confirm.
6. **Deterministic Compliance Assessment**: 15 statutory checks (R01–R15) deterministically evaluated to compute compliance score, blocking failures, advisory notices, and actionable recommendations.
7. **Official PDF Assessment Report**: Generate and download an authenticated statutory compliance certificate.
8. **Consignment Ledger**: Search, filter, inspect, and manage archived consignment audits in the ledger.
