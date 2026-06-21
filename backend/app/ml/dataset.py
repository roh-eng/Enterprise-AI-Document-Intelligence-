"""
Synthetic training dataset for document classification.

Shipping a real labelled corpus would bloat the repo and raise licensing
questions, so we *generate* a realistic, learnable dataset programmatically.
Each of the five categories has its own characteristic vocabulary and sentence
templates; documents are assembled by sampling several category sentences plus a
little shared "business filler" so the classes overlap slightly (producing
honest, sub-100% metrics and a meaningful confusion matrix).

The generator is seeded, so the dataset — and therefore the trained model and
its reported metrics — is fully reproducible.
"""

from __future__ import annotations

import random

# The five target categories (kept in one place; imported elsewhere).
CATEGORIES: list[str] = ["Resume", "Invoice", "Legal", "Medical", "Research"]

# Characteristic sentence fragments per category. Real-world distinguishing
# language for each document type.
_TEMPLATES: dict[str, list[str]] = {
    "Resume": [
        "Experienced software engineer skilled in Python, Java and cloud architecture.",
        "Professional summary highlighting leadership and project management experience.",
        "Work experience includes senior developer roles at technology companies.",
        "Education: Bachelor of Science in Computer Science from a state university.",
        "Key skills include communication, teamwork, problem solving and analytics.",
        "Achievements: promoted twice and led a team of five engineers.",
        "Certifications in AWS, Scrum and data engineering with hands-on projects.",
        "References available upon request and a portfolio of completed projects.",
        "Objective: seeking a challenging role to grow my career and skills.",
        "Proficient in machine learning, databases, and full stack web development.",
    ],
    "Invoice": [
        "Invoice number 4471 issued for services rendered in the billing period.",
        "Total amount due is payable within thirty days of the invoice date.",
        "Itemised charges include quantity, unit price, subtotal and applicable tax.",
        "Please remit payment to the bank account listed on this invoice.",
        "Billing address and shipping address for the customer purchase order.",
        "Tax rate applied at the standard percentage with the grand total below.",
        "Payment terms net 30 with a late fee for overdue balances.",
        "This receipt confirms the transaction and the outstanding balance due.",
        "Purchase order reference, line items, discount and amount payable.",
        "Vendor details, customer account number and the total invoice value.",
    ],
    "Legal": [
        "This agreement is entered into between the parties on the effective date.",
        "The plaintiff and defendant shall comply with the terms herein.",
        "Whereas the parties agree to the covenants and conditions set forth.",
        "This contract is governed by the laws of the applicable jurisdiction.",
        "Liability, indemnification and confidentiality clauses are binding hereunder.",
        "The court hereby orders the parties to arbitration per the statute.",
        "Termination of this agreement requires written notice to the counterparty.",
        "Intellectual property rights and obligations are defined in this clause.",
        "The witness affirms under oath the testimony provided to the tribunal.",
        "Pursuant to section four, the lessee shall pay rent to the lessor.",
    ],
    "Medical": [
        "The patient presented with symptoms including fever, cough and fatigue.",
        "Diagnosis was confirmed following laboratory tests and clinical examination.",
        "Prescribed medication and dosage with instructions for the treatment plan.",
        "Medical history includes hypertension and prior surgical procedures.",
        "The physician recommended follow-up imaging and blood pressure monitoring.",
        "Patient vitals: heart rate, blood pressure, temperature and oxygen levels.",
        "Treatment outcomes and recovery progress documented in the clinical notes.",
        "Allergies, immunisation records and the prescribed therapy are noted.",
        "The diagnosis indicates an infection requiring antibiotics and rest.",
        "Referral to a specialist for further cardiology evaluation was advised.",
    ],
    "Research": [
        "This study investigates the effect of the proposed method on accuracy.",
        "The abstract summarises the hypothesis, methodology and key findings.",
        "Experimental results demonstrate a statistically significant improvement.",
        "The literature review surveys prior work and related publications.",
        "We propose a novel algorithm evaluated on benchmark datasets.",
        "The methodology section describes the experimental setup and metrics.",
        "Figures and tables present the empirical analysis and discussion.",
        "The conclusion outlines limitations and directions for future research.",
        "Citations reference peer-reviewed papers and the dataset used.",
        "Our contribution advances the state of the art in this domain.",
    ],
}

# Generic business sentences shared across all categories. Used heavily so the
# class-specific signal is diluted (otherwise the problem is trivially perfect).
_FILLER: list[str] = [
    "Please review the attached document for further details.",
    "Contact the relevant department for any questions or clarifications.",
    "All information contained herein is confidential and proprietary.",
    "The document was prepared and reviewed by the responsible team.",
    "Date, reference number and signature are recorded for the record.",
    "Please find the relevant information summarised in the section below.",
    "This document is provided for informational purposes only.",
    "Further correspondence should reference the identifier above.",
]

# Deliberately ambiguous sentences that mix vocabulary from several domains.
# Sprinkling these in creates genuine class overlap, so the models make a few
# realistic mistakes (a non-trivial confusion matrix) and can be compared.
_AMBIGUOUS: list[str] = [
    "Payment for the services rendered is due as per the signed agreement.",
    "The research budget invoice was submitted for review and approval.",
    "The patient signed the consent agreement before the procedure.",
    "The study reports the total cost and the itemised research expenses.",
    "The contract covers the medical treatment plan and associated fees.",
    "The candidate has experience preparing legal and financial documents.",
    "An analysis of the data summary and the attached report is included.",
]


def generate_dataset(
    samples_per_class: int = 100, seed: int = 42
) -> tuple[list[str], list[str]]:
    """
    Generate a labelled but intentionally *noisy* dataset.

    Each document mixes a few category sentences with a larger amount of shared
    filler and some ambiguous cross-domain sentences, so the classes overlap and
    the models achieve realistic (sub-100%) accuracy.

    Returns
    -------
    (texts, labels) : parallel lists of document strings and their category.
    """
    rng = random.Random(seed)
    texts: list[str] = []
    labels: list[str] = []

    for category in CATEGORIES:
        sentences = _TEMPLATES[category]
        for _ in range(samples_per_class):
            # Few category-specific sentences, lots of shared noise.
            chosen = rng.choices(sentences, k=rng.randint(2, 4))
            chosen += rng.choices(_FILLER, k=rng.randint(2, 4))
            chosen += rng.choices(_AMBIGUOUS, k=rng.randint(0, 2))
            rng.shuffle(chosen)
            texts.append(" ".join(chosen))
            labels.append(category)

    # Shuffle the whole dataset so train/test splits are not class-ordered.
    combined = list(zip(texts, labels))
    rng.shuffle(combined)
    texts, labels = map(list, zip(*combined))
    return texts, labels
