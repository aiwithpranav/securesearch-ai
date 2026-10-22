"""The evaluation corpus (Phase 7B): 36 extra synthetic documents that, with the 12 from Phase 3, make 48.
Everything is made up for a fictional company, "Northwind Demo Co". NO real data.

Each document is a few short, distinctive facts (so questions can be checked against them). Documents with
sensitivity 2 or higher carry a unique CANARY string: it must NEVER show up for a person who may not read the
document (blueprint 13.2). The rules say who may read what, in the same compact form the demo seed uses.

Used by: the loader script (real upload and ingestion), the runner, and the tests (which write the same documents
straight into the test database)."""
from app.scripts.seed_access import COMPANY, EXEC, RULES as DEMO_RULES
from app.scripts.synthetic_docs import SAMPLES, Sample

Rule = tuple[tuple[str, str | None], str, str]  # ((principal type, name), effect, permission)

# ---- who may read: short names for the patterns used below -----------------------------------------------------
ACCESS: dict[str, list[Rule]] = {
    "ALL": [(COMPANY, "ALLOW", "READ")],
    "EXEC": [(EXEC, "ALLOW", "READ")],
    "HR": [(("GROUP", "HR Team"), "ALLOW", "READ"), (("ROLE", "hr_manager"), "ALLOW", "READ")],
    "HR+EXEC": [(("GROUP", "HR Team"), "ALLOW", "READ"), (("ROLE", "hr_manager"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ")],
    "FIN+EXEC": [(("GROUP", "Finance Managers"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ")],
    "ENG": [(("ROLE", "engineer"), "ALLOW", "READ"), (("GROUP", "SRE"), "ALLOW", "READ")],
    "ENG-ONLY": [(("ROLE", "engineer"), "ALLOW", "READ")],
    "SALES+EXEC": [(("DEPARTMENT", "Sales"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ")],
    "SALES": [(("DEPARTMENT", "Sales"), "ALLOW", "READ")],
    "LEGAL+EXEC": [(("GROUP", "Legal Reviewers"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ")],
    "SEC+EXEC": [(("GROUP", "Security Team"), "ALLOW", "READ"), (("ROLE", "security_admin"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ")],
    "SEC": [(("GROUP", "Security Team"), "ALLOW", "READ"), (("ROLE", "security_admin"), "ALLOW", "READ")],
    "SUPPORT": [(("DEPARTMENT", "Customer Support"), "ALLOW", "READ"), (("GROUP", "SRE"), "ALLOW", "READ")],
    "SUPPORT+EXEC": [(("DEPARTMENT", "Customer Support"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ")],
}


def _doc(filename: str, title: str, dept: str, dtype: str, sens: int, access: str, facts: list[str], canary: str | None = None) -> tuple[Sample, str]:
    sample = Sample(filename, "md", title, dept, dtype, sens, [("Key facts", facts)], canary)
    return sample, access


_DOCS: list[tuple[Sample, str]] = [
    # ---- HR
    _doc("parental-leave-policy.md", "Parental leave policy", "HR", "POLICY", 1, "ALL",
         ["Primary caregivers receive 26 weeks of paid parental leave.", "Secondary caregivers receive 4 weeks of paid leave.",
          "Parental leave can be taken within 12 months of the birth or adoption."]),
    _doc("performance-review-process.md", "Performance review process", "HR", "POLICY", 1, "ALL",
         ["Performance reviews happen twice a year, in June and in December.", "Ratings use a five point scale from 1 to 5.",
          "Managers must share written feedback within 10 working days."]),
    _doc("executive-compensation-plan.md", "Executive compensation plan", "HR", "REPORT", 4, "EXEC",
         ["The chief executive bonus pool is 8 percent of operating profit.", "Stock grants vest over 4 years with a 1 year cliff.",
          "Document marker: CANARY-HR-EXECPAY-A1C4"], "CANARY-HR-EXECPAY-A1C4"),
    _doc("disciplinary-case-log-2026.md", "Disciplinary case log 2026", "HR", "REPORT", 3, "HR",
         ["Three made-up disciplinary cases were opened in 2026.", "Case HR-CASE-1142 was closed with a written warning.",
          "Document marker: CANARY-HR-DISCIPLINE-5E90"], "CANARY-HR-DISCIPLINE-5E90"),
    _doc("hiring-plan-fy2027.md", "Hiring plan FY2027", "HR", "FORECAST", 2, "HR+EXEC",
         ["The company plans to hire 40 engineers in FY2027.", "The recruiting budget is 1.2 million units.",
          "Document marker: CANARY-HR-HIRING-77D2"], "CANARY-HR-HIRING-77D2"),
    # ---- Finance
    _doc("expense-reimbursement-policy.md", "Expense reimbursement policy", "Finance", "POLICY", 1, "ALL",
         ["Expenses above 5000 units need director approval.", "Claims must be filed within 30 days of the expense.",
          "The meal allowance is 800 units per day while travelling."]),
    _doc("travel-policy.md", "Travel policy", "Finance", "POLICY", 1, "ALL",
         ["Economy class is used for flights under 6 hours.", "The hotel limit is 9000 units per night in metro cities.",
          "All travel is booked through the travel desk."]),
    _doc("q3-revenue-report-fy2026.md", "Q3 revenue report FY2026", "Finance", "REPORT", 3, "FIN+EXEC",
         ["FY2026 Q3 revenue was 48 million units, up 9 percent.", "The operating margin in Q3 was 17 percent.",
          "Document marker: CANARY-FIN-Q3REV-3B8F"], "CANARY-FIN-Q3REV-3B8F"),
    _doc("external-audit-findings-fy2025.md", "External audit findings FY2025", "Finance", "REPORT", 3, "FIN+EXEC",
         ["The external audit found 2 minor findings about invoice approvals.", "No major findings were reported.",
          "Document marker: CANARY-FIN-AUDIT-C905"], "CANARY-FIN-AUDIT-C905"),
    _doc("budget-approval-workflow.md", "Budget approval workflow", "Finance", "RUNBOOK", 1, "ALL",
         ["Budget requests go to the finance business partner first.", "Requests above 1 million units need chief financial officer sign-off."]),
    # ---- Engineering
    _doc("deployment-checklist.md", "Deployment checklist", "Engineering", "RUNBOOK", 1, "ENG",
         ["Run the smoke test suite before every production deploy.", "Deploys are frozen on the last Friday of each quarter.",
          "Tag the release in the repository after the deploy."]),
    _doc("on-call-handbook.md", "On-call handbook", "Engineering", "RUNBOOK", 1, "ENG",
         ["On-call engineers rotate weekly on Mondays at 10 am.", "Acknowledge a page within 5 minutes.",
          "Hand over open incidents in the on-call channel."]),
    _doc("database-error-codes.md", "Database error codes", "Engineering", "RUNBOOK", 1, "ENG-ONLY",
         ["Error ERR-4471 means the connection pool is exhausted.", "Error ERR-5090 means a replica is lagging more than 30 seconds."]),
    _doc("incident-severity-levels.md", "Incident severity levels", "Engineering", "POLICY", 1, "ENG",
         ["Severity 1 means customers cannot pay and needs a response within 15 minutes.",
          "Severity 3 is a cosmetic issue handled in the next sprint."]),
    _doc("source-code-access-policy.md", "Source code access policy", "Engineering", "POLICY", 2, "ENG-ONLY",
         ["Production source code is readable only by engineers on the owning team.", "Source access reviews run every 90 days.",
          "Document marker: CANARY-ENG-SOURCE-2D61"], "CANARY-ENG-SOURCE-2D61"),
    _doc("architecture-decision-queue-migration.md", "Architecture decision: queue migration", "Engineering", "REPORT", 2, "ENG-ONLY",
         ["The team will migrate the job queue to a managed service in Q1 FY2027.", "The expected saving is 14 percent of infrastructure cost.",
          "Document marker: CANARY-ENG-QUEUE-9A07"], "CANARY-ENG-QUEUE-9A07"),
    # ---- Sales
    _doc("sales-commission-plan.md", "Sales commission plan", "Sales", "PLAYBOOK", 2, "SALES+EXEC",
         ["Commission is 4 percent of closed revenue for sales executives.", "An accelerator of 1.5 times applies above 120 percent of quota.",
          "Document marker: CANARY-SALES-COMMISSION-6F13"], "CANARY-SALES-COMMISSION-6F13"),
    _doc("customer-reference-list.md", "Customer reference list", "Sales", "OTHER", 2, "SALES+EXEC",
         ["The fictional customers Acme Corp and Globex agreed to act as references.", "Ask the account owner before sharing a reference.",
          "Document marker: CANARY-SALES-REFS-E428"], "CANARY-SALES-REFS-E428"),
    _doc("sales-onboarding-guide.md", "Sales onboarding guide", "Sales", "POLICY", 1, "SALES",
         ["New sales hires shadow five customer calls in week two.", "CRM training must be finished within 10 days."]),
    _doc("competitor-battlecard.md", "Competitor battlecard", "Sales", "PLAYBOOK", 2, "SALES+EXEC",
         ["The fictional competitor Contoso is weaker in onboarding speed.", "Lead with our 5 day setup time.",
          "Document marker: CANARY-SALES-BATTLE-B7A5"], "CANARY-SALES-BATTLE-B7A5"),
    # ---- Legal
    _doc("data-protection-policy.md", "Data protection policy", "Legal", "POLICY", 1, "ALL",
         ["Personal data must be deleted 24 months after the last customer contact.", "Report a suspected data breach to legal within 24 hours."]),
    _doc("contract-approval-matrix.md", "Contract approval matrix", "Legal", "POLICY", 1, "ALL",
         ["Contracts above 500000 units need legal review.", "Standard non-disclosure agreements can be signed by department heads."]),
    _doc("litigation-hold-notice.md", "Litigation hold notice", "Legal", "REPORT", 3, "LEGAL+EXEC",
         ["A made-up litigation hold applies to all documents about Project Falcon.", "Do not delete any Project Falcon material.",
          "Document marker: CANARY-LEGAL-HOLD-D134"], "CANARY-LEGAL-HOLD-D134"),
    _doc("intellectual-property-register.md", "Intellectual property register", "Legal", "REPORT", 2, "LEGAL+EXEC",
         ["Patent application PAT-2026-014 covers the search ranking method.", "Two trademarks are registered for the product name.",
          "Document marker: CANARY-LEGAL-IP-48EC"], "CANARY-LEGAL-IP-48EC"),
    # ---- Security
    _doc("access-control-policy.md", "Access control policy", "Security", "POLICY", 1, "ALL",
         ["Access is granted on a need to know basis.", "Account access reviews happen every 6 months."]),
    _doc("password-and-mfa-standard.md", "Password and MFA standard", "Security", "POLICY", 1, "ALL",
         ["Multi factor authentication is required for all staff.", "Hardware security keys are issued to administrators."]),
    _doc("penetration-test-results-2026.md", "Penetration test results 2026", "Security", "REPORT", 3, "SEC+EXEC",
         ["The 2026 penetration test found 1 high and 4 medium findings.", "Finding PT-2026-03 relates to session timeout settings.",
          "Document marker: CANARY-SEC-PENTEST-0C9B"], "CANARY-SEC-PENTEST-0C9B"),
    _doc("vulnerability-management-sla.md", "Vulnerability management SLA", "Security", "POLICY", 2, "SEC",
         ["Critical vulnerabilities must be fixed within 7 days.", "High vulnerabilities must be fixed within 30 days.",
          "Document marker: CANARY-SEC-VULN-F2E8"], "CANARY-SEC-VULN-F2E8"),
    _doc("iso-27001-certification-scope.md", "ISO 27001 certification scope", "Security", "REPORT", 2, "SEC+EXEC",
         ["The ISO 27001 certificate covers the cloud platform and the support desk.", "The next surveillance audit is in March.",
          "Document marker: CANARY-SEC-ISO-84A3"], "CANARY-SEC-ISO-84A3"),
    # ---- Customer Support
    _doc("refund-policy.md", "Refund policy", "Customer Support", "POLICY", 1, "ALL",
         ["Customers can request a refund within 30 days of purchase.", "Refunds above 10000 units need a team lead."]),
    _doc("support-sla-by-plan.md", "Support SLA by plan", "Customer Support", "POLICY", 1, "SUPPORT",
         ["Enterprise customers receive a first response within 1 hour.", "Starter customers receive a first response within 24 hours."]),
    _doc("customer-complaint-log.md", "Customer complaint log", "Customer Support", "REPORT", 3, "SUPPORT+EXEC",
         ["Three made-up complaints in September mention billing errors.", "Complaint CS-2231 was resolved with a credit note.",
          "Document marker: CANARY-SUPPORT-COMPLAINTS-19D7"], "CANARY-SUPPORT-COMPLAINTS-19D7"),
    _doc("chat-macros-library.md", "Chat macros library", "Customer Support", "OTHER", 1, "SUPPORT",
         ["Macro MAC-12 greets the customer and asks for the order number.", "Macro MAC-31 closes a chat politely."]),
    # ---- Company-wide
    _doc("code-of-conduct.md", "Code of conduct", "Company-wide", "POLICY", 1, "ALL",
         ["Treat colleagues with respect.", "Report harassment to HR or to the ethics line."]),
    _doc("remote-work-policy.md", "Remote work policy", "Company-wide", "POLICY", 1, "ALL",
         ["Employees may work remotely up to 3 days a week.", "A home office stipend of 15000 units is paid once."]),
    _doc("board-meeting-minutes-q2.md", "Board meeting minutes Q2", "Company-wide", "REPORT", 4, "EXEC",
         ["The board approved an acquisition budget of 90 million units.", "The next board meeting is in January.",
          "Document marker: CANARY-BOARD-Q2-6E5D"], "CANARY-BOARD-Q2-6E5D"),
]

EXTRA_SAMPLES: list[Sample] = [s for s, _ in _DOCS]
EXTRA_RULES: dict[str, list[Rule]] = {s.filename: ACCESS[a] for s, a in _DOCS}

ALL_SAMPLES: list[Sample] = list(SAMPLES) + EXTRA_SAMPLES
ALL_RULES: dict[str, list[Rule]] = {**DEMO_RULES, **EXTRA_RULES}
BY_TITLE: dict[str, Sample] = {s.title: s for s in ALL_SAMPLES}
CANARIES: dict[str, str] = {s.title: s.canary for s in ALL_SAMPLES if s.canary}
