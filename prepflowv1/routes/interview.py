from flask import Blueprint, request, jsonify, session
import json, os, re
import requests as http_requests
from ..models.database import get_db
interview_bp = Blueprint('interview', __name__)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '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')
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── AI CALL ────────────────────────────────────────────────────────────────────
def call_ai_api(prompt: str, system: str = "") -> str:
    key = os.environ.get('GROQ_API_KEY', GROQ_API_KEY).strip()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = http_requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "max_tokens": 4096, "temperature": 0.7},
            timeout=60
        )
        try:
            body = resp.json()
        except Exception:
            return f"AI Error: Cannot parse response (HTTP {resp.status_code})"

        if resp.status_code != 200:
            err = ""
            if isinstance(body, dict):
                err_obj = body.get("error", {})
                err = err_obj.get("message", str(err_obj)) if isinstance(err_obj, dict) else str(err_obj)
            return f"AI Error: HTTP {resp.status_code} — {err or str(body)[:200]}"

        try:
            choices = body.get("choices", [])
            if not choices or not isinstance(choices, list):
                return f"AI Error: No choices in response"
            message = choices[0].get("message", {})
            if not isinstance(message, dict):
                return f"AI Error: Bad message format"
            content = message.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            print(f"[Groq RAW] {repr(content[:400])}")
            return content
        except Exception as e:
            return f"AI Error: Extract failed — {e}"

    except http_requests.exceptions.ConnectionError:
        return "AI Error: Cannot connect to Groq"
    except http_requests.exceptions.Timeout:
        return "AI Error: Request timed out"
    except Exception as e:
        return f"AI Error: {type(e).__name__}: {e}"


# ── JSON EXTRACTION ────────────────────────────────────────────────────────────
def _extract_block(s, open_ch, close_ch):
    depth, start, in_str, esc = 0, None, False, False
    for i, ch in enumerate(s):
        if esc:            esc = False; continue
        if ch == '\\' and in_str: esc = True; continue
        if ch == '"':      in_str = not in_str; continue
        if in_str:         continue
        if ch == open_ch:
            if depth == 0: start = i
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0 and start is not None:
                return s[start:i+1]
    return None


def parse_as(text, expected_type):
    if not text or not isinstance(text, str):
        return None
    cleaned = text.strip()
    for fence in ['```json', '```JSON', '```']:
        cleaned = cleaned.replace(fence, '')
    cleaned = cleaned.strip()
    candidates = [cleaned]
    obj = _extract_block(cleaned, '{', '}')
    if obj: candidates.append(obj)
    arr = _extract_block(cleaned, '[', ']')
    if arr: candidates.append(arr)
    for c in candidates:
        try:
            parsed = json.loads(c)
            if isinstance(parsed, expected_type):
                return parsed
        except Exception:
            pass
    return None


def to_int_score(val):
    try: return max(0, min(10, int(float(str(val)))))
    except: return 5


# ── QUESTION GENERATION ────────────────────────────────────────────────────────
def generate_questions(role, topic, difficulty, count=5):
    system = (
        "You are a senior technical interviewer. "
        "Reply with ONLY a valid JSON array. No markdown. No explanation. "
        "Start your response with [ and end with ]."
    )
    prompt = (
        f"Generate exactly {count} {difficulty}-level interview questions "
        f"for a {role} about {topic}.\n"
        f'Each item must have: "question", "type" (technical|behavioral|situational), "hint".\n'
        f"Reply with ONLY the JSON array, nothing else."
    )
    raw = call_ai_api(prompt, system)
    if not raw.startswith("AI Error:"):
        parsed = parse_as(raw, list)
        if parsed:
            out = [
                {"question": str(q.get("question", "")),
                 "type":     str(q.get("type", "technical")),
                 "hint":     str(q.get("hint", ""))}
                for q in parsed if isinstance(q, dict) and q.get("question")
            ]
            if out:
                return out[:count]
    print(f"[AI] Fallback questions. raw={raw[:150]}")
    return _fallback_questions(role, topic, difficulty, count)


def _fallback_questions(role, topic, difficulty, count):
    bank = [
        {"question": f"Explain the core concepts of {topic} and a real project where you applied them.", "type":"technical",   "hint":"Name a real project with measurable outcomes."},
        {"question": f"What is the hardest problem you solved as a {role}? Walk through your approach.", "type":"behavioral",  "hint":"Use STAR: Situation, Task, Action, Result."},
        {"question": f"How do you stay current with {topic} developments?",                              "type":"situational", "hint":"Mention communities, papers, courses."},
        {"question": "Describe a time you had to learn a new technology quickly under pressure.",        "type":"behavioral",  "hint":"Focus on learning strategy and outcome."},
        {"question": f"Design a scalable {topic} system handling 10 million users.",                     "type":"technical",   "hint":"Architecture, caching, databases, load balancing."},
        {"question": f"What are common pitfalls in {topic} and how do you prevent them?",                "type":"technical",   "hint":"Name 3 specific pitfalls with solutions."},
        {"question": "Tell me about a time you disagreed with your team on a technical decision.",      "type":"behavioral",  "hint":"Focus on communication and outcome."},
        {"question": f"How do you debug a complex {topic} issue in an unfamiliar codebase?",             "type":"situational", "hint":"Walk through your systematic debugging process."},
        {"question": f"What metrics would you track after shipping a new {topic} feature?",              "type":"technical",   "hint":"Business, performance, and user metrics."},
        {"question": f"Describe your ideal development workflow as a {role}.",                           "type":"behavioral",  "hint":"Testing, code review, CI/CD, documentation."},
    ]
    return bank[:count]


# ── EVALUATE ANSWER ────────────────────────────────────────────────────────────
def evaluate_answer(question, answer, role):
    if len(answer.strip()) < 10:
        return {
            "score": 1,
            "feedback": "Your answer is too short. Please write a detailed response with at least a few sentences.",
            "strengths": [],
            "improvements": ["Write 3-5 detailed sentences", "Include specific examples", "Use STAR method for behavioral questions"],
            "model_answer": ""
        }

    system = (
        "You are a senior technical interviewer evaluating a candidate. "
        "Reply with ONLY a valid JSON object. No markdown. No explanation. "
        "Start your response with { and end with }."
    )
    prompt = (
        f"Evaluate this interview answer.\n\n"
        f"Role: {role}\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        f"Score from 0 to 10 where: 0-3=poor, 4-6=average, 7-8=good, 9-10=excellent.\n\n"
        f"Reply with ONLY this JSON object:\n"
        + '{"score":7,"feedback":"your detailed assessment here","strengths":["strength 1","strength 2"],"improvements":["improvement 1","improvement 2"],"model_answer":"what an ideal answer would say"}'
    )

    raw = call_ai_api(prompt, system)
    print(f"[evaluate] raw={repr(raw[:300])}")

    if raw.startswith("AI Error:"):
        return {"score": 5, "feedback": f"AI error: {raw}",
                "strengths": [], "improvements": [], "model_answer": ""}

    parsed = parse_as(raw, dict)
    if parsed and "score" in parsed:
        return {
            "score":        to_int_score(parsed.get("score", 5)),
            "feedback":     str(parsed.get("feedback", "Good attempt.")),
            "strengths":    [str(s) for s in parsed.get("strengths", []) if s],
            "improvements": [str(s) for s in parsed.get("improvements", []) if s],
            "model_answer": str(parsed.get("model_answer", "")),
        }

    # Prose fallback
    print(f"[AI] Prose fallback. raw={repr(raw[:300])}")
    m = re.search(r'\b(10|[0-9])\s*(?:/\s*10|\s+out\s+of\s+10)?', raw, re.IGNORECASE)
    score = to_int_score(m.group(1)) if m else 5
    return {
        "score": score,
        "feedback": raw.strip()[:600] if raw.strip() else "Could not parse response.",
        "strengths": [],
        "improvements": ["Submit again for structured feedback"],
        "model_answer": ""
    }


# ── ROUTES ─────────────────────────────────────────────────────────────────────
@interview_bp.route('/api/interview/start', methods=['POST'])
def start_interview():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    data       = request.get_json() or {}
    role       = data.get('role', 'Software Engineer')
    topic      = data.get('topic', 'Python')
    difficulty = data.get('difficulty', 'medium')
    count      = int(data.get('count', 5))
    questions  = generate_questions(role, topic, difficulty, count)
    db  = get_db()
    cur = db.execute(
        'INSERT INTO interviews (user_id,role,topic,difficulty,total_questions,interview_type) VALUES (?,?,?,?,?,?)',
        (session['user_id'], role, topic, difficulty, len(questions), 'standard'))
    interview_id = cur.lastrowid
    db.commit(); db.close()
    return jsonify({'interview_id': interview_id, 'questions': questions, 'total': len(questions)})


@interview_bp.route('/api/interview/submit', methods=['POST'])
def submit_answer():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    data         = request.get_json() or {}
    interview_id = data.get('interview_id')
    question     = data.get('question', '')
    answer       = data.get('answer', '')
    role         = data.get('role', 'Software Engineer')
    if not answer.strip():
        return jsonify({'error': 'Answer cannot be empty'}), 400
    ev = evaluate_answer(question, answer, role)
    db = get_db()
    db.execute('INSERT INTO answers (interview_id,question,answer,feedback,score) VALUES (?,?,?,?,?)',
               (interview_id, question, answer, json.dumps(ev), ev.get('score', 0)))
    db.commit(); db.close()
    return jsonify({'evaluation': ev})


@interview_bp.route('/api/interview/end', methods=['POST'])
def end_interview():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    data         = request.get_json() or {}
    interview_id = data.get('interview_id')
    db      = get_db()
    answers = db.execute('SELECT score FROM answers WHERE interview_id=?', (interview_id,)).fetchall()
    avg     = round(sum(a['score'] for a in answers) / len(answers), 2) if answers else 0
    db.execute('UPDATE interviews SET score=?,completed=1 WHERE id=?', (avg, interview_id))
    db.commit()
    interview = db.execute('SELECT * FROM interviews WHERE id=?', (interview_id,)).fetchone()
    db.close()
    return jsonify({'score': avg, 'interview': dict(interview)})


@interview_bp.route('/api/interview/history', methods=['GET'])
def get_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    db   = get_db()
    rows = db.execute('SELECT * FROM interviews WHERE user_id=? ORDER BY date DESC LIMIT 20',
                      (session['user_id'],)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@interview_bp.route('/api/interview/<int:interview_id>/answers', methods=['GET'])
def get_answers(interview_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    db      = get_db()
    answers = db.execute('SELECT * FROM answers WHERE interview_id=?', (interview_id,)).fetchall()
    db.close()
    result = []
    for a in answers:
        row = dict(a)
        try: row['feedback_parsed'] = json.loads(row['feedback'])
        except: row['feedback_parsed'] = {'feedback': row['feedback']}
        result.append(row)
    return jsonify(result)


# ── CODING ─────────────────────────────────────────────────────────────────────
@interview_bp.route('/api/coding/evaluate', methods=['POST'])
def evaluate_code():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    data     = request.get_json() or {}
    code     = data.get('code', '')
    problem  = data.get('problem', '')
    language = data.get('language', 'python')

    system = (
        "You are a senior software engineer reviewing code. "
        "Reply with ONLY a valid JSON object. No markdown. No explanation. "
        "Start with { and end with }."
    )
    prompt = (
        f"Review this {language} solution for: {problem}\n\n"
        f"```{language}\n{code}\n```\n\n"
        f"Reply with ONLY this JSON:\n"
        + '{"score":7,"correctness":true,"feedback":"detailed review","time_complexity":"O(n)","space_complexity":"O(1)","improvements":["tip 1","tip 2"],"optimized_solution":"optimized code here"}'
    )
    raw = call_ai_api(prompt, system)
    if not raw.startswith("AI Error:"):
        parsed = parse_as(raw, dict)
        if parsed and 'score' in parsed:
            return jsonify({
                "score":              to_int_score(parsed.get('score', 5)),
                "correctness":        bool(parsed.get('correctness', True)),
                "feedback":           str(parsed.get('feedback', '')),
                "time_complexity":    str(parsed.get('time_complexity', 'N/A')),
                "space_complexity":   str(parsed.get('space_complexity', 'N/A')),
                "improvements":       [str(x) for x in parsed.get('improvements', []) if x],
                "optimized_solution": str(parsed.get('optimized_solution', '')),
            })
    return jsonify({"score":5,"correctness":True,"feedback":"Could not evaluate. Try again.",
                    "time_complexity":"N/A","space_complexity":"N/A","improvements":[],"optimized_solution":""})


def _fallback_coding_problems(topic, difficulty):
    banks = {
        "arrays":[
            {"id":1,"title":"Two Sum","difficulty":difficulty,"description":"Given an integer array and a target, return indices of two numbers that add up to target.","examples":[{"input":"nums=[2,7,11,15], target=9","output":"[0,1]"},{"input":"nums=[3,2,4], target=6","output":"[1,2]"}],"constraints":["Exactly one valid answer"],"tags":["arrays","hash-map"]},
            {"id":2,"title":"Maximum Subarray","difficulty":difficulty,"description":"Find the contiguous subarray with the largest sum.","examples":[{"input":"nums=[-2,1,-3,4,-1,2,1,-5,4]","output":"6"}],"constraints":["1<=nums.length<=10^5"],"tags":["arrays","kadane"]},
            {"id":3,"title":"Product Except Self","difficulty":difficulty,"description":"Return array where answer[i] = product of all except nums[i]. No division, O(n).","examples":[{"input":"nums=[1,2,3,4]","output":"[24,12,8,6]"}],"constraints":["No division","O(n)"],"tags":["arrays","prefix"]},
        ],
        "strings":[
            {"id":1,"title":"Valid Anagram","difficulty":difficulty,"description":"Return true if t is an anagram of s.","examples":[{"input":"s='anagram',t='nagaram'","output":"true"}],"constraints":["lowercase only"],"tags":["strings","hash-map"]},
            {"id":2,"title":"Longest Without Repeating","difficulty":difficulty,"description":"Find length of longest substring without repeating characters.","examples":[{"input":"s='abcabcbb'","output":"3"}],"constraints":["0<=s.length<=5*10^4"],"tags":["strings","sliding-window"]},
            {"id":3,"title":"Group Anagrams","difficulty":difficulty,"description":"Group strings that are anagrams of each other.","examples":[{"input":"['eat','tea','tan','ate','nat','bat']","output":"[['eat','tea','ate'],['tan','nat'],['bat']]"}],"constraints":["1<=strs.length<=10^4"],"tags":["strings","hash-map"]},
        ],
        "dynamic programming":[
            {"id":1,"title":"Climbing Stairs","difficulty":difficulty,"description":"Climb 1 or 2 steps. How many distinct ways to reach the top?","examples":[{"input":"n=5","output":"8"}],"constraints":["1<=n<=45"],"tags":["dp","fibonacci"]},
            {"id":2,"title":"Coin Change","difficulty":difficulty,"description":"Minimum coins to make amount. Return -1 if impossible.","examples":[{"input":"coins=[1,2,5],amount=11","output":"3"}],"constraints":["1<=coins.length<=12"],"tags":["dp"]},
            {"id":3,"title":"Longest Increasing Subsequence","difficulty":difficulty,"description":"Length of longest strictly increasing subsequence.","examples":[{"input":"nums=[10,9,2,5,3,7,101,18]","output":"4"}],"constraints":["1<=nums.length<=2500"],"tags":["dp","binary-search"]},
        ],
        "trees":[
            {"id":1,"title":"Max Depth Binary Tree","difficulty":difficulty,"description":"Return maximum depth of binary tree.","examples":[{"input":"[3,9,20,null,null,15,7]","output":"3"}],"constraints":["0<=nodes<=10^4"],"tags":["trees","dfs"]},
            {"id":2,"title":"Validate BST","difficulty":difficulty,"description":"Determine if binary tree is a valid BST.","examples":[{"input":"[2,1,3]","output":"true"},{"input":"[5,1,4,null,null,3,6]","output":"false"}],"constraints":["unique values"],"tags":["trees","dfs"]},
            {"id":3,"title":"Level Order Traversal","difficulty":difficulty,"description":"Return level-order traversal as list of lists.","examples":[{"input":"[3,9,20,null,null,15,7]","output":"[[3],[9,20],[15,7]]"}],"constraints":["0<=nodes<=2000"],"tags":["trees","bfs"]},
        ],
        "graphs":[
            {"id":1,"title":"Number of Islands","difficulty":difficulty,"description":"Count islands in binary grid.","examples":[{"input":"[['1','1','0'],['0','1','0'],['0','0','1']]","output":"2"}],"constraints":["1<=m,n<=300"],"tags":["graphs","dfs"]},
            {"id":2,"title":"Course Schedule","difficulty":difficulty,"description":"Can you finish all courses? Detect cycle.","examples":[{"input":"n=2,[[1,0]]","output":"true"}],"constraints":["1<=n<=2000"],"tags":["graphs","topological-sort"]},
            {"id":3,"title":"Clone Graph","difficulty":difficulty,"description":"Deep copy a connected undirected graph.","examples":[{"input":"[[2,4],[1,3],[2,4],[1,3]]","output":"[[2,4],[1,3],[2,4],[1,3]]"}],"constraints":["0<=nodes<=100"],"tags":["graphs","dfs"]},
        ],
        "sorting":[
            {"id":1,"title":"Kth Largest Element","difficulty":difficulty,"description":"Find kth largest element in unsorted array.","examples":[{"input":"nums=[3,2,1,5,6,4],k=2","output":"5"}],"constraints":["1<=k<=nums.length"],"tags":["sorting","heap"]},
            {"id":2,"title":"Sort Colors","difficulty":difficulty,"description":"Sort 0s,1s,2s in-place.","examples":[{"input":"[2,0,2,1,1,0]","output":"[0,0,1,1,2,2]"}],"constraints":["in-place","O(n)"],"tags":["sorting","two-pointers"]},
            {"id":3,"title":"Merge Intervals","difficulty":difficulty,"description":"Merge all overlapping intervals.","examples":[{"input":"[[1,3],[2,6],[8,10]]","output":"[[1,6],[8,10]]"}],"constraints":["1<=intervals.length<=10^4"],"tags":["sorting","intervals"]},
        ],
        "linked lists":[
            {"id":1,"title":"Reverse Linked List","difficulty":difficulty,"description":"Reverse a singly linked list.","examples":[{"input":"1->2->3->4->5","output":"5->4->3->2->1"}],"constraints":["0<=nodes<=5000"],"tags":["linked-list"]},
            {"id":2,"title":"Detect Cycle","difficulty":difficulty,"description":"Detect if linked list has cycle using O(1) space.","examples":[{"input":"[3,2,0,-4],pos=1","output":"true"}],"constraints":["O(1) space"],"tags":["linked-list","floyd"]},
            {"id":3,"title":"Merge Two Sorted Lists","difficulty":difficulty,"description":"Merge two sorted linked lists into one.","examples":[{"input":"1->2->4 and 1->3->4","output":"1->1->2->3->4->4"}],"constraints":["0<=nodes<=50"],"tags":["linked-list"]},
        ],
    }
    return banks.get(topic.lower(), banks["arrays"])


@interview_bp.route('/api/coding/problems', methods=['GET'])
def get_coding_problems():
    difficulty = request.args.get('difficulty', 'medium')
    topic      = request.args.get('topic', 'arrays')
    system = (
        "You are a coding interview expert. "
        "Reply with ONLY a valid JSON array. No markdown. No explanation. "
        "Start with [ and end with ]."
    )
    prompt = (
        f"Generate 3 {difficulty} LeetCode-style coding problems on: {topic}\n"
        f"Reply with ONLY the JSON array:\n"
        f'[{{"id":1,"title":"...","difficulty":"{difficulty}","description":"...","examples":[{{"input":"...","output":"..."}}],"constraints":["..."],"tags":["..."]}}]'
    )
    raw = call_ai_api(prompt, system)
    if not raw.startswith("AI Error:"):
        parsed = parse_as(raw, list)
        if parsed:
            valid = []
            for i, p in enumerate(parsed):
                if isinstance(p, dict) and p.get('title') and p.get('description'):
                    p.setdefault('id', i+1); p.setdefault('difficulty', difficulty)
                    p.setdefault('examples', []); p.setdefault('constraints', []); p.setdefault('tags', [topic])
                    valid.append(p)
            if valid:
                return jsonify(valid)
    return jsonify(_fallback_coding_problems(topic, difficulty))
