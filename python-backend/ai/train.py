from vanna.ollama import Ollama
from vanna.chromadb import ChromaDB_VectorStore
import logging
import os
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
# Vanna configuration
class MyVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)

vn = MyVanna(config={'model': 'gemma3:12b', 'host': 'localhost', 'port': 11434})
vn.connect_to_mssql(odbc_conn_str="DRIVER={ODBC Driver 17 for SQL Server};SERVER=4.247.166.77;DATABASE=ABICRM;UID=rajeshc;PWD=Admin@123$")

	
# Train schema
logger.info("Training Vanna with VIEW_PATIENT_SUM schema")
try:
    vn.train(ddl="""
    CREATE TABLE VIEW_PATIENT_SUM (
        PatientNumber VARCHAR(25),
        PNAME VARCHAR(100),
        OrgName VARCHAR(100),
        Location VARCHAR(100),
        EMail VARCHAR(100),
        SEX CHAR(1) CHECK (SEX IN ('M', 'F')),
        Age VARCHAR(10),
        numericAge FLOAT(10),
        MobileNumber VARCHAR(15),
        CONDITION VARCHAR(MAX),
        REPEAT INT,
        LastVisitDate DATETIME,
        ExpectedVisitDate DATETIME,
        FirstVisitDate DATETIME,
        TotalVisits INT,
        TotalAmount FLOAT(50),
        AverageTicket FLOAT(50)
    );
    """)
    logger.info("Schema trained successfully")
except Exception as e:
    logger.error("Schema training failed: %s", str(e))
    raise


conditions = [
    'Acid-Base Imbalance', 'Allergic Reactions', 'Allergic Reactions or Infections', 'Allergic Reactions or Parasitic Infections', 'Anemia',
    'Ankylosing Spondylitis', 'Antiphospholipid Syndrome', 'Aspergillosis', 'Autoimmune Diseases', 'Autoimmune Hepatitis',
    'Bacterial Infections', 'Bipolar Disorder', 'Bleeding Disorders', 'Blood Clotting Disorders', 'Blood Disorders',
    'Breast Cancer', 'Calcium Imbalance', 'Cancer', 'Cardiovascular Disease', 'Celiac Disease',
    'Chikungunya', 'Chlamydia', 'Chronic Infections or Inflammatory Conditions', 'Cortisol Abnormality', 'COVID-19',
    'Cytomegalovirus Infection', 'Dengue', 'Depression', 'Diabetes', 'Diabetic Ketoacidosis',
    'Drug Abuse', 'Electrolyte Imbalance', 'Epilepsy', 'Filariasis', 'Folate Deficiency',
    'Food', 'Food Intolerance', 'Fungal Infections', 'Gastric Cancer', 'Gastric Ulcers',
    'Gastrointestinal Bleeding', 'General Health Checkup', 'Gonorrhea', 'Gout', 'Hashimoto\'s Thyroiditis',
    'Heart Attack', 'Heart Failure', 'Hemolytic Anemia', 'Hemophilia', 'Hepatitis A',
    'Hepatitis B', 'Hepatitis C', 'Hepatitis E', 'Herpes', 'HIV',
    'Hormonal Imbalance', 'Immune System Disorders', 'Infections', 'Infections or Inflammation', 'Inflammation',
    'Inflammatory Bowel Disease (IBD)', 'Iron Deficiency', 'Kidney Disease', 'Kidney Function', 'Kidney Stones',
    'Liver Cancer or Testicular Cancer', 'Liver Disorders', 'Lupus', 'Malaria', 'Muscle Disorders',
    'NORMAL', 'Organ Transplant', 'Ovarian Cancer', 'Ovarian Reserve', 'Pancreatic Cancer',
    'Pancreatitis', 'Parasitic Infections', 'Pregnancy', 'Prostate Cancer', 'Rheumatoid Arthritis',
    'Rubella Infection', 'Sarcoidosis', 'Sickle Cell Anemia', 'Smoking', 'Streptococcal Infections',
    'Syphilis', 'Thyroid Disorders', 'Toxoplasmosis', 'Tuberculosis', 'Typhoid',
    'Urinary Tract Infections', 'Vitamin B12 Deficiency', 'Vitamin D Deficiency', 'Vitamin E Deficiency'
]


# Add medical conditions as documents in ChromaDB
try:
    unique_conditions = list(dict.fromkeys(conditions))
    for condition in unique_conditions:
        safe_condition = condition.replace(" ", "_").replace("/", "_").replace("'", "")
        document_id = f"condition_{safe_condition}"

        vn.add_documentation(
            document_id=document_id,
            documentation=condition,
            metadata={
                "category": "Medical Condition",
                "source": "healthcare"
            }
        )

    # No need to call vn.commit()
    logger.info(f"Successfully added {len(unique_conditions)} medical conditions to ChromaDB")
except Exception as e:
    logger.error("Failed to add medical conditions: %s", str(e))
    raise


# Train Vanna to improve awareness of conditions
logger.info("Training Vanna with additional context")
try:
    # Add documentation for domain knowledge
    vn.train(
        documentation="Medical conditions stored in the CONDITION column of VIEW_PATIENT_SUM, including infections, autoimmune diseases, cancers, vitamin deficiencies, and general health states. Use CAST(numericAge AS INT) for age-related queries, not Age (VARCHAR)."
    )
    
    logger.info("Vanna trained successfully with documentation")
except Exception as e:
    logger.error("Failed to train Vanna: %s", str(e))
    raise



# Training queries with example
logger.info("Training Vanna with example queries")
training_queries = [
    {
        "question": "Show me 5000 Female patients aged 20 to 50 and name starting with A, who has Allergic Reactions or Parasitic Infections condition",
        "sql": """SELECT TOP 5000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE SEX = 'F' AND PNAME LIKE 'A%' AND CONDITION LIKE '%Allergic Reactions or Parasitic Infections%' AND CAST(numericAge AS INT) BETWEEN 20 AND 50;"""
    },
    {
        "question": "Give me all Patients who are suffering with Hepatitis A or Hepatitis B or Hepatitis C or Hepatitis E and who have visited since 1st Jan 2025",
        "sql": """SELECT PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION IN ('Hepatitis A', 'Hepatitis B', 'Hepatitis C', 'Hepatitis E') AND LastVisitDate >= '2025-01-01';"""
    },
    {
        "question": "Show me all patients who has Anemia condition, age ranges from 20 to 30",
        "sql": """SELECT PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION LIKE '%Anemia%' AND CAST(numericAge AS INT) BETWEEN 20 AND 30;"""
    },
    {
        "question": "Show 20000 patients with Vitamin D Deficiency age between 10 to 20",
        "sql": """SELECT TOP 20000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE SEX = 'M' AND CONDITION LIKE '%Vitamin D Deficiency%' AND CAST(numericAge AS INT) BETWEEN 10 AND 20;"""
    },
    {
        "question": "Give 10000 patients diagnosed with Hepatitis B between age 25 to 35 who have missed the expected visit or appointment",
        "sql": """SELECT TOP 10000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION LIKE '%Hepatitis B%' AND CAST(numericAge AS INT) BETWEEN 25 AND 35 AND LastVisitDate <= ExpectedVisitDate AND ExpectedVisitDate <= GETDATE();"""
    },
    {
        "question": "Give me top 10 patients with the highest total amount spent",
        "sql": """SELECT TOP 10 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM ORDER BY TotalAmount DESC;"""
    },
    {
        "question": "Show me 20000 female patients with Diabetes aged 40 to 60",
        "sql": """SELECT TOP 20000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE SEX = 'F' AND CONDITION LIKE '%Diabetes%' AND CAST(numericAge AS INT) BETWEEN 40 AND 60;"""
    },
    {
        "question": "I need 10000 patients with more than 5 visits",
        "sql": """SELECT TOP 10000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE TotalVisits > 5;"""
    },
    {
        "question": "20000 patients who visited in the last 30 days",
        "sql": """SELECT TOP 20000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE LastVisitDate >= DATEADD(DAY, -30, GETDATE());"""
    },
    {
        "question": "Give 25000 patients with an average spent above 1000",
        "sql": """SELECT TOP 25000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE AverageTicket > 1000;"""
    },
    {
        "question": "Show me 30000 patients with repeat visits",
        "sql": """SELECT TOP 30000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE REPEAT > 0;"""
    },
    {
        "question": "Give 20000 patients from Bangalore",
        "sql": """SELECT TOP 20000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE Location = 'Bangalore';"""
    },
    {
        "question": "Patients with expected visits in the next 7 days",
        "sql": """SELECT PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE ExpectedVisitDate BETWEEN GETDATE() AND DATEADD(DAY, 7, GETDATE());"""
    },
    {
        "question": "Give me 100 patients details diagnosed with diabetes, aged between 30 and 50, have expected visits within the next 10 days",
        "sql": """SELECT TOP 100 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION LIKE '%Diabetes%' AND numericAge BETWEEN 30 AND 50 AND ExpectedVisitDate BETWEEN GETDATE() AND DATEADD(DAY, 10, GETDATE());"""
    },
    {
        "question": "Give 1000 diabetes patients with age between 30 to 50 whose expected visit date is in next 30 days",
        "sql": """SELECT TOP 1000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION LIKE '%Diabetes%' AND numericAge BETWEEN 30 AND 50 AND ExpectedVisitDate BETWEEN GETDATE() AND DATEADD(DAY, 30, GETDATE());"""
    },
    {
        "question": "Give me 15000 patients with Hypertension aged 50 to 70 who visited in the last 90 days",
        "sql": """SELECT TOP 15000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION LIKE '%Cardiovascular Disease%'  AND CAST(numericAge AS INT) BETWEEN 50 AND 70 AND LastVisitDate >= DATEADD(DAY, -90, GETDATE());"""
    },
    {
        "question": "Give me 10000 patients with Thyroid Disorders who have more than 10 visits",
        "sql": """SELECT TOP 10000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION LIKE '%Thyroid Disorders%' AND TotalVisits > 10;"""
    },
    {
        "question": "20000 female patients with Diabetes who have spent over 1000 in total",
        "sql": """SELECT TOP 20000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE SEX = 'F' AND CONDITION LIKE '%Diabetes%' AND TotalAmount > 1000;"""
    },
    {
        "question": "Give 25000 patients from Orange Diagnostics with General Health Checkup condition",
        "sql": """SELECT TOP 25000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE OrgName = 'Orange Diagnostics' AND CONDITION LIKE '%General Health Checkup%';"""
    },
    {
        "question": "I need 2500 patients diagnosed with diabetes only",
        "sql": """SELECT TOP 2500 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION = 'Diabetes';"""
    },
    {
        "question": "Give me 2500 patients having only thyroid",
        "sql": """SELECT TOP 2500 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION = 'Thyroid Disorders';"""
    },
    {
        "question": "1000 patients diagnosed with only anemia whose expected visits in next 7 days",
        "sql": """SELECT TOP 1000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION = 'Anemia' AND ExpectedVisitDate BETWEEN GETDATE() AND DATEADD(DAY, 7, GETDATE());"""
    },
    {
        "question": "Give me patients who have only 1 health condition",
        "sql": """SELECT TOP 20000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION NOT LIKE '%,%';"""
    },
    {
        "question": "Give me patient who have covid-19 only",
        "sql": """SELECT TOP 20000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION = 'COVID-19';"""
    },
    {
        "question": "Show me 2000 female diebetic patients who has email address",
        "sql": """SELECT TOP 2000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE WHERE SEX = 'F' AND CONDITION LIKE '%Diabetes%' AND EMail != '';"""
    },
    {
        "question": "Give me latest 100 patients with diabetes only medical condition to recommend next tests",
        "sql": """SELECT TOP 100 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION = 'Diabetes';"""
    },
    {
        "question": "Give me 10000 cancer patient details",
        "sql": """SELECT TOP 10000 PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION LIKE '%cancer%';"""
    },
    {
        "question": "Give me all Patients who are suffering with vitamin deficiency and are in age of 20 to 40 and have not visited since last 6 months",
        "sql": """SELECT PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION LIKE '%Vitamin Deficiency%' AND CAST(numericAge AS INT) BETWEEN 20 AND 40 AND DATEDIFF(DAY, FirstVisitDate, CURRENT_TIMESTAMP) >= 183;"""
    },
    {
        "question": "Give me all female patients with diabetes only condition and age between 40 to 60 having expected visit date in next 7 days",
        "sql": """SELECT PatientNumber,PNAME,OrgName,Location,EMail,SEX,Age,MobileNumber,CONDITION,REPEAT,FirstVisitDate,LastVisitDate,ExpectedVisitDate,TotalVisits,TotalAmount,AverageTicket FROM VIEW_PATIENT_SUM WHERE CONDITION = 'Diabetes' AND SEX = 'F' AND numericAge BETWEEN 40 AND 60 AND ExpectedVisitDate BETWEEN GETDATE() AND DATEADD(DAY, 7, GETDATE());"""
    }
    
]

# Train queries with duplicate checking
try:
    for query in training_queries:
        # Train the query directly without duplicate check
        vn.train(question=query["question"], sql=query["sql"])
        logger.info("Trained query: %s", query["question"])
    logger.info("Vanna training completed")
except Exception as e:
    logger.error("Query training failed: %s", str(e))
    raise

# Log ChromaDB size
db_size = 0
if os.path.exists('./chroma_db'):
    db_size = sum(os.path.getsize(os.path.join('./chroma_db', f)) for f in os.listdir('./chroma_db') if os.path.isfile(os.path.join('./chroma_db', f)))
logger.info("ChromaDB size after training: %.2f MB", db_size / (1024 * 1024))