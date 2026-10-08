import streamlit as st
import sqlite3
import os
import json
import re
from datetime import datetime
import google.generativeai as genai

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="JSS AI Study Buddy", page_icon="📚", layout="wide")

DB_PATH = "study_buddy.db"
from syllabus_data import FULL_SYLLABUS

@st.cache_resource
def refresh_syllabus_once():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    cu = c.cursor()
    cu.execute("SELECT id, subject_name FROM subjects")
    ids = {n: i for i, n in cu.fetchall()}
    cu.execute("DELETE FROM units")
    for subject, units in FULL_SYLLABUS.items():
        if subject in ids:
            for label, hrs, title, topics in units:
                cu.execute(
                    "INSERT INTO units (subject_id, unit_number, unit_title, topics) VALUES (?,?,?,?)",
                    (ids[subject], f"{label} ({hrs} Hrs)", title, topics),
                )
    c.commit()
    c.close()
    return True
# Custom CSS for a more colorful, polished look
st.markdown("""
<style>
    .stButton>button {
        border-radius: 10px;
        border: none;
        background: linear-gradient(90deg, #6A0DAD, #9B59B6);
        color: white;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: scale(1.03);
        box-shadow: 0 4px 12px rgba(106, 13, 173, 0.3);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F3E8FF, #FFFFFF);
    }
    h1, h2, h3 {
        color: #6A0DAD;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE SETUP (runs automatically, only once)
# ============================================================
def init_db():
    first_time = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL,
        semester INTEGER NOT NULL,
        elective_group TEXT,
        textbook_title TEXT,
        textbook_author TEXT,
        web_reference TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER,
        unit_number TEXT,
        unit_title TEXT,
        topics TEXT,
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS pyqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER,
        question_text TEXT,
        marks INTEGER,
        is_ai_predicted INTEGER DEFAULT 1,
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS generated_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        subject_id INTEGER,
        topic TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()

    if first_time:
        seed_data(cur)
        conn.commit()

    return conn

def seed_data(cur):
    subjects = [
        # (name, semester, elective_group, textbook_title, textbook_author, web_reference)
        ("Fundamentals of Mathematics for Computer Applications", 1, None, "Discrete Mathematics and its Applications", "Kenneth H Rosen", "https://www.tutorialspoint.com/discrete_mathematics/index.htm"),
        ("Programming and Data Structures using C", 1, None, "Data Structures Using C and C++", "Aaron M. Tenenbaum", "https://nptel.ac.in/courses/106102064"),
        ("Python Programming", 1, None, "Think Python: How to Think Like a Computer Scientist", "Allen B. Downey", "https://onlinecourses.nptel.ac.in/noc24_cs57/preview"),
        ("Database Management System", 1, None, "Database System Concepts", "A. Silberschatz, Henry F. Korth, S. Sudharshan", "https://www.tutorialspoint.com/sql/sql-rdbms-concepts.htm"),
        ("Operating System with Linux", 1, None, "Operating System Concepts", "Silberschatz", "https://onlinecourses.nptel.ac.in/noc19_cs65"),
        ("Communication & Social Skills for Professional Development", 1, None, "Technical Communication - Principles and Practices", "Meenakshi Raman, Sangeeta Sharma", "http://www2.ece.ohio-state.edu/~passino/ee481.html"),

        ("Object Oriented Programming using Java", 2, None, "Java - The Complete Reference", "Herbert Schildt", "http://www.learnjavaonline.org/"),
        ("Agile Software Engineering", 2, None, "Software Engineering", "Various", "https://www.coursehero.com"),
        ("Advance Design and Analysis of Algorithms", 2, None, "Introduction to Algorithms", "T. H Cormen, C E Leiserson, R L Rivest, C Stein", "https://ocw.mit.edu/courses/6-854j-advanced-algorithms-fall-2008/"),
        ("Web Development", 2, None, "Beginning HTML5 and CSS3", "Christopher Murphy et al.", "https://www.w3schools.com/html"),
        ("Entrepreneurship & Business Basics", 2, None, "Entrepreneurship", "Barringer & Ireland", "https://hbr.org/2020/09/3-tips-for-successfully-managing-family-businesses"),
        ("Financial Technologies", 2, "Elective-I", "The Future of Finance", "Henri Arslanian, Fabrice Fischer", "https://www.amazon.in/Digital-Banking-Indian-Institute-finance"),
        ("Computer Graphics", 2, "Elective-I", "Computer Graphics Principles & Practice", "Foley et al.", "https://gfxcourses.stanford.edu/cs248a/winter25"),
        ("Data Communication and Computer Networks", 2, "Elective-I", "Data Communications and Networking", "B. A. Forouzan", "http://freevideolectures.com/Course/2276/Computer-Networks"),
        ("Cryptography and Cyber Security", 2, "Elective-I", "Cryptography and Network Security", "William Stallings", "https://www.coursera.org/learn/crypto"),

        ("Machine Learning Techniques", 3, None, "Machine Learning", "Tom M. Mitchell", "https://onlinecourses.nptel.ac.in/noc23_cs18/preview"),
        ("Data Analytics", 3, None, "Mining of Massive Datasets", "Anand Rajaraman, Jeffrey David Ullman", "https://towardsdatascience.com"),
        ("Research Methodology", 3, None, "Reflexive Methodology", "Mats Alvesson, Kaj Skoldberg", None),
        ("Cloud Computing", 3, "Elective-2", "Cloud Computing", "Lizhe Wang, Rajiv Ranjan, Jinjun Chen", "https://cloud.google.com/training"),
        ("Block Chain Technology", 3, "Elective-2", "Mastering Bitcoin", "Andreas M. Antonopoulos", "https://bitcoin.org/en/"),
        ("Internet of Things", 3, "Elective-2", "The Internet of Things", "Raj Kamal", "https://onlinecourses.nptel.ac.in/noc19_cs65"),
        ("Data Warehousing and Data Mining", 3, "Elective-2", "Data Mining Concepts and Techniques", "Jiawei Han, Micheline Kamber, Jian Pei", "https://nptel.ac.in/courses/106/105/106105174/"),
        ("Prompt Engineering", 3, "Elective-3", "Prompt Engineering for Generative AI", "James Phoenix, Mike Taylor", "https://www.promptingguide.ai/"),
        ("Natural Language Processing", 3, "Elective-3", "Speech and Language Processing", "Daniel Jurafsky, James H. Martin", "https://web.stanford.edu/class/cs224n/"),
        ("Mobile Application Development", 3, "Elective-3", "Professional Android 2 Application Development", "Reto Meier", None),
        ("Distributed System", 3, "Elective-3", "Distributed Systems: Concepts and Design", "Coulouris, Dollimore, Kindberg", "https://nptel.ac.in/courses/106106168"),

        ("Major Project", 4, None, None, None, None),
    ]
    cur.executemany(
        "INSERT INTO subjects (subject_name, semester, elective_group, textbook_title, textbook_author, web_reference) VALUES (?,?,?,?,?,?)",
        subjects
    )

    cur.execute("SELECT id, subject_name FROM subjects")
    sid = {name: i for i, name in cur.fetchall()}
    units = [
    # Fundamentals of Mathematics
    (sid["Fundamentals of Mathematics for Computer Applications"], "Unit I", "Linear Systems and Matrices",
     "Complex matrices, Hermitian/Skew-Hermitian/Unitary matrices, elementary transformation, rank, Cayley-Hamilton theorem, eigenvalues and eigenvectors"),
    (sid["Fundamentals of Mathematics for Computer Applications"], "Unit II", "Set Theory and Relations",
     "Sets, operations, cardinality, inclusion-exclusion, pigeonhole principle, relations, closures, equivalence relations, partial orderings"),
    (sid["Fundamentals of Mathematics for Computer Applications"], "Unit III", "Mathematical Logic",
     "Propositional logic, propositional equivalences, predicates and quantifiers, rules of inference, introduction to proofs"),
    (sid["Fundamentals of Mathematics for Computer Applications"], "Unit IV", "Graph Theory",
     "Graphs and graph models, terminology, isomorphism, connectivity, Euler and Hamilton paths, shortest path problems, planar graphs, graph coloring"),
    (sid["Fundamentals of Mathematics for Computer Applications"], "Unit V", "Random Variables and Probability Distribution",
     "Discrete/continuous probability distributions, mean, variance, covariance, binomial and normal distribution, exponential distribution"),

    # Programming and Data Structures using C
    (sid["Programming and Data Structures using C"], "Unit I", "C Fundamentals",
     "Structure of a C program, data types, expressions, decision making, looping, arrays, strings"),
    (sid["Programming and Data Structures using C"], "Unit II", "Functions and Pointers",
     "Pass by value/reference, recursion, pointer arithmetic, dynamic memory allocation, structures, algorithm analysis basics"),
    (sid["Programming and Data Structures using C"], "Unit III", "Stacks and Queues",
     "Array representation, prefix/infix/postfix expressions, simple/circular/priority queues"),
    (sid["Programming and Data Structures using C"], "Unit IV", "Linked Lists and Hashing",
     "Singly/doubly linked lists, linked list implementation of stacks, hash tables, hash functions"),
    (sid["Programming and Data Structures using C"], "Unit V", "Non-Linear Data Structures",
     "Graphs, graph traversal, binary trees, tree traversals, binary search trees"),

    # Python Programming
    (sid["Python Programming"], "Unit I", "Python Basics and Control Flow",
     "Data types, variables, if/else, for/while loops, break/continue/pass"),
    (sid["Python Programming"], "Unit II", "Data Structures in Python",
     "Strings, lists, tuples, sets, dictionaries and their manipulation methods"),
    (sid["Python Programming"], "Unit III", "Functions and Exception Handling",
     "Def statements, return values, lambda, map/filter/reduce, iterators, generators, exception handling"),
    (sid["Python Programming"], "Unit IV", "File Handling",
     "read(), readline(), readlines(), write(), writelines(), file pointer manipulation using seek"),

    # DBMS
    (sid["Database Management System"], "Unit I", "Introduction to Databases",
     "Database applications, relational databases, database design, data storage, transaction management"),
    (sid["Database Management System"], "Unit II", "ER Model",
     "Design process, ER model, constraints, ER diagrams, reduction to relational schemas"),
    (sid["Database Management System"], "Unit III", "SQL Basics",
     "SQL data definition, basic queries, set operations, aggregate functions, nested subqueries, joins, views"),
    (sid["Database Management System"], "Unit IV", "Advanced SQL",
     "Functions/procedures, triggers, recursive queries, relational algebra, tuple relational calculus"),
    (sid["Database Management System"], "Unit V", "Normalization",
     "Atomic domains, first normal form, functional dependencies, decomposition, normal forms, database design process"),

    # OS with Linux
    (sid["Operating System with Linux"], "Unit I", "OS Concepts and Process Management",
     "Process concept, scheduling, threads, CPU scheduling algorithms, critical section problem, semaphores"),
    (sid["Operating System with Linux"], "Unit II", "Deadlocks and Memory Management",
     "Deadlock prevention/avoidance/detection, paging, segmentation, virtual memory, page replacement algorithms"),
    (sid["Operating System with Linux"], "Unit III", "File Systems",
     "File concepts, access methods, directory structure, allocation methods, free space management"),
    (sid["Operating System with Linux"], "Unit IV", "I/O Systems",
     "Mass storage structure, disk scheduling algorithms, swap space management"),
    (sid["Operating System with Linux"], "Unit V", "Linux Shell",
     "Linux architecture, commands, shell scripting, command line arguments, exit status"),

    # Communication
    (sid["Communication & Social Skills for Professional Development"], "Unit I", "Process of Communication",
     "Language as a tool, levels of communication, communication networks"),
    (sid["Communication & Social Skills for Professional Development"], "Unit II", "Technology in Communication",
     "Software for creating/writing/presenting/transmitting documents"),
    (sid["Communication & Social Skills for Professional Development"], "Unit III", "Effective Presentation",
     "Defining purpose, audience analysis, visual aids, kinesics, proxemics"),
    (sid["Communication & Social Skills for Professional Development"], "Unit IV", "Ethics",
     "Definition of ethics, integrity, ethics in business, illusion of communication"),
    (sid["Communication & Social Skills for Professional Development"], "Unit V", "Professional Ethics",
     "Ethical behavior of IT professionals, supporting ethical practices of IT users"),

    # OOP Java
    (sid["Object Oriented Programming using Java"], "Unit I", "Java Fundamentals and OOP",
     "JVM, classes, constructors, inheritance, polymorphism, encapsulation, abstraction, packages"),
    (sid["Object Oriented Programming using Java"], "Unit II", "Exception Handling and Multithreading",
     "try/catch/finally, checked/unchecked exceptions, threads, thread lifecycle, synchronization"),
    (sid["Object Oriented Programming using Java"], "Unit III", "Java New Features",
     "Lambda expressions, Stream API, default/static methods, try-with-resources, records, sealed classes"),
    (sid["Object Oriented Programming using Java"], "Unit IV", "Collections Framework",
     "List/Set/Map interfaces, ArrayList, HashMap, TreeMap, Comparable/Comparator"),
    (sid["Object Oriented Programming using Java"], "Unit V", "Advanced Collections",
     "Sorting, hash table class, properties class, deeper collection framework hierarchy"),

    # Agile Software Engineering
    (sid["Agile Software Engineering"], "Unit I", "Introduction to Software Engineering",
     "Software characteristics, SDLC models: waterfall, prototype, spiral, iterative"),
    (sid["Agile Software Engineering"], "Unit II", "Requirements and SQA",
     "Requirement engineering process, SRS document, verification/validation, ISO 9000, SEI-CMM"),
    (sid["Agile Software Engineering"], "Unit III", "Software Design",
     "Architectural design, modularization, coupling/cohesion, function/object oriented design, software metrics"),
    (sid["Agile Software Engineering"], "Unit IV", "Software Testing",
     "Unit/integration/acceptance/regression testing, white box/black box testing, alpha/beta testing"),
    (sid["Agile Software Engineering"], "Unit V", "Maintenance and Project Management",
     "Software maintenance categories, configuration management, COCOMO, risk analysis"),

    # DAA
    (sid["Advance Design and Analysis of Algorithms"], "Unit I", "Sorting and Analysis",
     "Complexity analysis, growth of functions, shell/quick/merge/heap sort, sorting in linear time"),
    (sid["Advance Design and Analysis of Algorithms"], "Unit II", "Advanced Data Structures",
     "Red-Black trees, B-trees, Binomial heaps, Fibonacci heaps, Tries, skip lists"),
    (sid["Advance Design and Analysis of Algorithms"], "Unit III", "Divide and Conquer, Greedy",
     "Matrix multiplication, convex hull, Knapsack, MST (Prim's/Kruskal's), shortest paths (Dijkstra/Bellman-Ford)"),
    (sid["Advance Design and Analysis of Algorithms"], "Unit IV", "Dynamic Programming",
     "Knapsack, all-pair shortest paths, backtracking, branch and bound, TSP, N-Queen"),
    (sid["Advance Design and Analysis of Algorithms"], "Unit V", "Advanced Topics",
     "Fast Fourier Transform, string matching, NP-completeness, approximation algorithms"),

    # Web Development
    (sid["Web Development"], "Unit I", "Web Basics",
     "History of web, HTML lists/tables/forms, XML, DTD, DOM and SAX"),
    (sid["Web Development"], "Unit II", "CSS",
     "Style sheets, box model, CSS positioning, page layouts and site design"),
    (sid["Web Development"], "Unit III", "Scripting and Networking",
     "JavaScript basics, AJAX, internet addressing, TCP/IP sockets"),
    (sid["Web Development"], "Unit IV", "Enterprise Java and Node.js",
     "JavaBeans, session/stateless beans, Node.js, Express, REST API, MongoDB"),
    (sid["Web Development"], "Unit V", "Servlets and JSP",
     "Servlet lifecycle, HTTP requests, session tracking, JSP scripting, custom tag libraries"),

    # Entrepreneurship
    (sid["Entrepreneurship & Business Basics"], "Unit I", "Concepts of Entrepreneurship",
     "Traits, entrepreneurship process, theories, role in economic growth"),
    (sid["Entrepreneurship & Business Basics"], "Unit II", "Types of Entrepreneurs",
     "Social entrepreneurship, corporate entrepreneurs, family business, industry types"),
    (sid["Entrepreneurship & Business Basics"], "Unit III", "Resource Mobilization",
     "Types of resources, funding sources, venture capital, angel investors, incubators"),
    (sid["Entrepreneurship & Business Basics"], "Unit IV", "Business Structures",
     "Private vs public company, partnership, e-business benefits and limitations"),

    # Machine Learning
    (sid["Machine Learning Techniques"], "Unit I", "Introduction to AI and ML",
     "History of AI, comparison with data science, types of ML, feature selection, data pre-processing"),
    (sid["Machine Learning Techniques"], "Unit II", "Supervised Learning",
     "Linear/multiple/logistic regression, KNN, Naive Bayes, decision trees, SVM, random forest"),
    (sid["Machine Learning Techniques"], "Unit III", "Unsupervised Learning",
     "Dimensionality reduction, K-Means, C-means, fuzzy C-means, EM algorithm, Apriori, HMMs"),
    (sid["Machine Learning Techniques"], "Unit IV", "Reinforcement Learning",
     "Bellman equation, Markov decision process, Q-learning, temporal difference learning"),
    (sid["Machine Learning Techniques"], "Unit V", "Neural Networks and Deep Learning",
     "Neural networks, DQN, CNN layers/architectures, RNN, speech-to-text, image classification"),

    # ============================================================
    # DATA ANALYTICS - FULLER OFFICIAL SYLLABUS
    # ============================================================
    (sid["Data Analytics"], "Unit I", "Introduction to Data Analytics",
     """Sources and nature of data, classification of data
(structured, semi-structured, unstructured), characteristics of data,
introduction to Big Data platform, need of data analytics,
evolution of analytic scalability, analytic process and tools,
analysis vs reporting, modern data analytic tools,
applications of data analytics.

Data Analytics Lifecycle:
Need, key roles for successful analytic projects,
various phases of data analytics lifecycle – discovery,
data preparation, model planning, model building,
communicating results, operationalization."""),

    (sid["Data Analytics"], "Unit II", "Data Analysis",
     """Regression modeling, multivariate analysis, Bayesian modeling,
inference and Bayesian networks, support vector and kernel methods,
analysis of time series: linear systems analysis & nonlinear dynamics,
rule induction, neural networks: learning and generalisation,
competitive learning, principal component analysis and neural networks,
fuzzy logic: extracting fuzzy models from data,
fuzzy decision trees, stochastic search methods."""),

    (sid["Data Analytics"], "Unit III", "Mining Data Streams",
     """Introduction to streams concepts, stream data model and architecture,
stream computing, sampling data in a stream, filtering streams,
counting distinct elements in a stream, estimating moments,
counting oneness in a window, decaying window,
Real-time Analytics Platform (RTAP) applications,
Case studies – real time sentiment analysis,
stock market predictions."""),

    (sid["Data Analytics"], "Unit IV", "Frequent Itemsets and Clustering",
     """Mining frequent itemsets, market based modelling,
Apriori algorithm, handling large data sets in main memory,
limited pass algorithm, counting frequent itemsets in a stream,
clustering techniques: hierarchical, K-means,
clustering high dimensional data, CLIQUE and ProCLUS,
frequent pattern based clustering methods,
clustering in non-euclidean space,
clustering for streams and parallelism."""),

    (sid["Data Analytics"], "Unit V", "Frame Works and Visualization",
     """MapReduce, Hadoop, Pig, Hive, HBase, MapR, Sharding,
NoSQL Databases, S3, Hadoop Distributed File Systems.

Visualization: visual data analysis techniques,
interaction techniques, systems and applications.

Introduction to R - R graphical user interfaces,
data import and export, attribute and data types,
descriptive statistics, exploratory data analysis,
visualization before analysis, analytics for unstructured data."""),

    # Research Methodology
    (sid["Research Methodology"], "Module I", "Introduction to Research",
     "Concept, need, purpose, research problem and design, literature review, hypothesis"),
    (sid["Research Methodology"], "Module II", "Types of Research Methods",
     "Historical, survey, experimental, case study, scientific and statistical research"),
    (sid["Research Methodology"], "Module III", "Research Techniques",
     "Questionnaire, interview, observation, statistics, report writing"),
    (sid["Research Methodology"], "Module IV", "Metric Studies and Style Manuals",
     "MS Excel, SPSS, scientometrics, infometrics, webometrics, citation styles"),

    # Cloud Computing
    (sid["Cloud Computing"], "Unit I", "Introduction to Cloud Computing",
     "Definition, evolution, IaaS/PaaS/SaaS, deployment models, cloud characteristics"),
    (sid["Cloud Computing"], "Unit II", "Resource Management and Security",
     "Inter-cloud resource management, provisioning, security challenges, IAM, security standards"),
    (sid["Cloud Computing"], "Unit III", "Virtualization",
     "Types of virtualization, VM placement/migration, VM clustering, Docker vs Hypervisor"),
    (sid["Cloud Computing"], "Unit IV", "Cloud Technologies and Advancements",
     "Hadoop MapReduce, Google App Engine, OpenStack, federation in the cloud"),
    (sid["Cloud Computing"], "Unit V", "Case Studies",
     "Cloud market analysis, shared security model, big data on cloud, MapReduce framework"),

    # Block Chain
    (sid["Block Chain Technology"], "Unit I", "Introduction to Blockchain",
     "History, evolution, key characteristics, components, blocks, hashing, Merkle trees"),
    (sid["Block Chain Technology"], "Unit II", "Cryptographic Principles",
     "Symmetric/asymmetric encryption, digital signatures, blockchain security models"),
    (sid["Block Chain Technology"], "Unit III", "Consensus Algorithms",
     "PoW, PoS, DPoS, PoA, PBFT, mining and validation, scalability"),
    (sid["Block Chain Technology"], "Unit IV", "Smart Contracts",
     "Ethereum, EVM, Solidity, dApps architecture"),
    (sid["Block Chain Technology"], "Unit V", "Applications",
     "Cryptocurrency, enterprise blockchain, government use cases, future trends"),

    # IoT
    (sid["Internet of Things"], "Unit I", "Introduction and Applications",
     "IoT definition, physical/logical design, communication models, applications"),
    (sid["Internet of Things"], "Unit II", "Hardware for IoT",
     "Sensors, actuators, RFID, wireless sensor networks, embedded platforms (Arduino, Raspberry Pi)"),
    (sid["Internet of Things"], "Unit III", "Developing IoT",
     "IoT methodology, purpose specification, process/domain/information/service specification"),
    (sid["Internet of Things"], "Unit IV", "Programming Arduino",
     "Arduino platform, IDE, coding, libraries, programming for IoT"),
    (sid["Internet of Things"], "Unit V", "Case Study",
     "Weather monitoring system, Python packages for IoT, Raspberry Pi"),

    # Data Warehousing and Data Mining
    (sid["Data Warehousing and Data Mining"], "Unit I", "Data Warehousing",
     "Components, architecture, DBMS schemas, OLAP, multidimensional data analysis"),
    (sid["Data Warehousing and Data Mining"], "Unit II", "Data Mining Basics",
     "Functionalities, preprocessing, association rule mining"),
    (sid["Data Warehousing and Data Mining"], "Unit III", "Classification and Prediction",
     "Decision trees, Bayesian classification, SVM, ensemble methods"),
    (sid["Data Warehousing and Data Mining"], "Unit IV", "Cluster Analysis",
     "Partitioning, hierarchical, density-based, grid-based clustering, outlier analysis"),
    (sid["Data Warehousing and Data Mining"], "Unit V", "Mining Complex Data",
     "Spatial, multimedia, text mining, web mining"),

    # Prompt Engineering
    (sid["Prompt Engineering"], "Unit I", "Introduction to LLMs",
     "Text generation models, brief history of language models, LLMs in the market"),
    (sid["Prompt Engineering"], "Unit II", "Prompting Techniques",
     "Five principles of prompting, types of prompts, components, personality in prompts"),
    (sid["Prompt Engineering"], "Unit III", "Text Generation Practices",
     "Generating lists, ELI5, universal translation, role prompting"),
    (sid["Prompt Engineering"], "Unit IV", "AI Content Creation",
     "Copywriting, social media posts, video scripts, prompts for research"),
    (sid["Prompt Engineering"], "Unit V", "Diffusion Models",
     "Image generation principles, DALL-E, Midjourney, Stable Diffusion, negative prompts"),

    # NLP
    (sid["Natural Language Processing"], "Unit I", "Overview and Morphology",
     "Regular expressions, finite state automata, inflectional/derivational morphology"),
    (sid["Natural Language Processing"], "Unit II", "Word Level and Syntactic Analysis",
     "N-grams, smoothing, POS tagging"),
    (sid["Natural Language Processing"], "Unit III", "Context Free Grammars",
     "CFG for English syntax, parsing, probabilistic CFGs"),
    (sid["Natural Language Processing"], "Unit IV", "Semantic Analysis",
     "Representing meaning, word sense disambiguation, information retrieval"),
    (sid["Natural Language Processing"], "Unit V", "Language Generation and Discourse",
     "Discourse, dialog systems, machine translation"),

    # Mobile App Dev
    (sid["Mobile Application Development"], "Unit I", "Introduction to Android",
     "Android platform, SDK, first Android app, manifest file"),
    (sid["Mobile Application Development"], "Unit II", "Android Application Design",
     "Activities, services, intents, permissions"),
    (sid["Mobile Application Development"], "Unit III", "UI Design Essentials",
     "User interface elements, layouts, animation"),
    (sid["Mobile Application Development"], "Unit IV", "Testing and Publishing",
     "Testing, publishing, application resources"),
    (sid["Mobile Application Development"], "Unit V", "Android APIs",
     "Data/storage APIs, SQLite, content providers, networking APIs"),

    # Distributed Systems
    (sid["Distributed System"], "Unit I", "Characterization of Distributed Systems",
     "Architectural models, logical clocks, message ordering"),
    (sid["Distributed System"], "Unit II", "Propositional Logic and Proof Techniques",
     "Logical operations, laws of logic, proof techniques"),
    (sid["Distributed System"], "Unit III", "Consensus and Recovery",
     "Agreement algorithms, checkpointing, rollback recovery"),
    (sid["Distributed System"], "Unit IV", "Transactions and Concurrency Control",
     "Locks, optimistic concurrency control, distributed transactions"),
    (sid["Distributed System"], "Unit V", "Distributed File Systems",
     "File service architecture, name services, distributed shared memory"),
]

    cur.executemany(
        "INSERT INTO units (subject_id, unit_number, unit_title, topics) VALUES (?,?,?,?)",
        units
    )

# ============================================================
# LLM SETUP (Gemini)
# ============================================================
MODEL_CHAIN = [
    "gemini-3.8-flash"
]
def get_gemini_response(prompt):
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)

    last_error = ""

    for model_name in MODEL_CHAIN:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text

            try:
                c = _cache_conn()
                c.execute(
                    "INSERT OR REPLACE INTO response_cache (key, response) VALUES (?,?)",
                    (key, text)
                )
                c.commit()
                c.close()
            except Exception:
                pass

            return text

        except Exception as e:
            last_error = str(e)
            continue

    if "429" in last_error or "quota" in last_error.lower():
        return "⚠️ The AI service's free daily limit has been reached for now. Answers you generated earlier are still saved, and the syllabus, PYQs and books sections work normally. Please try again later."

    return f"⚠️ Could not generate a response right now. ({last_error[:150]})"


def parse_quiz_response(text):
    try:
        cleaned = text.strip()

        # Remove markdown code fences if Gemini adds them
        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned
        )

        data = json.loads(cleaned)

        # Support both:
        # [ {...}, {...} ]
        # and {"questions": [ {...}, {...} ]}
        if isinstance(data, dict) and "questions" in data:
            data = data["questions"]

        if not isinstance(data, list):
            return None

        # Validate each question
        for q in data:
            if not all(
                key in q
                for key in ["question", "options", "answer", "explanation"]
            ):
                return None

            if not isinstance(q["options"], dict):
                return None

            if set(q["options"].keys()) != {"A", "B", "C", "D"}:
                return None

            if q["answer"] not in ["A", "B", "C", "D"]:
                return None

        return data

    except Exception:
        return None
# ============================================================
# APP START
# ============================================================
conn = init_db()
refresh_syllabus_once()
cur = conn.cursor()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

# ---------------- LOGIN PAGE ----------------
if not st.session_state.logged_in:
    col1, col2 = st.columns([1, 5])

    with col1:
        st.image("jss_logo.png", width=80)

    with col2:
        st.title("JSS AI Study Buddy")

    st.caption("Your AI-powered companion for MCA studies — notes, PYQs, quizzes, and more.")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        roll = st.text_input("Roll Number", key="login_roll")
        pwd = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Login"):
            cur.execute("SELECT id, name, password FROM users WHERE roll_number=?", (roll,))
            row = cur.fetchone()
            if row and row[2] == pwd:
                st.session_state.logged_in = True
                st.session_state.user_id = row[0]
                st.session_state.user_name = row[1]
                st.rerun()
            else:
                st.error("Invalid roll number or password.")

    with tab2:
        name = st.text_input("Full Name", key="signup_name")
        roll_new = st.text_input("Roll Number", key="signup_roll")
        pwd_new = st.text_input("Create Password", type="password", key="signup_pwd")
        if st.button("Sign Up"):
            try:
                cur.execute("INSERT INTO users (name, roll_number, password) VALUES (?,?,?)", (name, roll_new, pwd_new))
                conn.commit()
                st.success("Account created! Please log in.")
            except sqlite3.IntegrityError:
                st.error("Roll number already registered.")

    st.stop()

# ---------------- MAIN APP (after login) ----------------
st.sidebar.image("jss_logo.png", width=70)
st.sidebar.title(f"👋 Hi, {st.session_state.user_name}")
page = st.sidebar.radio("Navigate", ["Syllabus", "AI Notes Generator", "Ask a Question", "MCQ Test", "PYQ Bank", "Books & References"])
language = st.sidebar.selectbox("Response Language / भाषा", ["English", "Hindi"])
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# Fetch subjects for dropdown, grouped by semester
cur.execute("SELECT id, subject_name, semester, elective_group FROM subjects ORDER BY semester, subject_name")
all_subjects = cur.fetchall()
semesters = sorted(set(s[2] for s in all_subjects))

lang_instruction = "Respond in English." if language == "English" else "Respond in Hindi (हिंदी में उत्तर दें), using simple conversational Hindi mixed with technical English terms where appropriate (Hinglish style is fine for technical words)."

# ---------------- SYLLABUS PAGE ----------------
if page == "Syllabus":
    st.header("📖 Syllabus Browser")
    sem_choice = st.selectbox("Select Semester", semesters)
    subs_in_sem = [s for s in all_subjects if s[2] == sem_choice]
    for s in subs_in_sem:
        label = s[1] + (f" ({s[3]})" if s[3] else "")
        with st.expander(label):
            cur.execute("SELECT unit_number, unit_title, topics FROM units WHERE subject_id=?", (s[0],))
            for u in cur.fetchall():
                st.markdown(f"**{u[0]}: {u[1]}**")
                st.write(u[2])
                st.divider()
            if not cur.execute("SELECT 1 FROM units WHERE subject_id=?", (s[0],)).fetchone():
                st.info("Detailed units not yet added for this subject.")

# ---------------- AI NOTES GENERATOR ----------------
elif page == "AI Notes Generator":
    st.header("📝 AI Notes Generator")

    sem_choice = st.selectbox("Semester", semesters, key="notes_sem")
    subs_in_sem = [s for s in all_subjects if s[2] == sem_choice]

    subject_choice = st.selectbox(
        "Subject",
        [s[1] for s in subs_in_sem],
        key="notes_subject"
    )

    subject_id = next(
        s[0] for s in subs_in_sem if s[1] == subject_choice
    )

    cur.execute(
        "SELECT unit_number, unit_title, topics FROM units WHERE subject_id=?",
        (subject_id,)
    )
    units_list = cur.fetchall()

    mode = st.radio(
        "Generate notes for:",
        ["Full Unit", "Specific Topic"]
    )

    if mode == "Full Unit" and units_list:
        unit_choice = st.selectbox(
            "Select Unit",
            [f"{u[0]}: {u[1]}" for u in units_list]
        )

        topic_text = unit_choice

        context = next(
            u[2]
            for u in units_list
            if f"{u[0]}: {u[1]}" == unit_choice
        )

    else:
        topic_text = st.text_input(
            "Enter specific topic (e.g., 'Logistic Regression')"
        )
        context = topic_text

    length = st.select_slider(
        "Answer length",
        options=["Short", "Concise", "Long"],
        value="Concise"
    )

    note_type = st.selectbox(
        "Note Type",
        [
            "Detailed Study Notes",
            "Quick Revision",
            "Exam-Oriented Notes"
        ],
        help="Choose how the AI should structure the generated notes."
    )

    if st.button("Generate Notes") and topic_text:

        with st.spinner("Generating notes..."):

            prompt = f"""You are a helpful academic tutor for an MCA student at JSS University.

Subject: {subject_choice}
Topic: {topic_text}
Context/related subtopics: {context}

Note Type: {note_type}
Length: {length}

Generate clear, accurate and well-structured study notes suitable for an MCA student.

Follow these note-type instructions:

- Detailed Study Notes:
  Explain the concepts clearly with definitions, important points,
  examples, advantages/disadvantages, applications and explanations
  where appropriate.

- Quick Revision:
  Focus on key definitions, important facts, formulas, keywords
  and short bullet points that can be revised quickly before an exam.

- Exam-Oriented Notes:
  Focus on concepts important for university examinations.
  Include important definitions, key points, comparisons,
  examples, advantages/disadvantages and likely exam points
  where appropriate.

Structure the answer as follows where applicable:
1. Topic Introduction
2. Definition / Meaning
3. Main Concepts
4. Important Points
5. Example / Illustration
6. Advantages and Limitations
7. Applications
8. Exam Quick Revision

Do not force sections that are not relevant to the selected topic.

Length instructions:
- Short = key points only
- Concise = balanced explanation
- Long = detailed explanation with examples

{lang_instruction}

Use clear headings, subheadings, numbered lists and bullet points where helpful.
Use simple academic language that an MCA student can understand.
Do not include information unrelated to the selected subject or topic.
"""

            result = get_gemini_response(prompt)

            st.markdown(result)

            cur.execute(
                "INSERT INTO generated_notes (user_id, subject_id, topic, content) VALUES (?,?,?,?)",
                (
                    st.session_state.user_id,
                    subject_id,
                    topic_text,
                    result
                )
            )

            conn.commit()

    st.divider()

    st.subheader("Your Saved Notes")

    cur.execute(
        "SELECT topic, content, created_at "
        "FROM generated_notes "
        "WHERE user_id=? AND subject_id=? "
        "ORDER BY created_at DESC LIMIT 5",
        (st.session_state.user_id, subject_id)
    )

    for note in cur.fetchall():
        with st.expander(f"{note[0]} — {note[2]}"):
            st.markdown(note[1])
# ---------------- ASK A QUESTION ----------------
elif page == "Ask a Question":
    st.header("💬 Ask a Question")
    sem_choice = st.selectbox("Semester", semesters, key="ask_sem")
    subs_in_sem = [s for s in all_subjects if s[2] == sem_choice]
    subject_choice = st.selectbox("Subject", [s[1] for s in subs_in_sem], key="ask_subject")
    length = st.select_slider("Answer length", options=["Short", "Concise", "Long"], value="Concise", key="ask_length")
    question = st.text_area("Your question")

    if st.button("Get Answer") and question:
        with st.spinner("Thinking..."):
            prompt = f"""You are a helpful academic tutor for an MCA student studying {subject_choice}.

Question: {question}
Answer length: {length}

Give a clear, accurate and easy-to-understand academic answer.

Answer guidelines:
- Start with a direct explanation of the answer.
- Explain important concepts using simple academic language.
- Use headings, bullet points or numbered lists where helpful.
- Include examples when they improve understanding.
- If the question asks for a comparison, use a clear comparison format.
- If the question involves steps or a process, explain them in order.
- Focus only on the asked question and the selected subject.
- Do not invent facts or include unrelated information.

Length instructions:
- Short = brief answer with key points
- Concise = balanced explanation with important details
- Long = detailed explanation with examples

{lang_instruction}
"""
            result = get_gemini_response(prompt)
            st.markdown(result)
# ---------------- MCQ TEST ----------------
elif page == "MCQ Test":
    st.header("🧠 MCQ Test")

    # Initialize quiz session state
    if "mcq_questions" not in st.session_state:
        st.session_state.mcq_questions = None

    if "mcq_subject" not in st.session_state:
        st.session_state.mcq_subject = None

    if "mcq_submitted" not in st.session_state:
        st.session_state.mcq_submitted = False

    if "mcq_score" not in st.session_state:
        st.session_state.mcq_score = None

    # ---------------- QUIZ SETTINGS ----------------
    sem_choice = st.selectbox(
        "Semester",
        semesters,
        key="mcq_sem"
    )

    subs_in_sem = [
        s for s in all_subjects
        if s[2] == sem_choice
    ]

    subject_choice = st.selectbox(
        "Subject",
        [s[1] for s in subs_in_sem],
        key="mcq_subject"
    )

    num_q = st.slider(
        "Number of questions",
        3,
        10,
        5,
        key="mcq_num"
    )

       # ---------------- GENERATE QUIZ ----------------
    if st.button("Generate MCQ Test"):

        with st.spinner("Creating quiz..."):

            prompt = f"""Create exactly {num_q} multiple choice questions
for an MCA student studying the subject: {subject_choice}.

{lang_instruction}

Return ONLY valid JSON.
Do not use markdown.
Do not use code fences.
Do not include any extra text before or after the JSON.

Use exactly this structure:

[
  {{
    "question": "Question text",
    "options": {{
      "A": "Option A",
      "B": "Option B",
      "C": "Option C",
      "D": "Option D"
    }},
    "answer": "A",
    "explanation": "Short explanation of the correct answer."
  }}
]

Rules:
- Create exactly {num_q} questions.
- Each question must have exactly four options.
- Options must be labelled A, B, C and D.
- The answer must be exactly A, B, C or D.
- Questions must be relevant to {subject_choice}.
- Do not repeat questions.
- Keep explanations short and clear.
"""

            raw_result = get_gemini_response(prompt)

            st.write("DEBUG - Gemini response:")
            st.code(raw_result)

            questions = parse_quiz_response(raw_result)

            if questions:
                # Clear answers from previous quiz
                for i in range(10):
                    st.session_state.pop(
                        f"mcq_answer_{i}",
                        None
                    )

                st.session_state.mcq_questions = questions
                st.session_state.mcq_submitted = False
                st.session_state.mcq_score = None

            else:
                st.error(
                    "⚠️ The AI returned an unexpected format. "
                    "Please try generating the test again."
                )

    # ---------------- DISPLAY QUIZ ----------------
    if (
        st.session_state.mcq_questions
        and st.session_state.mcq_subject == subject_choice
    ):

        questions = st.session_state.mcq_questions

        st.divider()

        st.subheader(
            f"📝 {st.session_state.mcq_subject} — Quiz"
        )

        st.info(
            f"Answer all {len(questions)} questions and then click "
            "**Submit Test**."
        )

        for i, q in enumerate(questions):

            st.markdown(
                f"### Q{i + 1}. {q['question']}"
            )

            options = q["options"]

            st.radio(
                "Select your answer:",
                ["A", "B", "C", "D"],
                format_func=lambda x, opts=options:
                    f"{x}. {opts[x]}",
                key=f"mcq_answer_{i}",
                disabled=st.session_state.mcq_submitted
            )

        # ---------------- SUBMIT TEST ----------------
        if not st.session_state.mcq_submitted:

            if st.button("✅ Submit Test"):

                score = 0

                for i, q in enumerate(questions):

                    selected = st.session_state.get(
                        f"mcq_answer_{i}"
                    )

                    if selected == q["answer"]:
                        score += 1

                st.session_state.mcq_score = score
                st.session_state.mcq_submitted = True

                st.rerun()

        # ---------------- SHOW RESULT ----------------
        if st.session_state.mcq_submitted:

            score = st.session_state.mcq_score
            total = len(questions)

            percentage = int(
                (score / total) * 100
            )

            st.divider()

            st.subheader("📊 Test Result")

            if percentage >= 80:
                st.success(
                    f"🎉 Excellent! Your score is "
                    f"**{score}/{total} ({percentage}%)**"
                )

            elif percentage >= 50:
                st.info(
                    f"👍 Good attempt! Your score is "
                    f"**{score}/{total} ({percentage}%)**"
                )

            else:
                st.warning(
                    f"📚 Keep practicing! Your score is "
                    f"**{score}/{total} ({percentage}%)**"
                )

            st.subheader("📖 Answer Review")

            for i, q in enumerate(questions):

                selected = st.session_state.get(
                    f"mcq_answer_{i}"
                )

                correct = q["answer"]

                if selected == correct:

                    st.markdown(
                        f"**Q{i + 1}: ✅ Correct**"
                    )

                else:

                    st.markdown(
                        f"**Q{i + 1}: ❌ Incorrect**"
                    )

                    if selected:
                        st.write(
                            f"Your answer: "
                            f"{selected}. "
                            f"{q['options'][selected]}"
                        )
                    else:
                        st.write("Your answer: Not attempted")

                    st.write(
                        f"Correct answer: "
                        f"{correct}. "
                        f"{q['options'][correct]}"
                    )

                st.caption(
                    f"Explanation: {q['explanation']}"
                )

                st.divider()

            # ---------------- NEW TEST ----------------
            if st.button("🔄 Generate New Test"):

                st.session_state.mcq_questions = None
                st.session_state.mcq_subject = None
                st.session_state.mcq_submitted = False
                st.session_state.mcq_score = None

                for i in range(10):
                    st.session_state.pop(
                        f"mcq_answer_{i}",
                        None
                    )

                st.rerun()

# ---------------- PYQ BANK ----------------
elif page == "PYQ Bank":
    st.header("📄 Previous Year Questions (AI-Predicted)")
    st.warning("⚠️ These are AI-predicted likely exam questions based on the syllabus and course outcomes — not verified past papers.")
    sem_choice = st.selectbox("Semester", semesters, key="pyq_sem")
    subs_in_sem = [s for s in all_subjects if s[2] == sem_choice]
    subject_choice = st.selectbox("Subject", [s[1] for s in subs_in_sem], key="pyq_subject")
    subject_id = next(s[0] for s in subs_in_sem if s[1] == subject_choice)

    cur.execute("SELECT question_text, marks FROM pyqs WHERE subject_id=?", (subject_id,))
    existing = cur.fetchall()
    for q in existing:
        st.markdown(f"- {q[0]} *({q[1]} marks)*")

    if st.button("Generate More AI-Predicted Questions"):
        with st.spinner("Predicting likely questions..."):
            cur.execute("SELECT unit_title, topics FROM units WHERE subject_id=?", (subject_id,))
            unit_info = cur.fetchall()
            unit_summary = "; ".join([f"{u[0]}: {u[1]}" for u in unit_info])
            prompt = f"""Based on this MCA syllabus content for {subject_choice}: {unit_summary}
Generate 5 likely exam questions (mix of 2-mark, 5-mark and 10-mark style questions) that could appear in a semester exam.
{lang_instruction}
Just list the questions with marks in brackets, no answers."""
        result = get_gemini_response(prompt)
        st.markdown(result)

    st.divider()
    st.subheader("📄 Real Previous Year Question Papers")
    pyqs_folder = "pyqs"
    if os.path.exists(pyqs_folder):
        def normalize(s):
            return ''.join(c.lower() for c in s if c.isalnum())

        subject_key = normalize(subject_choice)
        all_files = sorted(os.listdir(pyqs_folder))
        matched = [f for f in all_files if f.lower().endswith('.pdf') and (normalize(f.replace('.pdf', '')) in subject_key or subject_key in normalize(f.replace('.pdf', '')))]

        if matched:
            for pdf_file in matched:
                pdf_path = os.path.join(pyqs_folder, pdf_file)
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label=f"📥 Download {pdf_file}",
                    data=pdf_bytes,
                    file_name=pdf_file,
                    mime="application/pdf",
                    key=f"pdf_{pdf_file}"
                )
        else:
            st.info("No scanned PYQs uploaded yet for this subject.")
    else:
        st.info("No scanned PYQs uploaded yet for this subject.")

# ---------------- BOOKS & REFERENCES ----------------
elif page == "Books & References":
    st.header("📚 Books & References")
    sem_choice = st.selectbox("Semester", semesters, key="books_sem")
    subs_in_sem = [s for s in all_subjects if s[2] == sem_choice]
    for s in subs_in_sem:
        cur.execute("SELECT textbook_title, textbook_author, web_reference FROM subjects WHERE id=?", (s[0],))
        book = cur.fetchone()
        if book and book[0]:
            st.markdown(f"**{s[1]}**")
            st.write(f"📘 *{book[0]}* — {book[1]}")
            if book[2]:
                st.markdown(f"🔗 [Reference link]({book[2]})")
            st.divider()
