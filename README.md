# -AI-Job-Application-Filler
The AI Job Application Filler is an advanced, automation-driven application that streamlines and accelerates the modern job-hunting process. Developed using Python and Streamlit, it combines artificial intelligence, natural language processing (NLP), web scraping, and form automation to provide an end-to-end solution for job seekers.


---

# 🤖 AI Job Application Filler

An **AI-powered application** built with **Python + Streamlit** that:

* Fetches job postings from **LinkedIn** and **Indeed**
* Generates **customized cover letters and answers** using AI
* Automatically **fills job application forms** (Selenium/Playwright)
* Tracks all applications in a **dashboard**
* Secures your **personal data** with encryption

---

## ✨ Features

* **Profile Management** → Store multiple resumes & personal details securely
* **Job Fetching** → Scrape or use APIs to pull jobs from Indeed/LinkedIn
* **AI Integration** → Generate tailored cover letters & form responses
* **Auto-Fill & Apply** → Automatically fill application forms with stored data + AI answers
* **Application Tracker** → Dashboard to monitor history, status, and exports
* **Automation** → Background job fetcher with scheduler (cron/Task Scheduler)
* **Security** → Encrypts personal data before storage

---

## 🛠️ Tech Stack

* **Frontend/UI**: Streamlit
* **Backend/Logic**: Python
* **AI/NLP**: OpenAI API, spaCy
* **Automation**: Selenium / Playwright
* **Database**: SQLite (default) / PostgreSQL (optional)
* **Deployment**: Streamlit Cloud (UI) + VPS/Heroku/AWS (automation scripts)

---

## 📂 Project Structure

```
job_filler/
├── app.py              # Streamlit app (UI dashboard)
├── scraper.py          # Job fetching from LinkedIn/Indeed
├── ai_helper.py        # AI cover letters & Q&A generation
├── autofill.py         # Selenium/Playwright form autofill
├── db.py               # Database for tracking & profiles
├── security.py         # Data encryption/decryption
├── utils.py            # Helper functions
├── assets/             # Resume, images, icons
└── requirements.txt    # Python dependencies
```

---

## ⚙️ Setup & Installation

### 1. Clone Repo

```bash
git clone https://github.com/yourusername/job-filler.git
cd job-filler
```

### 2. Create Virtual Environment

```bash
python3 -m venv siva
source siva/bin/activate   # macOS/Linux
siva\Scripts\activate      # Windows
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run Streamlit App

```bash
streamlit run app.py
```

---

## 🔑 Usage Workflow

1. **Set up Profile** → Enter details (name, email, resume, preferences) in Streamlit.
2. **Fetch Jobs** → Scraper/API pulls relevant jobs.
3. **AI Assistance** → App generates tailored cover letters & answers.
4. **Review & Apply** →

   * Semi-auto mode → Review before submission
   * Full-auto mode → System fills & submits via Selenium/Playwright
5. **Track Applications** → View applied jobs in dashboard, export CSV.
6. **Automation** → Schedule background fetch/apply jobs with cron or Task Scheduler.

---

## 🔐 Security

* All personal details stored in **encrypted DB** (`cryptography` library).
* Resume files stored locally in `assets/`.
* Avoid sharing DB files publicly.

---

## 🚀 Deployment

* **Streamlit Cloud** → Deploy UI dashboard.
* **Backend scripts** (Selenium automation + scheduler) → Deploy on VPS (Heroku/AWS).
* For production, separate **UI (Streamlit)** and **automation service**.

---

## ⚠️ Challenges / Notes

* LinkedIn & Indeed have **anti-bot protections** → too much automation may trigger blocks.
* Recommended: **semi-automated mode** (AI pre-fills, user clicks submit).
* Ensure compliance with each job portal’s **Terms of Service**.

---

## 📌 Future Enhancements

* Job recommendation engine (match scores)
* AI resume optimizer (customize CV per job)
* Chrome extension for inline autofill
* Notification system (email/Slack alerts)
* Analytics dashboard (success rates, trends)

---

## 🧑‍💻 Contributing

Contributions welcome! Please fork the repo, create a feature branch, and submit a PR.

---

## 📜 License

MIT License – free to use & modify.

---
