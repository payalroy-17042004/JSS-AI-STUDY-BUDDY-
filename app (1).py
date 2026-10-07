import streamlit as st
import sqlite3
import os
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="JSS AI Study Buddy", page_icon="📚", layout="wide")

DB_PATH = "study_buddy.db"
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
# DATABASE SETUP
# Syllabus records are refreshed automatically without deleting users/notes/PYQs.
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

    if first_time or not cur.execute("SELECT 1 FROM subjects LIMIT 1").fetchone():
        seed_data(cur)
    else:
        refresh_units(cur)

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

    refresh_units(cur)

def refresh_units(cur):
    """Refresh only the syllabus-unit records; user accounts, notes and PYQs are preserved."""
    cur.execute("DELETE FROM units")
    cur.execute("SELECT id, subject_name FROM subjects")
    sid = {name: i for i, name in cur.fetchall()}

    units = [
        (sid['Fundamentals of Mathematics for Computer Applications'], 'Unit I', 'Linear Systems and Matrices', """Linear Systems and Matrices: Complex matrices, Hermitian , Skew-Hermitian, Unitary matrices, Elementary transformation, Inverse of a matrix , Echelon forms, Rank of matrix, Solution of linear systems, Characteristic equation, Cayley- Hamilton theorem, Eigen values and eigenvectors."""),
        (sid['Fundamentals of Mathematics for Computer Applications'], 'Unit II', 'Set Theory and Relations', """Set Theory: Sets, Operations on sets, Cardinality of sets, inclusion- exclusion principle, pigeon hole principle. Relations: Relations and Their Properties, n-ary Relations and Their Application, Representing Relations ,Closures of Relations ,Equivalence Relations, Partial Orderings"""),
        (sid['Fundamentals of Mathematics for Computer Applications'], 'Unit III', 'Mathematical Logic', """Mathematical Logic: Propositional Logic, Applications of Propositional Logic, Propositional Equivalences Predicates and Quantifiers, Nested Quantifiers, Rules of Inference Introduction to Proofs"""),
        (sid['Fundamentals of Mathematics for Computer Applications'], 'Unit IV', 'Graph Theory', """Graph Theory: Graphs and Graphs models, Graph Terminology and Special Types of Graphs ,Representing Graphs and Graph Isomorphism, Connectivity,Euler and Hamilton Paths, Shortest- Path Problems, Planar Graphs, Graph Coloring."""),
        (sid['Fundamentals of Mathematics for Computer Applications'], 'Unit V', 'Random Variables and Probability Distribution', """Random variable and probability distribution: Concept of random variable ,discrete probability distributions ,continuous probability distributions, Mean ,variance and co-variance and co-variance ofRandom variables. Binomial and normal distribution ,Exponential and normal distribution with mean and variables and problems"""),
        (sid['Programming and Data Structures using C'], 'Unit I', 'C Fundamentals', """Structure of a C program, compilation and linking processes, Constants, Variables, Data Types, Expressions using operators in C, Managing Input and Output operations, Decision Making and Branching, Looping statements. Arrays – Initialization, Declaration, One dimensional and Two- dimensional arrays. Strings- String operations."""),
        (sid['Programming and Data Structures using C'], 'Unit II', 'Functions and Pointers', """Functions – Pass by value, Pass by reference, Recursion. Pointers- Declaring and Initializing Pointers, Pointer Arithmetic, Function and Pointer Parameters, Pointer and Arrays, Dynamic Memory Allocation, Structures- Defining and using a Structure, Passing Structures to Functions, Structure and Pointers. Basics of Data Structures and Algorithms: Algorithms as a technology, Analyzing algorithms, Growth of Functions Asymptotic notations, Types of data structures."""),
        (sid['Programming and Data Structures using C'], 'Unit III', 'Stacks and Queues', """Stack: Definition, Array representation, Prefix, Infix and Postfix expressions, Utility and conversion of these expressions from one to another. Queue: Definition, Array representation, Types of queues: Simple queue, Circular queue, double ended queue, Priority queue."""),
        (sid['Programming and Data Structures using C'], 'Unit IV', 'Linked Lists and Hashing', """Linked List, Inserting and Removing nodes from a list, singly linked List, Doubly Linked List, Linked list Implementation of Stacks. Dictionaries, Hash Table Representation, Hash Functions."""),
        (sid['Programming and Data Structures using C'], 'Unit V', 'Non-Linear Data Structures', """Non-Linear Data Structures: Need for non-linear structures, Graphs: Introduction to Graph, Graph Traversal Techniques. Trees: Types of Trees, Binary Tree, Representation of Binary trees using arrays and lists, Binary tree traversals, Binary search trees"""),
        (sid['Python Programming'], 'Unit I', 'Python Basics and Control Flow', """Introduction to Python Basics : Entering Expressions into the Interactive Shell, The Integer, Floating-Point, and String Data Types, String Concatenation and Replication, Storing Values in Variables, Your First Program, Dissecting Your Program. Python Program Flow Control Conditional blocks: if, else and else if, Simple for loops in python, For loop using ranges, string, list and dictionaries. Use of while loops in python, Loop manipulation using pass, continue, break and else. Programming using Python conditional and loop blocks."""),
        (sid['Python Programming'], 'Unit II', 'Data Structures in Python', """Using string data type and string operations, Defining list and list slicing, Use of Tuple data type, String, List, Set and Dictionary, Manipulations Building blocks of python programs, string manipulation methods, List manipulation. Dictionary manipulation, Programming using string, list and dictionary in-built functions."""),
        (sid['Python Programming'], 'Unit III', 'Functions and Exception Handling', """Def Statements with Parameters, Return Values and return Statements, The None Value, Keyword Arguments and print(), Local and Global Scope, Introduction to functional programming and Lamda function , map, filter and reduce , Iterator and Generator in Python, Exception Handling."""),
        (sid['Python Programming'], 'Unit IV', 'File Handling', """Reading files, Writing files in python, Understanding read functions, read(), readline(), readlines(). Understanding write functions, write() and writelines() Manipulating file pointer using seek Programming, using file operations."""),
        (sid['Database Management System'], 'Unit I', 'Relational Model', """Database-System Applications, Purpose of Database Systems, View of Data, Database Languages, Relational Databases, Database Design, Data Storage and Querying, Transaction Management, Database Architecture, Data Mining and Information Retrieval, Specialty Databases, Database Users and Administrators, History of Database Systems. Introduction to the Relational Model: Structure of Relational Databases, Database Schema, Keys, Schema Diagrams, Relational Query Languages."""),
        (sid['Database Management System'], 'Unit II', 'ER Model and Database Design', """Overview of the Design Process, The Entity Relationship Model, Constraints, Removing Redundant Attributes in Entity Sets, Entity Relationship Diagrams, Reduction to Relational Schemas, Entity-Relationship Design Issues, Extended E-R Features, Other Aspects of Database Design."""),
        (sid['Database Management System'], 'Unit III', 'SQL', """Overview of the SQL Query Language, SQL Data Definition, Basic Structure of SQL Queries, Additional Basic Operations, Set Operations, Null Values, Aggregate Functions, Nested Subqueries, Modification of the Database. Intermediate SQL: Join Expressions, Views, Transactions, Integrity Constraints, SQL Data Types and Schemas."""),
        (sid['Database Management System'], 'Unit IV', 'Advanced SQL and Relational Query Languages', """Accessing SQL from a Programming Language, Functions and Procedures, Triggers, Recursive Queries, Advanced Aggregation Features, OLAP. Formal Relational Query Languages: The Relational Algebra, The Tuple Relational Calculus."""),
        (sid['Database Management System'], 'Unit V', 'Normalization', """Features of Good Relational Design, Atomic Domains and First Normal Form, Decomposition Using Functional Dependencies, Functional Dependency Theory, Algorithm for Decomposition, Decomposition Using Multivalued Dependencies, More Normal Forms, Database-Design Process.."""),
        (sid['Operating System with Linux'], 'Unit I', 'Operating System Concepts and Process Management', """Operating System concepts: Types of Operating Systems, Operating System Components & Services, System calls. Process Management: Process Concept, Process Scheduling, Threads, CPU Scheduling Criteria, Scheduling algorithm. The Critical Section Problem, Semaphores, Classical problems of synchronization, Monitors."""),
        (sid['Operating System with Linux'], 'Unit II', 'Memory Management', """Deadlocks – system model, Characterization, Dead lock prevention, avoidance and detection, Recovery from dead lock. Memory Management: Logical and Physical address space, Swapping, Contiguous allocation, Paging, Segmentation, Segmentation with paging, Virtual memory -Demand paging and its performance, Page replacement algorithms, Allocation of frames, Thrashing."""),
        (sid['Operating System with Linux'], 'Unit III', 'File System', """File System: Concept of a file, access methods, directory structure, file system mounting, file sharing, protection. File system implementation: file system structure, file system implementation, directory implementation, allocation methods, free-space management, efficiency and performance."""),
        (sid['Operating System with Linux'], 'Unit IV', 'I/O Systems', """I/O System: Mass storage structure - overview of mass storage structure, disk structure, disk attachment, disk scheduling algorithms, swap space management, stable storage implementation, tertiary storage structure."""),
        (sid['Operating System with Linux'], 'Unit V', 'Linux', """Introduction and interacting with shell and Desktop to Linux: History, salient features, Linux system architecture, Linux command format, Linux internal and external commands, Directory commands, File related commands, Disk related commands. The Linux Shell Basic command cls, cat, cal, date, calendar, who, printf, tty, sty, uname, passwd, echo, tput, bc, script, spell and ispell, Introduction to Shell Scripting, Shell Scripts, read, Command Line Arguments, Exit Status of a Command."""),
        (sid['Communication & Social Skills for Professional Development'], 'Unit I', 'Process of Communication', """Introduction, Process of Communication, Language as a Tool, Levels of Communication, Communication Networks, Importance of Technical Communication. Definition of Noise, rehousing in strategic Decision Making."""),
        (sid['Communication & Social Skills for Professional Development'], 'Unit II', 'Technology in Communication', """Impact of Technology, Software for Creating Messages, Software for Writing Documents, Software for Presenting Documents, Transmitting Documents."""),
        (sid['Communication & Social Skills for Professional Development'], 'Unit III', 'Effective Presentation', """Effective Presentation: Introduction, Defining purpose, Analyzing Audience and Locale, Organizing Contents, preparing outline, Visual Aids, Kinesics, Proxemics, Paralinguistic, Chronemics, Sample speech."""),
        (sid['Communication & Social Skills for Professional Development'], 'Unit IV', 'Ethics', """What are Ethics: Definition of ethics, Importance of Integrity, Ethics in the Business world.. The illusion of communication: Failing to confirm the message, Forgetting the call to action, Fearing to disagree, Ignoring the beauty of arguments, choosing the wrong medium, Danger of half-baked ideas, the Art of explanation; word selection, Game played people with truth, Faces of ‘no’."""),
        (sid['Communication & Social Skills for Professional Development'], 'Unit V', 'Professional Ethics', """Professional, The ethics behavior of IT professionals, IT users: Supporting the ethical practices of IT users."""),
        (sid['Object Oriented Programming using Java'], 'Unit I', 'Java Fundamentals and OOP', """Introduction: Why Java, History of Java, JVM, JRE, Java Environment, Java Source File Structure, and Compilation. Fundamental, Programming Structures in Java: Defining Classes in Java, Constructors, Methods, Access Specifies, Static Members, Final Members, Comments, Data types, Variables, Operators, Control Flow, Arrays & String. Object Oriented Programming: Class, Object, Inheritance Super Class, Sub Class, Overriding, Overloading, Encapsulation, Polymorphism, Abstraction, Interfaces, and Abstract Class. Packages: Defining Package, CLASSPATH Setting for Packages, Making JAR Files for Library Packages, Import and Static Import Naming Convention for Packages"""),
        (sid['Object Oriented Programming using Java'], 'Unit II', 'Exception Handling and Multithreading', """Exception Handling and Multithreaded Programming: The Idea behind Exception, Exceptions & Errors, Types of Exception, Control Flow in Exceptions, JVM Reaction to Exceptions, Use of try, catch, finally, throw, throws in Exception Handling, In-built and User Defined Exceptions, Checked and Un-Checked Exceptions. Input /Output Basics: Byte Streams and Character Streams, Reading and Writing File in Java. Multithreading: Thread, Thread Life Cycle, Creating Threads, Thread Priorities, Synchronizing Threads, Inter-thread Communication."""),
        (sid['Object Oriented Programming using Java'], 'Unit III', 'New Java Features', """Java New Features: Functional Interfaces, Lambda Expression, Method References, Stream API, Default Methods, Static Method, Base64 Encode and Decode, For Each Method, Try-with resources, Type Annotations, Repeating Annotations, Java Module System, Diamond Syntax with Inner Anonymous Class, Local Variable Type Inference, Switch Expressions, Yield Keyword, Text Blocks, Records, Sealed Classes."""),
        (sid['Object Oriented Programming using Java'], 'Unit IV', 'Collection Framework', """Java Collections Framework: Collection in Java, Collection Framework in Java, Hierarchy of Collection Framework, Iterator Interface, Collection Interface, List Interface, Array List, Linked List, Vector, Stack, Queue Interface, Set Interface, Hash Set, Linked Hash Set, Sorted Set Interface, Tree Set, Map Interface, Hash Map Class, Linked Hash Map Class, Tree Map Class, Hash table Class, Sorting, Comparable Interface, Comparator Interface, Properties Class in Java."""),
        (sid['Object Oriented Programming using Java'], 'Unit V', 'Advanced Java / Spring Framework', """Java Collections Framework: Collection in Java, Collection Framework in Java, Hierarchy of Collection Framework, Iterator Interface, Collection Interface, List Interface, Array List, Linked List, Vector, Stack, Queue Interface, Set Interface, Hash Set, Linked HashSet, Sorted Set Interface, Tree Set, Map Interface, Hash Map Class, Linked Hash Map Class, Tree Map Class, Hash table Class, Sorting, Comparable Interface, Comparator Interface, Properties Class in Java."""),
        (sid['Agile Software Engineering'], 'Unit I', 'Introduction to Software Engineering', """Introduction: Introduction to Software Engineering, Software Components, Software Characteristics, Software Crisis, Software Engineering Processes, Similarity and Differences from Conventional Engineering Processes, Software Quality Attributes. Software Development Life Cycle (SDLC) Models: Water Fall Model, Prototype Model, Spiral Model, Evolutionary Development Models, Iterative Enhancement Models."""),
        (sid['Agile Software Engineering'], 'Unit II', 'Software Requirements and SQA', """Software Requirement Specifications (SRS): Requirement Engineering Process: Elicitation, Analysis, Documentation, Review and Management of User Needs, Feasibility Study, Information Modeling, Data Flow Diagrams, Entity Relationship Diagrams, Decision Tables, SRS Document, IEEE Standards for SRS. Software Quality Assurance (SQA): Verification and Validation, SQA Plans, Software Quality Frameworks, ISO 9000 Models, SEI-CMM Model."""),
        (sid['Agile Software Engineering'], 'Unit III', 'Software Design', """Software Design: Basic Concept of Software Design, Architectural Design, Low Level Design: Modularization, Design Structure Charts, Pseudo Codes, Flow Charts, Coupling and Cohesion Measures, Design Strategies: Function Oriented Design, Object Oriented Design, Top-Down and Bottom-Up Design. Software Measurement and Metrics: Various Size Oriented Measures: Halestead’s Software Science, Function Point (FP) Based Measures, And Cyclomatic Complexity Measures: Control Flow Graphs."""),
        (sid['Agile Software Engineering'], 'Unit IV', 'Software Testing', """Software Testing: Testing Objectives, Unit Testing, Integration Testing, Acceptance Testing, Regression Testing, Testing for Functionality and Testing for Performance, Top Down and Bottom Up Testing Strategies: Test Drivers and Test Stubs, Structural Testing (White Box Testing), Functional Testing (Black Box Testing), Test Data Suit Preparation, Alpha and Beta Testing of Products. Static Testing Strategies: Formal Technical Reviews (Peer Reviews), Walk Through, Code Inspection, Compliance with Design and Coding Standards."""),
        (sid['Agile Software Engineering'], 'Unit V', 'Software Maintenance and Project Management', """Software Maintenance and Software Project Management: Software as an Evolutionary Entity, Need for Maintenance, Categories of Maintenance: Preventive, Corrective and Perfective Maintenance, Cost of Maintenance, Software Re- Engineering, Reverse Engineering. Software Configuration Management Activities, Change Control Process, Software Version Control, An Overview of CASE Tools. Estimation of Various Parameters such as Cost, Efforts, Schedule/Duration, Constructive Cost Models (COCOMO), Resource Allocation Models, Software Risk Analysis and Management."""),
        (sid['Advance Design and Analysis of Algorithms'], 'Unit I', 'Introduction and Sorting', """Introduction: Algorithms, analyzing algorithms, Complexity of algorithms, Growth of functions, Performance measurements, Sorting and order Statistics - Shell sort, Quick sort, Merge sort, Heap sort, Comparison of sorting algorithms, Sorting in linear time."""),
        (sid['Advance Design and Analysis of Algorithms'], 'Unit II', 'Advanced Data Structures', """Advanced Data Structures: Red-Black trees, B – trees, Binomial Heaps, Fibonacci Heaps, Tries, skip list"""),
        (sid['Advance Design and Analysis of Algorithms'], 'Unit III', 'Divide and Conquer and Greedy Methods', """Divide and Conquer with Examples such as Sorting, Matrix Multiplication, Convex hull and Searching. Greedy methods with Examples such as Optimal Reliability Allocation, Knapsack, Minimum Spanning trees – Prim’s and Kruskal’s algorithms, Single source shortest paths - Dijkstra’s and Bellman Ford algorithms"""),
        (sid['Advance Design and Analysis of Algorithms'], 'Unit IV', 'Dynamic Programming, Backtracking and Branch and Bound', """Dynamic Programming with Examples such as Knapsack. All pair shortest paths – Warshal’s and Floyd’s algorithms, Resource allocation problem. Backtracking, Branch and Bound with examples such as Travelling Salesman Problem, Graph Coloring, n-Queen Problem, Hamiltonian Cycles and Sum of subsets."""),
        (sid['Advance Design and Analysis of Algorithms'], 'Unit V', 'Selected Topics', """Selected Topics: Algebraic Computation, Fast Fourier Transform, String Matching, Theory of NP-completeness, Approximation algorithms and Randomized algorithms."""),
        (sid['Web Development'], 'Unit I', 'Introduction to Web Development', """Introduction: Introduction and Web Development Strategies, History of Web and Internet, Protocols Governing Web, Writing Web Projects, Connecting to Internet, Introduction to Internet services and tools, Introduction to client-server computing. Web Page Designing: HTML: List, Table, Images, Frames, forms, XML: Document type definition (DTD), XML schemes, Object Models, presenting and using XML, Using XML Processors: DOM and SAX"""),
        (sid['Web Development'], 'Unit II', 'CSS', """CSS: Creating Style Sheet, CSS Properties, CSS Styling (Background, Text Format, Controlling Fonts), Working with block elements and objects, Working with Lists and Tables, CSS Id and Class, Box Model (Introduction, Border properties, Padding Properties, Margin properties) CSS Advanced (Grouping, Dimension, Display, Positioning, Floating, Align, Pseudo class, Navigation Bar, Image Sprites, Attribute sector), CSS Color, Creating page Layout and Site Designs."""),
        (sid['Web Development'], 'Unit III', 'JavaScript and Networking', """Scripting: Java script: Introduction, documents, forms, statements, functions, objects, introduction to AJAX. Networking: Internet Addressing, InetAddress, Factory Methods, Instance Methods, TCP/IP Client Sockets, URL, URL Connection, TCP/IP Server Sockets, and Datagram."""),
        (sid['Web Development'], 'Unit IV', 'Enterprise Java and Node.js', """Enterprise Java Bean: Creating a JavaBeans, JavaBeans Properties, Types of beans, Stateful Session bean, Stateless Session bean, Entity bean. Node.js: Introduction, Environment Setup, REPL Terminal, NPM (Node Package Manager) Callbacks Concept, Events, Packaging, Express Framework, Restful API. Node.js with MongoDB: MongoDB Create Database, Create Collection, Insert, delete, update, join, sort, query."""),
        (sid['Web Development'], 'Unit V', 'Servlets and JSP', """Servlets: Servlet Overview and Architecture, Interface Servlet and the Servlet Life Cycle, Handling HTTP get Requests, Handling HTTP post Requests, Redirecting Requests to Other Resources, Session Tracking, Cookies, Session Tracking with Http Session Java Server Pages (JSP): Introduction, Java Server Pages Overview, A First Java Server Page Example, Implicit Objects, Scripting, Standard Actions, Directives, Custom Tag Libraries."""),
        (sid['Entrepreneurship & Business Basics'], 'Unit I', 'Concept and Definitions of Entrepreneurship', """Concept and Definitions Entrepreneurship, Traits and Qualities of Entrepreneurs, Entrepreneurship process; Theories of entrepreneurship; Factors affecting the emergence of entrepreneurship; Role of an entrepreneur in economic growth as an innovator."""),
        (sid['Entrepreneurship & Business Basics'], 'Unit II', 'Classification and Types of Entrepreneurs', """Classification and Types of Entrepreneurs: Social Entrepreneurship; Corporate Entrepreneurs, Family Business: Concept, structure, and kinds of family firms; Culture and evolution of family firm; Managing Business, Industry Types:-Primary- Secondary-Tertiary."""),
        (sid['Entrepreneurship & Business Basics'], 'Unit III', 'Resource Mobilization', """Resources mobilization, types of resources, Process of resource mobilization, Arrangement of funds, Traditional sources of financing, Venture capital, Angel investors, Business Incubators."""),
        (sid['Entrepreneurship & Business Basics'], 'Unit IV', 'Business Structures and E-Business', """Difference between Private Company and Public Company, Role of Sole Trading company and Partnership Firm, Distinguish between Partnership Co-operative society and Joint Stock Companies. Benefits of E- Business. Limitations of E-Business:- Meaning of online transaction and Types of On-line payment mechanism."""),
        (sid['Financial Technologies'], 'Unit I', 'Introduction to Financial Technologies', """Introduction to Financial Technology: Financial technology brief history, Evolution of financial Technologies, Challenges in Financial technologies, Infrastructural needs, Financial Applications in banking, share market and insurance sector."""),
        (sid['Financial Technologies'], 'Unit II', 'Digital Financial Services', """Core Banking Solution: Introduction and benefits of CBS, Evolution of CBS, CBS infrastructure, CBS Modules (HO and Branch modules), Delivery Channels, Market Trends in CBS implementation. Challenges in CBS implementation"""),
        (sid['Financial Technologies'], 'Unit III', 'Financial Technology Applications', """Electronic Payment Systems: Introduction and working of electronic payment systems, electronic payment Types, E- currency (Crypto- currency and digital cash), Mobile/digital wallets, Payment gateways, Challenges in electronic payment systems."""),
        (sid['Financial Technologies'], 'Unit IV', 'RegTech', """Emerging Trends in Financial Technologies Applications of AI for financial services, Applications of Block-chain Technology for financial services, financial institutions and cloud-based offering, Deception technology, IoT based customized products for financial Services."""),
        (sid['Financial Technologies'], 'Unit V', 'Emerging Trends in Financial Technologies', """FinTech Regulation and RegTech Introduction - FinTech Regulations Evolution of RegTech – RegTech Ecosystem: Financial Institutions – RegTech Ecosystem Ensuring Compliance from the Start: Suitability and Funds – RegTech Startups: Challenges."""),
        (sid['Computer Graphics'], 'Unit I', 'Graphics Fundamentals', """Basic raster graphics algorithms for drawing 2 D Primitives liner, circles, ellipses, arcs, clipping, clipping circles, ellipses & polygon."""),
        (sid['Computer Graphics'], 'Unit II', '2D Transformations and Viewing', """Polygon Meshes in 3D, curves, cubic & surfaces, Solid modeling. Geometric Transformation: 2D, 3D transformations, window to viewport transformations, acromatic and color models. Graphics Hardware: Hardcopy & display techniques, Input devices, image scanners"""),
        (sid['Computer Graphics'], 'Unit III', '3D Graphics and Modeling', """Shading Tech: Transparency, Shadows, Object reflection, Gouraud & Phong shading techniques. Visible surface determination techniques for visible line determination, Z-buffer algorithm, scanline algorithm, algorithm for oct-tres, algorithm for curve surfaces, visible surfaces ray- tracing, recursive ray tracing, radio-city methods."""),
        (sid['Computer Graphics'], 'Unit IV', 'Visible Surface and Rendering', """Elementary filtering tech, elementary Image Processing techniques, Geometric & multi-pass transformation mechanisms for image storage & retrieval. Procedural models, fractals, grammar- based models, multi-particle system, volume rendering"""),
        (sid['Computer Graphics'], 'Unit V', 'Multimedia, Graphics and Animation', """Multimedia : Introduction to Multimedia : Classification of Multimedia, Multimedia Software, Components of Multimedia – Audio : Analog to Digital conversion, sound card fundamentals, Audio play backing and recording Video, Text : Hypertext, Hyper media and Hyper Graphics, Graphics and Animation : Classification of Animation ."""),
        (sid['Data Communication and Computer Networks'], 'Unit I', 'Data Communication and Network Fundamentals', """Data Communications: Components, Data Representation, Data Flow, Networks; Network Criteria, Physical Structures, Network Types: LAN, WAN, Switching, Network Models: Protocol Layering: Principles of Protocol Layering, Logical Connections, TCP/IP Protocol Suite: Layered Architecture, Layers in the TCP/IP Protocol Suite, Addressing, Multiplexing and Demultiplexing, The OSI Model; OSI versus TCP/IP, Lack of OSI Model’s Success,"""),
        (sid['Data Communication and Computer Networks'], 'Unit II', 'Data Link Layer', """Introduction to Physical Layer: Data and Signals, Periodic Analog Signals, Digital Signals, Transmission Impairment, Data Rate Limits, Performance, Switching: Circuit-Switched Networks, Packet Switching."""),
        (sid['Data Communication and Computer Networks'], 'Unit III', 'Network Layer', """Introduction to Data-Link Layer, Link-Layer Addressing: Address Resolution Protocol (ARP), Error Detection and Correction: Introduction, Types of Errors, Redundancy, Detection versus Correction, Coding, Block coding: Error Detection, Cyclic Code: Cyclic Redundancy Check. Introduction to Network Layer : Network-Layer Services: Packetizing, Routing and Forwarding, Packet Switching: Datagram Approach, Virtual-Circuit Approach, Network Layer"""),
        (sid['Data Communication and Computer Networks'], 'Unit IV', 'Transport Layer', """Introduction to Transport-Layer: Transport Layer Services: Transport-Layer Protocols. Introduction to Application Layer, Services, Application-Layer Paradigms, World Wide Web and HTTP: FTP: Two Connections, Control Connection, Data Connection, Security for FTP, E- Mail: Architecture, Web-Based Mail, Domain Name System (DNS): Name Space, DNS in the Internet, Resolution."""),
        (sid['Data Communication and Computer Networks'], 'Unit V', 'Application Layer', """Application Layer: Application Layer: File Transfer, Access and Management, Electronic 8 mail, Virtual Terminals, Other application. Example Networks - Internet and Public Networks."""),
        (sid['Cryptography and Cyber Security'], 'Unit I', 'Introduction to Cryptography and Security', """Introduction To Security: Computer Security Concepts – The OSI Security Architecture – Security Attacks – Security Services and Mechanisms – A Model for Network Security – Classical encryption techniques: Substitution techniques, Transposition techniques, Steganography – Foundations of modern cryptography: Perfect security – Information Theory – Product Cryptosystem – Cryptanalysis."""),
        (sid['Cryptography and Cyber Security'], 'Unit II', 'Symmetric Key Cryptography', """Symmetric Ciphers: Number theory – Algebraic Structures – Modular Arithmetic – Euclid‘s algorithm – Congruence and matrices – Group, Rings, Fields, Finite Fields SYMMETRIC KEY CIPHERS: SDES – Block Ciphers – DES, Strength of DES – Differential and linear cryptanalysis – Block cipher design principles – Block cipher mode of operation – Evaluation criteria for AES – Pseudorandom Number Generators – RC4 – Key distribution."""),
        (sid['Cryptography and Cyber Security'], 'Unit III', 'Asymmetric Key Cryptography', """Mathematics Of Asymmetric Key Cryptography: Primes – Primality Testing –Factorization – Euler’s totient function, Fermat’s and Euler’s Theorem – Chinese Remainder Theorem – Exponentiation and logarithm .ASYMMETRIC KEY CIPHERS: RSA cryptosystem – Key distribution – Key management –Hellman key exchange -– Elliptic curve arithmetic – Elliptic curve cryptography"""),
        (sid['Cryptography and Cyber Security'], 'Unit IV', 'Digital Signatures and Authentication', """Authentication requirement – Authentication function – MAC – Hash function – Security of hashfunction: HMAC, CMAC – SHA – Digital signature and authentication protocols – DSS – Schnorr Digital Signature Scheme – ElGamal cryptosystem – Entity Authentication: Biometrics, Passwords, Challenge Response protocols – Authentication applications – Kerberos MUTUAL TRUST: Key management and distribution – Symmetric key distribution using symmetric and asymmetric encryption – Distribution of public keys – X.509 Certificates."""),
        (sid['Cryptography and Cyber Security'], 'Unit V', 'Key Management and Distribution', """Cyber Crime and Information Security – classifications of Cyber Crimes – Tools and Methods –Password Cracking, Key loggers, Spywares, SQL Injection – Network Access Control – Cloud Security – Web Security – Wireless Security."""),
        (sid['Machine Learning Techniques'], 'Unit I', 'Introduction to Machine Learning', """Introduction to AI and ML History of AI, Comparison of AI with Data Science, Need of AI in Mechanical Engineering, Introduction to Machine Learning. Basics: Reasoning, problem solving, Knowledge representation, Planning, Learning, Perception, Motion and manipulation. Types of Machine learning: Supervised, Unsupervised, semi-supervised and reinforcement learning Feature selection Mechanisms, Data engineering and pre-processing, Data processing cycle, Data processing methods."""),
        (sid['Machine Learning Techniques'], 'Unit II', 'Supervised Learning', """Supervised Learning- Linear Regression, Multiple Regression, Logistic Regression, Classification; classifier models, K Nearest Neighbour (KNN), Naive Bayes, Decision Trees, Support Vector Machine (SVM), Random Forest"""),
        (sid['Machine Learning Techniques'], 'Unit III', 'Unsupervised Learning', """Unsupervised Learning- Dimensionality reduction; Clustering; K-Means clustering; C-means clustering; Fuzzy C means clustering, EM Algorithm, Association Analysis- Association Rules in Large Databases, Apriori algorithm, Markov models: Hidden Markov models (HMMs)."""),
        (sid['Machine Learning Techniques'], 'Unit IV', 'Reinforcement Learning', """Reinforcement learning- Introduction to reinforcement learning, Methods and elements of reinforcement learning, Bellman equation, Markov decision process (MDP), Q learning, Value function approximation, Temporal difference learning, Applications of Reinforcement learning."""),
        (sid['Machine Learning Techniques'], 'Unit V', 'Neural Networks and Deep Learning', """Neural Network and Deep Learning architecture : Concept of neural networks, Deep Q Neural Network (DQN), A Convolution neural network (CNN) -Layers in CNN -CNN architectures. Recurrent Neural Network -Applications: Speech-to-text conversion , Image classification-time series prediction."""),
        (sid['Data Analytics'], 'Unit I', 'Introduction to Data Analytics', """Introduction to Data Analytics: Sources and nature of data, classification of data (structured, semi-structured, unstructured), characteristics of data, introduction to Big Data platform, need of data analytics, evolution of analytic scalability, analytic process and tools, analysis vs reporting, modern data analytic tools, applications of data analytics. Data Analytics Lifecycle: Need, key roles for successful analytic projects, various phases of data analytics lifecycle – discovery, data preparation, model planning, model building, communicating results, operationalization."""),
        (sid['Data Analytics'], 'Unit II', 'Data Analysis', """Data Analysis: Regression modeling, multivariate analysis, Bayesian modeling, inference and Bayesian networks, support vector and kernel methods, analysis of time series: linear systems analysis & nonlinear dynamics, rule induction, neural networks: learning and generalisation, competitive learning, principal component analysis and neural networks, fuzzy logic: extracting fuzzy models from data, fuzzy decision trees, stochastic search methods.."""),
        (sid['Data Analytics'], 'Unit III', 'Mining Data Streams', """Mining Data Streams: Introduction to streams concepts, stream data model and architecture, stream computing, sampling data in a stream, filtering streams, counting distinct elements in a stream, estimating moments, counting oneness in a window, decaying window, Real-time Analytics Platform ( RTAP) applications, Case studies – real time sentiment analysis, stock market predictions."""),
        (sid['Data Analytics'], 'Unit IV', 'Frequent Itemsets and Clustering', """Frequent Itemsets and Clustering: Mining frequent itemsets, market based modelling, Apriorialgorithm, handling large data sets in main memory, limited pass algorithm, counting frequent itemsets in a stream, clustering techniques: hierarchical, K-means, clustering high dimensional data, CLIQUE and ProCLUS, frequent pattern based clustering methods, clustering in non-euclidean space, clustering for streams and parallelism"""),
        (sid['Data Analytics'], 'Unit V', 'Frameworks and Visualization', """Frame Works and Visualization: MapReduce, Hadoop, Pig, Hive, HBase, MapR, Sharding, NoSQL Databases, S3, Hadoop Distributed File Systems, Visualization: visual data analysis techniques, interaction techniques, systems and applications. Introduction to R - R graphical user interfaces, data import and export, attribute and data types, descriptive statistics, exploratory data analysis, visualization before analysis, analytics for unstructured data."""),
        (sid['Cloud Computing'], 'Unit I', 'Introduction to Cloud Computing', """Introduction to Cloud Computing: Definition of Cloud – Evolution of Cloud Computing , Adoption of cloud-based IT resources, Service Models: Infrastructure-as-a-Service (IaaS), Platform-as-a-Service (PaaS), Software-as-a-Service (SaaS), Deployment models: Public Cloud, Private Cloud, Hybrid Cloud, Community Cloud, Cloud Computing Characteristics."""),
        (sid['Cloud Computing'], 'Unit II', 'Resource Management and Security in Cloud', """Resource Management And Security In Cloud: Inter Cloud Resource Management – Resource Provisioning and Resource Provisioning Methods – Global Exchange of Cloud Resources – Security Overview – Cloud Security Challenges – Software‐as‐a‐Service Security – Security Governance – Virtual Machine Security – IAM – Security Standard"""),
        (sid['Cloud Computing'], 'Unit III', 'Virtualization', """Challenges of cloud computing, Virtualization concept, Types of virtualizations, Demo of virtualization, Virtualization Merits, Role of virtualization in cloud computing, Virtualization Demerits, VM Placement, VM Migration, VM Migration Demo, VM clustering, Design Issues in VM Clustering, Need of Dockers and Containers, Docker Eco-System, Hypervisor vs Docker"""),
        (sid['Cloud Computing'], 'Unit IV', 'Cloud Technologies and Advancements', """Cloud Technologies And Advancements Hadoop: MapReduce – Virtual Box — Google App Engine – Programming Environment for Google App Engine –– Open Stack – Federation in the Cloud – Four Levels of Federation – Federated Services and Applications – Future of Federation."""),
        (sid['Cloud Computing'], 'Unit V', 'Case Study', """Case Study: Cloud Market analysis, Security and Compliances, Shared securitymodel inIAAS/PAAS/SAAS, Shared technology issues, Data loss or leakage,Account or servicehijacking, Implementation of cloud security, Security Groups,Network Access Control Lists, Cloud databases, Parallel Query Execution withNoSQL Database, Big Data, Handling Big Data on Cloud Platform, Map- Reduceframework for large clusters using Hadoop, Design of data applications based onMap Reduce in Apache Hadoop."""),
        (sid['Block Chain Technology'], 'Unit I', 'Introduction to Blockchain', """Introduction to Blockchain: Definition, History, and Evolution of Blockchain., Blockchain vs Traditional Databases, Key Characteristics of Blockchain (Decentralization, Immutability, Transparency, Security). Blockchain Components: Blocks, Hashing, and Merkle Trees. Transactions and Ledgers. Peer- to-Peer (P2P) Network. Blockchain Types: Public, Private, and Consortium Blockchains. Use Cases and Applications of Blockchain (Cryptocurrencies, Smart Contracts, Supply Chain, etc.). Overview of Bitcoin: Introduction to Bitcoin and its working. Understanding the concept of mining and consensus in Bit coin."""),
        (sid['Block Chain Technology'], 'Unit II', 'Cryptographic Principles', """Cryptographic Principles: Basics of Cryptography: Symmetric vs Asymmetric encryption. Hashing Algorithms (SHA-256, MD5, etc.).Public/Private Key Cryptography. Digital Signatures and Certificates: How digital signatures ensure transaction integrity, Blockchain transaction signing and verification process Block chain Security Models: Security issues in block chain: 51% Attack, Double Spending, Sybil Attacks. Blockchain and Privacy: Zero-knowledge proofs, Ring signatures, Stealth Addresses. Smart Contract Security: Vulnerabilities in Smart Contracts (Reentrancy attacks, Integer overflow, etc.). Best practices in writing secure smart contracts."""),
        (sid['Block Chain Technology'], 'Unit III', 'Consensus Algorithms', """Overview of Consensus Algorithms: Definition and Importance of Consensus in Blockchain., Proof of Work (PoW), Proof of Stake (PoS), Delegated Proof of Stake (DPoS)., Other Consensus Algorithms: Proof of Authority (PoA), Practical Byzantine Fault Tolerance (PBFT), and more. Mining and Validation in Blockchain: Mining process in Proof of Work and its energyconcerns. Staking in Proof of Stake and Delegated Proof of Stake. Blockchain Scalability and Performance: Scalability issues in blockchain networks. Layer 2 solutions (e.g., Lightning Network, Plasma, Sharding) Blockchain Network Models: Permissioned vs Permissionless Blockchain networks. Interoperability and Cross-chain communication (e.g., Polkadot, Cosmos)."""),
        (sid['Block Chain Technology'], 'Unit IV', 'Smart Contracts', """Topics: Introduction to Smart Contracts: Definition and importance of Smart Contracts in Blockchain. Use cases of Smart Contracts (DeFi, NFT, insurance, etc.). Ethereum Block chain Platform: Ethereum Overview: Ethereum Virtual Machine (EVM), Gas, Ether.,Ethereum Development Frameworks (Truffle, Hardhat). Smart Contract Development: Writing smart contracts in Solidity. Testing and deploying smart contracts on Ethereum testnets. DecentralizedApplications (dApps):Introduction to dApps architecture. Building a simple dApp using Ethereum and Smart Contracts."""),
        (sid['Block Chain Technology'], 'Unit V', 'Blockchain Applications', """Topics: Blockchain in Cryptocurrency: Overview of Bitcoin, Ethereum, and other popular crypto currencies., Wallets, Exchanges, and Blockchain Transactions. Enterprise Blockchain Solutions: Blockchain for Supply Chain Management, Healthcare, Voting Systems, and IoT., Case Studies: IBM’s Hyperledger, VeChain, and other enterprise blockchain platforms., Blockchain in Government and Public Sector: Blockchain in Digital Identity, Land Records, and Governance. Future of Blockchain: Blockchain 3.0 and beyond: Interoperability, Scalability, and Sustainability. Emerging Trends: Web3, NFTs, DAOs, Metaverse, and more"""),
        (sid['Internet of Things'], 'Unit I', 'Introduction and Applications', """Introduction and Applications: Introduction to IoT–Definition, Characteristics, functional requirements, motivation, Physical design-things in IoT, IoT protocols, Logical Design-functional blocks, communication models, Communication APIs,M2M Communication, IoT Examples. Design Principles for Connected Devices: IoT/M2M systems layers and design standardization, communication technologies, data enrichment and consolidation, ease of designing and affordability, Applications–Home Automation, Cities, Environment, Energy, Agriculture, Health, Industry."""),
        (sid['Internet of Things'], 'Unit II', 'Hardware for IoT', """Hardware for IoT: Sensors, Digital sensors, actuators, radio frequency identification (RFID) technology, wireless sensor networks, participatory sensing technology. Embedded Platforms for IoT: Embedded computing basics, Overview of IOT supported Hardware platforms such as Arduino, NetArduino, Raspberry pi, Beagle Bone, Intel Galileo boards and ARM cortex."""),
        (sid['Internet of Things'], 'Unit III', 'Developing Internet of Things', """Developing Internet of Things: IoT Methodology-Purpose & Requirements specification, process specification, domain model specification, information model specification, service specification, IoT level specifications"""),
        (sid['Internet of Things'], 'Unit IV', 'Programming the Arduino', """Programming the Ardunio: Ardunio Platform Boards Anatomy, Ardunio IDE, coding, using emulator, using libraries, additions in ardunio, programming the ardunio for IoT."""),
        (sid['Internet of Things'], 'Unit V', 'Case Study on IoT System', """Case Study on IoT System:Case study for weather monitoring system-modules & package of python, python packages of interest for IoT-JSON, XML, HTTP &URLLib, SMTPLib. Exemplary device-Rasberry pi, Linux on Raspberry pi"""),
        (sid['Data Warehousing and Data Mining'], 'Unit I', 'Data Warehousing and Business Analysis', """Data Warehousing and Business Analysis: - Data warehousing Components –Building a Data warehouse –Data Warehouse Architecture – DBMS Schemas for Decision Support – Data Extraction, Cleanup, and Transformation Tools –Metadata – reporting – Query tools and Applications – Online Analytical Processing (OLAP) – OLAP and Multidimensional Data Analysis."""),
        (sid['Data Warehousing and Data Mining'], 'Unit II', 'Data Mining', """Data Mining: - Data Mining Functionalities – Data Preprocessing – Data Cleaning – Data Integration and Transformation – Data Reduction – Data Discretization and Concept Hierarchy Generation- Architecture Of A Typical Data Mining Systems- Classification Of Data Mining Systems. Association Rule Mining: - Efficient and Scalable Frequent Item set Mining Methods – Mining Various Kinds of Association Rules – Association Mining to Correlation Analysis – Constraint- Based Association Mining."""),
        (sid['Data Warehousing and Data Mining'], 'Unit III', 'Classification and Prediction', """Classification and Prediction: - Issues Regarding Classification and Prediction – Classification by Decision Tree Introduction – Bayesian Classification – Rule Based Classification – Classification by Back propagation – Support Vector Machines – Associative Classification – Lazy Learners – Other Classification Methods – Prediction – Accuracy and Error Measures – Evaluating the Accuracy of a Classifier or Predictor – Ensemble Methods – Model Section."""),
        (sid['Data Warehousing and Data Mining'], 'Unit IV', 'Cluster Analysis', """Cluster Analysis: - Types of Data in Cluster Analysis – A Categorization of Major Clustering Methods – Partitioning Methods – Hierarchical methods – Density-Based Methods – Grid-Based Methods – Model-Based Clustering Methods – Clustering High-Dimensional Data – Constraint- Based Cluster Analysis – Outlier Analysis."""),
        (sid['Data Warehousing and Data Mining'], 'Unit V', 'Mining Complex Data', """Mining Object, Spatial, Multimedia, Text and Web Data: Multidimensional Analysis and Descriptive Mining of Complex Data Objects – Spatial Data Mining – Multimedia Data Mining – Text Mining – Mining the World Wide Web."""),
        (sid['Natural Language Processing'], 'Unit I', 'Overview and Morphology', """OVERVIEW AND MORPHOLOGY: Introduction – Models -and Algorithms - -Regular Expressions Basic Regular Expression Patterns – Finite State Automata Understand the wireless sensor network principles. Morphology -Inflectional Morphology - Derivational Morphology. Finite-State Morphological Parsing -- Porter Stemmer"""),
        (sid['Natural Language Processing'], 'Unit II', 'Word Level and Syntactic Analysis', """WORD LEVEL AND SYNTACTIC ANALYSIS: N-grams Models of Syntax - Counting Words Unsmoothed N-grams .Smoothing- Back-off Deleted Interpolation – Entropy - English Word Classes - Tag sets for English Part of Speech Tagging-Rule Based Part of Speech Tagging - Stochastic Part of Speech Tagging - Transformation-Based Tagging."""),
        (sid['Natural Language Processing'], 'Unit III', 'Context Free Grammars', """CONTEXT FREE GRAMMARS: Context Free Grammars for English Syntax- Context-Free Rules and Trees -Understand the network simulation tools. Sentence- Level Constructions– Agreement – Sub Categorization .Parsing – Top-down – Early Parsing -feature Structures – Probabilistic Context-Free Grammars."""),
        (sid['Natural Language Processing'], 'Unit IV', 'Semantic Analysis', """SEMANTIC ANALYSIS: Representing Meaning-Meaning Structure of Language-First Order Predicate Calculus Representing Linguistically Relevant Concepts -Syntax-Driven Semantic Analysis - Semantic Attachments -Syntax-Driven Analyzer. Robust Analysis - Lexemes and Their Senses - Internal Structure - Word Sense Disambiguation -Information Retrieval."""),
        (sid['Natural Language Processing'], 'Unit V', 'Language Generation and Discourse Analysis', """FLANGUAGE GENERATION AND DISCOURSE ANALYSIS: Discourse -Reference Resolution - Text Coherence -Discourse Structure – Coherence. Dialog and Conversational Agents - Dialog Acts – Interpretation -Conversational Agents. Language Generation– Architecture-Surface Realizations - Discourse Planning .Machine Translation -Transfer Metaphor– Interlingua – Statistical Approaches"""),
        (sid['Mobile Application Development'], 'Unit I', 'Introduction to Android', """Introduction to Android: The Android Platform, Android SDK, Eclipse Installation, Android Installation, Building you First Android application, Understanding Anatomy of Android Application, Android Manifest file."""),
        (sid['Mobile Application Development'], 'Unit II', 'Android Application Design Essentials', """Android Application Design Essentials: Anatomy of an Android applications, Android terminologies, Application Context, Activities, Services, Intents, Receiving and Broadcasting Intents, Android Manifest File and its common settings, Using Intent Filter, Permissions."""),
        (sid['Mobile Application Development'], 'Unit III', 'Android User Interface Design Essentials', """Android User Interface Design Essentials: User Interface Screen elements, Designing User Interfaces with Layouts, Drawing and Working with Animation."""),
        (sid['Mobile Application Development'], 'Unit IV', 'Testing and Publishing', """Testing : Android applications, Publishing Android application, Using Android preferences, Managing Application resources in a hierarchy, working with different types of resources."""),
        (sid['Mobile Application Development'], 'Unit V', 'Using Common Android APIs', """Using Common Android APIs: Using Android Data and Storage APIs, Managing data using Sqlite, Sharing Data between Applications with Content Providers, Using Android Networking APIs, Using Android Web APIs, Using Android Telephony APIs, Deploying Android Application to the World."""),
        (sid['Distributed System'], 'Unit I', 'Characterization of Distributed Systems', """Characterization of Distributed Systems: Introduction, Examples of distributed Systems, Resource sharing and the Web Challenges. Architectural models, Fundamental Models. Theoretical Foundation for Distributed System: Limitation of Distributed system, absence of global clock, shared memory, Logical clocks ,Lamport’s& vectors logical clocks. Concepts in Message Passing Systems: causal order, total order, total causal order, Techniques for Message Ordering, Causal ordering of messages, global state, termination detection."""),
        (sid['Distributed System'], 'Unit II', 'Propositional Logic and Proof Techniques', """Propositional Logic and Proof Techniques: Propositions, Logical operations, Truth tables, Logical equivalence and laws of logic (De Morgan’s laws, distributive, associative, etc.), Predicates and quantifiers, Rules of inference, Proof techniques (Direct proof, proof by contradiction, proof by contraposition)."""),
        (sid['Distributed System'], 'Unit III', 'Consensus and Recovery', """CONSENSUS AND RECOVERY: Consensus and Agreement Algorithms- Problem Definition, Overview of Results, Agreement in a Failure, Free System(Synchronous and Asynchronous), Agreement in Synchronous Systems with Failures, Checkpointing and Rollback Recovery- Introduction, Background and Definitions, Issues in Failure Recovery, Checkpoint - based Recovery, Coordinated Checkpointing Algorithm, Algorithm for Asynchronous Checkpointing and Recovery."""),
        (sid['Distributed System'], 'Unit IV', 'Transactions and Concurrency Control', """Transactions and Concurrency Control: Introduction, Transactions, Nested Transactions, Locks, Optimistic Concurrency Control, Timestamp Ordering, Comparison of Methods for Concurrency Control. Distributed Transactions: Introduction, Flat and Nested Distributed Transactions, Atomic Commit Protocols, Concurrency Control in Distributed Transactions, Distributed Deadlocks, Transaction Recovery."""),
        (sid['Distributed System'], 'Unit V', 'Distributed File Systems', """Distributed File Systems: Introduction, File Service Architecture, Case Study 1: Sun Network File System, Case Study 2: The Andrew File System. Name Services: Introduction, Name Services and the Domain Name System, Directory Services, Case Study of the Global Name Services. Distributed Shared Memory: Introduction, Design and Implementation Issues, Sequential Consistency and IVY case study, Release Consistency, Munin Case Study, Other Consistency Models."""),
        (sid['Prompt Engineering'], 'Unit I', 'Introduction to Large Language Models', """Introduction to Large Language Models What are Text Generation Models, Large Language Models are Magic, A Brief History of Language Models, LLMs in the Market"""),
        (sid['Prompt Engineering'], 'Unit II', 'Understanding Prompting and Prompt Techniques', """Understanding Prompting and Prompt Techniques Five Principles of Prompting, Introducing LLM Prompts, How LLM Prompts Work, Types of Prompts, Components of an Prompt, Defining Personality in Prompts, Mix and Match Strategic Combination for Enhanced Prompts, Challenges and Limitations of Using Prompts."""),
        (sid['Prompt Engineering'], 'Unit III', 'Standard Practices for Text Generation', """Standard Practices for Text Generation Generating Lists, Explain It Like I’m Five, Universal Translation Through LLMs, Ask For Context, Text Style Unbundling, Identifying the Desired Textual Features, Generating New Content with the Extracted Features, Role Prompting, Analyzing Existing Prompts for Strengths and Weaknesses."""),
        (sid['Prompt Engineering'], 'Unit IV', 'Generating Text with AI for Content Creation', """Generating Text with AI for Content Creation Using AI for Copywriting, Creating Social Media Posts. Writing Video Scripts, Using AI for Personalized Messaging, Creating Engaging and Tailored Content with AI, Techniques for Crafting Effective Prompts for Surveys, Assessments, and Data Collection, Using Prompts in Research Methodology."""),
        (sid['Prompt Engineering'], 'Unit V', 'Introduction to Diffusion Models for Image Generation', """Introduction to Diffusion Models for Image Generation Introduction to Image Generation with AI, Principles of Designing Prompts for Image Generation, Available Models - OpenAI DALL-E, Midjourney, Stable Diffusion, Google Gemini, Text to Video, Model Comparison, Reverse Engineering Prompts, Negative Prompts, Prompt Re-Writing, Prompt Analysis."""),
        (sid['Research Methodology'], 'Module – I', 'Introduction to Research', """Introduction to Research: Concept, Need, and Purpose, Research Problem and Research Design, Literature Review, Hypothesis: Definition, Types, Sources, and Functions"""),
        (sid['Research Methodology'], 'Module – II', 'Types of Research Methods', """Types of Research Methods: Historical, Survey, and Experimental, Case Study, Scientific Research and Statistical Research, etc."""),
        (sid['Research Methodology'], 'Module – III', 'Research Techniques', """Research Techniques: Research Techniques and Tools: Questionnaire, Interview, Observation, Schedule and Check-list, etc., Library Records and Reports., Statistics and its Applications, Descriptive Statistics – Measures of Central Tendency: & Dispersion, Correlations and linear regression, Chi-Square test, t-test, z-test, f-test., Presentation of Data: Tabular, Graphic, Bar Diagram and Pie Chart, etc. Report Writing."""),
        (sid['Research Methodology'], 'Module – IV', 'Metric Studies and Style Manuals', """Metric Studies and Style Manuals: Statistical Packages – MS Excel, SPSS, and Web-based Statistical Analysis Tools, etc., Metric Studies and Style Manuals, Scientometrics, Infometrics, and Webometrics, Manual Structure, Style, Contents- ISI, MLA, APA, CHICAGO, etc."""),
    ]

    cur.executemany(
        "INSERT INTO units (subject_id, unit_number, unit_title, topics) VALUES (?,?,?,?)",
        units
    )


# ============================================================
# LLM SETUP (Gemini)
# ============================================================
def get_gemini_response(prompt):
    try:
        import google.generativeai as genai
        api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        if not api_key:
            return "⚠️ Gemini API key not configured. Please add it in Streamlit secrets."
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3.6-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error generating response: {e}"

# ============================================================
# APP START
# ============================================================
conn = init_db()
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
    subject_choice = st.selectbox("Subject", [s[1] for s in subs_in_sem], key="notes_subject")
    subject_id = next(s[0] for s in subs_in_sem if s[1] == subject_choice)

    cur.execute("SELECT unit_number, unit_title, topics FROM units WHERE subject_id=?", (subject_id,))
    units_list = cur.fetchall()

    mode = st.radio("Generate notes for:", ["Full Unit", "Specific Topic"])
    if mode == "Full Unit" and units_list:
        unit_choice = st.selectbox("Select Unit", [f"{u[0]}: {u[1]}" for u in units_list])
        topic_text = unit_choice
        context = next(u[2] for u in units_list if f"{u[0]}: {u[1]}" == unit_choice)
    else:
        topic_text = st.text_input("Enter specific topic (e.g., 'Logistic Regression')")
        context = topic_text

    length = st.select_slider("Answer length", options=["Short", "Concise", "Long"], value="Concise")

    if st.button("Generate Notes") and topic_text:
        with st.spinner("Generating notes..."):
            prompt = f"""You are a helpful academic tutor for an MCA student at JSS University.
Subject: {subject_choice}
Topic: {topic_text}
Context/related subtopics: {context}

Write clear, well-structured study notes on this topic suitable for exam preparation.
Length: {length} (Short = key points only, Concise = balanced paragraph explanation, Long = detailed explanation with examples).
{lang_instruction}
Use headings and bullet points where helpful."""
            result = get_gemini_response(prompt)
            st.markdown(result)
            cur.execute("INSERT INTO generated_notes (user_id, subject_id, topic, content) VALUES (?,?,?,?)",
                        (st.session_state.user_id, subject_id, topic_text, result))
            conn.commit()

    st.divider()
    st.subheader("Your Saved Notes")
    cur.execute("SELECT topic, content, created_at FROM generated_notes WHERE user_id=? AND subject_id=? ORDER BY created_at DESC LIMIT 5",
                (st.session_state.user_id, subject_id))
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
Answer length: {length}.
{lang_instruction}"""
            result = get_gemini_response(prompt)
            st.markdown(result)

# ---------------- MCQ TEST ----------------
elif page == "MCQ Test":
    st.header("🧠 MCQ Test Generator")
    sem_choice = st.selectbox("Semester", semesters, key="mcq_sem")
    subs_in_sem = [s for s in all_subjects if s[2] == sem_choice]
    subject_choice = st.selectbox("Subject", [s[1] for s in subs_in_sem], key="mcq_subject")
    num_q = st.slider("Number of questions", 3, 10, 5)

    if st.button("Generate MCQ Test"):
        with st.spinner("Creating quiz..."):
            prompt = f"""Create {num_q} multiple choice questions for an MCA student on the subject: {subject_choice}.
For each question, give 4 options (A-D), and clearly indicate the correct answer with a short explanation.
{lang_instruction}
Format each question clearly numbered."""
            result = get_gemini_response(prompt)
            st.markdown(result)

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