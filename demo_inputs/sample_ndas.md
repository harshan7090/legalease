# LegalEase — Sample Test Clauses & Expected Outputs

Use these clauses to test all four prompt templates manually or via `run_demo.py`.

---

## 🧪 Sample Clause 1 — NDA Non-Compete (Primary Test)

### Clause Text

```
Non-Compete and Non-Solicitation. During the term of this Agreement and for a period of
two (2) years following the termination or expiration thereof, for any reason, Employee
shall not, directly or indirectly, (i) engage in any business activity that competes with
the Company's Business within the Restricted Territory; (ii) solicit, induce, or attempt
to induce any employee, consultant, or contractor of the Company to terminate their
relationship with the Company; or (iii) solicit, divert, or attempt to divert any client,
customer, or business partner of the Company with whom Employee had material contact
during the twelve (12) months preceding termination. "Restricted Territory" means any
country, state, or province in which the Company conducts or has conducted business
during the twelve (12) months preceding termination. Employee acknowledges that the
restrictions herein are reasonable and necessary to protect the Company's legitimate
business interests, including its Confidential Information, client relationships, and
goodwill. In the event of a breach, the Company shall be entitled to seek injunctive
relief without the requirement to post bond, in addition to all other remedies available
at law or in equity.
```

---

### Expected Output — 📖 Explain

> *The model should translate the clause into plain English, approximately:*

**Expected (illustrative):**
- This clause says you cannot work for a competitor for **2 years after leaving** the company.
- You also cannot try to take the company's employees or clients with you.
- The geographic scope is broad: any region the company has done business in recently.
- If you break these rules, the company can go to court immediately for an injunction — meaning a judge can order you to stop — without the company having to put up any financial guarantee.
- **Key concern:** The "Restricted Territory" definition is potentially very wide.

**Expected Confidence:** ~75–85%
**Expected Risk Badge:** 🟢 LOW or 🟡 MEDIUM

---

### Expected Output — 📋 Summarize

> *The model should output structured bullets:*

**Expected (illustrative):**

**Obligations:**
- Employee must not compete with the Company for 2 years post-termination.
- Employee must not solicit Company employees, consultants, or contractors.
- Employee must not solicit clients they had contact with in the last 12 months.

**Rights:**
- Company may seek injunctive relief immediately upon breach.
- Company retains all other legal and equitable remedies.

**Restrictions:**
- Employee restricted from any competing business activity, direct or indirect.
- Restriction applies globally wherever the Company has operated in the last 12 months.

**Red Flags:**
- 🚩 "Restricted Territory" is potentially global — this is unusually broad.
- 🚩 "Directly or indirectly" is vague and could cover tangential activities.
- 🚩 No carve-out for employee's general skills or prior knowledge.
- 🚩 "Without requirement to post bond" removes a typical procedural protection for employees.

**Expected Confidence:** ~78–88%

---

### Expected Output — ❓ Generate Questions

> *The model should generate 5 numbered questions like:*

**Expected (illustrative):**

1. **How is "Restricted Territory" defined in practice?** — Ask your attorney whether the broad geographic scope could prevent you from working anywhere in your industry.
2. **Is a 2-year non-compete enforceable in your state/country?** — Many jurisdictions limit or prohibit non-competes (e.g., California bans them entirely).
3. **What counts as "competing business activity"?** — Seek clarity on whether freelance work, consulting, or working in a different department of a competitor counts.
4. **What consideration are you receiving for this restriction?** — Courts often require that a non-compete be supported by adequate compensation.
5. **What happens if you work for a startup that later competes with the Company?** — You need to know at what point a future employer might trigger this clause.

**Expected Confidence:** ~80–90%

---

### Expected Output — 🐛 Debug

*For Debug mode, use this belief as input instead of the clause:*

> **User belief:** *"If I work in a different city, a non-compete clause from my old employer cannot affect me because geography makes it unenforceable."*

**Expected (illustrative):**

This belief contains a significant misconception:

- **Misconception 1:** Geography alone does not make a non-compete unenforceable. Courts evaluate scope, duration, and legitimate business interest — not just distance.
- **Misconception 2:** "A different city" is irrelevant if the Restricted Territory clause covers the entire country or any region the employer operates in.
- **Correction:** Enforceability depends on the specific jurisdiction, the clause's scope, whether the employee received consideration, and whether the restriction is proportionate.
- **Important note:** In California, non-competes are almost entirely void. In most other U.S. states, they can be enforced if reasonably scoped.

**Expected Confidence:** ~70–82%

---

## 🧪 Sample Clause 2 — Indemnification Clause

```
Indemnification. The Contractor shall defend, indemnify, and hold harmless the Client,
its officers, directors, employees, and agents from and against any and all claims,
damages, losses, costs, and expenses (including reasonable attorneys' fees) arising out
of or relating to: (a) any breach of this Agreement by Contractor; (b) the negligence
or willful misconduct of Contractor; or (c) any third-party claim that Contractor's
work product infringes any intellectual property right. The Client's liability to
Contractor under this Agreement shall not exceed the total fees paid in the six (6)
months preceding the claim.
```

**Key risk signals to detect:** indemnification, intellectual property, liability cap
**Expected Risk Badge:** 🟡 MEDIUM to 🔴 HIGH (asymmetric indemnification)

---

## 🧪 Sample Clause 3 — Arbitration & Class Action Waiver

```
Dispute Resolution. Any dispute, controversy, or claim arising out of or relating to
this Agreement shall be resolved exclusively by binding arbitration administered by the
American Arbitration Association under its Commercial Arbitration Rules. The arbitration
shall take place in New York, New York. Each party shall bear its own costs. THE PARTIES
HEREBY WAIVE ANY RIGHT TO A JURY TRIAL AND TO PARTICIPATE IN CLASS ACTION PROCEEDINGS.
```

**Key risk signals to detect:** arbitration, class-action, waiver
**Expected Risk Badge:** 🔴 HIGH (class action waiver is highly significant)

---

## ✅ How to Use These in the App

1. Copy a clause text above.
2. Paste it into the LegalEase chat input.
3. Select the desired template in the sidebar.
4. Compare the AI output to the expected output above.
5. Verify the Risk Badge color matches expectations.
6. Test multi-turn memory: after Explain, follow up with "What should I negotiate?"
