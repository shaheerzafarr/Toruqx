import os
import csv
import time
import json
import requests
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load env variables from root folder
load_dotenv(dotenv_path=".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_BASE_URL = "http://localhost:8000/api/v1"
CSV_PATH = "evaluation/golden_dataset.csv"
REPORT_PATH = "evaluation/report.json"

if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    raise ValueError("GEMINI_API_KEY is not configured in .env file.")

# Initialize the Gemini Client for judge evaluations
client = genai.Client(api_key=GEMINI_API_KEY)

def judge_answer(question: str, ground_truth: str, generated_answer: str) -> dict:
    """
    Leverages Gemini as a judge to grade accuracy and correctness on a 1-5 scale.
    Features automatic retry on rate limits (429).
    """
    prompt = f"""You are an expert AI evaluator. Compare the generated answer from a RAG system against the ground truth reference answer.

Question: {question}
Ground Truth: {ground_truth}
Generated Answer: {generated_answer}

Rate the accuracy and correctness of the generated answer compared to the ground truth.
Score the response on a scale of 1 to 5:
1: Completely wrong, irrelevant, or hallucinatory.
2: Mostly wrong, missing core facts, or major errors.
3: Partially correct but missing minor details or contains slight inaccuracies.
4: Mostly correct, capturing the core answer accurately with no errors.
5: Completely correct and fully accurate, matching the ground truth's meaning.

Format your output strictly as a single JSON object with the following fields:
{{
    "score": <int>,
    "reason": "<str>"
}}
Do not output markdown block formatting (like ```json). Return ONLY the raw JSON string."""

    max_retries = 3
    retry_delay = 15.0
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )
            cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned_text)
            return result
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                print(f"  [Judge Rate Limit] Hit 429. Waiting {retry_delay}s to retry judge...")
                time.sleep(retry_delay)
            else:
                return {"score": 1, "reason": f"Evaluation extraction failed: {str(e)}"}

def main():
    print("==================================================")
    print("  Enterprise RAG Knowledge Assistant Evaluator    ")
    print("==================================================")
    
    # 1. Authenticate and create a chat session
    import random
    eval_username = f"evaluator_{random.randint(1000, 9999)}"
    eval_password = "evaluator_password_123"
    token = None
    
    print("[1/5] Authenticating with backend...")
    try:
        signup_resp = requests.post(f"{API_BASE_URL}/auth/signup", json={"username": eval_username, "password": eval_password})
        if signup_resp.status_code == 201:
            token = signup_resp.json()["access_token"]
        else:
            # Fallback to login
            login_resp = requests.post(f"{API_BASE_URL}/auth/login", json={"username": eval_username, "password": eval_password})
            login_resp.raise_for_status()
            token = login_resp.json()["access_token"]
        print("Successfully authenticated and obtained JWT token.")
    except Exception as e:
        print(f"Error during authentication: {str(e)}")
        return

    print("Initializing evaluation chat session...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        sess_resp = requests.post(f"{API_BASE_URL}/chat/session", json={"title": "Evaluation Session"}, headers=headers)
        sess_resp.raise_for_status()
        session_id = sess_resp.json()["id"]
        print(f"Session initialized with ID: {session_id}")
    except Exception as e:
        print(f"Error: Failed to connect to FastAPI backend at {API_BASE_URL}. Ensure uvicorn is running.")
        print(str(e))
        return

    # 2. Read Golden Dataset
    print("\n[2/5] Loading golden dataset...")
    questions = []
    with open(CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append((row["question"], row["ground_truth"]))
    
    total_q = len(questions)
    print(f"Loaded {total_q} questions for evaluation.")

    # 3. Loop and evaluate
    print("\n[3/5] Running RAG queries and judging responses...")
    results = []
    total_score = 0
    total_latency = 0
    
    for idx, (question, ground_truth) in enumerate(questions):
        print(f"\nEvaluating Q{idx+1}/{total_q}: '{question}'")
        
        # Call RAG API
        start_time = time.time()
        try:
            msg_resp = requests.post(
                f"{API_BASE_URL}/chat/session/{session_id}/message",
                json={"query": question, "limit": 3},
                headers=headers
            )
            msg_resp.raise_for_status()
            res_json = msg_resp.json()
            generated_answer = res_json["answer"]
            sources = res_json["sources"]
        except Exception as e:
            generated_answer = f"Error querying RAG backend: {str(e)}"
            sources = []
            
        latency = time.time() - start_time
        total_latency += latency
        
        # Check source recall (expected file ingested was enterprise_rag_specs.txt)
        source_recall = 0
        if any("enterprise_rag_specs.txt" in s.get("filename", "") for s in sources):
            source_recall = 1
            
        # Call Judge LLM
        judge = judge_answer(question, ground_truth, generated_answer)
        score = judge.get("score", 1)
        reason = judge.get("reason", "No reason provided.")
        total_score += score
        
        print(f"  RAG Answer: {generated_answer}")
        print(f"  Judge Score: {score}/5")
        print(f"  Judge Reason: {reason}")
        print(f"  Source Recall: {source_recall} | Latency: {latency:.3f}s")
        
        results.append({
            "question_index": idx + 1,
            "question": question,
            "ground_truth": ground_truth,
            "generated_answer": generated_answer,
            "sources": [s["filename"] for s in sources],
            "score": score,
            "reason": reason,
            "source_recall": source_recall,
            "latency_seconds": latency
        })

        # Free-tier rate limiting safety delay (5 RPM limit = 12 seconds per request cycle)
        if idx < total_q - 1:
            print("  Waiting 12 seconds for rate limit compliance...")
            time.sleep(12)

    # 4. Compute metrics
    avg_accuracy = (total_score / (total_q * 5)) * 100
    avg_latency = total_latency / total_q
    avg_score = total_score / total_q
    avg_recall = sum(r["source_recall"] for r in results) / total_q

    summary = {
        "total_questions": total_q,
        "average_score": round(avg_score, 2),
        "average_correctness_percentage": round(avg_accuracy, 2),
        "average_source_recall": round(avg_recall, 2),
        "average_latency_seconds": round(avg_latency, 3),
    }

    # 5. Output report
    report = {
        "summary": summary,
        "evaluations": results
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as rf:
        json.dump(report, rf, indent=2)

    print("\n==================================================")
    print("               EVALUATION SUMMARY                 ")
    print("==================================================")
    print(f"Total Questions Evaluated : {total_q}")
    print(f"Average Correctness Score : {avg_score:.2f} / 5.00 ({avg_accuracy:.1f}%)")
    print(f"Average Source Recall     : {avg_recall * 100:.1f}%")
    print(f"Average Response Latency  : {avg_latency:.3f} seconds")
    print(f"Detailed report saved to: {REPORT_PATH}")
    print("==================================================")

if __name__ == "__main__":
    main()
