import streamlit as st
import sqlite3
import hashlib
import json
import requests
import openai
from datetime import datetime, timedelta
import pandas as pd
import time
import logging
from typing import Dict, List, Optional
import re
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import schedule
import threading
import smtplib
# Fixed import - try multiple approaches for email MIME classes
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
except ImportError:
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart    
    except ImportError:
        # Fallback: define minimal classes if import fails
        class MimeText:
            def __init__(self, text, subtype='plain'):
                self.text = text
                self.subtype = subtype
                self._payload = text
            
            def as_string(self):
                return self.text
        
        class MimeMultipart:
            def __init__(self):
                self._parts = []
                self._headers = {}
            
            def __setitem__(self, key, value):
                self._headers[key] = value
            
            def __getitem__(self, key):
                return self._headers.get(key)
            
            def attach(self, part):
                self._parts.append(part)
            
            def as_string(self):
                return str(self._parts)

import os
from bs4 import BeautifulSoup
import uuid
import plotly.express as px
import plotly.graph_objects as go

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
st.set_page_config(
    page_title="Job Application Automation System",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

@dataclass
class JobProfile:
    id: str
    name: str
    skills: List[str]
    experience: str
    summary: str
    target_positions: List[str]
    created_at: datetime

@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    salary_range: str
    posted_date: datetime
    match_score: float
    source: str

@dataclass
class Application:
    id: str
    job_id: str
    profile_id: str
    status: str
    applied_date: datetime
    cover_letter: str
    custom_answers: Dict[str, str]
    response_received: bool
    notes: str

class DatabaseManager:
    def __init__(self, db_name: str = "job_automation.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                skills TEXT,
                experience TEXT,
                summary TEXT,
                target_positions TEXT,
                resume_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                url TEXT,
                salary_range TEXT,
                posted_date TIMESTAMP,
                match_score REAL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Applications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                profile_id TEXT,
                user_id TEXT,
                status TEXT DEFAULT 'pending',
                applied_date TIMESTAMP,
                cover_letter TEXT,
                custom_answers TEXT,
                response_received BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id),
                FOREIGN KEY (profile_id) REFERENCES profiles (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                user_id TEXT PRIMARY KEY,
                openai_api_key TEXT,
                email_settings TEXT,
                automation_settings TEXT,
                notification_settings TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query: str, params: tuple = (), fetch: bool = False):
        """Execute database query safely"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
                conn.close()
                return result
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database error: {e}")
            return None if fetch else False

class AuthManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username: str, password: str, email: str = "") -> bool:
        """Register new user"""
        user_id = str(uuid.uuid4())
        password_hash = self.hash_password(password)
        
        return self.db.execute_query(
            "INSERT INTO users (id, username, password_hash, email) VALUES (?, ?, ?, ?)",
            (user_id, username, password_hash, email)
        )
    
    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return user ID"""
        password_hash = self.hash_password(password)
        result = self.db.execute_query(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash),
            fetch=True
        )
        return result[0][0] if result else None

class JobScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_indeed_jobs(self, keywords: str, location: str, limit: int = 20) -> List[Job]:
        """Search for jobs on Indeed (simplified version)"""
        jobs = []
        try:
            # This is a simplified version - you'd need to implement proper Indeed scraping
            # or use their API if available
            url = f"https://www.indeed.com/jobs?q={keywords}&l={location}"
            
            # For demo purposes, creating sample jobs
            for i in range(min(limit, 5)):
                job = Job(
                    id=str(uuid.uuid4()),
                    title=f"Sample {keywords} Position {i+1}",
                    company=f"Company {i+1}",
                    location=location,
                    description=f"Sample job description for {keywords} position requiring relevant skills and experience.",
                    url=f"https://example.com/job/{i+1}",
                    salary_range="$50,000 - $80,000",
                    posted_date=datetime.now() - timedelta(days=i),
                    match_score=0.8 - (i * 0.1),
                    source="indeed"
                )
                jobs.append(job)
                
        except Exception as e:
            logger.error(f"Error scraping Indeed: {e}")
            
        return jobs
    
    def search_linkedin_jobs(self, keywords: str, location: str, limit: int = 20) -> List[Job]:
        """Search for jobs on LinkedIn (simplified version)"""
        jobs = []
        try:
            # For demo purposes, creating sample jobs
            for i in range(min(limit, 5)):
                job = Job(
                    id=str(uuid.uuid4()),
                    title=f"LinkedIn {keywords} Role {i+1}",
                    company=f"LinkedIn Company {i+1}",
                    location=location,
                    description=f"LinkedIn job posting for {keywords} with comprehensive benefits and growth opportunities.",
                    url=f"https://linkedin.com/jobs/view/{i+1000}",
                    salary_range="$60,000 - $90,000",
                    posted_date=datetime.now() - timedelta(days=i+1),
                    match_score=0.9 - (i * 0.08),
                    source="linkedin"
                )
                jobs.append(job)
                
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {e}")
            
        return jobs

class AIAssistant:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Updated OpenAI client initialization for newer versions
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            self.client = None
    
    def generate_cover_letter(self, job: Job, profile: JobProfile) -> str:
        """Generate AI-powered cover letter"""
        try:
            if not self.client:
                return self._fallback_cover_letter(job, profile)
                
            prompt = f"""
            Write a professional cover letter for the following job application:
            
            Job Title: {job.title}
            Company: {job.company}
            Job Description: {job.description[:500]}...
            
            Candidate Profile:
            Name: Professional Candidate
            Skills: {', '.join(profile.skills)}
            Experience: {profile.experience}
            Summary: {profile.summary}
            
            Make it personalized, professional, and highlight relevant skills.
            Keep it under 300 words.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            return self._fallback_cover_letter(job, profile)
    
    def generate_qa_answers(self, questions: List[str], job: Job, profile: JobProfile) -> Dict[str, str]:
        """Generate answers for common application questions"""
        answers = {}
        
        try:
            if not self.client:
                return {}
                
            for question in questions:
                prompt = f"""
                Answer this job application question professionally:
                Question: {question}
                
                Context:
                Job: {job.title} at {job.company}
                Your background: {profile.summary}
                Your skills: {', '.join(profile.skills)}
                
                Provide a concise, professional answer (2-3 sentences).
                """
                
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7
                )
                
                answers[question] = response.choices[0].message.content.strip()
                
        except Exception as e:
            logger.error(f"Error generating Q&A: {e}")
            
        return answers
    
    def calculate_job_match_score(self, job: Job, profile: JobProfile) -> float:
        """Calculate job match score using AI"""
        try:
            if not self.client:
                return 0.5
                
            prompt = f"""
            Rate the job match on a scale of 0.0 to 1.0 based on how well the candidate fits the job:
            
            Job: {job.title} at {job.company}
            Job Description: {job.description[:300]}...
            
            Candidate:
            Skills: {', '.join(profile.skills)}
            Experience: {profile.experience}
            Target Positions: {', '.join(profile.target_positions)}
            
            Return only a decimal number between 0.0 and 1.0.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )
            
            score_text = response.choices[0].message.content.strip()
            return float(re.findall(r'0?\.\d+|[01]', score_text)[0])
            
        except Exception as e:
            logger.error(f"Error calculating match score: {e}")
            return 0.5
    
    def _fallback_cover_letter(self, job: Job, profile: JobProfile) -> str:
        """Fallback cover letter template"""
        return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job.title} position at {job.company}. With my background in {profile.experience} and expertise in {', '.join(profile.skills[:3])}, I am excited about the opportunity to contribute to your team.

{profile.summary}

I am particularly drawn to this role because it aligns perfectly with my career goals and allows me to leverage my skills in a meaningful way. I would welcome the opportunity to discuss how my experience can benefit your organization.

Thank you for your consideration.

Sincerely,
[Your Name]"""

class FormAutomator:
    def __init__(self):
        self.driver = None
    
    def setup_driver(self, headless: bool = True):
        """Setup Chrome WebDriver"""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            logger.error(f"Error setting up driver: {e}")
            return False
    
    def fill_application_form(self, job_url: str, profile: JobProfile, 
                            cover_letter: str, custom_answers: Dict[str, str]) -> bool:
        """Automated form filling (simplified)"""
        if not self.driver:
            if not self.setup_driver():
                return False
        
        try:
            self.driver.get(job_url)
            time.sleep(3)
            
            # This is a simplified version - you'd need to implement
            # specific selectors for each job board
            
            # Try to find and fill common form fields
            common_fields = {
                'name': ['name', 'full_name', 'applicant_name'],
                'email': ['email', 'email_address', 'contact_email'],
                'phone': ['phone', 'phone_number', 'mobile'],
                'cover_letter': ['cover_letter', 'message', 'additional_info']
            }
            
            # Fill basic info
            self._fill_field_by_selectors(common_fields['name'], "John Doe")
            self._fill_field_by_selectors(common_fields['email'], "john.doe@email.com")
            self._fill_field_by_selectors(common_fields['phone'], "+1234567890")
            self._fill_field_by_selectors(common_fields['cover_letter'], cover_letter)
            
            # Handle file uploads (resume)
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for file_input in file_inputs:
                if profile and hasattr(profile, 'resume_path'):
                    file_input.send_keys(profile.resume_path)
            
            logger.info(f"Successfully filled application form for {job_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error filling form: {e}")
            return False
    
    def _fill_field_by_selectors(self, selectors: List[str], value: str):
        """Try multiple selectors to fill a field"""
        for selector in selectors:
            try:
                # Try by name
                element = self.driver.find_element(By.NAME, selector)
                element.clear()
                element.send_keys(value)
                return
            except NoSuchElementException:
                try:
                    # Try by ID
                    element = self.driver.find_element(By.ID, selector)
                    element.clear()
                    element.send_keys(value)
                    return
                except NoSuchElementException:
                    continue
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()

class NotificationManager:
    def __init__(self, email_settings: Dict[str, str]):
        self.email_settings = email_settings
    
    def send_email_notification(self, subject: str, body: str, to_email: str):
        """Send email notification with improved error handling"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_settings.get('from_email')
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_settings.get('smtp_server', 'smtp.gmail.com'), 587)
            server.starttls()
            server.login(self.email_settings.get('from_email'), self.email_settings.get('password'))
            
            # Use send_message if available, otherwise fallback to sendmail
            if hasattr(server, 'send_message'):
                server.send_message(msg)
            else:
                text = msg.as_string()
                server.sendmail(self.email_settings.get('from_email'), to_email, text)
            
            server.quit()
            
            logger.info(f"Email notification sent to {to_email}")
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            st.warning(f"Email notification failed: {str(e)}")

class JobAutomationApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.auth = AuthManager(self.db)
        self.job_scraper = JobScraper()
        self.form_automator = FormAutomator()
        
        # Initialize session state
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
        if 'ai_assistant' not in st.session_state:
            st.session_state.ai_assistant = None
    
    def run(self):
        """Main application runner"""
        st.title("💼 Job Application Automation System")
        
        if not st.session_state.user_id:
            self.show_auth_page()
        else:
            self.show_main_app()
    
    def show_auth_page(self):
        """Authentication page"""
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.subheader("Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login"):
                user_id = self.auth.authenticate_user(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with tab2:
            st.subheader("Register")
            new_username = st.text_input("Username", key="reg_username")
            new_email = st.text_input("Email", key="reg_email")
            new_password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            if st.button("Register"):
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif self.auth.register_user(new_username, new_password, new_email):
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Registration failed. Username might already exist.")
    
    def show_main_app(self):
        """Main application interface"""
        # Sidebar navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.selectbox(
            "Choose a page",
            ["Dashboard", "Profiles", "Job Search", "Applications", "Analytics", "Settings"]
        )
        
        if st.sidebar.button("Logout"):
            st.session_state.user_id = None
            st.rerun()
        
        # Main content
        if page == "Dashboard":
            self.show_dashboard()
        elif page == "Profiles":
            self.show_profiles_page()
        elif page == "Job Search":
            self.show_job_search_page()
        elif page == "Applications":
            self.show_applications_page()
        elif page == "Analytics":
            self.show_analytics_page()
        elif page == "Settings":
            self.show_settings_page()
    
    def show_dashboard(self):
        """Dashboard page"""
        st.header("📊 Dashboard")
        
        # Get statistics
        stats = self.get_user_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Applications", stats.get('total_applications', 0))
        
        with col2:
            st.metric("Pending Applications", stats.get('pending_applications', 0))
        
        with col3:
            st.metric("Response Rate", f"{stats.get('response_rate', 0):.1f}%")
        
        with col4:
            st.metric("Active Profiles", stats.get('active_profiles', 0))
        
        # Recent activity
        st.subheader("Recent Activity")
        recent_applications = self.get_recent_applications()
        
        if recent_applications:
            df = pd.DataFrame([
                {
                    'Date': app['applied_date'],
                    'Job Title': app['job_title'],
                    'Company': app['company'],
                    'Status': app['status']
                }
                for app in recent_applications
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No recent applications found.")
        
        # Quick actions
        st.subheader("Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Search Jobs", use_container_width=True):
                st.session_state.quick_action = "search_jobs"
        
        with col2:
            if st.button("📝 Create Profile", use_container_width=True):
                st.session_state.quick_action = "create_profile"
        
        with col3:
            if st.button("📊 View Analytics", use_container_width=True):
                st.session_state.quick_action = "view_analytics"
    
    def show_profiles_page(self):
        """Profiles management page"""
        st.header("👤 Profiles")
        
        tab1, tab2 = st.tabs(["My Profiles", "Create New Profile"])
        
        with tab1:
            profiles = self.get_user_profiles()
            
            if profiles:
                for profile in profiles:
                    with st.expander(f"📄 {profile['name']}"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Experience:** {profile['experience']}")
                            st.write(f"**Skills:** {profile['skills']}")
                            st.write(f"**Summary:** {profile['summary']}")
                            st.write(f"**Target Positions:** {profile['target_positions']}")
                        
                        with col2:
                            if st.button("Edit", key=f"edit_{profile['id']}"):
                                st.session_state.edit_profile = profile['id']
                            if st.button("Delete", key=f"delete_{profile['id']}"):
                                self.delete_profile(profile['id'])
                                st.rerun()
            else:
                st.info("No profiles found. Create your first profile!")
        
        with tab2:
            self.show_profile_form()
    
    def show_profile_form(self, profile_data=None):
        """Profile creation/editing form"""
        st.subheader("Create New Profile" if not profile_data else "Edit Profile")
        
        with st.form("profile_form"):
            name = st.text_input("Profile Name", value=profile_data.get('name', '') if profile_data else '')
            experience = st.text_area("Experience Summary", value=profile_data.get('experience', '') if profile_data else '')
            skills = st.text_area("Skills (comma-separated)", value=profile_data.get('skills', '') if profile_data else '')
            summary = st.text_area("Professional Summary", value=profile_data.get('summary', '') if profile_data else '')
            target_positions = st.text_area("Target Positions (comma-separated)", value=profile_data.get('target_positions', '') if profile_data else '')
            
            resume_file = st.file_uploader("Upload Resume", type=['pdf', 'doc', 'docx'])
            
            submitted = st.form_submit_button("Save Profile")
            
            if submitted and name and skills:
                profile_id = str(uuid.uuid4()) if not profile_data else profile_data['id']
                
                # Save resume file
                resume_path = None
                if resume_file:
                    resume_path = f"resumes/{st.session_state.user_id}_{profile_id}_{resume_file.name}"
                    os.makedirs("resumes", exist_ok=True)
                    with open(resume_path, "wb") as f:
                        f.write(resume_file.getbuffer())
                
                success = self.db.execute_query(
                    "INSERT OR REPLACE INTO profiles (id, user_id, name, skills, experience, summary, target_positions, resume_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (profile_id, st.session_state.user_id, name, skills, experience, summary, target_positions, resume_path)
                )
                
                if success:
                    st.success("Profile saved successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to save profile")
    
    def show_job_search_page(self):
        """Job search page"""
        st.header("🔍 Job Search")
        
        # Search form
        with st.form("job_search_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                keywords = st.text_input("Keywords", placeholder="e.g., Python Developer")
                location = st.text_input("Location", placeholder="e.g., New York, NY")
            
            with col2:
                job_sources = st.multiselect("Job Sources", ["Indeed", "LinkedIn"], default=["Indeed"])
                max_results = st.slider("Max Results", 5, 50, 20)
            
            search_submitted = st.form_submit_button("🔍 Search Jobs")
        
        if search_submitted and keywords:
            with st.spinner("Searching for jobs..."):
                jobs = []
                
                if "Indeed" in job_sources:
                    indeed_jobs = self.job_scraper.search_indeed_jobs(keywords, location, max_results//2)
                    jobs.extend(indeed_jobs)
                
                if "LinkedIn" in job_sources:
                    linkedin_jobs = self.job_scraper.search_linkedin_jobs(keywords, location, max_results//2)
                    jobs.extend(linkedin_jobs)
                
                # Save jobs to database
                for job in jobs:
                    self.db.execute_query(
                        "INSERT OR REPLACE INTO jobs (id, title, company, location, description, url, salary_range, posted_date, match_score, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (job.id, job.title, job.company, job.location, job.description, job.url, job.salary_range, job.posted_date, job.match_score, job.source)
                    )
                
                st.success(f"Found {len(jobs)} jobs!")
                st.session_state.search_results = jobs
        
        # Display search results
        if 'search_results' in st.session_state and st.session_state.search_results:
            st.subheader("Search Results")
            
            for job in st.session_state.search_results:
                with st.expander(f"📋 {job.title} at {job.company}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Location:** {job.location}")
                        st.write(f"**Salary:** {job.salary_range}")
                        st.write(f"**Posted:** {job.posted_date.strftime('%Y-%m-%d')}")
                        st.write(f"**Description:** {job.description[:200]}...")
                        st.write(f"**Match Score:** {job.match_score:.2f}/1.0")
                    
                    with col2:
                        profiles = self.get_user_profiles()
                        if profiles:
                            selected_profile = st.selectbox(
                                "Select Profile", 
                                [p['name'] for p in profiles],
                                key=f"profile_{job.id}"
                            )
                            
                            if st.button("Apply Now", key=f"apply_{job.id}"):
                                self.apply_to_job(job, selected_profile, profiles)
                        else:
                            st.info("Create a profile first to apply")
                        
                        if st.button("View Details", key=f"details_{job.id}"):
                            st.session_state.selected_job = job
    
    def show_applications_page(self):
        """Applications tracking page"""
        st.header("📄 My Applications")
        
        applications = self.get_user_applications()
        
        if applications:
            # Filter options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    ["All", "pending", "applied", "interview", "rejected", "accepted"]
                )
            
            with col2:
                date_filter = st.date_input("From Date", value=datetime.now() - timedelta(days=30))
            
            with col3:
                company_filter = st.text_input("Company Filter")
            
            # Apply filters
            filtered_apps = applications
            if status_filter != "All":
                filtered_apps = [app for app in filtered_apps if app['status'] == status_filter]
            if company_filter:
                filtered_apps = [app for app in filtered_apps if company_filter.lower() in app['company'].lower()]
            
            # Display applications
            for app in filtered_apps:
                with st.expander(f"📋 {app['job_title']} at {app['company']} - {app['status'].title()}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Applied Date:** {app['applied_date']}")
                        st.write(f"**Status:** {app['status'].title()}")
                        st.write(f"**Profile Used:** {app['profile_name']}")
                        if app['notes']:
                            st.write(f"**Notes:** {app['notes']}")
                        
                        # Show cover letter if available
                        if app['cover_letter']:
                            with st.expander("View Cover Letter"):
                                st.text(app['cover_letter'])
                    
                    with col2:
                        new_status = st.selectbox(
                            "Update Status",
                            ["pending", "applied", "interview", "rejected", "accepted"],
                            index=["pending", "applied", "interview", "rejected", "accepted"].index(app['status']),
                            key=f"status_{app['id']}"
                        )
                        
                        notes = st.text_area("Notes", value=app['notes'] or "", key=f"notes_{app['id']}")
                        
                        if st.button("Update", key=f"update_{app['id']}"):
                            self.update_application_status(app['id'], new_status, notes)
                            st.success("Application updated!")
                            st.rerun()
        else:
            st.info("No applications found. Start applying to jobs!")
    
    def show_analytics_page(self):
        """Analytics and reporting page"""
        st.header("📊 Analytics & Reports")
        
        # Get analytics data
        analytics_data = self.get_analytics_data()
        
        if not analytics_data['applications']:
            st.info("No application data available for analytics.")
            return
        
        # Application status distribution
        st.subheader("Application Status Distribution")
        status_counts = {}
        for app in analytics_data['applications']:
            status = app['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            fig_pie = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="Application Status Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Applications over time
        st.subheader("Applications Over Time")
        df_apps = pd.DataFrame(analytics_data['applications'])
        df_apps['applied_date'] = pd.to_datetime(df_apps['applied_date'])
        df_apps['date'] = df_apps['applied_date'].dt.date
        
        daily_apps = df_apps.groupby('date').size().reset_index(name='count')
        
        fig_line = px.line(
            daily_apps,
            x='date',
            y='count',
            title="Applications per Day"
        )
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Top companies applied to
        st.subheader("Top Companies")
        company_counts = df_apps['company'].value_counts().head(10)
        
        if not company_counts.empty:
            fig_bar = px.bar(
                x=company_counts.values,
                y=company_counts.index,
                orientation='h',
                title="Top 10 Companies Applied To"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Response rate analysis
        st.subheader("Response Rate Analysis")
        responded = len([app for app in analytics_data['applications'] if app['response_received']])
        total = len(analytics_data['applications'])
        response_rate = (responded / total * 100) if total > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Applications", total)
        
        with col2:
            st.metric("Responses Received", responded)
        
        with col3:
            st.metric("Response Rate", f"{response_rate:.1f}%")
    
    def show_settings_page(self):
        """Settings and configuration page"""
        st.header("⚙️ Settings")
        
        tab1, tab2, tab3, tab4 = st.tabs(["AI Settings", "Email Settings", "Automation", "Account"])
        
        with tab1:
            st.subheader("AI Assistant Settings")
            
            current_settings = self.get_user_settings()
            
            openai_key = st.text_input(
                "OpenAI API Key",
                value=current_settings.get('openai_api_key', ''),
                type="password",
                help="Enter your OpenAI API key for AI-powered features"
            )
            
            if st.button("Test AI Connection"):
                if openai_key:
                    try:
                        st.session_state.ai_assistant = AIAssistant(openai_key)
                        st.success("AI connection successful!")
                    except Exception as e:
                        st.error(f"AI connection failed: {e}")
                else:
                    st.error("Please enter an API key")
            
            if st.button("Save AI Settings"):
                self.save_user_settings({'openai_api_key': openai_key})
                st.success("Settings saved!")
        
        with tab2:
            st.subheader("Email Notification Settings")
            
            email_settings = current_settings.get('email_settings', {})
            
            from_email = st.text_input("From Email", value=email_settings.get('from_email', ''))
            email_password = st.text_input("Email Password", value=email_settings.get('password', ''), type="password")
            smtp_server = st.text_input("SMTP Server", value=email_settings.get('smtp_server', 'smtp.gmail.com'))
            
            enable_notifications = st.checkbox("Enable Email Notifications", value=email_settings.get('enabled', False))
            
            if st.button("Save Email Settings"):
                email_config = {
                    'from_email': from_email,
                    'password': email_password,
                    'smtp_server': smtp_server,
                    'enabled': enable_notifications
                }
                self.save_user_settings({'email_settings': email_config})
                st.success("Email settings saved!")
        
        with tab3:
            st.subheader("Automation Settings")
            
            automation_settings = current_settings.get('automation_settings', {})
            
            auto_apply = st.checkbox("Enable Auto-Apply", value=automation_settings.get('auto_apply', False))
            min_match_score = st.slider("Minimum Match Score for Auto-Apply", 0.0, 1.0, automation_settings.get('min_match_score', 0.7))
            daily_limit = st.number_input("Daily Application Limit", min_value=1, max_value=50, value=automation_settings.get('daily_limit', 10))
            
            st.warning("⚠️ Auto-apply is experimental. Review applications before submission.")
            
            if st.button("Save Automation Settings"):
                auto_config = {
                    'auto_apply': auto_apply,
                    'min_match_score': min_match_score,
                    'daily_limit': daily_limit
                }
                self.save_user_settings({'automation_settings': auto_config})
                st.success("Automation settings saved!")
        
        with tab4:
            st.subheader("Account Settings")
            
            if st.button("Export Data"):
                self.export_user_data()
            
            st.subheader("⚠️ Danger Zone")
            if st.button("Delete Account", type="secondary"):
                if st.session_state.get('confirm_delete'):
                    self.delete_user_account()
                    st.success("Account deleted successfully!")
                    st.session_state.user_id = None
                    st.rerun()
                else:
                    st.session_state.confirm_delete = True
                    st.error("Click again to confirm account deletion")
    
    # Helper methods
    def get_user_statistics(self):
        """Get user dashboard statistics"""
        stats = {}
        
        # Total applications
        result = self.db.execute_query(
            "SELECT COUNT(*) FROM applications WHERE user_id = ?",
            (st.session_state.user_id,),
            fetch=True
        )
        stats['total_applications'] = result[0][0] if result else 0
        
        # Pending applications
        result = self.db.execute_query(
            "SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'pending'",
            (st.session_state.user_id,),
            fetch=True
        )
        stats['pending_applications'] = result[0][0] if result else 0
        
        # Response rate
        result = self.db.execute_query(
            "SELECT COUNT(*) FROM applications WHERE user_id = ? AND response_received = 1",
            (st.session_state.user_id,),
            fetch=True
        )
        responses = result[0][0] if result else 0
        stats['response_rate'] = (responses / stats['total_applications'] * 100) if stats['total_applications'] > 0 else 0
        
        # Active profiles
        result = self.db.execute_query(
            "SELECT COUNT(*) FROM profiles WHERE user_id = ?",
            (st.session_state.user_id,),
            fetch=True
        )
        stats['active_profiles'] = result[0][0] if result else 0
        
        return stats
    
    def get_recent_applications(self, limit=5):
        """Get recent applications"""
        result = self.db.execute_query(
            """SELECT a.applied_date, j.title as job_title, j.company, a.status 
               FROM applications a 
               JOIN jobs j ON a.job_id = j.id 
               WHERE a.user_id = ? 
               ORDER BY a.applied_date DESC 
               LIMIT ?""",
            (st.session_state.user_id, limit),
            fetch=True
        )
        
        if result:
            return [
                {
                    'applied_date': row[0],
                    'job_title': row[1],
                    'company': row[2],
                    'status': row[3]
                }
                for row in result
            ]
        return []
    
    def get_user_profiles(self):
        """Get user profiles"""
        result = self.db.execute_query(
            "SELECT id, name, skills, experience, summary, target_positions FROM profiles WHERE user_id = ?",
            (st.session_state.user_id,),
            fetch=True
        )
        
        if result:
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'skills': row[2],
                    'experience': row[3],
                    'summary': row[4],
                    'target_positions': row[5]
                }
                for row in result
            ]
        return []
    
    def delete_profile(self, profile_id):
        """Delete a profile"""
        return self.db.execute_query(
            "DELETE FROM profiles WHERE id = ? AND user_id = ?",
            (profile_id, st.session_state.user_id)
        )
    
    def apply_to_job(self, job, selected_profile_name, profiles):
        """Apply to a job"""
        # Find the selected profile
        profile_data = next((p for p in profiles if p['name'] == selected_profile_name), None)
        if not profile_data:
            st.error("Profile not found")
            return
        
        # Create JobProfile object
        profile = JobProfile(
            id=profile_data['id'],
            name=profile_data['name'],
            skills=profile_data['skills'].split(',') if profile_data['skills'] else [],
            experience=profile_data['experience'],
            summary=profile_data['summary'],
            target_positions=profile_data['target_positions'].split(',') if profile_data['target_positions'] else [],
            created_at=datetime.now()
        )
        
        # Generate cover letter using AI if available
        cover_letter = ""
        if st.session_state.ai_assistant:
            try:
                cover_letter = st.session_state.ai_assistant.generate_cover_letter(job, profile)
            except Exception as e:
                logger.error(f"Error generating cover letter: {e}")
                cover_letter = f"Dear Hiring Manager,\n\nI am interested in the {job.title} position at {job.company}.\n\nBest regards"
        
        # Create application record
        app_id = str(uuid.uuid4())
        success = self.db.execute_query(
            "INSERT INTO applications (id, job_id, profile_id, user_id, status, applied_date, cover_letter) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (app_id, job.id, profile_data['id'], st.session_state.user_id, 'applied', datetime.now(), cover_letter)
        )
        
        if success:
            st.success(f"Successfully applied to {job.title} at {job.company}!")
            
            # Send notification if enabled
            user_settings = self.get_user_settings()
            email_settings = user_settings.get('email_settings', {})
            if email_settings.get('enabled'):
                notification_manager = NotificationManager(email_settings)
                user_email = self.get_user_email()
                if user_email:
                    notification_manager.send_email_notification(
                        f"Job Application Submitted - {job.title}",
                        f"Your application for {job.title} at {job.company} has been submitted successfully.",
                        user_email
                    )
        else:
            st.error("Failed to submit application")
    
    def get_user_applications(self):
        """Get user applications with job details"""
        result = self.db.execute_query(
            """SELECT a.id, a.status, a.applied_date, a.cover_letter, a.notes, a.response_received,
                      j.title as job_title, j.company, p.name as profile_name
               FROM applications a
               JOIN jobs j ON a.job_id = j.id
               JOIN profiles p ON a.profile_id = p.id
               WHERE a.user_id = ?
               ORDER BY a.applied_date DESC""",
            (st.session_state.user_id,),
            fetch=True
        )
        
        if result:
            return [
                {
                    'id': row[0],
                    'status': row[1],
                    'applied_date': row[2],
                    'cover_letter': row[3],
                    'notes': row[4],
                    'response_received': bool(row[5]),
                    'job_title': row[6],
                    'company': row[7],
                    'profile_name': row[8]
                }
                for row in result
            ]
        return []
    
    def update_application_status(self, app_id, status, notes):
        """Update application status and notes"""
        return self.db.execute_query(
            "UPDATE applications SET status = ?, notes = ? WHERE id = ? AND user_id = ?",
            (status, notes, app_id, st.session_state.user_id)
        )
    
    def get_analytics_data(self):
        """Get analytics data"""
        applications = self.get_user_applications()
        
        return {
            'applications': applications,
            'total_applications': len(applications),
            'response_rate': len([app for app in applications if app['response_received']]) / len(applications) * 100 if applications else 0
        }
    
    def get_user_settings(self):
        """Get user settings"""
        result = self.db.execute_query(
            "SELECT openai_api_key, email_settings, automation_settings, notification_settings FROM settings WHERE user_id = ?",
            (st.session_state.user_id,),
            fetch=True
        )
        
        if result:
            row = result[0]
            return {
                'openai_api_key': row[0] or '',
                'email_settings': json.loads(row[1]) if row[1] else {},
                'automation_settings': json.loads(row[2]) if row[2] else {},
                'notification_settings': json.loads(row[3]) if row[3] else {}
            }
        return {}
    
    def save_user_settings(self, settings):
        """Save user settings"""
        current_settings = self.get_user_settings()
        current_settings.update(settings)
        
        return self.db.execute_query(
            "INSERT OR REPLACE INTO settings (user_id, openai_api_key, email_settings, automation_settings, notification_settings) VALUES (?, ?, ?, ?, ?)",
            (
                st.session_state.user_id,
                current_settings.get('openai_api_key', ''),
                json.dumps(current_settings.get('email_settings', {})),
                json.dumps(current_settings.get('automation_settings', {})),
                json.dumps(current_settings.get('notification_settings', {}))
            )
        )
    
    def get_user_email(self):
        """Get user email"""
        result = self.db.execute_query(
            "SELECT email FROM users WHERE id = ?",
            (st.session_state.user_id,),
            fetch=True
        )
        return result[0][0] if result and result[0][0] else None
    
    def export_user_data(self):
        """Export user data"""
        try:
            # Get all user data
            profiles = self.get_user_profiles()
            applications = self.get_user_applications()
            settings = self.get_user_settings()
            
            export_data = {
                'profiles': profiles,
                'applications': applications,
                'settings': {k: v for k, v in settings.items() if k != 'openai_api_key'},  # Don't export API key
                'exported_at': datetime.now().isoformat()
            }
            
            # Create download
            json_data = json.dumps(export_data, indent=2, default=str)
            st.download_button(
                label="📥 Download Data Export",
                data=json_data,
                file_name=f"job_automation_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"Export failed: {e}")
    
    def delete_user_account(self):
        """Delete user account and all associated data"""
        try:
            # Delete all user data
            self.db.execute_query("DELETE FROM applications WHERE user_id = ?", (st.session_state.user_id,))
            self.db.execute_query("DELETE FROM profiles WHERE user_id = ?", (st.session_state.user_id,))
            self.db.execute_query("DELETE FROM settings WHERE user_id = ?", (st.session_state.user_id,))
            self.db.execute_query("DELETE FROM users WHERE id = ?", (st.session_state.user_id,))
            
            # Clear session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
                
        except Exception as e:
            st.error(f"Account deletion failed: {e}")

def run_automation_scheduler():
    """Background scheduler for automation tasks"""
    def check_and_apply():
        """Check for new jobs and auto-apply if conditions are met"""
        try:
            # This would run the automation logic
            # For now, it's a placeholder
            logger.info("Running automation check...")
        except Exception as e:
            logger.error(f"Automation error: {e}")
    
    # Schedule automation to run every hour
    schedule.every().hour.do(check_and_apply)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # Start the automation scheduler in a background thread
    automation_thread = threading.Thread(target=run_automation_scheduler, daemon=True)
    automation_thread.start()
    
    # Run the Streamlit app
    app = JobAutomationApp()
    app.run()
