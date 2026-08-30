"""Infrastructure shared by the stakeholder/auth service and the CV service.

Nothing in here is business logic. It exists so that both applications can
apply the same HTTP hardening without either importing the other.
"""
