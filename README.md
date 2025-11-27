# 🤖 Employee AI Agents (RAG + SQL)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A powerful AI-powered system that interacts with employee data using **Natural Language**. It combines **RAG (Retrieval-Augmented Generation)** for document queries and **SQL Agents** for database queries.

## 🚀 Features
- **RAG System:** Uses `rag_model.py` to answer questions based on internal knowledge.
- **SQL Integration:** Queries `company.db` directly to fetch structured employee data.
- **Automated Database Setup:** Includes scripts to generate and manage the employee database.

## 📂 Project Structure
```bash
Employee-AI-Agents/
├── app.py                  # 🚀 Main application (Run this file)
├── rag_model.py            # 🧠 AI Logic for RAG (Retrieval Augmented Generation)
├── create_db.py            # 🗄️ Script to initialize/reset the database
├── utils.py                # 🛠️ Helper functions
├── company.db              # 💾 SQLite Database file
├── requirements.txt        # 📦 List of python dependencies
├── .env                    # 🔑 API Keys (Do NOT upload to GitHub)
└── README.md               # 📄 Project documentation

⚙️ Installation
Run these commands one by one in your terminal to set up the project:

# 1. Clone the repository
git clone https://github.com/harinderkaur2360-svg/Employee-AI-Agents.git
cd Employee-AI-Agents

# 2. Create and Activate Virtual Environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Setup API Key (Create a .env file manually and add this line)
# GROQ_API_KEY=your_groq_api_key_here

# 5. Initialize Database (Optional)
python create_db.py

# 6. Run the Application
streamlit run app.pys

🤝 Contributing

    Fork the repo.

    Create a new branch.

    Commit changes and Push.

    Submit a Pull Request.

Author: Harinder Kaur