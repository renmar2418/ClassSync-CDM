# Irregular Student Slot Infiltration & Backload Unit Rules

## 1. The Core Scenario: "Can an Irreg sit in a Regular section while carrying backload units?"

**Answer: YES, absolutely.** In Philippine university administration (including CdM), this is standard procedure:
1. An irregular student is authorized to "sit-in" or officially enroll in an open slot of a **regular block section** (e.g., join `BSIT-3A` for major subjects).
2. Concurrently, they "cross-enroll" into lower-year sections (e.g., joining `BSIT-1B` or `BSIT-2A`) to clear **backload/prerequisite units** from previous years.

However, to prevent classroom overcrowding, schedule chaos, and CHED policy violations, the system enforces **3 strict guardrails**.

---

## 2. The 3 System Guardrails for Irregulars in Regular Slots

```mermaid
flowchart TD
    Irreg["Irregular Student (e.g., 3rd Year Standing with Backloads)"]
    
    subgraph Selection["Subject & Slot Selection in Mobile App"]
        Major["Selects Regular 3rd Year Subject: IT311 in BSIT-3A"]
        Backload["Selects Backload 1st Year Subject: CC101 in BSIT-1B"]
    end

    subgraph Guardrails["ClassSync Automated Audit & Validation"]
        G1{"1. Room / Section Seat Capacity Check<br>(Current Enrolled < Room Max Capacity?)"}
        G2{"2. Time Overlap & Conflict Check<br>(Does IT311 clash with CC101?)"}
        G3{"3. Total Unit Load vs. Overload Cap<br>(Total Units <= Max Allowed Units?)"}
    end

    Irreg --> Selection
    Selection --> G1
    G1 -->|No Seats in Sec 3A| Reject1["❌ Blocked: Section Full. Try BSIT-3B"]
    G1 -->|Seat Available| G2
    G2 -->|Time Overlap| Reject2["⚠️ Conflict: Overlaps Mon 10:00 AM. Pick another section"]
    G2 -->|Zero Clash| G3
    G3 -->|Exceeds Cap (e.g., >24 units)| Reject3["🚫 Blocked: Overload requires Dean permit"]
    G3 -->|Within Cap| Enrolled["🟢 Successfully Enrolled in Both Regular Slot & Backload Slot"]
```

---

### Guardrail 1: Dynamic Seat Capacity (Preventing Room Overcrowding)
* **The Rule:** A regular section (e.g., `BSIT-3A`) might have 38 regular students assigned to a room with a maximum capacity of 45 seats.
* **The System Math:**
  $$\text{Available Irreg Slots} = \text{Room Capacity} - \text{Regular Block Enrollees}$$
  $$\text{Available Slots} = 45 - 38 = 7 \text{ vacant seats}$$
* **System Action:** If all 7 vacant seats are taken, the section is flagged as **"FULL"**, preventing the irregular student from joining that specific block and guiding them to `BSIT-3B`.

---

### Guardrail 2: Time Clash Prevention (Cross-Year Conflict)
* **The Rule:** Regular block sections are designed so subjects within the *same* year level never conflict. However, 1st-year subjects and 3rd-year subjects are scheduled independently and frequently overlap.
* **System Action:** The instant an irregular student picks `IT311` (Mon 09:00–10:30) and attempts to add backload `CC101` (Mon 10:00–11:30), the validator blocks the submission:
  > *"Conflict Detected: CC101 overlaps with IT311 by 30 minutes on Monday. Recommended: Select CC101 Section 1C scheduled on Wednesday 01:00 PM."*

---

### Guardrail 3: Backload Unit Cap & Overload Policy
* **Regular Unit Ceiling:** Prospectus standard load is typically **21 to 24 units**.
* **The Overload Exception (Graduating / Dean's Permit):**
  - If a student wants to take their full regular 3rd-year load (21 units) **PLUS** a 3-unit backload subject (Total = 24 units), the system verifies the **Program Head / Dean Overload Authorization**.
  - Non-graduating students are capped at standard maximums (e.g., 21 units) unless an explicit Dean's overload waiver is uploaded to their Advising Record.

---

## 3. How to Explain This to Your Classmate (Taglish Script)

> "Oo, pwedeng-pwede! Actually normal na normal yan sa college. Ang tawag doon: **nakiki-sit-in si irreg sa regular section habang nag-ke-clear ng backload.**
> 
> Ganito yung magiging logic ng ClassSync para hindi magkagulo:
> 
> 1. **May Slot Cap (Capacity Check):**  
>    Halimbawa, ang room ng `BSIT-3A` kasya 45 students. 38 lang silang regulars. Ibig sabihin, may **7 open slots** para sa mga irregs. Pwedeng pumasok si irreg doon habang may slot pa!
> 
> 2. **Bawal Magpatong ang Oras (Cross-Year Clash Check):**  
>    Dahil kumukuha siya ng 3rd year subject sa `3A` tapos kukuha pa siya ng 1st year backload subject sa `1B`, babantayan ng app natin kung magkasabay yung oras nung dalawa. Pag nag-clash, sasabihin ng app: *'Conflict sa oras, pumili ka ng ibang section para sa backload mo.'*
> 
> 3. **Unit Limit (Overload Check):**  
>    Bantay-sarado pa rin yung max units na pinayagan ni Program Head. Kung 21 units lang ang allowed sa kanya, hindi siya pwedeng mag-enroll ng 24 units unless may approved **Overload Permit** galing kay Dean.
> 
> Kaya solve lahat: nakaka-join si irreg sa regular slots, nakakapag-backload siya, pero hindi mag-o-overcrowd ang room at walang magkapatong na schedule!"
