# UI/UX Laws Applied in ClassSync

This document formalizes how **Universal UI/UX & Interaction Design Laws** (HCI principles) are implemented across the **ClassSync Web Dashboard** and **Mobile Application**. This directly addresses **ITHUMCI (Human-Computer Interaction)** requirements and provides material for **Chapter 3 & 4 of the Capstone Manuscript (Ma'am Lamadora)**.

---

## 1. Summary of Applied UI/UX Laws

| UX Law | Formal Principle | Concrete Implementation in ClassSync |
| :--- | :--- | :--- |
| **Fitts's Law** | Time to acquire a target is a function of distance and target size. | **48px minimum touch targets** on mobile navigation, bottom action sheets, and thumb-zone primary CTA buttons ("Export Schedule", "Auto-Resolve"). |
| **Hick's Law** | Decision time increases with number and complexity of choices. | **Role-based view segregation**: Students see only their class stream, Teachers see teaching load, Admins see management tools. Complex scheduling filters are broken down into step-by-step wizards. |
| **Miller's Law** | Working memory holds $7 \pm 2$ chunks of information. | Schedule timetables chunk information into **Day $\rightarrow$ Time Slot $\rightarrow$ Subject Card**; multi-section filters chunk options by Institute and Program. |
| **Jakob's Law** | Users expect your app to work like other apps they already know. | Follows standard Google Calendar / Outlook calendar layouts (days of week columns, vertical time markers, swipeable mobile week view). |
| **Law of Proximity** | Objects near each other appear grouped together. | Subject code, instructor avatar, room number, and time badge are encapsulated within a unified, padded card boundary with clear margins. |
| **Law of Similarity** | Elements sharing visual characteristics are perceived to belong together. | Consistent color-coding: 🔴 Red = Conflict / Double-booking, 🟢 Green = Vacant / Validated, 🔵 Blue = Enrolled class, 🟡 Yellow = Pending draft. |
| **Aesthetic-Usability Effect** | Users perceive aesthetically pleasing design as more usable. | **Soft Rouge Design System**: clean typography (Inter), rounded card radiuses (12px), soft shadows, and clean neutral palettes reducing visual fatigue during long scheduling sessions. |
| **Peak-End Rule** | People judge an experience by its emotional peak and its end. | When a schedule is successfully generated and published, the user receives an explicit, celebratory confirmation modal with one-click export actions. |

---

## 2. In-Depth Breakdown & Concrete Application

### 1. Fitts's Law (Touch Targets & Mobile Thumb Zone)
* **Application on Mobile App (Ma'am Gretchen):**
  - **Thumb-Zone Navigation:** Primary destinations (`Home`, `Schedule`, `Rooms`, `Alerts`) are fixed to a bottom navigation bar with a height of **72px** and touch-accessible bounding boxes.
  - **Action Button Prominence:** Critical action buttons like **"Generate Schedule"** or **"Resolve Conflict"** span full width or occupy the bottom-right corner where mobile thumbs reach naturally with minimal muscle strain.
  - **Desktop:** Interactive buttons and table controls strictly adhere to minimum $44 \text{px} \times 44 \text{px}$ click zones.

---

### 2. Hick's Law (Reducing Cognitive Overload)
* **Application on Timetable Management:**
  - In traditional scheduling software, administrators face hundreds of dropdowns simultaneously, leading to analysis paralysis.
  - ClassSync breaks schedule generation into a **progressive 3-step pipeline**:
    1. *Select Academic Period & Institute*
    2. *Review Readiness & Check Constraints*
    3. *Review Candidates & Save as Draft*
  - Irrelevant options are hidden until preceding steps are validated.

---

### 3. Miller’s Law (Chunking Information)
* **Application on Timetable Grids:**
  - A timetable containing 50+ classes is overwhelming. ClassSync chunks classes into discrete temporal blocks:
    - **Current Day:** Emphasized in hero cards (Next Class Summary).
    - **By Time Block:** Morning (07:00–12:00), Afternoon (13:00–17:00), Evening (17:30–21:00).
    - **By Room Cards:** Rooms group capacity, air conditioning, and equipment into small, readable chip tags.

---

### 4. Jakob’s Law (Standard Mental Models)
* **Application on Familiar UX Patterns:**
  - Students and faculty already know how Google Calendar, Canvas, or Outlook work.
  - ClassSync utilizes:
    - Standard Monday–Saturday column headers.
    - Familiar OAuth "Sign in with Google" button placement.
    - Standard drawer menus on mobile and collapsible sidebar on desktop.

---

### 5. Law of Proximity & Law of Common Region
* **Application on Conflict Notification Cards:**
  - When the OR-Tools solver detects a room overlap:
    - The conflicting classes, the shared room badge, and the "Resolve Clash" button are visually encapsulated inside a bordered alert card (`border-l-4 border-red-500`).
    - Whitespace separates unrelated courses so the administrator instantly knows which two entities are clashing.

---

### 6. Law of Similarity (Semantic Color System)
* **Status Badges & Schedule Visuals:**
  - The UI uses consistent semantic color tokens across Web and Mobile:
    - `bg-emerald-50 text-emerald-700`: Free room / Successful constraint pass / Published timetable.
    - `bg-amber-50 text-amber-700`: Unpublished draft / Warning (e.g., 90% room capacity).
    - `bg-rose-50 text-rose-700`: Critical conflict / Overlapping professor / Room unavailable.
  - To respect **WCAG 2.2 AA accessibility**, color is **never** used alone; every colored badge is paired with a distinct text label and semantic icon.

---

### 7. Doherty Threshold (Response Time & System Feedback)
* **Application on Solver & API Performance:**
  - Productive human-computer interaction requires system feedback within **400ms**.
  - When calculating schedules with OR-Tools, ClassSync immediately displays an animated skeleton / progress indicator (`Calculating feasible timetable...`).
  - Mobile room-search responds in $<100\text{ms}$ by querying localized Firestore projections.

---

## 3. How to Cite This in Chapter 3/4 of the Manuscript (Ma'am Lamadora)

> *"In compliance with Human-Computer Interaction (HCI) standards and WCAG 2.2 AA accessibility guidelines, ClassSync systematically applies foundational UX laws. **Fitts's Law** is respected through 48px touch targets anchored in the mobile thumb zone. **Hick's Law** and **Miller's Law** are incorporated by chunking extensive timetable grids into progressive steps and discrete time blocks. Semantic feedback follows the **Law of Similarity** and **Law of Proximity** to ensure conflict alerts and room availability states are immediately interpretable with zero ambiguity."*
