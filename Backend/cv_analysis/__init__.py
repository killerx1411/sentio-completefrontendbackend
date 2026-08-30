"""Sentio Mind CV / behavioural-intelligence system.

Everything that touches OpenCV, DeepFace, MediaPipe, face_recognition or MTCNN
lives under this package. The stakeholder/authentication service
(``app_factory.create_auth_app``) imports nothing from ``cv_analysis``.

Dependency direction is one-way::

    cv_analysis  ->  auth       (authn/authz, DB pool, rate limiter)
    auth         -X- cv_analysis (never)

This module intentionally imports nothing so that ``import cv_analysis`` stays
cheap; the heavy CV stack is only pulled in by ``cv_analysis.libraries``.
"""
