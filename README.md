# Aroha: Senior Citizen Assistance System
**Alias:** Aroha

## Project Description
Aroha is a web platform connecting senior citizens and family members with community volunteers and Barangay staff for real-time assistance request tracking.

* **Problem Addressed:** Eliminates fragmented communication and delays in providing timely care and support to elderly residents.
* **Intended Users:** Family Members (Requesters), Volunteers, Barangay Staff, and Admins.

---

## Important Features
* **Role-Based Access Control (RBAC):** Tailored dashboards and permissions for Requesters, Volunteers, Staff, and Admins.
* **Secure Authentication & Approvals:** 2FA/OTP email login verification and administrative account approval workflows.
* **Request Lifecycle Management:** Real-time task tracking (`Pending` → `In Progress` → `Completed`).
* **Volunteer Task Feed:** Interactive dashboard for community volunteers to browse, claim, and fulfill local requests.
* **Barangay Governance:** Directory and monitoring panel for staff to review requests, approve user sign-ups, and manage administrative actions.

---

## OOP Implementation
* **Inheritance:** The `User` model extends Django's `AbstractUser`, and custom authentication views extend framework base views.
* **Encapsulation:** Security validation logic and request state workflows are bundled inside dedicated model and form classes.
* **Abstraction:** Django ORM hides raw SQL queries and Supabase PostgreSQL operations behind clean Python methods.
* **Polymorphism:** Framework methods like `clean()`, `form_valid()`, and `__str__()` are overridden to execute custom behaviors.

---

## Setup Instructions

1. **Clone Repository & Install Dependencies**
   ```bash
   git clone [https://github.com/your-username/aroha.git](https://github.com/your-username/aroha.git)
   cd aroha
   pip install -r requirements.txt
